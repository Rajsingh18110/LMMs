#!/usr/bin/env python3
"""
Cyberpunk Voice Assistant TUI (Textual Framework)
High-aesthetic, futuristic terminal interface for LMMs Voice Assistant.
Implements:
1. Cyberpunk Neon Theme (#0A0A12, #BD00FF, #00E5FF, #00FFA3, #FFB800)
2. Live System Telemetry (CPU, RAM, Net speed, Time)
3. Collapsible Neural Thought Box (<think> isolation)
4. Smooth ASCII Equalizer Sound Wave (30 FPS block animation)
5. Typewriter Streaming with Hindi Devanagari & English support
6. Dynamic Border Glow / Status Pulsing
"""

import math
import time
import re
from datetime import datetime
import psutil

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.widgets import Static, Collapsible, Label, Footer
from textual.reactive import reactive
from rich.text import Text
from rich import box
from rich.panel import Panel

# ==========================================
# CYBERPUNK STYLING & PALETTE (TCSS)
# ==========================================
CYBER_CSS = """
Screen {
    background: #0A0A12;
    color: #E2E8F0;
    layout: vertical;
    padding: 0 1;
}

#header-container {
    height: 3;
    dock: top;
    margin-bottom: 1;
    border: round #BD00FF;
    background: #0E0E1A;
    padding: 0 1;
}

.header-title {
    color: #00E5FF;
    text-style: bold;
    width: 35%;
}

.header-telemetry {
    color: #00FFA3;
    text-align: right;
    width: 65%;
}

#chat-scroll {
    height: 1fr;
    scrollbar-gutter: stable;
    scrollbar-color: #BD00FF #0A0A12;
}

.panel-box {
    margin-bottom: 1;
    padding: 1 2;
    background: #0E0E1A;
}

#user-box {
    border: round #00E5FF;
}

#thought-collapsible {
    border: round #4A3563;
    background: #14111D;
    color: #A89BBF;
    margin-bottom: 1;
}

#thought-collapsible > Contents {
    background: #14111D;
    color: #8C7A9E;
    padding: 0 1;
}

#ai-box {
    border: round #BD00FF;
    min-height: 5;
}

#ai-box.speaking {
    border: round #00FFA3;
}

#ai-box.thinking {
    border: round #FFB800;
}

#ai-box.listening {
    border: round #00E5FF;
}

#waveform-box {
    height: 5;
    dock: bottom;
    border: round #00E5FF;
    background: #0E0E1A;
    align: center middle;
    margin-top: 1;
}

#footer-bar {
    height: 3;
    dock: bottom;
    border: round #BD00FF;
    background: #0E0E1A;
    padding: 0 1;
}
"""

def extract_thoughts_and_response(text: str):
    """Cleanly isolates <think> reasoning tokens from spoken response."""
    thoughts = ""
    spoken = text
    if "<think>" in text:
        if "</think>" in text:
            m = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
            if m:
                thoughts = m.group(1).strip()
            spoken = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        else:
            parts = text.split("<think>", 1)
            thoughts = parts[1].strip()
            spoken = parts[0].strip()
    return thoughts, spoken

class TelemetryHeader(Static):
    """Displays real-time hardware telemetry and time."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_net_time = time.time()
        self.last_net_io = psutil.net_io_counters()
        self.cached_net_str = "↑0.0 ↓0.0 KB/s"

    def _get_net_speeds(self):
        now = time.time()
        dt = now - self.last_net_time
        if dt >= 1.0:
            try:
                curr = psutil.net_io_counters()
                up_kb = (curr.bytes_sent - self.last_net_io.bytes_sent) / (dt * 1024.0)
                dn_kb = (curr.bytes_recv - self.last_net_io.bytes_recv) / (dt * 1024.0)
                self.cached_net_str = f"↑{up_kb:.1f} ↓{dn_kb:.1f} KB/s"
                self.last_net_io = curr
                self.last_net_time = now
            except Exception:
                pass
        return self.cached_net_str

    def update_telemetry(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        time_str = datetime.now().strftime("%H:%M:%S")
        net = self._get_net_speeds()

        text = Text()
        text.append("CPU: ", style="bold #00FFA3")
        text.append(f"{cpu:.0f}%  ", style="#FFFFFF")
        text.append("RAM: ", style="bold #00E5FF")
        text.append(f"{ram.used/(1024**3):.1f}/{ram.total/(1024**3):.1f}GB  ", style="#FFFFFF")
        text.append("NET: ", style="bold #BD00FF")
        text.append(f"{net}  ", style="#FFFFFF")
        text.append("TIME: ", style="bold #FFB800")
        text.append(f"{time_str}", style="#FFFFFF")
        self.update(text)

class EqualizerWaveform(Static):
    """Renders real-time 30 FPS multi-row ASCII frequency wave equalizer."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t0 = time.perf_counter()
        self.mode = "listening"
        self.amplitude = 0.2

    def update_frame(self, mode: str):
        self.mode = mode
        t = time.perf_counter() - self.t0
        is_active = (mode in ("speaking", "listening"))
        self.amplitude = (0.75 + 0.25 * math.sin(t * 8.0)) if is_active else 0.15

        width = max(30, min(70, self.size.width - 4))
        rows = 3
        heights = []
        for x in range(width):
            norm_x = (x - width / 2.0) / (width * 0.42)
            env = math.exp(-norm_x * norm_x)
            h = (
                math.sin(x * 0.35 + t * 5.2) * 0.45 +
                math.sin(x * 0.72 - t * 3.6) * 0.30 +
                math.cos(x * 0.22 + t * 2.1) * 0.25
            )
            val = max(0.08, abs(h) * env * self.amplitude * rows)
            heights.append(val)

        row_colors = ["#00E5FF", "#00FFA3", "#BD00FF"]
        res_text = Text()
        for r in range(rows - 1, -1, -1):
            color = row_colors[r % len(row_colors)]
            chars = []
            for h in heights:
                diff = h - r
                if diff >= 1.0:
                    chars.append("█")
                elif diff >= 0.75:
                    chars.append("▇")
                elif diff >= 0.50:
                    chars.append("▆")
                elif diff >= 0.25:
                    chars.append("▃")
                else:
                    chars.append(" ")
            res_text.append("".join(chars) + "\n", style=f"bold {color}")
        self.update(res_text)

class CyberpunkVoiceApp(App):
    """The complete Cyberpunk Voice Assistant TUI."""
    CSS = CYBER_CSS
    TITLE = "⚡ LMMs CyberVoice Live"

    mode = reactive("listening") # listening, thinking, speaking
    user_query = reactive("नमस्ते, आप क्या कर रहे हो?")
    ai_full_text = reactive("हाँ जी! मैं एक एआई असिस्टेंट हूँ जो आपकी मदद करने के लिए यहाँ हूँ।")
    ai_displayed_text = reactive("")
    thought_text = reactive("User greeted in Hindi. Formulating concise, friendly response without internal monologue.")

    def compose(self) -> ComposeResult:
        # 1. Header Bar
        with Horizontal(id="header-container"):
            yield Label("⚡ LMMs CYBERVOICE LIVE [v2.4]", classes="header-title")
            yield TelemetryHeader(id="telemetry", classes="header-telemetry")

        # 2. Central Scroll Area
        with VerticalScroll(id="chat-scroll"):
            # User Input Box
            yield Static(id="user-box", classes="panel-box")
            
            # Collapsible Neural Thoughts
            with Collapsible(title="💭 NEURAL REASONING (INTERNAL)", id="thought-collapsible", collapsed=True):
                yield Static(id="thought-content")

            # AI Response Box
            yield Static(id="ai-box", classes="panel-box")

        # 3. Dynamic Audio Equalizer Waveform
        yield EqualizerWaveform(id="waveform-box")

        # 4. Footer Status & Controls
        with Horizontal(id="footer-bar"):
            yield Label("[Space]: Cycle Status  |  [T]: Demo Typewriter  |  [Ctrl+C]: Exit", id="footer-keys")
            yield Label(id="footer-status")

    def on_mount(self) -> None:
        # Telemetry timer
        self.set_interval(1.0, self.update_telemetry)
        # Waveform animation timer (30 FPS)
        self.set_interval(1.0 / 30.0, self.update_wave)
        # Typewriter timer
        self.typewriter_index = 0
        self.set_interval(0.03, self.tick_typewriter)

        self.update_ui_state()

    def update_telemetry(self) -> None:
        telem = self.query_one(TelemetryHeader)
        telem.update_telemetry()

    def update_wave(self) -> None:
        wave = self.query_one(EqualizerWaveform)
        wave.update_frame(self.mode)

    def watch_mode(self, old_mode: str, new_mode: str) -> None:
        ai_box = self.query_one("#ai-box")
        ai_box.remove_class("listening", "thinking", "speaking")
        ai_box.add_class(new_mode)
        self.update_ui_state()

    def tick_typewriter(self) -> None:
        if self.mode == "speaking" and self.typewriter_index < len(self.ai_full_text):
            self.typewriter_index += 1
            self.ai_displayed_text = self.ai_full_text[:self.typewriter_index]
            self.render_ai_box()

    def render_ai_box(self) -> None:
        ai_box = self.query_one("#ai-box")
        t = Text()
        t.append("🤖 LMMs NEURAL VOICE  ", style="bold #BD00FF")
        if self.mode == "speaking":
            t.append("● SPEAKING\n\n", style="bold #00FFA3")
            t.append(self.ai_displayed_text, style="bold #00FFA3")
        elif self.mode == "thinking":
            t.append("⚡ SYNTHESIZING RESPONSE...\n\n", style="bold #FFB800")
            t.append("(Generating neural reasoning and stream output...)", style="dim #FFB800")
        else:
            t.append("● LISTENING\n\n", style="bold #00E5FF")
            t.append("(Awaiting user speech...)", style="dim #777777")
        ai_box.update(t)

    def update_ui_state(self) -> None:
        # Update user box
        user_box = self.query_one("#user-box")
        u_text = Text()
        u_text.append("👤 USER AUDIO QUERY\n\n", style="bold #00E5FF")
        u_text.append(self.user_query, style="bold #FFFFFF")
        user_box.update(u_text)

        # Update thought box
        thought_content = self.query_one("#thought-content")
        thought_content.update(Text(self.thought_text, style="dim #A89BBF"))

        # Update AI box
        self.render_ai_box()

        # Update footer
        status_lbl = self.query_one("#footer-status")
        if self.mode == "speaking":
            status_lbl.update(Text("● STATUS: SPEAKING", style="bold #00FFA3"))
        elif self.mode == "thinking":
            status_lbl.update(Text("⚡ STATUS: THINKING", style="bold #FFB800"))
        else:
            status_lbl.update(Text("● STATUS: LISTENING", style="bold #00E5FF"))

    def action_cycle_status(self) -> None:
        modes = ["listening", "thinking", "speaking"]
        idx = (modes.index(self.mode) + 1) % len(modes)
        self.mode = modes[idx]
        if self.mode == "speaking":
            self.typewriter_index = 0
            self.ai_displayed_text = ""

    def on_key(self, event) -> None:
        if event.key == "space":
            self.action_cycle_status()
        elif event.key == "t":
            self.mode = "speaking"
            self.typewriter_index = 0
            self.ai_displayed_text = ""

if __name__ == "__main__":
    app = CyberpunkVoiceApp()
    app.run()
