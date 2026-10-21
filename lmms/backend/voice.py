import math
import time
import sys
import shutil
import threading
import subprocess
import os
import queue
import re
import random
import textwrap
import asyncio

_stop_event = threading.Event()
_anim_thread = None
_status_text = "Listening..."
_heard_text = ""      # What the user said (shown on top in User box)
_ai_text = ""         # Live streaming response from AI (shown in AI box)
_tts_queue = queue.Queue()
_playback_queue = queue.Queue()

ROWS = 6
GH = ROWS * 4
MAX_W = 100
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

def _vis_len(s):
    clean = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', s)
    length = 0
    for ch in clean:
        length += 2 if ord(ch) > 0x2000 else 1
    return length

def _pad_line(line, width):
    v = _vis_len(line)
    if v < width:
        return line + " " * (width - v)
    return line

def _make_box(title, text, width, height=None, border_color="\033[1;36m", title_color="\033[1;37m", text_color="\033[0m"):
    inner_w = max(10, width - 4)
    raw_lines = []
    if text and text.strip():
        for p in text.strip().split("\n"):
            p_strip = p.strip()
            if not p_strip:
                continue
            w = textwrap.wrap(p_strip, width=inner_w)
            raw_lines.extend(w if w else [""])
    else:
        raw_lines = [""]

    if height is not None:
        if len(raw_lines) > height:
            raw_lines = raw_lines[-height:]  # Auto-scroll to show latest streaming text
        elif len(raw_lines) < height:
            raw_lines += [""] * (height - len(raw_lines))

    v_title = _vis_len(title)
    dashes_len = max(0, width - 5 - v_title)
    header = f"{border_color}╭─ {title_color}{title}{border_color} " + "─" * dashes_len + f"╮\033[0m"
    footer = f"{border_color}╰" + "─" * (width - 2) + f"╯\033[0m"
    
    body = []
    for line in raw_lines:
        padded = _pad_line(f"{text_color}{line}\033[0m", inner_w)
        body.append(f"{border_color}│\033[0m {padded} {border_color}│\033[0m")
    return [header] + body + [footer]

def animate_siri_wave_slim():
    global _status_text, _heard_text, _ai_text
    
    # Enable Alternate Screen Buffer and hide cursor
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    
    FPS = 30
    voice = VoiceLevel()
    phases = [0.0] * len(LAYERS)
    t0 = last_t = time.perf_counter()
    
    try:
        while not _stop_event.is_set():
            columns, lines = shutil.get_terminal_size()
            W = max(40, min(MAX_W, columns - 4))
            pad = " " * max(0, (columns - W) // 2)
            
            now = time.perf_counter()
            dt, last_t = now - last_t, now
            
            is_active = ("Speaking" in _status_text) or ("Listening" in _status_text)
            level = voice.update(now - t0, dt) if is_active else 0.15
            for i, layer in enumerate(LAYERS):
                phases[i] += layer[1] * (0.7 + level) * dt * 3.0
                
            frame = render_wave(build_grid(W * 2, phases, level), W)
            frame_lines = [pad + ln for ln in frame.split("\n")]
            
            # --- Gemini Live Layout ---
            # 1. Header
            header_title = "🎙️  LMMs Voice Live"
            header_dashes = max(0, (W - _vis_len(header_title) - 4) // 2)
            header_str = pad + f"\033[1;36m╭{'─' * header_dashes} \033[1;37m{header_title}\033[1;36m {'─' * max(0, W - _vis_len(header_title) - 4 - header_dashes)}╮\033[0m"
            
            # 2. User Box (Top)
            user_display = _heard_text or "Listening to your voice... Speak now and press ENTER"
            user_title = "👤 You"
            user_box_lines = _make_box(user_title, user_display, W, height=2, border_color="\033[1;36m", title_color="\033[1;37m", text_color="\033[0;37m")
            
            # 3. AI Box (Middle)
            if "Speaking" in _status_text:
                ai_title = "🤖 LMMs Assistant  \033[1;32m● Speaking\033[0m"
                border_c = "\033[1;35m"
            elif "Thinking" in _status_text or "Transcribing" in _status_text:
                ai_title = f"🤖 LMMs Assistant  \033[1;33m● {_status_text}\033[0m"
                border_c = "\033[1;33m"
            else:
                ai_title = "🤖 LMMs Assistant  \033[2m● Waiting\033[0m"
                border_c = "\033[2;35m"
                
            # Dynamic height for AI Box based on available terminal height
            fixed_rows = 1 + len(user_box_lines) + ROWS + 3 + 2
            ai_height = max(3, min(14, lines - fixed_rows))
            ai_display = _ai_text or "(Waiting for model response...)"
            ai_box_lines = _make_box(ai_title, ai_display, W, height=ai_height, border_color=border_c, title_color="\033[1;35m", text_color="\033[1;37m")
            
            # 4. Status / Wave section
            status_line = pad + f"\033[1;34m🔊 {_status_text}\033[0m".center(columns)
            footer_line = pad + "\033[2;37m[ Press ENTER to submit speech | Press Ctrl+C to cancel ]\033[0m".center(columns)
            
            # Assemble all lines
            all_lines = (
                [header_str] +
                [pad + ln for ln in user_box_lines] +
                [""] +
                [pad + ln for ln in ai_box_lines] +
                [""] +
                frame_lines +
                [status_line, footer_line]
            )
            
            out_parts = ["\033[H"]
            for ln in all_lines[:lines]:
                out_parts.append(ln + "\033[K\n")
            out_parts.append("\033[J")
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
    r'\bacha\b', r'\bachha\b', r'\bsahi\b', r'\bsamajh\b', r'\bwala\b',
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
    if matches / max(len(words), 1) >= 0.20:
        return 'hindi'
    return 'english'

def clean_text_for_tts(text):
    text = text.replace("*", "").replace("#", "").replace("`", "")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002700-\U000027BF]', '', text)
    return text.strip()

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
            downloaded = False
            
            # 1. Primary: Direct in-process edge_tts (fastest, high quality neural)
            try:
                import edge_tts
                async def _save_edge():
                    comm = edge_tts.Communicate(clean_t, voice_name)
                    await comm.save(tmp_file)
                asyncio.run(_save_edge())
                if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 100:
                    downloaded = True
            except Exception:
                downloaded = False
                
            # 2. Secondary fallback: gTTS
            if not downloaded:
                try:
                    from gtts import gTTS
                    gtts_lang = 'hi' if lang == 'hindi' else 'en'
                    tts = gTTS(clean_t, lang=gtts_lang)
                    tts.save(tmp_file)
                    if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 100:
                        downloaded = True
                except Exception:
                    downloaded = False
            
            if downloaded:
                _playback_queue.put((tmp_file, clean_t, _tts_queue))
            else:
                _tts_queue.task_done()
                
        except queue.Empty:
            continue
        except Exception:
            try:
                _tts_queue.task_done()
            except Exception:
                pass

def audio_play_worker():
    global _status_text
    while not _stop_event.is_set():
        original_queue = None
        try:
            item = _playback_queue.get(timeout=0.1)
            if item is None:
                continue
            tmp_file, text, original_queue = item
            
            display_text = text if len(text) <= 50 else text[:47] + "..."
            _status_text = f"Speaking: {display_text}"
            
            played = False
            # 1. Prefer mpg123 if installed (ultra fast, native audio)
            mpg_bin = shutil.which("mpg123")
            if mpg_bin:
                try:
                    p = subprocess.Popen([mpg_bin, "-q", tmp_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    while p.poll() is None:
                        time.sleep(0.05)
                        if _stop_event.is_set():
                            p.terminate()
                            break
                    played = True
                except Exception:
                    played = False
                    
            # 2. Fallback to ffplay
            if not played:
                ffplay_bin = shutil.which("ffplay")
                if ffplay_bin:
                    try:
                        p = subprocess.Popen([ffplay_bin, "-nodisp", "-autoexit", tmp_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        while p.poll() is None:
                            time.sleep(0.05)
                            if _stop_event.is_set():
                                p.terminate()
                                break
                        played = True
                    except Exception:
                        played = False
                        
            # 3. Fallback to pygame.mixer
            if not played:
                try:
                    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(tmp_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                        if _stop_event.is_set():
                            pygame.mixer.music.stop()
                            break
                    pygame.mixer.quit()
                    played = True
                except Exception:
                    pass
                
            try:
                os.remove(tmp_file)
            except Exception:
                pass
                
            if original_queue is not None:
                original_queue.task_done()
        except queue.Empty:
            continue
        except Exception:
            try:
                if original_queue is not None:
                    original_queue.task_done()
            except Exception:
                pass

def wait_for_tts():
    # Wait until all tasks in the queue are processed
    _tts_queue.join()

def set_heard_text(text):
    """Set what the user said - shown on top in User box"""
    global _heard_text
    _heard_text = text

def set_ai_text(text):
    """Set live AI response text"""
    global _ai_text
    _ai_text = text

class VoiceSession:
    def __init__(self):
        self.thread = None
        self.tts_dl_thread = None
        self.tts_play_thread = None
        self.sentence_buffer = ""

    def start_animation(self, text):
        global _stop_event, _anim_thread, _status_text, _heard_text, _ai_text
        _status_text = text
        _heard_text = ""
        _ai_text = ""
        self.sentence_buffer = ""
        _stop_event.clear()
        
        while not _tts_queue.empty():
            try:
                _tts_queue.get_nowait()
            except Exception:
                pass
                
        while not _playback_queue.empty():
            try:
                _playback_queue.get_nowait()
            except Exception:
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

    def update_ai_response(self, text):
        global _ai_text
        _ai_text = text

    def stop_animation(self):
        global _stop_event
        _stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.tts_dl_thread and self.tts_dl_thread.is_alive():
            self.tts_dl_thread.join(timeout=1.0)
        if self.tts_play_thread and self.tts_play_thread.is_alive():
            self.tts_play_thread.join(timeout=1.0)
        # Restore normal terminal screen and cursor
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()

def play_audio(text, voice="female"):
    _tts_queue.put((text, voice))

def stream_audio(text_chunk, voice="female"):
    _tts_queue.put((text_chunk, voice))
