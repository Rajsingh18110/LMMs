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
from typing import Optional, Tuple, Dict
import psutil

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich import box

# Synchronization & State
_stop_event = threading.Event()
_anim_thread = None
_status_text = "Listening..."
_heard_text = ""         # User transcribed input
_ai_text = ""            # Spoken dialogue (rendered cleanly in Markdown)
_thoughts_text = ""      # Internal reasoning (<think>), hidden by default
_show_thoughts = False   # Drop-down toggle: False by default per user specification
_is_speaking_audio = False

_tts_queue = queue.Queue()
_playback_queue = queue.Queue()

# Performance & Flicker Prevention Cache
_last_rendered_ai_text = None
_cached_ai_markdown = None

# Professional Executive Slate Theme (Clean, No Clashing Rainbow Colors)
THEME = {
    "bg": "#0B0F17",           # Deep Slate Charcoal
    "panel_bg": "#111827",     # Dark Slate Container
    "border_idle": "#1E293B",  # Muted Dark Slate
    "border_active": "#38BDF8",# Ice Blue
    "border_user": "#334155",  # Steel Slate
    "text_bright": "#F8FAFC",  # Pure Crisp White
    "text_dim": "#64748B",     # Muted Slate Gray
    "accent_speaking": "#10B981", # Clean Emerald Green
    "accent_thinking": "#38BDF8", # Ice Blue
    "accent_listen": "#94A3B8",   # Light Slate
}

def extract_thoughts_and_response(text: str) -> Tuple[str, str]:
    """
    Separates <think>...</think> reasoning from spoken response.
    Guarantees that TTS and the spoken reply NEVER contain thinking tags.
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
            parts = text.split("<think>", 1)
            thoughts = parts[1].strip()
            spoken_text = parts[0].strip()
    return thoughts, spoken_text

def render_sleek_equalizer(t: float, width: int = 50, is_active: bool = False) -> str:
    """
    Renders an elegant, low-profile soundwave in Ice-Blue using 8x sub-cell blocks.
    Zero jitter, smooth fluid motion.
    """
    blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    chars = []
    level = (0.75 + 0.25 * math.sin(t * 8.0)) if is_active else 0.12
    for x in range(width):
        norm_x = (x - width / 2.0) / (width * 0.40)
        env = math.exp(-norm_x * norm_x)
        h = (
            math.sin(x * 0.32 + t * 5.0) * 0.48 +
            math.sin(x * 0.65 - t * 3.2) * 0.32 +
            math.cos(x * 0.20 + t * 2.0) * 0.20
        )
        val = max(0.05, abs(h) * env * level)
        idx = int(val * 8)
        chars.append(blocks[min(8, max(0, idx))])
        
    wave_str = "".join(chars)
    color = THEME["accent_speaking"] if is_active else THEME["border_active"]
    return f"[{color}]{wave_str}[/]"

def build_professional_frame(
    t: float,
    status: str,
    heard: str,
    thoughts: str,
    ai_text: str,
) -> Group:
    """
    Assembles a clean, executive, clutter-free Terminal Voice Interface:
    1. Minimalist Top Bar (Hardware stats + Time in muted slate)
    2. User Query Box (Clean text, subtle border)
    3. AI Response Box (Ice-Blue accent, Rich Markdown)
    4. Optional Collapsible Thought Box (Hidden by default, shown only when _show_thoughts=True)
    5. Sleek Audio Waveform + Single-line Footer
    """
    global _last_rendered_ai_text, _cached_ai_markdown

    is_speaking = ("Speaking" in status or _is_speaking_audio)
    is_thinking = ("Thinking" in status or "Synthesizing" in status)
    
    if is_speaking:
        active_border = THEME["accent_speaking"]
        status_dot = f"[bold {THEME['accent_speaking']}]● Speaking[/]"
    elif is_thinking:
        active_border = THEME["accent_thinking"]
        status_dot = f"[bold {THEME['accent_thinking']}]● Processing[/]"
    else:
        active_border = THEME["border_active"]
        status_dot = f"[bold {THEME['border_active']}]● Listening[/]"

    # 1. Minimalist Top Bar
    cols, _ = shutil.get_terminal_size((100, 30))
    time_str = datetime.now().strftime("%H:%M:%S")
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()

    hdr_tbl = Table.grid(expand=True)
    hdr_tbl.add_column("left", justify="left")
    hdr_tbl.add_column("right", justify="right")
    hdr_tbl.add_row(
        f"[bold {THEME['text_bright']}]LMMs Voice[/] [dim {THEME['text_dim']}]• Live[/]",
        f"[dim {THEME['text_dim']}]CPU {cpu:.0f}%  RAM {ram.used/(1024**3):.1f}GB  {time_str}[/]"
    )
    hdr_panel = Panel(
        hdr_tbl,
        style=f"on {THEME['bg']}",
        border_style=THEME["border_idle"],
        box=box.ROUNDED,
        padding=(0, 1)
    )

    # 2. User Query Panel
    if heard:
        user_body = Text(heard, style=f"bold {THEME['text_bright']}")
    else:
        user_body = Text("Listening... Speak now and press ENTER to submit", style=f"dim {THEME['text_dim']}")
        
    user_panel = Panel(
        user_body,
        title=f"[{THEME['text_dim']}] You [/{THEME['text_dim']}]",
        title_align="left",
        border_style=THEME["border_user"],
        box=box.ROUNDED,
        style=f"on {THEME['panel_bg']}",
        padding=(0, 1)
    )

    # 3. Optional Reasoning Panel (Only if user explicitly enabled it)
    thought_panel = None
    if _show_thoughts and thoughts:
        disp = thoughts if len(thoughts) <= 400 else thoughts[-397:] + "..."
        thought_panel = Panel(
            Text(disp, style=f"dim {THEME['text_dim']}"),
            title=f"[{THEME['text_dim']}] Internal Reasoning (T to hide) [/{THEME['text_dim']}]",
            title_align="left",
            border_style=THEME["border_idle"],
            box=box.ROUNDED,
            style=f"on {THEME['bg']}",
            padding=(0, 1)
        )

    # 4. Spoken AI Response Panel (Cached Rich Markdown for ZERO Flicker)
    if ai_text:
        if ai_text != _last_rendered_ai_text:
            _cached_ai_markdown = Markdown(ai_text)
            _last_rendered_ai_text = ai_text
        ai_content = _cached_ai_markdown
    else:
        if is_thinking:
            ai_content = Text("Generating response...", style=f"dim {THEME['text_dim']}")
        else:
            ai_content = Text("Waiting for speech...", style=f"dim {THEME['text_dim']}")

    ai_panel = Panel(
        ai_content,
        title=f"[bold {active_border}] Assistant [/]",
        title_align="left",
        border_style=active_border,
        box=box.ROUNDED,
        style=f"on {THEME['panel_bg']}",
        padding=(0, 1)
    )

    # 5. Sleek Audio Waveform Bar (Compact, Noisy Labels Removed)
    wave_w = max(30, min(cols - 16, 70))
    wave_markup = render_sleek_equalizer(t, width=wave_w, is_active=(is_speaking or not heard))
    wave_text = Text.from_markup(wave_markup, justify="center")

    # 6. Minimalist Footer
    ftr_tbl = Table.grid(expand=True)
    ftr_tbl.add_column("left", justify="left")
    ftr_tbl.add_column("center", justify="center")
    ftr_tbl.add_column("right", justify="right")
    
    thought_hint = "T: Reasoning" if thoughts else ""
    ftr_tbl.add_row(
        f"[dim {THEME['text_dim']}]Press ENTER to submit • Ctrl+C to cancel {thought_hint}[/]",
        wave_text,
        status_dot
    )
    ftr_panel = Panel(
        ftr_tbl,
        style=f"on {THEME['bg']}",
        border_style=THEME["border_idle"],
        box=box.ROUNDED,
        padding=(0, 1)
    )

    items = [hdr_panel, user_panel]
    if thought_panel is not None:
        items.append(thought_panel)
    items.extend([ai_panel, ftr_panel])
    return Group(*items)

def animate_cyberpunk_voice():
    """
    Zero-Flicker 20 FPS Terminal Display Loop.
    20 FPS is optimal for Linux terminals (QTerminal / Alacritty), eliminating tearing
    while maintaining fluid soundwave animation.
    """
    global _status_text, _heard_text, _ai_text, _thoughts_text
    console = Console(force_terminal=True, color_system="truecolor")
    
    t0 = time.perf_counter()
    TARGET_FPS = 20
    FRAME_INTERVAL = 1.0 / TARGET_FPS

    # Enable Alternate Screen Buffer and hide cursor
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()

    try:
        with Live(console=console, screen=True, refresh_per_second=TARGET_FPS) as live:
            while not _stop_event.is_set():
                now = time.perf_counter()
                t = now - t0

                frame = build_professional_frame(
                    t=t,
                    status=_status_text,
                    heard=_heard_text,
                    thoughts=_thoughts_text,
                    ai_text=_ai_text
                )
                live.update(frame)

                elapsed = time.perf_counter() - now
                sleep_time = FRAME_INTERVAL - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    finally:
        # Restore normal terminal screen and cursor cleanly
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
    """Strips Markdown symbols, code blocks, emojis, and stray think tags for fast TTS playback."""
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
            item = _tts_queue.get(timeout=0.05)
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
            
            # Primary: Fast in-process edge_tts
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
                
            # Secondary fallback: gTTS
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
    global _status_text, _is_speaking_audio
    while not _stop_event.is_set():
        original_queue = None
        try:
            item = _playback_queue.get(timeout=0.05)
            if item is None:
                continue
            tmp_file, text, original_queue = item
            
            display_text = text if len(text) <= 50 else text[:47] + "..."
            _status_text = f"Speaking: {display_text}"
            _is_speaking_audio = True
            
            played = False
            mpg_bin = shutil.which("mpg123")
            if mpg_bin:
                try:
                    p = subprocess.Popen([mpg_bin, "-q", tmp_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    while p.poll() is None:
                        time.sleep(0.04)
                        if _stop_event.is_set():
                            p.terminate()
                            break
                    played = True
                except Exception:
                    played = False
                    
            if not played:
                ffplay_bin = shutil.which("ffplay")
                if ffplay_bin:
                    try:
                        p = subprocess.Popen([ffplay_bin, "-nodisp", "-autoexit", tmp_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        while p.poll() is None:
                            time.sleep(0.04)
                            if _stop_event.is_set():
                                p.terminate()
                                break
                        played = True
                    except Exception:
                        played = False
                        
            if not played:
                try:
                    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(tmp_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.04)
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
                
            _is_speaking_audio = False
            if original_queue is not None:
                original_queue.task_done()
        except queue.Empty:
            _is_speaking_audio = False
            continue
        except Exception:
            _is_speaking_audio = False
            try:
                if original_queue is not None:
                    original_queue.task_done()
            except Exception:
                pass

def wait_for_tts():
    _tts_queue.join()

class VoiceSession:
    """Manages an active voice assistant session with professional HUD animation and low-latency audio."""
    def __init__(self):
        self.thread = None
        self.tts_dl_thread = None
        self.tts_play_thread = None
        self.sentence_buffer = ""
        self.last_spoken_len = 0
        self.first_chunk_sent = False

    def start_animation(self, text: str = "Listening..."):
        global _stop_event, _anim_thread, _status_text, _heard_text, _ai_text, _thoughts_text, _is_speaking_audio
        _status_text = text
        _heard_text = ""
        _ai_text = ""
        _thoughts_text = ""
        _is_speaking_audio = False
        self.sentence_buffer = ""
        self.last_spoken_len = 0
        self.first_chunk_sent = False
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

    def toggle_thoughts(self):
        global _show_thoughts
        _show_thoughts = not _show_thoughts

    def stop_animation(self):
        global _stop_event, _is_speaking_audio
        _stop_event.set()
        _is_speaking_audio = False
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
