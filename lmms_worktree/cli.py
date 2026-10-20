"""
lmms_worktree.cli - CLI Command Handler for /worktree.
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from lmms_worktree.manager import default_worktree_manager

console = Console()


def handle_worktree_cli(args: List[str], workspace: str) -> None:
    """Dispatches /worktree commands."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "on":
        try:
            session = default_worktree_manager.enable(workspace)
            console.print(Panel(
                f"[bold green]✓ Git Worktree Isolation Active[/bold green]\n\n"
                f"[dim]Worktree Directory:[/dim] [cyan]{session.worktree_dir}[/cyan]\n"
                f"[dim]Ephemeral Branch:[/dim]   [magenta]{session.ephemeral_branch}[/magenta]\n"
                f"[dim]Base Commit:[/dim]        [yellow]{session.base_commit[:8]}[/yellow]\n\n"
                f"[white]All agent file edits and shell commands now run inside the worktree.\n"
                f"Your working tree is 100% untouched until you run [bold cyan]/worktree apply[/bold cyan].[/white]",
                title="[bold green]Worktree Sandbox[/bold green]",
                border_style="green",
            ))
        except Exception as e:
            console.print(f"[bold red]Failed to enable worktree:[/bold red] {e}")

    elif subcmd in ("off", "discard"):
        status = default_worktree_manager.status(workspace)
        if not status.active:
            console.print("[yellow]Worktree isolation is not currently active.[/yellow]")
            return

        if status.changed_files and subcmd == "off":
            console.print(f"[bold yellow]Warning: Worktree has {len(status.changed_files)} unapplied changes.[/bold yellow]")
            ans = input("Discard all worktree changes? (y/n): ").strip().lower()
            if ans != "y":
                console.print("[dim]Worktree left active. Use `/worktree apply` to merge changes or `/worktree discard` to force wipe.[/dim]")
                return

        default_worktree_manager.discard(workspace)
        console.print("[bold yellow]✓ Worktree discarded and cleaned up. Working directory restored to main workspace.[/bold yellow]")

    elif subcmd == "status":
        status = default_worktree_manager.status(workspace)
        if not status.active:
            console.print(Panel(
                "[dim]Status:[/dim] [yellow]Inactive (Normal Workspace Mode)[/yellow]\n"
                "Run [bold cyan]/worktree on[/bold cyan] to enable isolated execution.",
                title="[bold cyan]Git Worktree Status[/bold cyan]",
                border_style="cyan",
            ))
        else:
            files_desc = "\n".join(f"  • {f}" for f in status.changed_files) if status.changed_files else "  [dim]No modified files yet[/dim]"
            console.print(Panel(
                f"[dim]Status:[/dim]           [bold green]ACTIVE (Isolated)[/bold green]\n"
                f"[dim]Worktree Dir:[/dim]     [cyan]{status.worktree_dir}[/cyan]\n"
                f"[dim]Branch:[/dim]           [magenta]{status.ephemeral_branch}[/magenta]\n"
                f"[dim]Base Commit:[/dim]      [yellow]{status.base_commit[:8] if status.base_commit else 'unknown'}[/yellow]\n\n"
                f"[bold white]Modified Files in Worktree ({len(status.changed_files)}):[/bold white]\n{files_desc}",
                title="[bold green]Git Worktree Status[/bold green]",
                border_style="green",
            ))

    elif subcmd == "diff":
        status = default_worktree_manager.status(workspace)
        if not status.active:
            console.print("[yellow]Worktree isolation is not currently active.[/yellow]")
            return

        diff_text = default_worktree_manager.diff(workspace)
        if diff_text == "No changes in worktree.":
            console.print("[dim]No changes in worktree.[/dim]")
        else:
            console.print(Panel(
                Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                title="[bold cyan]Worktree Unified Diff[/bold cyan]",
                border_style="cyan",
            ))

    elif subcmd == "apply":
        status = default_worktree_manager.status(workspace)
        if not status.active:
            console.print("[yellow]Worktree isolation is not currently active.[/yellow]")
            return

        # Show diff before applying
        diff_text = default_worktree_manager.diff(workspace)
        if diff_text != "No changes in worktree.":
            console.print(Panel(
                Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                title="[bold yellow]Pending Changes to Merge[/bold yellow]",
                border_style="yellow",
            ))

        ans = input("Merge and apply these changes to your working tree? (y/n): ").strip().lower()
        if ans != "y":
            console.print("[dim]Apply cancelled. Worktree remains active.[/dim]")
            return

        success, msg = default_worktree_manager.apply(workspace)
        if success:
            console.print(f"[bold green]✓ {msg}[/bold green]")
        else:
            console.print(f"[bold red]✖ {msg}[/bold red]")

    else:
        console.print(
            "Usage: /worktree on | /worktree off | /worktree status | /worktree diff | /worktree apply | /worktree discard"
        )
