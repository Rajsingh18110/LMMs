#!/usr/bin/env python3
"""
LMMs CyberVoice LIVE - Interactive Visualizer & Animation Demo
==============================================================
Runs an autonomous or interactive preview of the 60 FPS Sci-Fi Terminal Cockpit:
- Audio DSP Visualizers (Mirrored, Bars, Braille-dot oscilloscope)
- Smooth State Transitions: LISTENING -> TRANSCRIBING -> THINKING -> SPEAKING -> IDLE
- Matrix Decode Scramble Effect on User Queries
- Real Rich Markdown Streaming with Karaoke Highlight & Blinking Cursor
- Rolling CPU/RAM/Net Sparklines
- Keyboard Controls: [SPACE] State, [V] Waveform Mode, [T] Reasoning, [M] Mute, [?] Help, [Q] Quit
"""

import sys
import os
import time
import argparse
import asyncio
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.cyberpunk_voice_tui import CyberpunkVoiceApp

DEMO_SCENARIOS = [
    {
        "state": "listening",
        "user_query": "नमस्ते Antigravity! आज क्या अपडेट है?",
        "thoughts": "User greeting in Hindi. Synthesizing briefing on system telemetry and GPU offload.",
        "reply": "## नमस्ते! **LMMs Voice HUD v2.5** लाइव है।\n- ⚡ **60 FPS** Zero-Flicker Cockpit\n- 🔊 **Audio-Reactive** Braille Oscilloscope\n- 🧠 **Zero `<think>` Voice Output**\n\nसब कुछ स्मूथ और हाई-परफॉर्मेंस चल रहा है!",
        "duration": 3.0
    },
    {
        "state": "thinking",
        "user_query": "Can you explain the GPU offload mechanics?",
        "thoughts": "Qwen3-8B occupies 4.7 GB. RTX 3050 has 6.0 GB VRAM. Calculating layer allocation: 36/36 layers offloaded to CUDA.",
        "reply": "### Pure GPU Offload Architecture\nModel **Qwen-8B** is fully loaded into VRAM (`36/36 layers`).\n- Inference Latency: `~2.2s`\n- Memory Bandwidth: `14 Gbps GDDR6`\n- Zero CPU thrashing detected.",
        "duration": 2.5
    },
    {
        "state": "speaking",
        "user_query": "Show me a code snippet for audio FFT.",
        "thoughts": "Generating Python numpy rfft demonstration with Hann window.",
        "reply": "```python\nimport numpy as np\n# 60 FPS Audio FFT\nwindowed = pcm_samples * np.hanning(len(pcm_samples))\nfft_mag = np.abs(np.fft.rfft(windowed))\n```\nAudio spectrum bands are dynamically clustered into **32 log-spaced bins**.",
        "duration": 6.0
    }
]

class DemoVoiceApp(CyberpunkVoiceApp):
    """Extends CyberpunkVoiceApp with autonomous demo scenario cycling."""
    def __init__(self, auto_cycle: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.auto_cycle = auto_cycle
        self.scenario_idx = 0
        self.last_cycle_time = time.perf_counter()

    def on_mount(self) -> None:
        super().on_mount()
        if self.auto_cycle:
            self.set_interval(0.5, self.check_auto_cycle)

    def check_auto_cycle(self) -> None:
        now = time.perf_counter()
        scenario = DEMO_SCENARIOS[self.scenario_idx]
        if now - self.last_cycle_time >= scenario["duration"]:
            self.scenario_idx = (self.scenario_idx + 1) % len(DEMO_SCENARIOS)
            nxt = DEMO_SCENARIOS[self.scenario_idx]
            self.user_query = nxt["user_query"]
            self.thought_text = nxt["thoughts"]
            self.ai_full_text = nxt["reply"]
            self.state_mode = nxt["state"]
            self.query_received_time = now
            self.last_cycle_time = now

def main():
    parser = argparse.ArgumentParser(description="LMMs CyberVoice Visualizer Demo")
    parser.add_argument("--fps", type=int, default=20, help="Target FPS (default: 20)")
    parser.add_argument("--theme", type=str, default="executive", choices=["executive", "cyberpunk", "synthwave", "matrix", "monochrome"], help="HUD color theme")
    parser.add_argument("--no-animation", action="store_true", help="Disable animations for slow/SSH connections")
    parser.add_argument("--manual", action="store_true", help="Disable auto-cycle and control manually with Space/V/T/M")
    args = parser.parse_args()

    app = DemoVoiceApp(
        auto_cycle=not args.manual,
        fps=args.fps,
        theme_name=args.theme,
        no_anim=args.no_animation
    )
    app.run()

if __name__ == "__main__":
    main()
