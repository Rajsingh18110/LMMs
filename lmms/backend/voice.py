import math
import time
import sys
import shutil
import threading
import subprocess
import os
import queue
import re

_stop_event = threading.Event()
_anim_thread = None
_status_text = "Listening..."
_heard_text = ""     # What the user said (shown on screen during speaking)
_tts_queue = queue.Queue()

import random

ROWS = 6
GH = ROWS * 4
MAX_W = 110
TH = 0.30

BIT = {(0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
       (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80}

LAYERS = [
    (1.2,  1.00, 1.00, 1.00, 0.70),
    (1.9, -0.70, 0.65, 0.65, 0.60),
    (0.8,  0.50, 0.85, 0.55, 0.60),
    (2.6,  0.40, 0.40, 0.45, 0.55),
]

class VoiceLevel:
    def __init__(self):
        self.level, self.target, self.next_change = 0.7, 0.7, 0.0

    def update(self, t, dt):
        if t >= self.next_change:
            self.target = random.choice([0.55, 0.7, 0.85, 1.0, 0.9, 0.75])
            self.next_change = t + random.uniform(0.3, 0.9)
        rate = 9.0 if self.target > self.level else 2.5
        self.level += (self.target - self.level) * min(1.0, rate * dt)
        return self.level

def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def build_grid(gw, phases, level):
    val = [[0.0] * gw for _ in range(GH)]
    cy = GH / 2
    A = GH / 2 - 1.0
    fade = [smoothstep(min(x / (gw * 0.10), (gw - 1 - x) / (gw * 0.10))) for x in range(gw)]
    env = [math.sin(math.pi * x / (gw - 1)) ** 1.2 for x in range(gw)]

    for (cycles, _, amp, bright, sigma), ph in zip(LAYERS, phases):
        w = 2 * math.pi * cycles / gw
        ys = [cy + A * amp * level * env[x] *
              (math.sin(x * w + ph) + 0.2 * math.sin(2 * x * w - ph * 1.4)) / 1.2
              for x in range(gw)]
        for x in range(gw):
            b = bright * fade[x]
            if b < 0.05:
                continue
            slope = (ys[min(x + 1, gw - 1)] - ys[max(x - 1, 0)]) / 2
            k = math.sqrt(1 + slope * slope)
            reach = int(2.2 * sigma * k) + 2
            yc = ys[x]
            for py in range(max(0, int(yc) - reach), min(GH, int(yc) + reach + 1)):
                d = (py + 0.5 - yc) / k
                val[py][x] += b * (math.exp(-(d / sigma) ** 2) + 0.15 * math.exp(-(d / (sigma * 3)) ** 2))
    return val

def render_wave(val, W):
    lines = []
    for row in range(ROWS):
        out, last = [], None
        for col in range(W):
            bits, m = 0, 0.0
            for dx in (0, 1):
                x = col * 2 + dx
                for dy in range(4):
                    v = val[row * 4 + dy][x]
                    if v > TH:
                        bits |= BIT[(dx, dy)]
                        if v > m:
                            m = v
            if bits:
                g = int(70 + 185 * min(1.0, m)) // 8 * 8
                if g != last:
                    out.append(f"\033[38;2;{g};{g};{g}m")
                    last = g
                out.append(chr(0x2800 + bits))
            else:
                out.append(" ")
        out.append("\033[0m")
        lines.append("".join(out))
    return "\n".join(lines)

def animate_siri_wave_slim():
    global _status_text
    
    # Enable Alternate Screen Buffer and hide cursor
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    
    FPS = 60
    voice = VoiceLevel()
    phases = [0.0] * len(LAYERS)
    t0 = last_t = time.perf_counter()
    
    # Pre-build the blank frame template
    prev_lines_count = 0
    
    try:
        while not _stop_event.is_set():
            columns, lines = shutil.get_terminal_size()
            W = max(40, min(MAX_W, columns - 1))
            pad = " " * max(0, (columns - W) // 2)
            
            now = time.perf_counter()
            dt, last_t = now - last_t, now
            level = voice.update(now - t0, dt)
            for i, layer in enumerate(LAYERS):
                phases[i] += layer[1] * (0.7 + level) * dt * 3.0
                
            frame = render_wave(build_grid(W * 2, phases, level), W)
            frame_lines = [pad + ln for ln in frame.split("\n")]
            
            # --- 2-line status: line1 = heard, line2 = speaking ---
            heard_line = f"\033[2;37m❓ You: {_heard_text}\033[0m" if _heard_text else ""
            status_line = f"\033[1;36m🔊 {_status_text}\033[0m"
            
            # Text in center, wave at bottom
            top_padding = max(0, (lines // 2) - 5)
            top_part_lines = (
                ["" ] * top_padding +
                [heard_line.center(columns + 20) if _heard_text else ""] +  # +20 for ANSI codes
                [status_line.center(columns + 20)]                          # +20 for ANSI codes
            )
            rem_lines = lines - len(top_part_lines) - ROWS - 1
            if rem_lines > 0:
                top_part_lines += [""] * rem_lines
                
            all_lines = top_part_lines + frame_lines
            
            # NO \033[2J ! Move cursor to home, overwrite each line → zero flicker
            out_parts = ["\033[H"]
            for ln in all_lines:
                # Pad line to full width to erase leftover chars, then move to next line
                out_parts.append(ln + "\033[K\n")
            sys.stdout.write("".join(out_parts))
            sys.stdout.flush()
            
            sleep_time = (1.0 / FPS) - (time.perf_counter() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
    finally:
        # Disable Alternate Screen Buffer and restore cursor
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()

# Common Hinglish words that English TTS mispronounces
_HINGLISH_WORDS = {
    r'\bhai\b', r'\bbhai\b', r'\bnahin\b', r'\bnahi\b', r'\bhaan\b',
    r'\bkya\b', r'\bkaro\b', r'\bkarna\b', r'\bthik\b', r'\btheek\b',
    r'\bacha\b', r'\bacha\b', r'\bsahi\b', r'\bsamajh\b', r'\bwala\b',
    r'\bwali\b', r'\bkuch\b', r'\bkuchh\b', r'\byaar\b', r'\bdost\b',
    r'\babhi\b', r'\bwaise\b', r'\bphir\b', r'\bbaad\b', r'\bpehle\b',
    r'\bmatlab\b', r'\blagta\b', r'\blagti\b', r'\bbal\b', r'\bbol\b',
    r'\bbata\b', r'\bpata\b', r'\bkab\b', r'\bkaise\b', r'\bkyun\b',
    r'\bjab\b', r'\btab\b', r'\bwoh\b', r'\bwo\b', r'\byeh\b', r'\bye\b',
    r'\baur\b', r'\bnahi\b', r'\bto\b', r'\bhi\b', r'\bhe\b', r'\bna\b',
}

_DEVANAGARI_RANGE = re.compile(r'[\u0900-\u097F]')
_HINGLISH_PAT = re.compile('|'.join(_HINGLISH_WORDS), re.IGNORECASE)

def detect_language(text):
    """Returns 'hindi' if text is Hindi/Hinglish, else 'english'."""
    if _DEVANAGARI_RANGE.search(text):
        return 'hindi'
    words = text.split()
    if len(words) == 0:
        return 'english'
    matches = len(_HINGLISH_PAT.findall(text))
    # If more than 25% of words are Hinglish, use Hindi voice
    if matches / max(len(words), 1) >= 0.25:
        return 'hindi'
    return 'english'

def clean_text_for_tts(text):
    text = text.replace("*", "").replace("#", "").replace("`", "")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove emojis and special unicode that confuse TTS
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002700-\U000027BF]', '', text)
    return text.strip()

_playback_queue = queue.Queue()

def tts_download_worker():
    import uuid
    while not _stop_event.is_set():
        try:
            item = _tts_queue.get(timeout=0.1)
            if item is None:
                _tts_queue.task_done()
                continue
            text, voice = item
            clean_t = clean_text_for_tts(text)
            if not clean_t:
                _tts_queue.task_done()
                continue
                
            # Auto-detect Hindi/Hinglish and pick the right natural voice
            lang = detect_language(clean_t)
            if lang == 'hindi':
                voice_name = "hi-IN-MadhurNeural" if voice == "male" else "hi-IN-SwaraNeural"
            else:
                voice_name = "en-IN-PrabhatNeural" if voice == "male" else "en-IN-NeerjaExpressiveNeural"
            
            tmp_file = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
            
            subprocess.run(
                ["edge-tts", "--voice", voice_name,
                 "--text", clean_t, "--write-media", tmp_file],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            
            _playback_queue.put((tmp_file, text, _tts_queue))
            
        except queue.Empty:
            continue
        except Exception:
            try:
                _tts_queue.task_done()
            except:
                pass

def audio_play_worker():
    global _status_text
    while not _stop_event.is_set():
        try:
            item = _playback_queue.get(timeout=0.1)
            if item is None:
                continue
            tmp_file, text, original_queue = item
            
            # Sync the text on screen with exactly what is being spoken!
            # Truncate long sentences for display
            display_text = text if len(text) <= 60 else text[:57] + "..."
            _status_text = f"Speaking: {display_text}"
            
            try:
                p = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", tmp_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while p.poll() is None:
                    time.sleep(0.05)
                    if _stop_event.is_set():
                        p.terminate()
                        break
            except FileNotFoundError:
                os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
                old_err = sys.stderr
                try:
                    with open(os.devnull, 'w') as f:
                        sys.stderr = f
                        import pygame
                        pygame.mixer.init()
                finally:
                    sys.stderr = old_err
                
                pygame.mixer.music.load(tmp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                    if _stop_event.is_set():
                        pygame.mixer.music.stop()
                        break
                pygame.mixer.quit()
                
            try:
                os.remove(tmp_file)
            except:
                pass
                
            original_queue.task_done()
        except queue.Empty:
            continue
        except Exception:
            try:
                if 'original_queue' in locals():
                    original_queue.task_done()
            except:
                pass

def wait_for_tts():
    # Wait until all tasks in the queue are processed
    _tts_queue.join()

def set_heard_text(text):
    """Set what the user said - shown on screen during AI speaking"""
    global _heard_text
    _heard_text = text

class VoiceSession:
    def __init__(self):
        self.thread = None
        self.tts_dl_thread = None
        self.tts_play_thread = None

    def start_animation(self, text):
        global _stop_event, _anim_thread, _status_text, _heard_text
        _status_text = text
        _heard_text = ""  # Clear heard text on new session
        _stop_event.clear()
        
        while not _tts_queue.empty():
            try:
                _tts_queue.get_nowait()
            except:
                pass
                
        while not _playback_queue.empty():
            try:
                _playback_queue.get_nowait()
            except:
                pass
                
        self.thread = threading.Thread(target=animate_siri_wave_slim, daemon=True)
        self.thread.start()
        _anim_thread = self.thread
        
        self.tts_dl_thread = threading.Thread(target=tts_download_worker, daemon=True)
        self.tts_dl_thread.start()
        
        self.tts_play_thread = threading.Thread(target=audio_play_worker, daemon=True)
        self.tts_play_thread.start()

    def update_status(self, text):
        global _status_text
        _status_text = text
    
    def set_heard(self, text):
        global _heard_text
        _heard_text = text

    def stop_animation(self):
        global _stop_event
        _stop_event.set()
        if self.thread:
            self.thread.join()
        if self.tts_dl_thread:
            self.tts_dl_thread.join()
        if self.tts_play_thread:
            self.tts_play_thread.join()

def play_audio(text, voice="female"):
    _tts_queue.put((text, voice))

def stream_audio(text_chunk, voice="female"):
    _tts_queue.put((text_chunk, voice))
