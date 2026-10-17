"""
LMMs CLI Engine - Interactive Streaming Terminal Chat
Minimalist, high-throughput streaming interface for local and remote models.
"""

from __future__ import annotations

import readline  # enables arrow key navigation & command history
import sys
import time
from typing import List, Dict, Optional

from lmms.cli.client import CLIClient
from lmms.cli.remote import RemoteManager

# ANSI Formatting
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_WHITE = "\033[1;37m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"


class InteractiveChat:
    """Terminal chat loop with real-time token streaming and network telemetry."""

    def __init__(self, model_name: str, base_url: Optional[str] = None):
        self.model_name = model_name
        self.client = CLIClient(base_url)
        self.remote_mgr = self.client.remote_mgr
        self.messages: List[Dict[str, str]] = []
        self.mode = "deep"
        self.think = True

    def run(self) -> None:
        """Start the interactive chat session."""
        info = self.remote_mgr.get_active_info()
        online, latency, _ = self.remote_mgr.ping(info["url"])
        lat_str = f"{latency}ms" if online else "OFFLINE"
        status_color = COLOR_GREEN if online else COLOR_RED

        # Session Header
        sys.stdout.write(f"\n💬 {COLOR_BOLD_WHITE}lmms-cli{COLOR_RESET} {COLOR_DIM}v1.0.0{COLOR_RESET}\n")
        sys.stdout.write(
            f"⚡ {COLOR_BOLD_WHITE}Target:{COLOR_RESET} {info['url']} "
            f"[{status_color}{info['mode'].upper()}{COLOR_RESET} · {COLOR_DIM}Ping: {lat_str}{COLOR_RESET}]\n"
        )
        sys.stdout.write(
            f"🧠 {COLOR_BOLD_WHITE}Model:{COLOR_RESET} {COLOR_CYAN}{self.model_name}{COLOR_RESET} "
            f"{COLOR_DIM}(Air Auto-Dispatch){COLOR_RESET}\n"
        )
        sys.stdout.write(f"{COLOR_DIM}ℹ Type /help for session controls, /exit to quit.{COLOR_RESET}\n\n")
        sys.stdout.flush()

        while True:
            try:
                # Prompt
                user_input = input(f"{COLOR_BOLD_CYAN}❯{COLOR_RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                sys.stdout.write(f"\n{COLOR_DIM}Exiting session.{COLOR_RESET}\n")
                break

            if not user_input:
                continue

            # Command Handling
            if user_input.startswith("/"):
                if self._handle_command(user_input):
                    break
                continue

            # Add to history
            self.messages.append({"role": "user", "content": user_input})

            # Stream Assistant Response
            sys.stdout.write(f"\n{COLOR_CYAN}lmms{COLOR_RESET} {COLOR_DIM}›{COLOR_RESET} ")
            sys.stdout.flush()

            t0 = time.perf_counter()
            token_count = 0
            full_response = ""

            try:
                for chunk in self.client.stream_chat(
                    model_name=self.model_name,
                    messages=self.messages,
                    mode=self.mode,
                    think=self.think
                ):
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    full_response += chunk
                    token_count += 1

                elapsed = max(0.01, time.perf_counter() - t0)
                tok_per_sec = token_count / elapsed

                self.messages.append({"role": "assistant", "content": full_response})

                # Stream Metrics Bar (Node.js/Yarn Dim Style)
                sys.stdout.write(
                    f"\n\n{COLOR_DIM}⏱ {token_count} chunks · {tok_per_sec:.1f} tok/s · {elapsed:.2f}s{COLOR_RESET}\n\n"
                )
                sys.stdout.flush()

            except Exception as e:
                sys.stdout.write(f"\n{COLOR_RED}✖ Error:{COLOR_RESET} {e}\n\n")
                sys.stdout.flush()

    def _handle_command(self, cmd_str: str) -> bool:
        """Handle in-session slash commands. Returns True if session should terminate."""
        parts = cmd_str.split()
        cmd = parts[0].lower()

        if cmd in ["/exit", "/quit", "/q"]:
            sys.stdout.write(f"{COLOR_DIM}Session ended.{COLOR_RESET}\n")
            return True

        elif cmd == "/help":
            sys.stdout.write(
                f"\n{COLOR_BOLD_WHITE}Session Controls:{COLOR_RESET}\n"
                f"  {COLOR_CYAN}/switch <model>{COLOR_RESET}    Switch active model\n"
                f"  {COLOR_CYAN}/models{COLOR_RESET}            List available models on target engine\n"
                f"  {COLOR_CYAN}/ps{COLOR_RESET}                Show currently running models\n"
                f"  {COLOR_CYAN}/stats{COLOR_RESET}             Show target hardware & memory profiler\n"
                f"  {COLOR_CYAN}/ping{COLOR_RESET}              Measure round-trip network latency\n"
                f"  {COLOR_CYAN}/mode [deep|fast]{COLOR_RESET} Toggle inference reasoning mode\n"
                f"  {COLOR_CYAN}/clear{COLOR_RESET}             Clear conversation history & screen\n"
                f"  {COLOR_CYAN}/exit{COLOR_RESET}              Exit chat\n\n"
            )

        elif cmd == "/ping":
            info = self.remote_mgr.get_active_info()
            online, lat, _ = self.remote_mgr.ping(info["url"])
            color = COLOR_GREEN if online else COLOR_RED
            status = "Online" if online else "Offline"
            sys.stdout.write(f"⚡ {info['url']} -> {color}{status}{COLOR_RESET} ({lat}ms)\n\n")

        elif cmd == "/models":
            models = self.client.list_models()
            if not models:
                sys.stdout.write(f"{COLOR_DIM}No models registered or target engine is idle.{COLOR_RESET}\n\n")
            else:
                sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Available Models:{COLOR_RESET}\n")
                for m in models:
                    name = m.get("name", str(m))
                    loc = m.get("location", "")
                    loc_str = f" {COLOR_DIM}({loc}){COLOR_RESET}" if loc else ""
                    is_cur = f" {COLOR_GREEN}*active*{COLOR_RESET}" if name == self.model_name else ""
                    sys.stdout.write(f"  • {COLOR_BOLD_WHITE}{name}{COLOR_RESET}{loc_str}{is_cur}\n")
                sys.stdout.write("\n")

        elif cmd == "/ps":
            ps_list = self.client.get_ps()
            if not ps_list:
                sys.stdout.write(f"{COLOR_DIM}No models currently in active memory.{COLOR_RESET}\n\n")
            else:
                sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Active Memory Footprint:{COLOR_RESET}\n")
                for item in ps_list:
                    m = item.get("model", "unknown")
                    vram = item.get("vram_gb", 0)
                    ram = item.get("ram_gb", 0)
                    sys.stdout.write(f"  • {COLOR_BOLD_WHITE}{m}{COLOR_RESET} {COLOR_DIM}[VRAM: {vram:.1f}GB | RAM: {ram:.1f}GB]{COLOR_RESET}\n")
                sys.stdout.write("\n")

        elif cmd == "/stats":
            try:
                stats = self.client.get_stats()
                sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Engine Telemetry:{COLOR_RESET}\n")
                for k, v in stats.items():
                    sys.stdout.write(f"  {COLOR_CYAN}{k:<20}{COLOR_RESET} : {COLOR_DIM}{v}{COLOR_RESET}\n")
                sys.stdout.write("\n")
            except Exception as e:
                sys.stdout.write(f"{COLOR_RED}Could not fetch stats:{COLOR_RESET} {e}\n\n")

        elif cmd == "/switch":
            if len(parts) < 2:
                sys.stdout.write("Usage: /switch <model_name>\n\n")
            else:
                self.model_name = parts[1]
                sys.stdout.write(f"✔ Switched active model to {COLOR_CYAN}{self.model_name}{COLOR_RESET}\n\n")

        elif cmd == "/mode":
            if len(parts) > 1 and parts[1] in ["deep", "fast", "code"]:
                self.mode = parts[1]
                sys.stdout.write(f"✔ Reasoning mode set to {COLOR_CYAN}{self.mode}{COLOR_RESET}\n\n")
            else:
                sys.stdout.write(f"Current mode: {self.mode}. Options: /mode deep | fast | code\n\n")

        elif cmd == "/clear":
            self.messages.clear()
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(f"{COLOR_DIM}Screen & conversation memory cleared.{COLOR_RESET}\n\n")

        else:
            sys.stdout.write(f"{COLOR_DIM}Unknown command: {cmd}. Type /help for options.{COLOR_RESET}\n\n")

        sys.stdout.flush()
        return False
