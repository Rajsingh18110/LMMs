"""
LMMs Standalone TUI (Terminal User Interface)
Interactive terminal studio powered by Rich and the decoupled LMMs Engine Client.
"""

from __future__ import annotations

import os
import sys
import time
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.markdown import Markdown

from lmms.cli.client import CLIClient
from lmms.cli.remote import RemoteManager
from lmms.cli.interactive import InteractiveChat

COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_WHITE = "\033[37m"

console = Console()


class LMMsTUI:
    """Standalone Terminal User Interface for local and LAN LMMs engines."""

    def __init__(self):
        self.client = CLIClient()
        self.remote_mgr = RemoteManager()
        self.active_model: Optional[str] = None
        self._ensure_active_model()

    def _ensure_active_model(self):
        try:
            ps = self.client.get_ps()
            if ps:
                self.active_model = ps[0].get("name", ps[0].get("model"))
            if not self.active_model:
                models = self.client.list_models()
                if models:
                    self.active_model = models[0].get("name")
        except Exception:
            pass

    def render_header(self) -> Panel:
        target_info = self.remote_mgr.get_active_info()
        url = target_info.get("url", "http://localhost:11435")
        mode = target_info.get("mode", "local").upper()

        status_text = Text()
        status_text.append("⚡ Target: ", style="bold cyan")
        status_text.append(f"{url} ({mode})  ", style="white")

        status_text.append("│ Active Model: ", style="bold green")
        status_text.append(f"{self.active_model or 'None Selected'}  ", style="bold yellow")

        try:
            stats = self.client.get_stats()
            vram = stats.get("vram_used_gb", 0)
            if vram:
                status_text.append(f"│ VRAM: {vram:.1f}GB  ", style="magenta")
        except Exception:
            pass

        return Panel(
            status_text,
            title="[bold cyan]LMMs Interactive Terminal Studio[/bold cyan]",
            subtitle="[dim]Type /help for slash commands | /exit to quit[/dim]",
            border_style="cyan"
        )

    def show_catalog(self):
        try:
            models = self.client.list_models()
            ps = self.client.get_ps()
            active_names = {p.get("name", p.get("model")) for p in ps}

            table = Table(title="Model Inventory", border_style="dim")
            table.add_column("Model Name", style="cyan bold")
            table.add_column("Size (GB)", justify="right")
            table.add_column("State", style="green")

            for m in models:
                name = m.get("name", str(m))
                size = f"{m.get('size_gb', 0):.1f} GB" if m.get("size_gb") else "-"
                is_active = name in active_names or (self.active_model and self.active_model in name)
                state = "[bold green]● Active[/bold green]" if is_active else "[dim]Stored[/dim]"
                table.add_row(name, size, state)

            console.print(table)
        except Exception as e:
            console.print(f"[red]Error fetching catalog: {e}[/red]")

    def run(self):
        console.clear()
        console.print(self.render_header())

        while True:
            try:
                prompt_label = f"\n[bold cyan]lmms[/bold cyan] ([green]{self.active_model or 'none'}[/green]) > "
                user_input = console.input(prompt_label).strip()

                if not user_input:
                    continue

                if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                    console.print("[dim]Exiting LMMs Terminal Studio...[/dim]")
                    break

                elif user_input.lower() in ["/clear", "clear"]:
                    console.clear()
                    console.print(self.render_header())

                elif user_input.lower() in ["/help", "help"]:
                    table = Table(title="Available Commands", border_style="cyan")
                    table.add_column("Command", style="cyan bold")
                    table.add_column("Description")
                    table.add_row("/models, /list", "Show local and loaded models")
                    table.add_row("/use <model>", "Select active model for chat")
                    table.add_row("/chat [model]", "Enter streaming conversation session")
                    table.add_row("/connect <ip[:port]>", "Target remote LAN engine")
                    table.add_row("/mode <auto|1|2>", "Switch engine dispatch mode")
                    table.add_row("/stats", "Inspect hardware and memory telemetry")
                    table.add_row("/clear", "Clear terminal screen")
                    table.add_row("/exit", "Exit LMMs Studio")
                    console.print(table)

                elif user_input.lower() in ["/models", "/list"]:
                    self.show_catalog()

                elif user_input.lower().startswith("/use "):
                    target = user_input.split(" ", 1)[1].strip()
                    self.active_model = target
                    console.print(f"[green]✔ Active model set to:[/green] [bold white]{target}[/bold white]")

                elif user_input.lower().startswith("/connect "):
                    target = user_input.split(" ", 1)[1].strip()
                    ok, msg = self.remote_mgr.set_remote(target)
                    if ok:
                        console.print(f"[green]✔ {msg}[/green]")
                        self.client = CLIClient()
                        self._ensure_active_model()
                    else:
                        console.print(f"[red]✖ {msg}[/red]")

                elif user_input.lower().startswith("/mode"):
                    parts = user_input.split(" ")
                    if len(parts) > 1:
                        mode_val = parts[1].strip()
                        import requests
                        target_url = self.remote_mgr.get_active_url()
                        try:
                            r = requests.post(f"{target_url}/v1/engine/mode", json={"mode": mode_val}, timeout=5)
                            if r.status_code == 200:
                                console.print(f"[green]✔ Engine mode switched to '{mode_val}'[/green]")
                            else:
                                console.print(f"[red]Failed to switch mode: {r.text}[/red]")
                        except Exception as e:
                            console.print(f"[red]Error contacting engine: {e}[/red]")
                    else:
                        console.print("[dim]Usage: /mode <auto|1|2>[/dim]")

                elif user_input.lower().startswith("/chat"):
                    parts = user_input.split(" ", 1)
                    model_to_use = parts[1].strip() if len(parts) > 1 else self.active_model
                    if not model_to_use:
                        console.print("[yellow]Please specify a model: /chat <model_name>[/yellow]")
                    else:
                        chat = InteractiveChat(model_name=model_to_use)
                        chat.run()
                        console.clear()
                        console.print(self.render_header())

                elif user_input.lower() in ["/stats"]:
                    stats = self.client.get_stats()
                    console.print(Panel(str(stats), title="System Telemetry", border_style="dim"))

                else:
                    # Direct conversation prompt
                    if not self.active_model:
                        console.print("[yellow]⚠ No model active. Run /models and /use <model> first.[/yellow]")
                        continue

                    console.print(f"\n[dim]Querying {self.active_model}...[/dim]")
                    t0 = time.time()
                    full_response = ""
                    token_count = 0

                    try:
                        for chunk in self.client.stream_chat(self.active_model, [{"role": "user", "content": user_input}]):
                            full_response += chunk
                            token_count += 1
                            sys.stdout.write(chunk)
                            sys.stdout.flush()

                        elapsed = time.time() - t0
                        tps = token_count / elapsed if elapsed > 0 else 0
                        sys.stdout.write(f"\n\n{COLOR_DIM}[{token_count} tokens in {elapsed:.2f}s | {tps:.1f} tok/s]{COLOR_RESET}\n")
                    except Exception as e:
                        console.print(f"\n[red]Error: {e}[/red]")

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Exiting...[/dim]")
                break


def launch_tui(args: Optional[List[str]] = None) -> None:
    """Entry point for standalone TUI."""
    tui = LMMsTUI()
    tui.run()


if __name__ == "__main__":
    launch_tui()
