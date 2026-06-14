import sys
import os
import json
import argparse
from rich.console import Console

console = Console()

def handle_cli(args):
    # Top-level parser
    parser = argparse.ArgumentParser(prog="lmms", description="LMMs Local AI Operating System")
    
    # Global Air Flags
    parser.add_argument("-air", action="store_true", help="Run single heavy model via Air Engine")
    parser.add_argument("--air", action="store_true", help="Run multiple models via Air Scheduler")
    
    # Fast aliases for modes
    parser.add_argument("-g", "--gui-alias", action="store_true", help="Launch GUI mode")
    parser.add_argument("-c", "--cli-alias", action="store_true", help="Launch CLI mode")
    parser.add_argument("-e", "--engine-alias", action="store_true", help="Launch Engine mode")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 1. Launcher & Mode Selection
    set_parser = subparsers.add_parser("set", help="Set default launch mode")
    set_parser.add_argument("--gui", action="store_true")
    set_parser.add_argument("--cli", action="store_true")
    set_parser.add_argument("--engine", action="store_true")
    
    subparsers.add_parser("gui", help="Directly launch GUI mode")
    subparsers.add_parser("cli", help="Directly launch CLI mode")
    subparsers.add_parser("engine", help="Directly launch Engine-only mode")

    # 2. Model Management
    pull_parser = subparsers.add_parser("pull", help="Download a model (auto-hardware selection)")
    pull_parser.add_argument("model", help="Model name")
    pull_parser.add_argument("--interactive", action="store_true", help="Manual selection")

    run_parser = subparsers.add_parser("run", help="Start and run a model")
    run_parser.add_argument("model", nargs="+", help="Model name(s)")

    stop_parser = subparsers.add_parser("stop", help="Stop an active model")
    stop_parser.add_argument("model", help="Model name")

    subparsers.add_parser("ps", help="List currently running models")
    subparsers.add_parser("list", help="List locally installed models")
    
    info_parser = subparsers.add_parser("info", help="Show detailed metadata for a model")
    info_parser.add_argument("model", help="Model name")

    rm_parser = subparsers.add_parser("rm", help="Delete a model")
    rm_parser.add_argument("model", help="Model name")

    search_parser = subparsers.add_parser("search", help="Search providers/HF for a model")
    search_parser.add_argument("query", help="Search query")

    bench_parser = subparsers.add_parser("benchmark", help="Benchmark speed/load/VRAM")
    bench_parser.add_argument("model", help="Model name")

    doc_parser = subparsers.add_parser("doctor", help="System health check")
    doc_parser.add_argument("--fix", action="store_true", help="Auto-fix minor issues")

    # Tool Execution
    tool_parser = subparsers.add_parser("tool", help="Directly test a Backend Tool")
    tool_parser.add_argument("name", help="Tool name")
    tool_parser.add_argument("args", nargs=argparse.REMAINDER, help="Tool arguments (e.g. key value)")

    chat_parser = subparsers.add_parser("chat", help="List or interact with current workspace chats")
    newchat_parser = subparsers.add_parser("newchat", help="Create a new chat in current workspace")

    # 3. Air Engine Subcommands
    air_parser = subparsers.add_parser("air", help="Air subsystem management")
    air_sub = air_parser.add_subparsers(dest="air_command")
    air_sub.add_parser("ps", help="List active Air models")
    air_sub.add_parser("cache", help="Show Air cache status")
    air_sub.add_parser("stats", help="Show swapping/VRAM metrics")
    air_unload = air_sub.add_parser("unload", help="Unload an Air model")
    air_unload.add_argument("model", nargs="?")
    air_sub.add_parser("benchmark", help="Air performance test")

    # 4. Install / Uninstall Components
    install_parser = subparsers.add_parser("install", help="Install LMMS components")
    install_parser.add_argument("--gui", action="store_true")
    install_parser.add_argument("--cli", action="store_true")
    install_parser.add_argument("--engine", action="store_true")
    install_parser.add_argument("--air", action="store_true")
    install_parser.add_argument("--full", action="store_true")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove LMMS components")
    uninstall_parser.add_argument("--gui", action="store_true")
    uninstall_parser.add_argument("--cli", action="store_true")
    uninstall_parser.add_argument("--engine", action="store_true")
    uninstall_parser.add_argument("--air", action="store_true")
    uninstall_parser.add_argument("--all", action="store_true")
    uninstall_parser.add_argument("--purge", action="store_true")

    # 5. Package Commands
    pkg_parser = subparsers.add_parser("package", help="Modular package manager")
    pkg_sub = pkg_parser.add_subparsers(dest="pkg_command")
    pkg_install = pkg_sub.add_parser("install", help="Install a package")
    pkg_install.add_argument("type", choices=["runtime", "provider", "tool"])
    pkg_install.add_argument("name")
    pkg_sub.add_parser("list", help="List installed packages")
    pkg_rm = pkg_sub.add_parser("remove", help="Remove a package")
    pkg_rm.add_argument("type", choices=["runtime", "provider", "tool"])
    pkg_rm.add_argument("name")

    # 6. Workspace Commands
    ws_parser = subparsers.add_parser("workspace", help="Workspace / project management")
    ws_sub = ws_parser.add_subparsers(dest="ws_command")
    ws_sub.add_parser("create", help="Create new workspace")
    ws_sub.add_parser("list", help="List workspaces")
    ws_open = ws_sub.add_parser("open", help="Open workspace folder")
    ws_open.add_argument("path")
    ws_sub.add_parser("close", help="Close current workspace")
    ws_del = ws_sub.add_parser("delete", help="Delete workspace")
    ws_del.add_argument("id")
    ws_rest = ws_sub.add_parser("restore", help="Restore workspace from snapshot")
    ws_rest.add_argument("id")

    # 7. Connectors
    conn_parser = subparsers.add_parser("connector", help="Connector management")
    conn_sub = conn_parser.add_subparsers(dest="conn_command")
    conn_tg = conn_sub.add_parser("telegram", help="Telegram connector")
    conn_tg_sub = conn_tg.add_subparsers(dest="tg_command")
    conn_tg_sub.add_parser("setup", help="Setup Telegram credentials")

    # 8. Agent / Task / Git / Route
    task_parser = subparsers.add_parser("task", help="Workflow task management")
    task_sub = task_parser.add_subparsers(dest="task_command")
    task_sub.add_parser("create")
    task_sub.add_parser("list")
    task_show = task_sub.add_parser("show")
    task_show.add_argument("id")
    task_comp = task_sub.add_parser("complete")
    task_comp.add_argument("id")
    task_block = task_sub.add_parser("block")
    task_block.add_argument("id")
    task_sub.add_parser("timeline")

    git_parser = subparsers.add_parser("git", help="Repository intelligence")
    git_sub = git_parser.add_subparsers(dest="git_command")
    git_sub.add_parser("status")
    git_sub.add_parser("commits")
    git_sub.add_parser("branch")
    git_sub.add_parser("timeline")
    git_sub.add_parser("memory")
    git_sub.add_parser("summarize")
    git_sub.add_parser("explain")

    agent_parser = subparsers.add_parser("agent", help="Autonomous agents")
    agent_sub = agent_parser.add_subparsers(dest="agent_command")
    agent_sub.add_parser("list")
    ag_run = agent_sub.add_parser("run")
    ag_run.add_argument("name")
    ag_en = agent_sub.add_parser("enable")
    ag_en.add_argument("name")
    ag_dis = agent_sub.add_parser("disable")
    ag_dis.add_argument("name")

    subparsers.add_parser("route", help="Routing decision")
    subparsers.add_parser("orchestrate", help="Multi-step handoff flow")

    parsed = parser.parse_args(args)

    from lmms.backend.logic.manager import backend_manager

    # Resolve Default Launch if no args provided
    if not parsed.command and not (parsed.gui_alias or parsed.cli_alias or parsed.engine_alias):
        mode = backend_manager.config.get("default_mode")
        if not mode:
            console.print("[cyan]Welcome to LMMS Operating System.[/cyan]")
            console.print("Select default mode:")
            console.print("[1] GUI")
            console.print("[2] CLI")
            console.print("[3] Engine")
            try:
                choice = input("Choice: ").strip()
                if choice == "1": mode = "gui"
                elif choice == "2": mode = "cli"
                elif choice == "3": mode = "engine"
                else:
                    console.print("[red]Invalid choice. Defaulting to CLI.[/red]")
                    mode = "cli"
                backend_manager.config.set("default_mode", mode)
                console.print(f"[green]Saved default mode: {mode}[/green]")
            except KeyboardInterrupt:
                sys.exit(0)
        
        # Override parsed command to boot the mode
        parsed.command = mode

    # Alias overrides
    if parsed.gui_alias: parsed.command = "gui"
    if parsed.cli_alias: parsed.command = "cli"
    if parsed.engine_alias: parsed.command = "engine"

    # Route Logic to Backend (Stubbed for Nervous System)
    # The CLI strictly parses commands. Backend executes logic.

    if parsed.command == "set":
        if parsed.gui:
            backend_manager.config.set("default_mode", "gui")
        elif parsed.cli:
            backend_manager.config.set("default_mode", "cli")
        elif parsed.engine:
            backend_manager.config.set("default_mode", "engine")
        console.print(f"[green]Default mode saved: {backend_manager.config.get('default_mode')}[/green]")

    elif parsed.command == "gui":
        console.print("[green]Launching GUI (Face)...[/green]")
        import subprocess
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        subprocess.Popen(["python3", "-m", "lmms.gui.app"], cwd=script_dir)
        sys.exit(0)

    elif parsed.command == "cli":
        console.print("[green]Starting CLI Chat Shell (Nervous System)...[/green]")
        import sys
        sys.argv = [sys.argv[0]]
        return # return to main.py loop

    elif parsed.command == "engine":
        console.print("[green]Starting Engine-only mode (Heart & API)...[/green]")
        from lmms.engine.server import run_server
        run_server()
        sys.exit(0)

    elif parsed.command == "pull":
        if parsed.interactive:
            console.print(f"[cyan]Interactive pull for {parsed.model}...[/cyan]")
        else:
            console.print(f"[cyan]Auto-detecting hardware and pulling best variant for {parsed.model}...[/cyan]")
        # Delegating to backend
        backend_manager.models.pull(parsed.model, interactive=parsed.interactive)

    elif parsed.command == "run":
        if parsed.air:
            console.print(f"[cyan]Starting Air Scheduler (multi-model) for {parsed.model}...[/cyan]")
        elif getattr(parsed, 'air', False): # handles -air if we added it as bool flag properly
            console.print(f"[cyan]Starting Air Execution (single heavy model) for {parsed.model[0]}...[/cyan]")
        else:
            console.print(f"[cyan]Starting standard execution for {parsed.model}...[/cyan]")
        
    elif parsed.command == "ps":
        console.print("[cyan]Currently running models:[/cyan]")
        # Map to Coordination Store via Backend
        stats = backend_manager.cache.get_stats()
        console.print(stats)

    elif parsed.command == "tool":
        import asyncio
        # Basic parsing: args can be simple key-value pairs or JSON string
        params = {}
        if parsed.args:
            if len(parsed.args) == 1 and parsed.args[0].startswith('{'):
                params = json.loads(parsed.args[0])
            elif len(parsed.args) % 2 == 0:
                for i in range(0, len(parsed.args), 2):
                    params[parsed.args[i]] = parsed.args[i+1]
            else:
                params["query"] = " ".join(parsed.args)
                
        async def run_tool():
            res = await backend_manager.tools.execute(parsed.name, params)
            console.print(json.dumps(res.data if res.success else res.error, indent=2))
            
        asyncio.run(run_tool())

    elif parsed.command == "workspace":
        if parsed.ws_command == "open":
            abs_path = os.path.abspath(parsed.path)
            backend_manager.config.set("active_workspace", abs_path)
            console.print(f"[green]Workspace Opened:[/green] {abs_path}")
            active_chat = backend_manager.chat_router.get_active_chat(abs_path)
            if active_chat['needs_context']:
                console.print("[dim]Context line injected for this session.[/dim]")
            console.print(f"Active Chat ID: {active_chat['chat_id']}")
            
        elif parsed.ws_command == "close":
            backend_manager.config.set("active_workspace", None)
            console.print("[green]Workspace Closed. Reverting to AI Chat.[/green]")

    elif parsed.command == "chat":
        ws = backend_manager.config.get("active_workspace")
        chats = backend_manager.chat_router.list_chats(ws)
        console.print(f"Chats for workspace: [bold]{ws if ws else 'NULL (No Workspace)'}[/bold]")
        for c in chats:
            console.print(f"- [cyan]{c['title']}[/cyan] ({c['chat_id'][:8]}...) Last Active: {c['last_active']}")

    elif parsed.command == "newchat":
        ws = backend_manager.config.get("active_workspace")
        chat_id = backend_manager.chat_router.create_new_chat(ws)
        console.print(f"[green]Created new chat[/green] {chat_id} in workspace {ws}")

    elif parsed.command == "connector":
        if parsed.conn_command == "telegram" and parsed.tg_command == "setup":
            from lmms.backend.connectors.telegram import set_telegram_config
            console.print("[cyan]Telegram Connector Setup[/cyan]")
            console.print("Please get your API ID and Hash from my.telegram.org")
            api_id = input("API ID: ").strip()
            api_hash = input("API Hash: ").strip()
            phone = input("Phone Number: ").strip()
            set_telegram_config(api_id, api_hash, phone)
            console.print("[green]Telegram credentials saved successfully![/green]")

    elif parsed.command == "air":
        if parsed.air_command == "ps":
            models = backend_manager.coordination.list_models()
            for m in models:
                console.print(f"- {m['model_name']} ({m['status']}): {m['last_action']}")
        else:
            console.print(f"[yellow]Air Engine command '{parsed.air_command}' routed to Backend.[/yellow]")

    else:
        # Generic catch-all for stubbed commands routing to Backend
        if parsed.command:
            console.print(f"[cyan]Routing command '{parsed.command}' to Backend...[/cyan]")
        else:
            parser.print_help()

if __name__ == "__main__":
    handle_cli(sys.argv[1:])
