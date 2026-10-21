import math
import time
import sys
import shutil
import threading
import subprocess
import os
import queue
import re
import asyncio
from datetime import datetime
import psutil

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

_stop_event = threading.Event()
_anim_thread = None
_status_text = "Listening..."
_heard_text = ""         # What user said (shown in User box)
_ai_text = ""            # Clean spoken AI reply (shown in AI box, zero think tags)
_thoughts_text = ""      # Internal reasoning (shown in muted Thought box if present)
_tts_queue = queue.Queue()
_playback_queue = queue.Queue()

# Network telemetry tracking
_last_net_time = time.time()
_last_net_io = psutil.net_io_counters()
_cached_net_str = "NET: ↑0.0 ↓0.0 KB/s"

def _get_network_speed():
    global _last_net_time, _last_net_io, _cached_net_str
    now = time.time()
    dt = now - _last_net_time
    if dt >= 1.0:
        try:
            curr = psutil.net_io_counters()
            up_kb = (curr.bytes_sent - _last_net_io.bytes_sent) / (dt * 1024.0)
            down_kb = (curr.bytes_recv - _last_net_io.bytes_recv) / (dt * 1024.0)
            _cached_net_str = f"NET: ↑{up_kb:.1f} ↓{down_kb:.1f} KB/s"
            _last_net_io = curr
            _last_net_time = now
        except Exception:
            pass
    return _cached_net_str

def extract_thoughts_and_response(text: str):
    """
    Separates <think>...</think> internal reasoning from the actual spoken dialogue.
    Guarantees that TTS and the spoken response box never contain thinking tags.
    """
    thoughts = ""
    spoken_text = text
    if "<think>" in text:
        if "</think>" in text:
            match = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
            if match:
                thoughts = match.group(1).strip()
            spoken_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        else:
            # Model is still thinking (closing tag not yet generated)
            parts = text.split("<think>", 1)
            thoughts = parts[1].strip()
            spoken_text = parts[0].strip()
    return thoughts, spoken_text

def render_multiline_equalizer(t: float, width: int = 50, rows: int = 3, level: float = 0.8) -> str:
    """Renders a dynamic cyberpunk ASCII sound wave equalizer using block characters."""
    heights = []
    for x in range(width):
        norm_x = (x - width / 2.0) / (width * 0.42)
        env = math.exp(-norm_x * norm_x)
        h = (
            math.sin(x * 0.35 + t * 5.2) * 0.45 +
            math.sin(x * 0.72 - t * 3.6) * 0.30 +
            math.cos(x * 0.22 + t * 2.1) * 0.25
        )
        val = max(0.08, abs(h) * env * level * rows)
        heights.append(val)

    row_colors = ["#00E5FF", "#00FFA3", "#BD00FF"]
    lines = []
    for r in range(rows - 1, -1, -1):
        color = row_colors[r % len(row_colors)]
        row_chars = []
        for h in heights:
            diff = h - r
            if diff >= 1.0:
                row_chars.append("█")
            elif diff >= 0.75:
                row_chars.append("▇")
            elif diff >= 0.50:
                row_chars.append("▆")
            elif diff >= 0.25:
                row_chars.append("▃")
            else:
                row_chars.append(" ")
        lines.append(f"[{color}]" + "".join(row_chars) + "[/]")
    return "\n".join(lines)

def build_cyberpunk_frame(t: float, status: str, heard: str, thoughts: str, ai_text: str, level: float = 0.8):
    """Assembles the high-aesthetic Cyberpunk Live terminal UI."""
    # Telemetry
    time_str = datetime.now().strftime("%H:%M:%S")
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    net_str = _get_network_speed()

    # Dynamic status glow
    if "Speaking" in status:
        glow = "#00FFA3"
        status_tag = "[bold #00FFA3]● SPEAKING[/]"
    elif "Thinking" in status or "Transcribing" in status or "Synthesizing" in status:
        glow = "#FFB800"
        status_tag = "[bold #FFB800]⚡ SYNTHESIZING[/]"
    else:
        glow = "#00E5FF"
        status_tag = "[bold #00E5FF]● LISTENING[/]"

    # 1. Telemetry Header (Minimalist Cyberpunk Bar)
    hdr_tbl = Table.grid(expand=True)
    hdr_tbl.add_column("title", justify="left")
    hdr_tbl.add_column("stats", justify="right")
    hdr_tbl.add_row(
        "[bold #00E5FF]⚡ LMMs[/] [bold #BD00FF]CYBERVOICE LIVE[/] [dim]v2.4[/]",
        f"[bold #00FFA3]CPU:[/] {cpu:.0f}%  [bold #00E5FF]RAM:[/] {ram.used/(1024**3):.1f}/{ram.total/(1024**3):.1f}GB  [bold #BD00FF]{net_str}[/]  [bold #FFFFFF]TIME:[/] {time_str}"
    )
    hdr_panel = Panel(hdr_tbl, style="on #0A0A12", border_style="#BD00FF", box=box.ROUNDED)

    # 2. User Query Panel
    if heard:
        user_content = Text(heard, style="bold #FFFFFF")
    else:
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        sp = spinner_chars[int(t * 10) % len(spinner_chars)]
        user_content = Text(f"{sp} Listening to microphone... Speak now and press ENTER to submit", style="dim #00E5FF")
        
    user_panel = Panel(user_content, title="[bold #00E5FF] 👤 USER AUDIO QUERY [/]", border_style="#00E5FF", box=box.ROUNDED, style="on #0A0A12")

    # 3. Collapsible / Muted Thought Panel (only when reasoning tokens exist)
    thought_panel = None
    if thoughts:
        # Show truncated snippet so it doesn't crowd out the response
        disp_thoughts = thoughts if len(thoughts) <= 400 else thoughts[:397] + "..."
        thought_panel = Panel(
            Text(disp_thoughts, style="dim #A89BBF"),
            title="[bold #7A5299] 💭 NEURAL REASONING (INTERNAL) [/]",
            border_style="#4A3563",
            box=box.ROUNDED,
            style="on #0A0A12"
        )

    # 4. Spoken AI Response Panel (Zero think tags, perfect multilingual alignment)
    if ai_text:
        ai_content = Text(ai_text, style=f"bold {glow}")
    else:
        ai_content = Text("(Waiting for model response...)", style="dim #777777")
        
    ai_panel = Panel(
        ai_content,
        title=f"[bold {glow}] 🤖 LMMs NEURAL VOICE [{status_tag}] [/]",
        border_style=glow,
        box=box.ROUNDED,
        style="on #0A0A12"
    )

    # 5. Live Animated Equalizer
    cols, _ = shutil.get_terminal_size()
    eq_width = max(30, min(65, cols - 16))
    eq_markup = render_multiline_equalizer(t, width=eq_width, rows=3, level=level)
    eq_text = Text.from_markup(eq_markup, justify="center")
    eq_panel = Panel(
        eq_text,
        title=f"[bold {glow}] 🔊 CYBER ACOUSTIC EQUALIZER [/]",
        border_style=glow,
        box=box.ROUNDED,
        style="on #0A0A12"
    )

    # 6. Minimalist Footer Controls
    ftr_tbl = Table.grid(expand=True)
    ftr_tbl.add_column("help", justify="left")
    ftr_tbl.add_column("status", justify="right")
    ftr_tbl.add_row(
        "[bold #00E5FF]⏎ ENTER[/]: Send Audio  •  [bold #FF0055]^C Ctrl+C[/]: Cancel Voice Mode",
        f"[bold {glow}]● {status}[/]"
    )
    ftr_panel = Panel(ftr_tbl, style="on #0A0A12", border_style=glow, box=box.ROUNDED)

    # Group all elements
    items = [hdr_panel, user_panel]
    if thought_panel:
        items.append(thought_panel)
    items.extend([ai_panel, eq_panel, ftr_panel])
    return Group(*items)

def animate_cyberpunk_voice():
    global _status_text, _heard_text, _ai_text, _thoughts_text
    console = Console(force_terminal=True, color_system="truecolor")
    
    t0 = time.perf_counter()
    FPS = 30
    
    try:
        with Live(console=console, screen=True, refresh_per_second=FPS) as live:
            while not _stop_event.is_set():
                now = time.perf_counter()
                t = now - t0
                
                is_active = ("Speaking" in _status_text) or ("Listening" in _status_text)
                level = (0.75 + 0.25 * math.sin(t * 8.0)) if is_active else 0.15
                
                frame = build_cyberpunk_frame(
                    t=t,
                    status=_status_text,
                    heard=_heard_text,
                    thoughts=_thoughts_text,
                    ai_text=_ai_text,
                    level=level
                )
                live.update(frame)
                
                sleep_time = (1.0 / FPS) - (time.perf_counter() - now)
                if sleep_time > 0:
                    time.sleep(sleep_time)
    finally:
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

def detect_language(text: str) -> str:
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

def clean_text_for_tts(text: str) -> str:
    # Remove any stray think tags that might have slipped through
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace("<think>", "").replace("</think>", "")
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
                
            lang = detect_language(clean_t)
            if lang == 'hindi':
                voice_name = "hi-IN-MadhurNeural" if voice == "male" else "hi-IN-SwaraNeural"
            else:
                voice_name = "en-IN-PrabhatNeural" if voice == "male" else "en-IN-NeerjaExpressiveNeural"
            
            tmp_file = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
            downloaded = False
            
            # 1. Primary: In-process edge_tts
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
            # 1. Prefer mpg123
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
    _tts_queue.join()

class VoiceSession:
    def __init__(self):
        self.thread = None
        self.tts_dl_thread = None
        self.tts_play_thread = None
        self.sentence_buffer = ""
        self.last_spoken_len = 0

    def start_animation(self, text: str = "Listening..."):
        global _stop_event, _anim_thread, _status_text, _heard_text, _ai_text, _thoughts_text
        _status_text = text
        _heard_text = ""
        _ai_text = ""
        _thoughts_text = ""
        self.sentence_buffer = ""
        self.last_spoken_len = 0
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
                
        self.thread = threading.Thread(target=animate_cyberpunk_voice, daemon=True)
        self.thread.start()
        _anim_thread = self.thread
        
        self.tts_dl_thread = threading.Thread(target=tts_download_worker, daemon=True)
        self.tts_dl_thread.start()
        
        self.tts_play_thread = threading.Thread(target=audio_play_worker, daemon=True)
        self.tts_play_thread.start()

    def update_status(self, text: str):
        global _status_text
        _status_text = text
    
    def set_heard(self, text: str):
        global _heard_text
        _heard_text = text

    def update_thoughts(self, text: str):
        global _thoughts_text
        _thoughts_text = text

    def update_ai_response(self, text: str):
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
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()

def play_audio(text: str, voice: str = "female"):
    _tts_queue.put((text, voice))

def stream_audio(text_chunk: str, voice: str = "female"):
    _tts_queue.put((text_chunk, voice))
