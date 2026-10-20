"""
lmms_sessions.cli - CLI Command Handler for /sessions, /fork, /resume, /rename, /compact.
"""

from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lmms_sessions.compactor import SessionCompactor
from lmms_sessions.models import CompactionResult
from lmms_sessions.store import SessionStore

console = Console()


class SessionCLI:
    """Handles session management commands and maintains active session pointer."""

    def __init__(self, store: Optional[SessionStore] = None, compactor: Optional[SessionCompactor] = None):
        self.store = store or SessionStore()
        self.compactor = compactor or SessionCompactor()
        self.active_session_id: str = ""
        self._ensure_initial_session()

    def _ensure_initial_session(self) -> str:
        """Ensures at least one session exists and sets it as active."""
        if self.active_session_id:
            return self.active_session_id

        sessions = self.store.list_sessions()
        if sessions:
            self.active_session_id = sessions[0]["session_id"]
        else:
            new_s = self.store.create_session(title="Default Session")
            self.active_session_id = new_s.session_id

        return self.active_session_id



    def handle_sessions(self, args: List[str]) -> None:
        """Dispatches `/sessions` command."""
        sessions = self.store.list_sessions()
        if not sessions:
            console.print("[dim]No sessions found. A default session will be created on message send.[/dim]")
            return

        table = Table(title="[bold cyan]LMMs Conversation Sessions[/bold cyan]", border_style="cyan")
        table.add_column("Active", justify="center", style="bold green", width=8)
        table.add_column("ID", style="yellow", width=10)
        table.add_column("Title", style="white")
        table.add_column("Parent", style="magenta", width=12)
        table.add_column("Msgs", justify="right", style="cyan", width=8)
        table.add_column("Updated", style="dim", width=20)

        for s in sessions:
            is_active = (s["session_id"] == self.active_session_id)
            active_marker = "★ [green]ACTIVE[/green]" if is_active else ""
            parent_id = s.get("parent_session_id") or "—"
            dt_str = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")

            table.add_row(
                active_marker,
                s["session_id"],
                s["title"],
                parent_id,
                str(s["message_count"]),
                dt_str,
            )

        console.print(table)
        console.print("[dim]Use [bold cyan]/resume <id>[/bold cyan] to switch or [bold cyan]/fork <name>[/bold cyan] to branch.[/dim]\n")

    def handle_fork(self, args: List[str]) -> None:
        """Dispatches `/fork [new_title]` command."""
        cur_id = self._ensure_initial_session()
        title = " ".join(args).strip() if args else None

        try:
            forked = self.store.fork_session(cur_id, new_title=title)
            self.active_session_id = forked.session_id
            console.print(Panel(
                f"[bold green]✓ Session Forked Successfully[/bold green]\n\n"
                f"[dim]New Session ID:[/dim]    [yellow]{forked.session_id}[/yellow]\n"
                f"[dim]Parent Session ID:[/dim] [magenta]{cur_id}[/magenta]\n"
                f"[dim]Title:[/dim]             [white]{forked.title}[/white]\n\n"
                f"[dim]All message history from parent has been duplicated into this branch.[/dim]",
                title="[bold green]Fork Lineage[/bold green]",
                border_style="green",
            ))
        except Exception as e:
            console.print(f"[bold red]Failed to fork session:[/bold red] {e}")

    def handle_resume(self, args: List[str]) -> None:
        """Dispatches `/resume [session_id]` with interactive picker if no argument."""
        sessions = self.store.list_sessions()
        if not sessions:
            console.print("[yellow]No sessions available to resume.[/yellow]")
            return

        target_id: Optional[str] = None

        if args:
            arg_id = args[0].strip()
            # Check for direct ID match or index match
            matched = next((s for s in sessions if s["session_id"].startswith(arg_id)), None)
            if matched:
                target_id = matched["session_id"]
            else:
                console.print(f"[bold red]Session matching '{arg_id}' not found.[/bold red]")
                return
        else:
            # Interactive picker
            console.print("\n[bold cyan]Select a session to resume:[/bold cyan]")
            for idx, s in enumerate(sessions, start=1):
                marker = "*" if s["session_id"] == self.active_session_id else " "
                dt_str = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")
                parent_info = f" (fork of {s['parent_session_id']})" if s.get("parent_session_id") else ""
                console.print(f"  {marker} [bold yellow][{idx}][/bold yellow] [cyan]{s['session_id']}[/cyan]: {s['title']} [dim]({s['message_count']} msgs, {dt_str}){parent_info}[/dim]")

            try:
                choice = input("\nEnter session number or ID (or press Enter to cancel): ").strip()
                if not choice:
                    console.print("[dim]Resume cancelled.[/dim]")
                    return

                if choice.isdigit():
                    num = int(choice)
                    if 1 <= num <= len(sessions):
                        target_id = sessions[num - 1]["session_id"]
                else:
                    matched = next((s for s in sessions if s["session_id"].startswith(choice)), None)
                    if matched:
                        target_id = matched["session_id"]
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Resume cancelled.[/dim]")
                return

        if target_id:
            session = self.store.get_session(target_id)
            if session:
                self.active_session_id = target_id
                console.print(f"[bold green]✓ Resumed session:[/bold green] [cyan]{session.session_id}[/cyan] ({session.title})")
            else:
                console.print(f"[bold red]Failed to load session '{target_id}'.[/bold red]")

    def handle_rename(self, args: List[str]) -> None:
        """Dispatches `/rename <new_title>`."""
        if not args:
            console.print("[yellow]Usage: /rename <new_session_title>[/yellow]")
            return

        cur_id = self._ensure_initial_session()
        new_title = " ".join(args).strip()
        ok = self.store.rename_session(cur_id, new_title)
        if ok:
            console.print(f"[bold green]✓ Session renamed to:[/bold green] [white]{new_title}[/white]")
        else:
            console.print(f"[bold red]Failed to rename session '{cur_id}'.[/bold red]")

    def handle_compact(self, args: List[str]) -> None:
        """Dispatches `/compact [restore]`."""
        cur_id = self._ensure_initial_session()

        if args and args[0].lower() == "restore":
            ok = self.store.restore_compaction(cur_id)
            if ok:
                msgs = self.store.get_messages(cur_id)
                console.print(Panel(
                    f"[bold green]✓ Pre-Compaction History Restored[/bold green]\n\n"
                    f"Session [cyan]{cur_id}[/cyan] rolled back to original {len(msgs)} messages.\n"
                    f"Zero message loss guarantee preserved.",
                    title="[bold green]Compaction Rollback[/bold green]",
                    border_style="green",
                ))
            else:
                console.print("[yellow]No previous compaction snapshot found to restore for this session.[/yellow]")
            return

        # Perform manual compaction
        result = self.compactor.compact(cur_id, self.store)
        if not result.success:
            console.print(Panel(
                f"[bold yellow]Compaction Not Performed[/bold yellow]\n\n"
                f"{result.error or result.summary}\n"
                f"[dim]All messages kept 100% intact.[/dim]",
                title="[bold yellow]Context Compaction[/bold yellow]",
                border_style="yellow",
            ))
            return

        saved_tokens = max(0, result.tokens_before - result.tokens_after)
        pct = (saved_tokens / result.tokens_before * 100.0) if result.tokens_before > 0 else 0.0

        console.print(Panel(
            f"[bold green]✓ Context Compaction Completed[/bold green]\n\n"
            f"[dim]Tokens Before:[/dim]      [yellow]{result.tokens_before}[/yellow]\n"
            f"[dim]Tokens After:[/dim]       [green]{result.tokens_after}[/green]\n"
            f"[dim]Tokens Saved:[/dim]       [cyan]{saved_tokens} ({pct:.1f}% reduction)[/cyan]\n"
            f"[dim]Turns Summarized:[/dim]   [white]{result.messages_compacted}[/white]\n\n"
            f"[bold white]Summary:[/bold white]\n[dim]{result.summary[:300]}...[/dim]\n\n"
            f"[dim]Use [bold cyan]/compact restore[/bold cyan] anytime to revert to full uncompacted dialogue.[/dim]",
            title="[bold green]Context Compaction Summary[/bold green]",
            border_style="green",
        ))


default_session_cli = SessionCLI()
