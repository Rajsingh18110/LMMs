"""
canvas.py — LMMs Rich Terminal Canvas
Markdown, code blocks, tables, graphs rendered beautifully in terminal.
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.columns import Columns
from rich.text import Text
import sys

console = Console()


class Canvas:
    """Rich terminal canvas for rendering AI output."""

    def __init__(self):
        self.enabled = True
        self._history = []

    def render(self, content: str, title: str = "LMMs", lang: str = None):
        """Auto-detect and render content beautifully."""
        stripped = content.strip()

        # Code block detection
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lang_hint = lines[0][3:].strip() or lang or "python"
            code = "\n".join(lines[1:])
            if code.endswith("```"):
                code = code[:-3].strip()
            self._render_code(code, lang_hint, title)

        # Markdown detection (has # headings or ** bold)
        elif any(stripped.startswith(p) for p in ["#", "**", "-", ">", "|"]) or "\n" in stripped:
            self._render_markdown(content, title)

        else:
            self._render_text(content, title)

        self._history.append({"title": title, "content": content})

    def _render_code(self, code: str, lang: str, title: str):
        syntax = Syntax(code, lang, theme="monokai", line_numbers=True, word_wrap=True)
        panel = Panel(syntax, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan", padding=(0, 1))
        console.print(panel)

    def _render_markdown(self, content: str, title: str):
        panel = Panel(
            Markdown(content),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)

    def _render_text(self, content: str, title: str):
        console.print(Panel(content, title=f"[bold]{title}[/bold]", border_style="blue", padding=(0, 2)))

    def render_graph(self, data: dict):
        """Render a text-based graph using plotext."""
        try:
            import plotext as plt
            plt.clf()
            plt.theme("dark")
            plt.title(data.get("title", "Graph"))
            plt.xlabel(data.get("xlabel", ""))
            plt.ylabel(data.get("ylabel", ""))

            gtype = data.get("type", "bar")
            x = data.get("x", [])
            y = data.get("y", [])

            if gtype == "bar":
                plt.bar(x, y)
            elif gtype == "scatter":
                plt.scatter(x, y)
            else:
                plt.plot(x, y)

            plt.show()
        except ImportError:
            console.print("[yellow]plotext not installed. Run /autoset[/yellow]")
        except Exception as e:
            console.print(f"[red]Graph error: {e}[/red]")

    def clear(self):
        console.clear()

    def show_history(self):
        if not self._history:
            console.print("[dim]No canvas history.[/dim]")
            return
        for i, item in enumerate(self._history[-5:]):
            console.print(f"[dim]{i+1}. {item['title']}[/dim]")


# Singleton
_canvas = Canvas()


def get_canvas() -> Canvas:
    return _canvas
