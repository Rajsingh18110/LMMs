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

from lmms.backend.voice_engine import (
    AudioAnalyzer,
    SystemStats,
    StateMachine,
    TextEffects,
    Theme,
    THEMES,
    interpolate_color
)

# Global synchronization events and queues
_stop_event = threading.Event()
_anim_thread = None
_status_text = "Listening..."
_heard_text = ""         # What user said (shown in User box)
_ai_text = ""            # Clean spoken AI reply (rendered in rich Markdown)
_thoughts_text = ""      # Internal reasoning (isolated in muted Thought box)
_visualizer_mode = "mirrored" # "bars", "mirrored", "braille"
_tts_queue = queue.Queue()
_playback_queue = queue.Queue()

# Global Audio & Telemetry Singletons
_analyzer = AudioAnalyzer(num_bars=48)
_sys_stats = SystemStats(history_len=24)
_state_machine = StateMachine(initial_state="listening")
_active_theme = Theme.CYBERPUNK
_session_start_time = time.time()
_is_speaking_audio = False

# Timing state for decode animation
_heard_received_time = 0.0
_last_heard_cache = ""

def extract_thoughts_and_response(text: str) -> Tuple[str, str]:
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

def build_cyberpunk_frame(
    t: float,
    status: str,
    heard: str,
    thoughts: str,
    ai_text: str,
    dt: float = 0.016,
    theme: Optional[Dict[str, str]] = None,
    mode: str = "mirrored"
) -> Group:
    """
    Assembles the 60 FPS Cinematic Cyberpunk terminal HUD with:
    - Live Telemetry & rolling sparklines (CPU, RAM, Net, Time)
    - User query with Matrix decode effect
    - Collapsible Neural Reasoning with token counter & elapsed time
    - Real Markdown rendering for spoken AI response
    - 8x Sub-cell / Braille audio-reactive visualizer with peak hold & gradient
    - Context-aware footer with keycaps
    """
    global _heard_received_time, _last_heard_cache
    theme = theme or _active_theme

    # 1. State Machine & Color Transition
    cur_state = "speaking" if ("Speaking" in status or _is_speaking_audio) else (
        "thinking" if ("Thinking" in status or "Synthesizing" in status) else (
            "transcribing" if "Transcribing" in status else "listening"
        )
    )
    _state_machine.set_state(cur_state)
    glow_color = _state_machine.get_color()
    status_badge = _state_machine.get_badge()

    # 2. Update Audio Analyzer & Smoothing Physics
    energy = 1.2 if cur_state == "speaking" else (0.6 if cur_state == "listening" else 0.25)
    _analyzer.update(cur_state, dt, energy_boost=energy)

    # 3. System Telemetry Bar (Header with Rolling Sparklines)
    cols, rows = shutil.get_terminal_size((100, 30))
    time_str = datetime.now().strftime("%H:%M:%S")
    cpu_spark = _sys_stats.render_sparkline(_sys_stats.cpu_history, 100.0, theme)
    ram_spark = _sys_stats.render_sparkline(_sys_stats.ram_history, 100.0, theme)
    ram_gb = psutil.virtual_memory()

    hdr_tbl = Table.grid(expand=True)
    hdr_tbl.add_column("title", justify="left")
    hdr_tbl.add_column("stats", justify="right")

    hdr_left = f"[bold {theme['cyan']}]⚡ LMMs[/] [bold {theme['magenta']}]CYBERVOICE LIVE[/] [dim {theme['dim_text']}]v2.5 (60 FPS)[/]"
    hdr_right = (
        f"[bold {theme['green']}]CPU:[/] {_sys_stats.cur_cpu:.0f}% {cpu_spark}  "
        f"[bold {theme['cyan']}]RAM:[/] {ram_gb.used/(1024**3):.1f}/{ram_gb.total/(1024**3):.1f}GB {ram_spark}  "
        f"[bold {theme['magenta']}]NET:[/] ↑{_sys_stats.cur_up_kb:.1f} ↓{_sys_stats.cur_down_kb:.1f}KB/s  "
        f"[bold {theme['amber']}]TIME:[/] {time_str}"
    )
    hdr_tbl.add_row(hdr_left, hdr_right)
    hdr_panel = Panel(
        hdr_tbl,
        style=f"on {theme['bg']}",
        border_style=theme["purple"],
        box=box.ROUNDED,
        padding=(0, 1)
    )

    # 4. User Query Panel (with Matrix Scramble Effect)
    if heard:
        if heard != _last_heard_cache:
            _heard_received_time = t
            _last_heard_cache = heard
        scramble_elapsed = t - _heard_received_time
        decoded_text = TextEffects.decode_scramble(heard, scramble_elapsed, duration=0.35)
        user_content = Text(decoded_text, style=f"bold {theme['bright_text']}")
    else:
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        sp = spinner_chars[int(t * 12) % len(spinner_chars)]
        user_content = Text(f"{sp} Listening to microphone... Speak clearly and press ENTER to submit", style=f"dim {theme['cyan']}")

    user_panel = Panel(
        user_content,
        title=f"[bold {theme['cyan']}] 👤 USER AUDIO QUERY [/]",
        border_style=theme["cyan"],
        box=box.ROUNDED,
        style=f"on {theme['panel_bg']}",
        padding=(0, 1)
    )

    # 5. Neural Reasoning Panel (Collapsible, Muted, Token & Time Counters)
    thought_panel = None
    if thoughts:
        token_count = len(thoughts.split())
        elapsed_sec = t
        disp_thoughts = thoughts if len(thoughts) <= 350 else thoughts[-347:] + "..."
        thought_body = Text(disp_thoughts, style=f"dim {theme['thought_text']}")
        thought_panel = Panel(
            thought_body,
            title=f"[bold {theme['thought_border']}] 💭 NEURAL REASONING  [dim]• {token_count} tokens  ⏱ {elapsed_sec:.1f}s[/] [/]",
            border_style=theme["thought_border"],
            box=box.ROUNDED,
            style=f"on {theme['bg']}",
            padding=(0, 1)
        )

    # 6. Spoken AI Response Panel (REAL MARKDOWN RENDERING!)
    if ai_text:
        # Render real rich Markdown so headers, bold, bullets, and inline code look stunning!
        ai_markdown = Markdown(ai_text)
        # Typewriter cursor at the end while speaking
        ai_content = ai_markdown
    else:
        if cur_state == "thinking":
            ai_content = Text("⚡ Synthesizing neural response and voice stream...", style=f"italic {theme['amber']}")
        else:
            ai_content = Text("(Waiting for model response...)", style=f"dim {theme['dim_text']}")

    ai_panel = Panel(
        ai_content,
        title=f"[bold {glow_color}] 🤖 LMMs NEURAL VOICE [{status_badge}] [/]",
        border_style=glow_color,
        box=box.ROUNDED,
        style=f"on {theme['panel_bg']}",
        padding=(0, 1)
    )

    # 7. Audio-Reactive Cyber Visualizer (8x Sub-cell / Braille Oscilloscope)
    vis_width = max(36, min(cols - 10, 84))
    vis_height = 4 if rows < 32 else 5

    if mode == "braille":
        vis_lines = _analyzer.render_braille_wave(vis_width, vis_height, theme, t)
    elif mode == "bars":
        vis_lines = _analyzer.render_bars(vis_width, vis_height, theme, t)
    else:
        # Default: mirrored spectrum with dim fade reflection
        vis_lines = _analyzer.render_mirrored(vis_width, vis_height, theme, t)

    # Subtle frequency axis labels beneath the visualizer
    freq_labels = f"[dim {theme['dim_text']}]80Hz             250Hz             1kHz             4kHz             8kHz[/]"
    vis_content = Text.from_markup("\n".join(vis_lines) + "\n" + freq_labels, justify="center")

    eq_panel = Panel(
        vis_content,
        title=f"[bold {glow_color}] 🔊 CYBER ACOUSTIC VISUALIZER [{mode.upper()}] [/]",
        border_style=glow_color,
        box=box.ROUNDED,
        style=f"on {theme['bg']}",
        padding=(0, 1)
    )

    # 8. Context-Aware Footer with Highlighted Keycaps
    ftr_tbl = Table.grid(expand=True)
    ftr_tbl.add_column("controls", justify="left")
    ftr_tbl.add_column("status", justify="right")

    controls_markup = (
        f"[bold {theme['cyan']} on #141b2d] ⏎ ENTER [/] Send  "
        f"[bold {theme['magenta']} on #141b2d] V [/] Waveform ({mode})  "
        f"[bold {theme['green']} on #141b2d] T [/] Toggle Thoughts  "
        f"[bold {theme['red']} on #141b2d] ^C [/] Cancel"
    )
    ftr_tbl.add_row(controls_markup, f"[bold {glow_color}]{status_badge}[/]")
    ftr_panel = Panel(
        ftr_tbl,
        style=f"on {theme['bg']}",
        border_style=glow_color,
        box=box.ROUNDED,
        padding=(0, 1)
    )

    # Assemble layout panels cleanly
    items = [hdr_panel, user_panel]
    if thought_panel is not None:
        items.append(thought_panel)
    items.extend([ai_panel, eq_panel, ftr_panel])
    return Group(*items)

def animate_cyberpunk_voice():
    """60 FPS Fixed-timestep animation loop with truecolor terminal rendering."""
    global _status_text, _heard_text, _ai_text, _thoughts_text, _visualizer_mode
    console = Console(force_terminal=True, color_system="truecolor")
    
    t0 = time.perf_counter()
    last_frame_time = t0
    last_poll_time = t0
    TARGET_FPS = 60
    FRAME_INTERVAL = 1.0 / TARGET_FPS

    # Enable Alternate Screen Buffer and hide cursor
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()

    try:
        with Live(console=console, screen=True, refresh_per_second=TARGET_FPS) as live:
            while not _stop_event.is_set():
                now = time.perf_counter()
                dt = now - last_frame_time
                last_frame_time = now
                t = now - t0

                # Periodic telemetry polling (every 0.5s)
                if now - last_poll_time >= 0.5:
                    _sys_stats.poll()
                    last_poll_time = now

                frame = build_cyberpunk_frame(
                    t=t,
                    status=_status_text,
                    heard=_heard_text,
                    thoughts=_thoughts_text,
                    ai_text=_ai_text,
                    dt=dt,
                    theme=_active_theme,
                    mode=_visualizer_mode
                )
                live.update(frame)

                # Precision sleep for constant 60 FPS
                elapsed = time.perf_counter() - now
                sleep_time = FRAME_INTERVAL - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    finally:
        # Restore normal terminal screen and cursor
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
    """Strips Markdown symbols, code blocks, emojis, and stray think tags for TTS voice clarity."""
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
            
            # 1. Primary: In-process edge_tts (Neural voice quality)
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
    global _status_text, _is_speaking_audio
    while not _stop_event.is_set():
        original_queue = None
        try:
            item = _playback_queue.get(timeout=0.1)
            if item is None:
                continue
            tmp_file, text, original_queue = item
            
            display_text = text if len(text) <= 50 else text[:47] + "..."
            _status_text = f"Speaking: {display_text}"
            _is_speaking_audio = True
            
            played = False
            # 1. Prefer mpg123
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
                    
            # 2. Fallback to ffplay
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
                        
            # 3. Fallback to pygame.mixer
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
    """Manages an active voice assistant session with HUD animation and audio playback."""
    def __init__(self):
        self.thread = None
        self.tts_dl_thread = None
        self.tts_play_thread = None
        self.sentence_buffer = ""
        self.last_spoken_len = 0

    def start_animation(self, text: str = "Listening..."):
        global _stop_event, _anim_thread, _status_text, _heard_text, _ai_text, _thoughts_text, _is_speaking_audio
        _status_text = text
        _heard_text = ""
        _ai_text = ""
        _thoughts_text = ""
        _is_speaking_audio = False
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

    def set_visualizer_mode(self, mode: str):
        global _visualizer_mode
        if mode in ("bars", "mirrored", "braille"):
            _visualizer_mode = mode

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
