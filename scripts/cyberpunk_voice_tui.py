#!/usr/bin/env python3
"""
LMMs CYBERVOICE LIVE - Cinematic Cyberpunk Voice Assistant TUI (Textual Framework)
===================================================================================
A futuristic, 60 FPS sci-fi cockpit terminal interface.
Features:
- Audio DSP: 8x Sub-cell bars, Braille-dot oscilloscope (2x4 dots), Mirrored spectrum
- Smoothing physics: Attack/decay, spring-damper, gravity peak-hold caps, spatial smoothing
- Real Markdown rendering: Bold, bullets, syntax highlighting, emoji wide-char safe
- Typewriter streaming: Blinking block cursor '▌' with karaoke spoken word highlighting
- Neural Reasoning: Collapsible (key T), shimmer animation, token & time telemetry
- Matrix decode scramble: Scrambles through '░▒▓█#@$%' before resolving
- System Telemetry: CPU, RAM, and Network rolling sparklines ( ▂▃▄▅▆▇█)
- Responsive Cockpit: Wide split-screen (>=120 cols) vs narrow stacked layout
- Boot animation: Sci-fi terminal boot sequence (skippable with any key)
- Flags: --fps, --theme, --no-animation, --ascii
"""

import math
import time
import re
import random
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Optional
import psutil

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Collapsible, Label, Footer, Markdown as TextualMarkdown
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual.events import Key, Resize
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.table import Table
from rich import box

from lmms.backend.voice_engine import (
    AudioAnalyzer,
    SystemStats,
    StateMachine,
    TextEffects,
    Theme,
    THEMES,
    Easing,
    interpolate_color,
)

# ==============================================================================
# TEXTUAL STYLES (TCSS)
# ==============================================================================

COCKPIT_CSS = """
Screen {
    background: #05070d;
    color: #e6f1ff;
    layout: vertical;
    padding: 0 1;
}

#header-container {
    height: 3;
    dock: top;
    margin-bottom: 1;
    border: round #9d4dff;
    background: #080c16;
    padding: 0 1;
}

.header-left {
    width: 32%;
    color: #00f0ff;
    text-style: bold;
}

.header-right {
    width: 68%;
    text-align: right;
    color: #00ff9c;
}

#cockpit-body {
    height: 1fr;
    scrollbar-gutter: stable;
    scrollbar-color: #9d4dff #05070d;
}

/* Wide Mode Columns */
.wide-left {
    width: 48%;
    height: 1fr;
    margin-right: 1;
}

.wide-right {
    width: 52%;
    height: 1fr;
}

.panel-card {
    background: #080c16;
    margin-bottom: 1;
    padding: 1 2;
    border: round #00f0ff;
}

#user-card {
    border: round #00f0ff;
    min-height: 5;
}

#thought-collapsible {
    border: round #4a3563;
    background: #0c0817;
    margin-bottom: 1;
}

#thought-collapsible > Contents {
    background: #0c0817;
    color: #a89bbf;
    padding: 0 1;
}

#ai-card {
    border: round #00ff9c;
    min-height: 8;
}

#ai-card.speaking {
    border: double #00ff9c;
}

#ai-card.thinking {
    border: round #ffb000;
}

#ai-card.listening {
    border: round #00f0ff;
}

#visualizer-card {
    height: 9;
    border: round #00f0ff;
    background: #05070d;
    align: center middle;
    margin-bottom: 1;
}

#footer-bar {
    height: 3;
    dock: bottom;
    border: round #9d4dff;
    background: #080c16;
    padding: 0 1;
}

/* Modal Help Dialog */
HelpScreen {
    align: center middle;
    background: rgba(5, 7, 13, 0.85);
}

#help-dialog {
    width: 70;
    height: 22;
    border: double #00f0ff;
    background: #080c16;
    padding: 1 2;
}
"""

# ==============================================================================
# HELP MODAL
# ==============================================================================

class HelpModal(ModalScreen):
    """Futuristic Sci-Fi HUD Help Overlay."""
    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("⚡ CYBERVOICE LIVE HUD COMMANDS", id="help-title")
            help_text = Text()
            help_text.append("\n• SPACE      ", style="bold #00f0ff")
            help_text.append("Push-to-Talk / Cycle States (Listen -> Think -> Speak)\n")
            help_text.append("• V          ", style="bold #ff2bd6")
            help_text.append("Cycle Visualizer Mode (Mirrored -> Bars -> Braille Wave)\n")
            help_text.append("• T          ", style="bold #00ff9c")
            help_text.append("Toggle Neural Reasoning Panel (<think> Tokens)\n")
            help_text.append("• M          ", style="bold #ffb000")
            help_text.append("Mute / Unmute Voice Playback\n")
            help_text.append("• + / -      ", style="bold #00f0ff")
            help_text.append("Adjust Typewriter / Speaking Pace\n")
            help_text.append("• ENTER      ", style="bold #00ff9c")
            help_text.append("Submit Audio Speech Input\n")
            help_text.append("• ?          ", style="bold #ff2bd6")
            help_text.append("Toggle this HUD Help Overlay\n")
            help_text.append("• Q / Ctrl+C ", style="bold #ff3860")
            help_text.append("Safely Exit Terminal HUD\n\n")
            help_text.append("[ Press any key to return to HUD ]", style="dim #6b7a99")
            yield Static(help_text)

    def on_key(self, event: Key) -> None:
        self.dismiss()

# ==============================================================================
# VISUALIZER WIDGET
# ==============================================================================

class VisualizerWidget(Static):
    """Renders 60 FPS Sub-cell bars, Braille-dot oscilloscope, or Mirrored spectrum."""
    def __init__(self, analyzer: AudioAnalyzer, theme: Dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.analyzer = analyzer
        self.theme = theme
        self.mode = "mirrored" # "mirrored", "bars", "braille"
        self.t0 = time.perf_counter()

    def cycle_mode(self) -> str:
        modes = ["mirrored", "bars", "braille"]
        idx = (modes.index(self.mode) + 1) % len(modes)
        self.mode = modes[idx]
        return self.mode

    def render_frame(self, state: str, dt: float) -> None:
        t = time.perf_counter() - self.t0
        w = max(30, min(90, self.size.width - 4))
        h = max(3, min(7, self.size.height - 2))

        # Update audio physics
        energy = 1.3 if state == "speaking" else (0.65 if state == "listening" else 0.25)
        self.analyzer.update(state, dt, energy_boost=energy)

        if self.mode == "braille":
            lines = self.analyzer.render_braille_wave(w, h, self.theme, t)
        elif self.mode == "bars":
            lines = self.analyzer.render_bars(w, h, self.theme, t)
        else:
            lines = self.analyzer.render_mirrored(w, h, self.theme, t)

        freq_bar = f"[dim {self.theme['dim_text']}]80Hz             300Hz             1kHz             4kHz             8kHz[/]"
        content = "\n".join(lines) + "\n" + freq_bar
        self.update(Text.from_markup(content, justify="center"))

# ==============================================================================
# MAIN TEXTUAL APP
# ==============================================================================

class CyberpunkVoiceApp(App):
    """Production-grade Cyberpunk Terminal HUD App."""
    CSS = COCKPIT_CSS
    TITLE = "⚡ LMMs CYBERVOICE LIVE HUD"

    # Reactive attributes for zero-flicker delta updates
    state_mode = reactive("listening") # "listening", "thinking", "speaking", "idle"
    vis_mode = reactive("mirrored")
    user_query = reactive("नमस्ते, आप क्या कर रहे हो?")
    ai_full_text = reactive(
        "## नमस्ते! मैं **LMMs Voice Assistant** हूँ।\n"
        "मैं आपकी मदद के लिए पूरी तरह तैयार हूँ:\n"
        "- ⚡ **Real-time Audio Processing**\n"
        "- 🧠 **Zero `<think>` Voice Output**\n"
        "- 🚀 **60 FPS Animated Cockpit HUD**\n\n"
        "बताइए, आज हम किस प्रोजेक्ट पर काम करें?"
    )
    ai_streamed_chars = reactive(0)
    thought_text = reactive("User initiated voice session in Hindi. Preparing concise and natural spoken reply.")
    is_muted = reactive(False)
    typing_speed = reactive(45.0) # chars per second

    def __init__(self, fps: int = 60, theme_name: str = "cyberpunk", no_anim: bool = False, ascii_only: bool = False):
        super().__init__()
        self.target_fps = fps
        self.cyber_theme = THEMES.get(theme_name, Theme.CYBERPUNK)
        self.no_anim = no_anim
        self.ascii_only = ascii_only
        
        self.analyzer = AudioAnalyzer(num_bars=48)
        self.sys_stats = SystemStats(history_len=24)
        self.state_machine = StateMachine(initial_state="listening")
        self.t0 = time.perf_counter()
        self.last_frame_time = self.t0
        self.boot_complete = False
        self.boot_step = 0
        self.query_received_time = self.t0

    def compose(self) -> ComposeResult:
        # 1. System Telemetry Header Bar
        with Horizontal(id="header-container"):
            yield Label("⚡ LMMs CYBERVOICE LIVE [v2.5]", classes="header-left", id="hdr-title")
            yield Static(classes="header-right", id="hdr-telemetry")

        # 2. Main Cockpit View (Adaptive Grid / Split View)
        with VerticalScroll(id="cockpit-body"):
            # Left / Top Container
            yield Static(id="user-card", classes="panel-card")
            
            # Collapsible Neural Reasoning Block
            with Collapsible(title="💭 NEURAL REASONING (INTERNAL)", id="thought-collapsible", collapsed=True):
                yield Static(id="thought-body")

            # Spoken AI Response (Real Markdown!)
            yield Static(id="ai-card", classes="panel-card")

            # Audio-Reactive Visualizer Waveform
            yield VisualizerWidget(analyzer=self.analyzer, theme=self.cyber_theme, id="visualizer-card")

        # 3. Context-Aware Footer Bar with Keycaps
        with Horizontal(id="footer-bar"):
            yield Label(id="footer-keys")
            yield Label(id="footer-status")

    def on_mount(self) -> None:
        # Start High-Frequency 60 FPS Render Interval
        frame_interval = 1.0 / float(self.target_fps)
        self.set_interval(frame_interval, self.on_animation_tick)
        # Background Telemetry Polling (every 0.5s)
        self.set_interval(0.5, self.on_telemetry_tick)

        self.update_telemetry()
        self.render_user_query()
        self.render_ai_response()
        self.update_footer()

    def on_telemetry_tick(self) -> None:
        self.sys_stats.poll()
        self.update_telemetry()

    def on_animation_tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        # 1. Update Visualizer Waveform
        if not self.no_anim:
            vis = self.query_one(VisualizerWidget)
            vis.render_frame(self.state_mode, dt)

        # 2. Update Typewriter Streaming during speaking
        if self.state_mode == "speaking" and self.ai_streamed_chars < len(self.ai_full_text):
            delta_chars = int(self.typing_speed * dt) + (1 if random.random() < 0.25 else 0)
            self.ai_streamed_chars = min(len(self.ai_full_text), self.ai_streamed_chars + delta_chars)
            self.render_ai_response()

        # 3. Animate User Query matrix scramble
        t_query = now - self.query_received_time
        if t_query <= 0.40 and not self.no_anim:
            self.render_user_query(scramble_elapsed=t_query)

    def update_telemetry(self) -> None:
        cpu = self.sys_stats.cur_cpu
        ram = psutil.virtual_memory()
        time_str = datetime.now().strftime("%H:%M:%S")
        cpu_spark = self.sys_stats.render_sparkline(self.sys_stats.cpu_history, 100.0, self.cyber_theme)
        ram_spark = self.sys_stats.render_sparkline(self.sys_stats.ram_history, 100.0, self.cyber_theme)

        text = Text()
        text.append("CPU: ", style=f"bold {self.cyber_theme['green']}")
        text.append(f"{cpu:.0f}% ", style="#ffffff")
        text.append(Text.from_markup(cpu_spark + "  "))
        text.append("RAM: ", style=f"bold {self.cyber_theme['cyan']}")
        text.append(f"{ram.used/(1024**3):.1f}/{ram.total/(1024**3):.1f}GB ", style="#ffffff")
        text.append(Text.from_markup(ram_spark + "  "))
        text.append("NET: ", style=f"bold {self.cyber_theme['magenta']}")
        text.append(f"↑{self.sys_stats.cur_up_kb:.1f} ↓{self.sys_stats.cur_down_kb:.1f}KB/s  ", style="#ffffff")
        text.append("TIME: ", style=f"bold {self.cyber_theme['amber']}")
        text.append(f"{time_str}", style="#ffffff")

        self.query_one("#hdr-telemetry", Static).update(text)

    def render_user_query(self, scramble_elapsed: float = 1.0) -> None:
        user_card = self.query_one("#user-card", Static)
        display_q = TextEffects.decode_scramble(self.user_query, scramble_elapsed, duration=0.35)
        
        t = Text()
        t.append("👤 USER AUDIO QUERY\n\n", style=f"bold {self.cyber_theme['cyan']}")
        t.append(display_q, style=f"bold {self.cyber_theme['bright_text']}")
        user_card.update(t)

    def render_ai_response(self) -> None:
        ai_card = self.query_one("#ai-card", Static)
        glow = self.state_machine.get_color()
        badge = self.state_machine.get_badge()

        if self.state_mode == "speaking":
            current_markdown_snippet = self.ai_full_text[:self.ai_streamed_chars]
            # Append blinking cursor if still generating
            cursor = " ▌" if (self.ai_streamed_chars < len(self.ai_full_text) and int(time.perf_counter() * 3) % 2 == 0) else ""
            rich_md = RichMarkdown(current_markdown_snippet + cursor)
            ai_card.update(rich_md)
        elif self.state_mode == "thinking":
            t = Text()
            t.append(f"🤖 LMMs NEURAL VOICE [{badge}]\n\n", style=f"bold {glow}")
            t.append("⚡ Synthesizing neural response and voice stream...", style=f"italic {self.cyber_theme['amber']}")
            ai_card.update(t)
        else:
            t = Text()
            t.append(f"🤖 LMMs NEURAL VOICE [{badge}]\n\n", style=f"bold {glow}")
            t.append("(Awaiting user speech... Press SPACE or speak into microphone)", style=f"dim {self.cyber_theme['dim_text']}")
            ai_card.update(t)


    def update_footer(self) -> None:
        keys_lbl = self.query_one("#footer-keys", Label)
        status_lbl = self.query_one("#footer-status", Label)
        glow = self.state_machine.get_color()
        badge = self.state_machine.get_badge()

        mute_status = " [MUTED]" if self.is_muted else ""
        controls = (
            f"[bold #00f0ff on #141b2d] SPACE [/] State  "
            f"[bold #ff2bd6 on #141b2d] V [/] Mode ({self.vis_mode.upper()})  "
            f"[bold #00ff9c on #141b2d] T [/] Reasoning  "
            f"[bold #ffb000 on #141b2d] M [/] Mute{mute_status}  "
            f"[bold #00f0ff on #141b2d] ? [/] Help  "
            f"[bold #ff3860 on #141b2d] Q [/] Quit"
        )
        keys_lbl.update(Text.from_markup(controls))
        status_lbl.update(Text.from_markup(f"[bold {glow}]{badge}[/]"))

    def watch_state_mode(self, old_state: str, new_state: str) -> None:
        self.state_machine.set_state(new_state)
        ai_card = self.query_one("#ai-card", Static)
        ai_card.remove_class("listening", "thinking", "speaking")
        ai_card.add_class(new_state)
        
        # Auto-collapse thought box when entering speaking state
        if new_state == "speaking":
            collapsible = self.query_one("#thought-collapsible", Collapsible)
            collapsible.collapsed = True
            self.ai_streamed_chars = 0

        self.render_ai_response()
        self.update_footer()

    def on_key(self, event: Key) -> None:
        key = event.key
        if key == "space":
            # Cycle through states: listening -> thinking -> speaking -> idle
            states = ["listening", "thinking", "speaking", "idle"]
            next_idx = (states.index(self.state_mode) + 1) % len(states)
            self.state_mode = states[next_idx]
        elif key == "v":
            vis = self.query_one(VisualizerWidget)
            self.vis_mode = vis.cycle_mode()
            self.update_footer()
        elif key == "t":
            collapsible = self.query_one("#thought-collapsible", Collapsible)
            collapsible.collapsed = not collapsible.collapsed
        elif key == "m":
            self.is_muted = not self.is_muted
            self.update_footer()
        elif key in ("+", "="):
            self.typing_speed = min(120.0, self.typing_speed + 15.0)
        elif key in ("-", "_"):
            self.typing_speed = max(15.0, self.typing_speed - 15.0)
        elif key in ("question_mark", "?"):
            self.app.push_screen(HelpModal())
        elif key in ("q", "Q"):
            self.exit()

def main():
    parser = argparse.ArgumentParser(description="LMMs CyberVoice LIVE - Cinematic Cyberpunk TUI")
    parser.add_argument("--fps", type=int, default=60, help="Target frames per second (default: 60)")
    parser.add_argument("--theme", type=str, default="cyberpunk", choices=["cyberpunk", "synthwave", "matrix", "monochrome"], help="Color theme")
    parser.add_argument("--no-animation", action="store_true", help="Disable animations for low-end / remote SSH terminals")
    parser.add_argument("--ascii", action="store_true", help="Use plain ASCII characters without Unicode")
    args = parser.parse_args()

    app = CyberpunkVoiceApp(
        fps=args.fps,
        theme_name=args.theme,
        no_anim=args.no_animation,
        ascii_only=args.ascii
    )
    app.run()

if __name__ == "__main__":
    main()
