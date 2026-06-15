from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table
from rich.align import Align
import sys
import random
import time
import shutil

# Ensure the UI doesn't hit the right edge of the terminal and wrap, breaking Live updates
try:
    terminal_width = shutil.get_terminal_size().columns
    console_width = min(terminal_width - 2, 120)
except:
    console_width = 100

console = Console(width=console_width)

GUI_MODE = False
stream_callback = None
info_callback = None
error_callback = None

ASCII_LOGO = r"""
[bold cyan]
  _      __  __ __  __     
 | |    |  \/  |  \/  |    
 | |    | \  / | \  / |___ 
 | |    | |\/| | |\/| / __|
 | |____| |  | | |  | \__ \
 |______|_|  |_|_|  |_|___/
[/bold cyan]
"""

QUOTES = [
    "Consulting the silicon oracle...",
    "Reticulating neural splines...",
    "Asking the void politely...",
    "Definitely not just predicting tokens...",
    "Warming up the neural networks..."
]

def show_welcome(mode="DEEP", models="qwen3:8b + gemma4"):
    console.print(Align.center(ASCII_LOGO))
    console.print(Align.center("[bold white]Your Local AI Powerhouse by MarkanM Team[/bold white]\n"))
    
    table = Table(show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    table.add_row("/fast", "Quick response (no tools)")
    table.add_row("/deep", "Deep reasoning with tools (Default)")
    table.add_row("/dual", "Multi-model debate mode")
    table.add_row("/file <path>", "Attach file to context")
    table.add_row("/folder <path>", "Attach folder to context")
    table.add_row("/attach", "Open GUI file picker")
    table.add_row("/connector", "Manage Cloud API connectors")
    table.add_row("/undo /redo", "Undo/Redo last action")
    table.add_row("/copy /paste", "Clipboard integration")
    
    console.print(Align.center(table))
    
    console.print(Align.center(f"\n[green]Current Mode:[/green] {mode.upper()}  |  [green]Loaded:[/green] {models}"))
    console.print(Align.center(f"[dim i]{random.choice(QUOTES)}[/dim i]\n"))


def show_help():
    try:
        from lmms.cli_commands import get_help_table
        console.print(get_help_table())
    except ImportError:
        console.print("[red]Could not load CLI commands list.[/red]")
    console.print("[dim i]Type / and press Tab for autocomplete[/dim i]")

def show_error(text: str):
    if GUI_MODE:
        if error_callback:
            error_callback(text)
        return
    console.print(f"[bold red]Error:[/bold red] {text}")

from rich.text import Text

class TimerSpinner:
    def __init__(self, mode, quote):
        self.start_time = time.time()
        self.mode = mode
        self.quote = quote
        
        self.thinking_messages = [
            "Asking the void politely...",
            "Reticulating neural splines...", 
            "Consulting the silicon oracle...",
            "Definitely not predicting tokens...",
            "Summoning intelligence from chaos..."
        ]
            
    def __rich_console__(self, console, options):
        elapsed = time.time() - self.start_time
        msg = self.thinking_messages[int(elapsed/3) % len(self.thinking_messages)]
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spin = spinner_chars[int(elapsed*10) % len(spinner_chars)]
        
        base_text = f"{spin} {msg} {elapsed:.1f}s"
        
        if self.mode == "fast":
            yield Text(base_text, style="bold green")
        elif self.mode == "deep":
            yield Text(base_text, style="bold blue")
        elif self.mode == "dual":
            yield Text(f"Qwen ●————○ Gemma | {base_text}", style="bold purple")
        else:
            yield Text(base_text, style="yellow")



def get_swapping_spinner(model_name: str):
    return Live(
        Spinner("bouncingBar", text=f"[magenta]Switching to {model_name}... (~5s)[/magenta]"),
        transient=True,
    )

def show_response(text: str, prefix: str = ""):
    if prefix:
        console.print(f"{prefix} ", end="")
    console.print(Markdown(text))

def stream_response(generator, model_name: str = "Assistant", show_load_time: bool = False, mode: str = "deep") -> str:
    start_time = time.time()
    full_text = ""
    load_time = None
    
    spinner = TimerSpinner(mode, random.choice(QUOTES))
    
    if GUI_MODE:
        for chunk in generator:
            if load_time is None:
                load_time = time.time() - start_time
            token = chunk.get("message", {}).get("content", "")
            if token:
                full_text += token
                if stream_callback:
                    stream_callback(full_text)
        return full_text

    with Live(spinner, console=console, auto_refresh=True, refresh_per_second=15) as live:
        for chunk in generator:
            if load_time is None:
                load_time = time.time() - start_time

            token = chunk.get("message", {}).get("content", "")
            if token:
                full_text += token
                live.update(
                    Panel(
                        Markdown(full_text),
                        title=f"[bold]{model_name}[/bold]",
                        title_align="left",
                        border_style="cyan"
                    )
                )
        
        total_time = time.time() - start_time
        respond_time = total_time - (load_time or 0)
        tokens = int(len(full_text.split()) * 1.3)
        
        if show_load_time and load_time is not None:
            footer = f"⚡ load: {load_time:.1f}s | respond: {respond_time:.1f}s | ~{tokens} tokens | [dim][c] copy[/dim]"
        else:
            footer = f"⚡ {total_time:.1f}s | ~{tokens} tokens | [dim][c] copy[/dim]"
            
        live.update(Panel(
            Markdown(full_text),
            title=f"[bold]{model_name}[/bold]",
            title_align="left",
            subtitle=footer,
            subtitle_align="right",
            border_style="green",
            padding=(1, 2)
        ))
    return full_text

def render_dual_stats(rounds: int, qwen_time: float, gemma_time: float):
    max_time = max(qwen_time, gemma_time, 0.1)
    qwen_bars = int((qwen_time / max_time) * 20)
    gemma_bars = int((gemma_time / max_time) * 20)
    
    qwen_str = "█" * qwen_bars + "░" * (20 - qwen_bars)
    gemma_str = "█" * gemma_bars + "░" * (20 - gemma_bars)
    
    confidence = max(100 - (rounds * 10), 10)
    
    stats = f"""[bold]DUAL Mode Agreement Reached[/bold]
Rounds Taken: {rounds}/6
Confidence: {confidence}%

[cyan]Qwen [/cyan] {qwen_str} {qwen_time:.1f}s
[green]Gemma[/green] {gemma_str} {gemma_time:.1f}s
"""
    console.print(Panel.fit(stats, border_style="magenta", title="Analytics"))

def show_info(msg: str):
    if GUI_MODE:
        if info_callback:
            info_callback(msg)
        return
    console.print(f"[dim cyan]{msg}[/dim cyan]")

def show_tool_use(tool_name: str, args: str):
    if GUI_MODE:
        if info_callback:
            info_callback(f"Tool: {tool_name}({args})")
        return
    console.print(f"[bold yellow]🛠  {tool_name}[/bold yellow] [dim]{args}[/dim]")
