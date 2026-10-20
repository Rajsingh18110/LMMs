"""
LMMs MCP CLI Interface
Handles `lmms mcp` CLI subcommands: add, list, remove, enable, disable, test, tools, logs.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import List, Optional

from rich.console import Console

from lmms_mcp.config import MCPConfig, CURATED_TEMPLATES
from lmms_mcp.manager import MCPServerManager
from lmms.cli.cligui.mcp_dashboard import MCPTerminalDashboard

console = Console()


def handle_mcp_cli(args: List[str]) -> int:
    """Main entrypoint for `lmms mcp ...` CLI commands."""
    parser = argparse.ArgumentParser(
        prog="lmms mcp",
        description="LMMs Model Context Protocol (MCP) Server and Tool Management",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="MCP Subcommands")

    # list
    subparsers.add_parser("list", help="List all configured MCP servers and their status")

    # add
    add_p = subparsers.add_parser("add", help="Add or update an MCP server")
    add_p.add_argument("name", help="Unique server name (or template key with --template)")
    add_p.add_argument("target", nargs="?", default="", help="Command (for stdio) or URL (for sse/http)")
    add_p.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio", help="Transport type")
    add_p.add_argument("--args", nargs="*", default=[], help="Command arguments (for stdio)")
    add_p.add_argument("--env", nargs="*", default=[], help="Environment variables in KEY=VAL format")
    add_p.add_argument("--sandbox", choices=["none", "bwrap", "restricted"], default="none", help="Sandbox isolation mode")
    add_p.add_argument("--template", action="store_true", help="Apply a curated server template")

    # remove
    rm_p = subparsers.add_parser("remove", help="Remove an MCP server")
    rm_p.add_argument("name", help="Name of the server to remove")

    # enable
    en_p = subparsers.add_parser("enable", help="Enable an MCP server")
    en_p.add_argument("name", help="Name of the server to enable")

    # disable
    dis_p = subparsers.add_parser("disable", help="Disable an MCP server")
    dis_p.add_argument("name", help="Name of the server to disable")

    # test
    test_p = subparsers.add_parser("test", help="Test connection to an MCP server and list tools")
    test_p.add_argument("name", help="Name of the server to test")

    # tools
    tools_p = subparsers.add_parser("tools", help="List discovered tools across active servers")
    tools_p.add_argument("name", nargs="?", default=None, help="Optional server name filter")

    # logs
    logs_p = subparsers.add_parser("logs", help="View recent logs for an MCP server")
    logs_p.add_argument("name", help="Name of the server")

    # templates
    subparsers.add_parser("templates", help="List available curated server templates")

    if not args:
        # Default action when no subcommand is provided is to display the dashboard
        dashboard = MCPTerminalDashboard()
        dashboard.display_full_dashboard()
        return 0

    parsed = parser.parse_args(args)
    config = MCPConfig()
    manager = MCPServerManager(config)
    dashboard = MCPTerminalDashboard(manager)

    if parsed.subcommand == "list" or not parsed.subcommand:
        dashboard.display_full_dashboard()
        return 0

    elif parsed.subcommand == "templates":
        console.print("\n[bold cyan]Available Curated MCP Templates:[/bold cyan]")
        for key, tmpl in CURATED_TEMPLATES.items():
            console.print(f"  • [bold white]{key:14}[/bold white] - {tmpl['description']}")
        console.print("\n[dim]To add a template: lmms mcp add <name> --template[/dim]\n")
        return 0

    elif parsed.subcommand == "add":
        if parsed.template:
            cfg = config.apply_template(parsed.name)
            if not cfg:
                console.print(f"[red]✖ Unknown template '{parsed.name}'. Run 'lmms mcp templates' to view all.[/red]")
                return 1
            console.print(f"[green]✓ Applied template '{parsed.name}' successfully.[/green]")
        else:
            if not parsed.target:
                console.print("[red]✖ Error: Must provide a command or URL for custom server.[/red]")
                return 1

            env_dict = {}
            for e in parsed.env:
                if "=" in e:
                    k, v = e.split("=", 1)
                    env_dict[k.strip()] = v.strip()

            config.add_server(
                name=parsed.name,
                command_or_url=parsed.target,
                transport=parsed.transport,
                args=parsed.args,
                env=env_dict,
                sandbox=parsed.sandbox,
                enabled=True,
            )
            console.print(f"[green]✓ MCP server '{parsed.name}' added successfully.[/green]")

        dashboard.display_full_dashboard()
        return 0

    elif parsed.subcommand == "remove":
        if config.remove_server(parsed.name):
            console.print(f"[green]✓ Removed MCP server '{parsed.name}'.[/green]")
            return 0
        console.print(f"[red]✖ Server '{parsed.name}' not found.[/red]")
        return 1

    elif parsed.subcommand == "enable":
        if config.enable_server(parsed.name):
            console.print(f"[green]✓ Enabled MCP server '{parsed.name}'.[/green]")
            return 0
        console.print(f"[red]✖ Server '{parsed.name}' not found.[/red]")
        return 1

    elif parsed.subcommand == "disable":
        if config.disable_server(parsed.name):
            console.print(f"[green]✓ Disabled MCP server '{parsed.name}'.[/green]")
            return 0
        console.print(f"[red]✖ Server '{parsed.name}' not found.[/red]")
        return 1

    elif parsed.subcommand == "test":
        server = config.get_server(parsed.name)
        if not server:
            console.print(f"[red]✖ Server '{parsed.name}' not found in configuration.[/red]")
            return 1

        console.print(f"[dim]Connecting to '{parsed.name}' ({server.transport})...[/dim]")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ok, msg, tools = loop.run_until_complete(manager.test_connection(parsed.name))
            if ok:
                console.print(f"[bold green]✓ Handshake succeeded![/bold green] {msg}")
                console.print(dashboard.render_tools_table(tools))
                return 0
            else:
                console.print(f"[bold red]✖ Connection failed:[/bold red] {msg}")
                return 1
        finally:
            loop.run_until_complete(manager.stop_all())
            loop.close()

    elif parsed.subcommand == "tools":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tools = loop.run_until_complete(manager.list_all_tools(filter_server=parsed.name))
            console.print(dashboard.render_tools_table(tools))
            return 0
        finally:
            loop.run_until_complete(manager.stop_all())
            loop.close()

    elif parsed.subcommand == "logs":
        dashboard.display_logs(parsed.name)
        return 0

    return 0
