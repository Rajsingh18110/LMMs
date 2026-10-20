"""
LMMs MCP Terminal Dashboard (cligui)
Renders high-aesthetic Rich terminal tables, status cards, and live views for MCP tools and servers.
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from lmms_mcp.config import MCPConfig, MCPServerConfig
from lmms_mcp.manager import MCPServerManager

console = Console()


class MCPTerminalDashboard:
    """Terminal UI renderer for MCP servers, tools, and telemetry."""

    def __init__(self, manager: Optional[MCPServerManager] = None):
        self.manager = manager or MCPServerManager()
        self.config = self.manager.config

    def render_summary_chips(self) -> Panel:
        """Renders summary chip cards for connected, starting, and error counts."""
        servers = self.config.list_servers()
        total = len(servers)
        enabled = sum(1 for s in servers if s.enabled)
        
        connected = 0
        errors = 0
        total_tools = 0

        for s in servers:
            st = self.manager.get_server_state(s.name)
            if st:
                if st.status == "connected":
                    connected += 1
                elif st.status == "error":
                    errors += 1
                total_tools += len(st.tools)

        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)

        c1 = f"[bold white]Total Configured:[/bold white] [bold cyan]{total}[/bold cyan] ({enabled} enabled)"
        c2 = f"[bold green]● Connected:[/bold green] [bold white]{connected}[/bold white]"
        c3 = f"[bold red]▲ Errors:[/bold red] [bold white]{errors}[/bold white]"
        c4 = f"[bold magenta]⚡ Available Tools:[/bold magenta] [bold white]{total_tools}[/bold white]"

        grid.add_row(c1, c2, c3, c4)
        return Panel(grid, title="[bold cyan]LMMs Model Context Protocol (MCP)[/bold cyan]", border_style="cyan")

    def render_server_table(self) -> Table:
        """Renders a formatted table of all configured MCP servers."""
        table = Table(
            title="Registered MCP Servers",
            title_style="bold cyan",
            border_style="dim white",
            header_style="bold magenta",
            show_lines=True,
        )
        table.add_column("Status", justify="center", width=12)
        table.add_column("Server Name", style="bold white", width=18)
        table.add_column("Transport", style="cyan", width=10)
        table.add_column("Tools", justify="center", width=8)
        table.add_column("Sandbox", style="yellow", width=10)
        table.add_column("Target (Command / URL)", style="dim white")

        servers = self.config.list_servers()
        if not servers:
            table.add_row("⚪ Idle", "[dim]No servers[/dim]", "-", "0", "-", "Use 'lmms mcp add' or apply a template")
            return table

        for s in servers:
            state = self.manager.get_server_state(s.name)
            status_str = "⚪ Disabled"
            tool_count = "0"

            if not s.enabled:
                status_str = "[dim]⚪ Disabled[/dim]"
            elif state:
                if state.status == "connected":
                    status_str = f"[green]🟢 {state.latency_ms:.0f}ms[/green]"
                    tool_count = f"[bold green]{len(state.tools)}[/bold green]"
                elif state.status == "starting":
                    status_str = "[yellow]🟡 Starting[/yellow]"
                elif state.status == "error":
                    status_str = "[red]🔴 Error[/red]"
            else:
                status_str = "[dim]⚪ Stopped[/dim]"

            target = ""
            if s.transport == "stdio":
                target = f"{s.command} {' '.join(s.args)}" if s.args else str(s.command)
            else:
                target = str(s.url)

            sandbox_badge = f"[cyan]{s.sandbox}[/cyan]" if s.sandbox != "none" else "[dim]none[/dim]"
            table.add_row(
                status_str,
                s.name,
                s.transport.upper(),
                tool_count,
                sandbox_badge,
                target[:65] + ("..." if len(target) > 65 else ""),
            )

        return table

    def render_tools_table(self, tools: List[Dict[str, Any]]) -> Table:
        """Renders a table of discovered tools across active servers."""
        table = Table(
            title="Discovered MCP Tools",
            title_style="bold magenta",
            border_style="dim white",
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Server", style="cyan", width=15)
        table.add_column("Tool Name", style="bold white", width=22)
        table.add_column("Description", style="dim white")
        table.add_column("Required Args", style="yellow", width=20)

        if not tools:
            table.add_row("-", "No tools found", "Start servers with 'lmms mcp test <name>'", "-")
            return table

        for t in tools:
            schema = t.get("inputSchema", {})
            req = ", ".join(schema.get("required", [])) or "[dim]none[/dim]"
            desc = t.get("description", "")
            table.add_row(
                t.get("server", "unknown"),
                t.get("name", "tool"),
                desc[:60] + ("..." if len(desc) > 60 else ""),
                req,
            )

        return table

    def display_full_dashboard(self) -> None:
        """Prints the full MCP summary cards and server table to console."""
        console.print()
        console.print(self.render_summary_chips())
        console.print(self.render_server_table())
        console.print()

    def display_logs(self, server_name: str) -> None:
        """Displays recent logs for an MCP server."""
        state = self.manager.get_server_state(server_name)
        if not state or not state.logs:
            console.print(f"[dim]No active logs captured for server '{server_name}'.[/dim]")
            return

        panel_text = "\n".join(state.logs)
        console.print(Panel(
            panel_text,
            title=f"[bold cyan]Server Logs: {server_name}[/bold cyan]",
            border_style="dim cyan",
        ))
