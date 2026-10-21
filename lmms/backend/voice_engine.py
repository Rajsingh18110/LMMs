"""
LMMs CyberVoice Engine - Core Audio DSP, Physics, Telemetry, and Visualizer Engine
Provides:
1. AudioAnalyzer: Real audio FFT + Hann window + log frequency bins + procedural speech envelope fallback
2. Smoothing Physics: Attack/decay, spring-damper, peak-hold gravity caps, EMA temporal & spatial smoothing
3. Visualizers: Sub-cell bars (8x), Mirrored spectrum, Braille-dot oscilloscope (2x4 dots), Circular/polar
4. SystemStats: CPU/RAM/Net telemetry with 30-sample rolling sparklines and eased interpolation
5. StateMachine: Animated state cross-fading (IDLE, LISTENING, TRANSCRIBING, THINKING, SPEAKING, ERROR, CANCELLED)
6. TextEffects: Typewriter with blinking block cursor, karaoke word highlighting, matrix decode glitch
7. Theme: Cyberpunk, Synthwave, Matrix, and Monochrome design tokens
"""

import math
import time
import re
import random
from collections import deque
from typing import List, Tuple, Dict, Optional
import psutil
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM & THEMES
# ==============================================================================

class Theme:
    CYBERPUNK = {
        "name": "cyberpunk",
        "bg": "#05070d",
        "panel_bg": "#080c16",
        "cyan": "#00f0ff",
        "green": "#00ff9c",
        "magenta": "#ff2bd6",
        "purple": "#9d4dff",
        "amber": "#ffb000",
        "red": "#ff3860",
        "dim_text": "#6b7a99",
        "bright_text": "#e6f1ff",
        "thought_border": "#4a3563",
        "thought_text": "#a89bbf",
        "spark_low": "#00ff9c",
        "spark_mid": "#ffb000",
        "spark_high": "#ff3860",
    }
    
    SYNTHWAVE = {
        "name": "synthwave",
        "bg": "#0c0817",
        "panel_bg": "#130d24",
        "cyan": "#00e5ff",
        "green": "#ffd166",
        "magenta": "#ff007f",
        "purple": "#7928ca",
        "amber": "#ff9e00",
        "red": "#ff0055",
        "dim_text": "#7b6f93",
        "bright_text": "#fdf7ff",
        "thought_border": "#582b72",
        "thought_text": "#b892d1",
        "spark_low": "#00e5ff",
        "spark_mid": "#ffd166",
        "spark_high": "#ff007f",
    }
    
    MATRIX = {
        "name": "matrix",
        "bg": "#020904",
        "panel_bg": "#041409",
        "cyan": "#00ff66",
        "green": "#00ff33",
        "magenta": "#00cc44",
        "purple": "#00882b",
        "amber": "#88ff00",
        "red": "#ff2200",
        "dim_text": "#2d6b3e",
        "bright_text": "#a3ffb8",
        "thought_border": "#00471b",
        "thought_text": "#4d9966",
        "spark_low": "#00ff33",
        "spark_mid": "#88ff00",
        "spark_high": "#ff2200",
    }
    
    MONOCHROME = {
        "name": "monochrome",
        "bg": "#0a0a0a",
        "panel_bg": "#141414",
        "cyan": "#ffffff",
        "green": "#d0d0d0",
        "magenta": "#a0a0a0",
        "purple": "#808080",
        "amber": "#cccccc",
        "red": "#ffffff",
        "dim_text": "#666666",
        "bright_text": "#ffffff",
        "thought_border": "#333333",
        "thought_text": "#888888",
        "spark_low": "#888888",
        "spark_mid": "#cccccc",
        "spark_high": "#ffffff",
    }

THEMES = {
    "cyberpunk": Theme.CYBERPUNK,
    "synthwave": Theme.SYNTHWAVE,
    "matrix": Theme.MATRIX,
    "monochrome": Theme.MONOCHROME,
}

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([c*2 for c in h])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rgb_to_hex(r: int, g: int, b: int) -> str:
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"

def interpolate_color(c1_hex: str, c2_hex: str, t: float) -> str:
    """Linearly interpolates two hex colors."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = hex_to_rgb(c1_hex)
    r2, g2, b2 = hex_to_rgb(c2_hex)
    return rgb_to_hex(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t)
    )

# ==============================================================================
# 2. EASING FUNCTIONS
# ==============================================================================

class Easing:
    @staticmethod
    def linear(t: float) -> float:
        return max(0.0, min(1.0, t))
        
    @staticmethod
    def ease_out_cubic(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) ** 3
        
    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 2.0 * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0

    @staticmethod
    def spring(t: float, damp: float = 0.65, freq: float = 12.0) -> float:
        t = max(0.0, min(1.0, t))
        return 1.0 - math.exp(-damp * t * 10.0) * math.cos(freq * t)

# ==============================================================================
# 3. AUDIO ANALYZER & SMOOTHING PHYSICS
# ==============================================================================

class AudioAnalyzer:
    """
    Computes real-time frequency band spectrum with:
    - Real Audio FFT (when PCM buffer received)
    - Speech-like procedural synthesis fallback (syllabic envelope ~4-6 Hz + formants)
    - Attack/Decay dynamics
    - Spring-damper and EMA temporal smoothing
    - Floating peak-hold caps that fall with gravity
    - Neighbor spatial smoothing for liquid motion
    """
    SUB_CELL_BLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    
    def __init__(self, num_bars: int = 48):
        self.num_bars = num_bars
        self.raw_levels = np.zeros(num_bars, dtype=np.float32)
        self.smooth_levels = np.zeros(num_bars, dtype=np.float32)
        self.peak_levels = np.zeros(num_bars, dtype=np.float32)
        self.peak_velocities = np.zeros(num_bars, dtype=np.float32)
        self.pcm_buffer = deque(maxlen=2048)
        self.t0 = time.perf_counter()
        self.last_update = self.t0
        
        # Procedural speech state
        self.speech_seed = random.random() * 100.0
        self.formant_shift = 0.0

    def feed_pcm(self, pcm_chunk: bytes):
        """Pipes raw 16-bit PCM mono or stereo audio into the FFT buffer."""
        try:
            samples = np.frombuffer(pcm_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            if len(samples) > 0:
                self.pcm_buffer.extend(samples)
        except Exception:
            pass

    def update(self, state: str, dt: float, energy_boost: float = 1.0) -> np.ndarray:
        """
        Updates frequency bar levels for the given time step.
        Returns smooth_levels array normalized between 0.0 and 1.0.
        """
        now = time.perf_counter()
        t = now - self.t0
        
        # 1. Target Level Generation
        target_levels = np.zeros(self.num_bars, dtype=np.float32)
        
        if len(self.pcm_buffer) >= 512:
            # Real FFT from buffered audio
            data = np.array(list(self.pcm_buffer)[-512:], dtype=np.float32)
            window = np.hanning(len(data))
            fft_mag = np.abs(np.fft.rfft(data * window))
            
            # Group into logarithmic bands (80 Hz to 8000 Hz)
            freq_indices = np.geomspace(2, len(fft_mag) - 1, num=self.num_bars + 1).astype(int)
            for i in range(self.num_bars):
                start = freq_indices[i]
                end = max(start + 1, freq_indices[i + 1])
                band_energy = np.mean(fft_mag[start:end]) * 4.0
                target_levels[i] = min(1.0, band_energy)
        else:
            # Procedural Speech & State Synthesizer
            if state == "speaking":
                # Syllable rhythm envelope (~4-6 Hz)
                syllable_env = (
                    0.55 + 
                    0.30 * math.sin(t * 11.0 + self.speech_seed) + 
                    0.15 * math.sin(t * 4.5)
                )
                syllable_env = max(0.12, syllable_env) * energy_boost
                
                # Three speech formants (F1, F2, F3) shifting across bands
                for i in range(self.num_bars):
                    norm_i = i / float(self.num_bars)
                    f1 = math.exp(-((norm_i - 0.22) / 0.12) ** 2) * 0.9
                    f2 = math.exp(-((norm_i - 0.48) / 0.16) ** 2) * 0.7
                    f3 = math.exp(-((norm_i - 0.78) / 0.20) ** 2) * 0.5
                    
                    harmonics = (
                        math.sin(i * 0.45 + t * 9.0) * 0.35 +
                        math.cos(i * 0.85 - t * 6.5) * 0.25 +
                        math.sin(i * 1.35 + t * 14.0) * 0.15
                    )
                    
                    val = (f1 + f2 + f3 + abs(harmonics)) * syllable_env * 0.65
                    # Natural vocal envelope taper at boundaries
                    taper = math.sin(norm_i * math.pi)
                    target_levels[i] = max(0.04, min(1.0, val * taper))
            elif state == "listening":
                # Ambient acoustic murmur with sensitive mic pulses
                mic_pulse = 0.25 + 0.15 * math.sin(t * 8.0)
                for i in range(self.num_bars):
                    norm_i = i / float(self.num_bars)
                    noise = (math.sin(i * 0.9 + t * 12.0) * 0.2 + math.cos(i * 1.7 - t * 7.0) * 0.15)
                    val = abs(noise) * mic_pulse * math.sin(norm_i * math.pi)
                    target_levels[i] = max(0.03, min(0.65, val))
            elif state in ("thinking", "transcribing"):
                # Rhythmic neural wave scanning back and forth
                scan_pos = (math.sin(t * 4.0) + 1.0) / 2.0
                for i in range(self.num_bars):
                    norm_i = i / float(self.num_bars)
                    dist = abs(norm_i - scan_pos)
                    wave = math.exp(-(dist / 0.18) ** 2) * 0.75
                    target_levels[i] = max(0.03, wave)
            else:
                # IDLE: Slow breathing sine-wave heartbeat line
                for i in range(self.num_bars):
                    norm_i = (i - self.num_bars / 2.0) / (self.num_bars * 0.45)
                    center_env = math.exp(-norm_i * norm_i)
                    heartbeat = (math.sin(i * 0.35 + t * 2.2) * 0.12 + 0.08) * center_env
                    target_levels[i] = max(0.02, min(0.35, heartbeat))

        # 2. Attack and Decay Physics
        # Fast attack (~0.65), smooth decay (~0.12)
        attack_rate = min(1.0, 0.65 * (dt * 60.0))
        decay_rate = min(1.0, 0.12 * (dt * 60.0))
        
        for i in range(self.num_bars):
            cur = self.smooth_levels[i]
            tgt = target_levels[i]
            if tgt > cur:
                self.smooth_levels[i] = cur + (tgt - cur) * attack_rate
            else:
                self.smooth_levels[i] = cur - (cur - tgt) * decay_rate

        # 3. Neighbor Spatial Smoothing (3-point filter for liquid flow)
        smoothed = np.copy(self.smooth_levels)
        for i in range(1, self.num_bars - 1):
            smoothed[i] = 0.20 * self.smooth_levels[i - 1] + 0.60 * self.smooth_levels[i] + 0.20 * self.smooth_levels[i + 1]
        self.smooth_levels = smoothed

        # 4. Floating Peak-Hold Caps with Simulated Gravity
        gravity = 0.035 * (dt * 60.0)
        for i in range(self.num_bars):
            cur = self.smooth_levels[i]
            peak = self.peak_levels[i]
            if cur >= peak:
                self.peak_levels[i] = cur
                self.peak_velocities[i] = 0.0
            else:
                self.peak_velocities[i] += gravity
                self.peak_levels[i] = max(cur, peak - self.peak_velocities[i])

        return self.smooth_levels

    def render_bars(self, width: int, height: int, theme: Dict[str, str], t: float) -> List[str]:
        """Renders standard multi-frequency spectrum bars with peak hold."""
        levels = self.smooth_levels
        peaks = self.peak_levels
        
        # Resize/interpolate to requested width
        indices = np.linspace(0, len(levels) - 1, width)
        w_levels = np.interp(indices, np.arange(len(levels)), levels)
        w_peaks = np.interp(indices, np.arange(len(peaks)), peaks)
        
        lines = []
        for r in range(height - 1, -1, -1):
            row_ratio = (r + 0.5) / float(height)
            # Gradient: Cyan (bottom) -> Green (mid) -> Magenta (top)
            if row_ratio < 0.5:
                color = interpolate_color(theme["cyan"], theme["green"], row_ratio * 2.0)
            else:
                color = interpolate_color(theme["green"], theme["magenta"], (row_ratio - 0.5) * 2.0)
            
            chars = []
            for c in range(width):
                val = w_levels[c] * height
                diff = val - r
                if diff >= 1.0:
                    chars.append("█")
                elif diff > 0.0:
                    idx = int(diff * 8)
                    chars.append(self.SUB_CELL_BLOCKS[min(8, max(1, idx))])
                else:
                    # Check peak hold cap
                    peak_row = int(w_peaks[c] * height)
                    if peak_row == r and w_peaks[c] > 0.1:
                        chars.append("▔")
                    else:
                        chars.append(" ")
            lines.append(f"[{color}]" + "".join(chars) + "[/]")
        return lines

    def render_mirrored(self, width: int, height: int, theme: Dict[str, str], t: float) -> List[str]:
        """Renders center-mirrored spectrum bars with dim fade reflection."""
        half_h = max(2, height // 2)
        top_lines = self.render_bars(width, half_h, theme, t)
        
        # Mirror bottom lines with dimmer color
        bottom_lines = []
        for ln in reversed(top_lines):
            # Invert blocks for upside-down reflection
            reflected = ln.replace("▔", " ").replace("█", "▄").replace("▇", "▃").replace("▆", "▂")
            bottom_lines.append(f"[dim]{reflected}[/]")
            
        return top_lines + bottom_lines

    def render_braille_wave(self, width: int, height: int, theme: Dict[str, str], t: float) -> List[str]:
        """
        Renders a true 2x4 dot Braille oscilloscope waveform (U+2800).
        Total pixel resolution: (width * 2) x (height * 4).
        """
        pixel_w = width * 2
        pixel_h = height * 4
        
        # Generate waveform points
        dots_matrix = np.zeros((pixel_h, pixel_w), dtype=bool)
        levels = self.smooth_levels
        
        for px in range(pixel_w):
            norm_x = px / float(pixel_w)
            band_idx = int(norm_x * (len(levels) - 1))
            amp = levels[band_idx]
            
            # Oscilloscope harmonic function
            wave = (
                math.sin(norm_x * 14.0 + t * 9.0) * 0.55 +
                math.cos(norm_x * 28.0 - t * 14.0) * 0.30 +
                math.sin(norm_x * 42.0 + t * 21.0) * 0.15
            )
            center_y = pixel_h / 2.0
            py = int(center_y + wave * amp * (pixel_h * 0.44))
            py = max(0, min(pixel_h - 1, py))
            dots_matrix[py, px] = True
            
            # Add subtle vertical trace thickness
            if 0 < py < pixel_h - 1 and amp > 0.3:
                dots_matrix[py - 1, px] = True
                dots_matrix[py + 1, px] = True

        # Convert 2x4 pixel blocks into Braille characters
        lines = []
        for r in range(height):
            char_row = []
            for c in range(width):
                code = 0x2800
                bx = c * 2
                by = r * 4
                
                # Column 0 dots
                if by + 0 < pixel_h and dots_matrix[by + 0, bx + 0]: code |= 0x01
                if by + 1 < pixel_h and dots_matrix[by + 1, bx + 0]: code |= 0x02
                if by + 2 < pixel_h and dots_matrix[by + 2, bx + 0]: code |= 0x04
                if by + 3 < pixel_h and dots_matrix[by + 3, bx + 0]: code |= 0x40
                
                # Column 1 dots
                if by + 0 < pixel_h and bx + 1 < pixel_w and dots_matrix[by + 0, bx + 1]: code |= 0x08
                if by + 1 < pixel_h and bx + 1 < pixel_w and dots_matrix[by + 1, bx + 1]: code |= 0x10
                if by + 2 < pixel_h and bx + 1 < pixel_w and dots_matrix[by + 2, bx + 1]: code |= 0x20
                if by + 3 < pixel_h and bx + 1 < pixel_w and dots_matrix[by + 3, bx + 1]: code |= 0x80
                
                char_row.append(chr(code))
            
            color_ratio = r / float(max(1, height - 1))
            color = interpolate_color(theme["cyan"], theme["magenta"], color_ratio)
            lines.append(f"[{color}]" + "".join(char_row) + "[/]")
            
        return lines

# ==============================================================================
# 4. SYSTEM STATS & SPARKLINE TELEMETRY
# ==============================================================================

class SystemStats:
    """Manages rolling 30-sample history buffers for CPU, RAM, and Network with sparklines."""
    SPARK_CHARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    
    def __init__(self, history_len: int = 24):
        self.history_len = history_len
        self.cpu_history = deque([10.0] * history_len, maxlen=history_len)
        self.ram_history = deque([30.0] * history_len, maxlen=history_len)
        self.net_history = deque([5.0] * history_len, maxlen=history_len)
        
        self.last_net_time = time.time()
        self.last_net_io = psutil.net_io_counters()
        self.cur_cpu = 0.0
        self.cur_ram = 0.0
        self.cur_up_kb = 0.0
        self.cur_down_kb = 0.0
        self.eased_cpu = 0.0
        self.eased_ram = 0.0

    def poll(self):
        now = time.time()
        dt = max(0.1, now - self.last_net_time)
        self.cur_cpu = psutil.cpu_percent()
        ram_info = psutil.virtual_memory()
        self.cur_ram = ram_info.percent
        
        try:
            curr_io = psutil.net_io_counters()
            self.cur_up_kb = (curr_io.bytes_sent - self.last_net_io.bytes_sent) / (dt * 1024.0)
            self.cur_down_kb = (curr_io.bytes_recv - self.last_net_io.bytes_recv) / (dt * 1024.0)
            self.last_net_io = curr_io
            self.last_net_time = now
        except Exception:
            pass
            
        self.cpu_history.append(self.cur_cpu)
        self.ram_history.append(self.cur_ram)
        self.net_history.append(self.cur_down_kb)

    def render_sparkline(self, values: deque, max_val: float = 100.0, theme: Optional[Dict[str, str]] = None) -> str:
        """Returns colored unicode sparkline from history values."""
        theme = theme or Theme.CYBERPUNK
        parts = []
        for v in values:
            norm = max(0.0, min(1.0, v / max(1.0, max_val)))
            idx = int(norm * 8)
            char = self.SPARK_CHARS[min(8, max(0, idx))]
            if norm < 0.50:
                color = theme["spark_low"]
            elif norm < 0.80:
                color = theme["spark_mid"]
            else:
                color = theme["spark_high"]
            parts.append(f"[{color}]{char}[/]")
        return "".join(parts)

# ==============================================================================
# 5. STATE MACHINE & CROSS-FADING TRANSITIONS
# ==============================================================================

class StateMachine:
    """
    States: IDLE, LISTENING, TRANSCRIBING, THINKING, SPEAKING, ERROR, CANCELLED
    Smoothly cross-fades active border colors and badges over 250ms.
    """
    STATE_CONFIG = {
        "idle": {
            "title": "● IDLE",
            "color": "#00f0ff",
            "badge_icon": "💤",
            "border_style": "round"
        },
        "listening": {
            "title": "🎙 LISTENING",
            "color": "#ff2bd6",
            "badge_icon": "🎙",
            "border_style": "round"
        },
        "transcribing": {
            "title": "⚡ TRANSCRIBING",
            "color": "#ffb000",
            "badge_icon": "⠋",
            "border_style": "round"
        },
        "thinking": {
            "title": "💭 SYNTHESIZING",
            "color": "#9d4dff",
            "badge_icon": "🧠",
            "border_style": "round"
        },
        "speaking": {
            "title": "🔊 SPEAKING",
            "color": "#00ff9c",
            "badge_icon": "●",
            "border_style": "double"
        },
        "error": {
            "title": "⚠ ERROR",
            "color": "#ff3860",
            "badge_icon": "✖",
            "border_style": "heavy"
        },
        "cancelled": {
            "title": "🚫 CANCELLED",
            "color": "#6b7a99",
            "badge_icon": "⏹",
            "border_style": "round"
        }
    }

    def __init__(self, initial_state: str = "listening"):
        self.current_state = initial_state
        self.prev_state = initial_state
        self.transition_start = time.perf_counter()
        self.transition_duration = 0.25 # 250 ms cross-fade

    def set_state(self, new_state: str):
        new_state = new_state.lower()
        if new_state not in self.STATE_CONFIG:
            new_state = "speaking" if "speak" in new_state else ("thinking" if "think" in new_state else "listening")
        if new_state != self.current_state:
            self.prev_state = self.current_state
            self.current_state = new_state
            self.transition_start = time.perf_counter()

    def get_color(self) -> str:
        now = time.perf_counter()
        progress = min(1.0, (now - self.transition_start) / self.transition_duration)
        c1 = self.STATE_CONFIG[self.prev_state]["color"]
        c2 = self.STATE_CONFIG[self.current_state]["color"]
        return interpolate_color(c1, c2, Easing.ease_in_out_quad(progress))

    def get_badge(self) -> str:
        cfg = self.STATE_CONFIG[self.current_state]
        return f"{cfg['badge_icon']} {cfg['title']}"

# ==============================================================================
# 6. TEXT EFFECTS (TYPEWRITER, KARAOKE HIGHLIGHT, MATRIX DECODE)
# ==============================================================================

class TextEffects:
    DECODE_CHARS = "░▒▓█#@$%&01"
    
    @staticmethod
    def decode_scramble(text: str, elapsed: float, duration: float = 0.35) -> str:
        """Matrix-style decode scramble resolving characters left to right."""
        if elapsed >= duration or not text:
            return text
        ratio = max(0.0, min(1.0, elapsed / duration))
        resolved_count = int(ratio * len(text))
        
        parts = []
        for i, char in enumerate(text):
            if i < resolved_count or char in (" ", "\n", "\t"):
                parts.append(char)
            else:
                parts.append(random.choice(TextEffects.DECODE_CHARS))
        return "".join(parts)

    @staticmethod
    def karaoke_highlight(text: str, progress_ratio: float, theme: Dict[str, str]) -> str:
        """
        Highlights currently spoken words bright and leaves upcoming words dimmed.
        Returns Rich formatted markup.
        """
        words = text.split(" ")
        if not words:
            return text
        cur_idx = int(progress_ratio * len(words))
        
        parts = []
        for i, w in enumerate(words):
            if i < cur_idx:
                parts.append(f"[{theme['bright_text']}]{w}[/]")
            elif i == cur_idx:
                parts.append(f"[bold {theme['cyan']} underline]{w}[/]")
            else:
                parts.append(f"[{theme['dim_text']}]{w}[/]")
        return " ".join(parts)
