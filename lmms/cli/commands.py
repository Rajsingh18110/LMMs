"""
LMMs CLI Engine - Command Dispatcher & Remote Operations Router
Handles 'connect', 'remote', 'chat', 'run', 'ps', 'list', and 'stats' commands.
"""

from __future__ import annotations

import sys
from typing import List

from lmms.cli.client import CLIClient
from lmms.cli.interactive import InteractiveChat
from lmms.cli.remote import RemoteManager

# ANSI Formatting
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_GREEN = "\033[1;32m"
COLOR_BOLD_WHITE = "\033[1;37m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"


def cmd_connect(args: List[str]) -> None:
    """Connect to a remote LMMs engine or discover engines on local Wi-Fi / LAN."""
    rm = RemoteManager()

    if args:
        target = args[0]
        sys.stdout.write(f"ℹ {COLOR_DIM}Verifying connection to {target}...{COLOR_RESET}\n")
        success, msg = rm.set_remote(target)
        if success:
            sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{msg}{COLOR_RESET}\n")
            sys.stdout.write(f"{COLOR_DIM}All subsequent CLI commands will now execute against this host.{COLOR_RESET}\n")
        else:
            sys.stdout.write(f"{COLOR_RED}✖{COLOR_RESET} {msg}\n")
            sys.exit(1)
        return

    # Auto-scan if no target given
    engines = rm.scan_lan()
    if not engines:
        sys.stdout.write(f"\n{COLOR_YELLOW}No LMMs engines detected on local Wi-Fi/LAN.{COLOR_RESET}\n")
        sys.stdout.write(f"{COLOR_DIM}Start an engine with 'lmms server' on any machine in the network.{COLOR_RESET}\n")
        return

    sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Discovered LMMs Engines on Wi-Fi / LAN:{COLOR_RESET}\n")
    for i, eng in enumerate(engines):
        loc_str = " (local)" if eng["is_local"] else " (LAN remote)"
        models_str = f", active: {', '.join(eng['active_models'])}" if eng["active_models"] else ""
        sys.stdout.write(
            f"  [{i + 1}] {COLOR_BOLD_CYAN}{eng['host']}:{eng['port']}{COLOR_RESET} "
            f"{COLOR_DIM}[{eng['latency_ms']}ms latency{loc_str}{models_str}]{COLOR_RESET}\n"
        )

    # If only 1 engine discovered and it's not localhost, connect directly
    if len(engines) == 1:
        target = f"{engines[0]['host']}:{engines[0]['port']}"
        sys.stdout.write(f"\n{COLOR_DIM}Auto-selecting single available target: {target}...{COLOR_RESET}\n")
        success, msg = rm.set_remote(target)
        if success:
            sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{msg}{COLOR_RESET}\n")
    else:
        sys.stdout.write(f"\n{COLOR_DIM}To connect to an engine, run:{COLOR_RESET} lmms connect <ip:port>\n")


def cmd_remote(args: List[str]) -> None:
    """Manage remote engines, subnets, and connection profiles."""
    rm = RemoteManager()
    sub = args[0].lower() if args else "status"

    if sub in ["status", "info"]:
        info = rm.get_active_info()
        online, lat, data = rm.ping(info["url"])
        st_color = COLOR_GREEN if online else COLOR_RED
        status_text = "ONLINE" if online else "OFFLINE"

        sys.stdout.write(f"\n{COLOR_BOLD_WHITE}LMMs Connection State:{COLOR_RESET}\n")
        sys.stdout.write(f"  • Mode        : {COLOR_BOLD_CYAN}{info['mode'].upper()}{COLOR_RESET}\n")
        sys.stdout.write(f"  • Target URL  : {COLOR_BOLD_WHITE}{info['url']}{COLOR_RESET}\n")
        sys.stdout.write(f"  • Status      : {st_color}{status_text}{COLOR_RESET} ({lat}ms round-trip)\n")
        if online and data.get("active_models"):
            sys.stdout.write(f"  • Loaded      : {COLOR_CYAN}{', '.join(data['active_models'])}{COLOR_RESET}\n")
        sys.stdout.write(f"\n{COLOR_DIM}Commands: 'lmms remote scan', 'lmms remote local', 'lmms remote list'{COLOR_RESET}\n\n")

    elif sub in ["scan", "discover"]:
        engines = rm.scan_lan()
        if not engines:
            sys.stdout.write(f"\n{COLOR_YELLOW}No LMMs engines detected on local subnet.{COLOR_RESET}\n")
        else:
            sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Active LAN Engines:{COLOR_RESET}\n")
            for eng in engines:
                sys.stdout.write(
                    f"  • {COLOR_BOLD_CYAN}{eng['host']}:{eng['port']}{COLOR_RESET} "
                    f"{COLOR_DIM}(Ping: {eng['latency_ms']}ms){COLOR_RESET}\n"
                )
            sys.stdout.write(f"\n{COLOR_DIM}Connect via: lmms connect <host:port>{COLOR_RESET}\n\n")

    elif sub in ["list", "ls"]:
        remotes = rm.list_remotes()
        if not remotes:
            sys.stdout.write(f"{COLOR_DIM}No remote hosts saved. Use 'lmms connect <ip:port>' or 'lmms remote scan'.{COLOR_RESET}\n")
        else:
            active_info = rm.get_active_info()
            sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Saved Remote Engines:{COLOR_RESET}\n")
            for r in remotes:
                is_active = (active_info["mode"] == "remote" and active_info.get("name") == r["name"])
                tag = f" {COLOR_GREEN}[ACTIVE]{COLOR_RESET}" if is_active else ""
                status_icon = f"{COLOR_GREEN}●{COLOR_RESET}" if r.get("online") else f"{COLOR_RED}○{COLOR_RESET}"
                lat = f"{r.get('latency_ms', 0):.1f}ms"
                sys.stdout.write(f"  {status_icon} {COLOR_BOLD_WHITE}{r['name']:<16}{COLOR_RESET} {r['url']} {COLOR_DIM}({lat}){COLOR_RESET}{tag}\n")
            sys.stdout.write("\n")

    elif sub in ["use", "switch"]:
        if len(args) < 2:
            sys.stdout.write("Usage: lmms remote use <name_or_ip>\n")
        else:
            success, msg = rm.set_remote(args[1])
            if success:
                sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{msg}{COLOR_RESET}\n")
            else:
                sys.stdout.write(f"{COLOR_RED}✖{COLOR_RESET} {msg}\n")

    elif sub in ["local", "reset"]:
        rm.set_local()
        sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} Switched active target back to {COLOR_BOLD_WHITE}localhost (127.0.0.1:11435){COLOR_RESET}\n")

    elif sub in ["rm", "remove", "delete"]:
        if len(args) < 2:
            sys.stdout.write("Usage: lmms remote rm <name>\n")
        else:
            if rm.remove_remote(args[1]):
                sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} Removed remote '{args[1]}'\n")
            else:
                sys.stdout.write(f"{COLOR_RED}✖{COLOR_RESET} Remote '{args[1]}' not found\n")

    else:
        sys.stdout.write(f"Unknown remote sub-command: '{sub}'. Available: status, scan, list, use, local, rm\n")


def cmd_chat(args: List[str]) -> None:
    """Start an interactive chat session with a model (local or remote)."""
    if not args:
        # Check active models or default to qwen
        client = CLIClient()
        ps = client.get_ps()
        if ps and ps[0].get("model"):
            model = ps[0]["model"]
        else:
            models = client.list_models()
            if models:
                model = models[0].get("name", "qwen2.5:7b")
            else:
                model = "qwen2.5:7b"
    else:
        model = args[0]

    chat = InteractiveChat(model_name=model)
    chat.run()


def cmd_ps(args: List[str]) -> None:
    """Display active model memory allocation (local or remote)."""
    client = CLIClient()
    info = client.remote_mgr.get_active_info()

    try:
        ps_list = client.get_ps()
        sys.stdout.write(f"⚡ {COLOR_BOLD_WHITE}Target:{COLOR_RESET} {info['url']} {COLOR_DIM}({info['mode'].upper()}){COLOR_RESET}\n")
        if not ps_list:
            sys.stdout.write(f"{COLOR_DIM}No models currently active or loaded in memory.{COLOR_RESET}\n")
            return

        sys.stdout.write(f"{COLOR_BOLD_WHITE}Active Models:{COLOR_RESET}\n")
        for item in ps_list:
            m = item.get("model", "unknown")
            vram = item.get("vram_gb", 0)
            ram = item.get("ram_gb", 0)
            sys.stdout.write(f"  • {COLOR_BOLD_CYAN}{m:<24}{COLOR_RESET} {COLOR_DIM}[VRAM: {vram:.1f}GB | RAM: {ram:.1f}GB]{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}Failed to query engine at {info['url']}:{COLOR_RESET} {e}\n")


def cmd_list(args: List[str]) -> None:
    """List all available models on target engine."""
    client = CLIClient()
    info = client.remote_mgr.get_active_info()

    try:
        models = client.list_models()
        sys.stdout.write(f"⚡ {COLOR_BOLD_WHITE}Target:{COLOR_RESET} {info['url']} {COLOR_DIM}({info['mode'].upper()}){COLOR_RESET}\n")
        if not models:
            sys.stdout.write(f"{COLOR_DIM}No models available on target engine.{COLOR_RESET}\n")
            return

        sys.stdout.write(f"{COLOR_BOLD_WHITE}Model Inventory:{COLOR_RESET}\n")
        for m in models:
            name = m.get("name", str(m))
            loc = m.get("location", "")
            loc_str = f" {COLOR_DIM}({loc}){COLOR_RESET}" if loc else ""
            sys.stdout.write(f"  • {COLOR_BOLD_CYAN}{name}{COLOR_RESET}{loc_str}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}Failed to query models from {info['url']}:{COLOR_RESET} {e}\n")


def cmd_stats(args: List[str]) -> None:
    """Query hardware and memory metrics from target engine."""
    client = CLIClient()
    info = client.remote_mgr.get_active_info()

    try:
        stats = client.get_stats()
        sys.stdout.write(f"⚡ {COLOR_BOLD_WHITE}Engine Telemetry ({info['url']}):{COLOR_RESET}\n")
        for k, v in stats.items():
            sys.stdout.write(f"  {COLOR_CYAN}{k:<22}{COLOR_RESET} : {COLOR_DIM}{v}{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}Failed to query stats from {info['url']}:{COLOR_RESET} {e}\n")


def cmd_server(args: List[str]) -> None:
    """Manage the local standalone LMMs API backend server (start, stop, status)."""
    from lmms.api.service import start_server_daemon, stop_server_daemon, get_server_daemon_status
    from lmms.api.server import run_server

    action = args[0].lower() if args else "status"

    if action in ["start", "up"]:
        port = 11435
        host = "0.0.0.0"
        engine_mode = "auto"
        foreground = False

        idx = 1
        while idx < len(args):
            arg = args[idx]
            if arg in ["--port", "-p"] and idx + 1 < len(args):
                try:
                    port = int(args[idx + 1])
                except ValueError:
                    pass
                idx += 2
            elif arg in ["--host", "-h"] and idx + 1 < len(args):
                host = args[idx + 1]
                idx += 2
            elif arg in ["--engine", "-e"] and idx + 1 < len(args):
                engine_mode = args[idx + 1]
                idx += 2
            elif arg in ["--foreground", "-f"]:
                foreground = True
                idx += 1
            else:
                idx += 1

        if foreground:
            sys.stdout.write(f"ℹ {COLOR_DIM}Starting LMMs server in foreground on {host}:{port}...{COLOR_RESET}\n")
            run_server(host=host, port=port)
        else:
            res = start_server_daemon(port=port, host=host, engine_mode=engine_mode)
            if res.get("status") == "already_running":
                sys.stdout.write(f"{COLOR_YELLOW}⚠{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server already running{COLOR_RESET} (PID {res['pid']}) at {res['url']}\n")
            else:
                sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server started in background{COLOR_RESET} (PID {res['pid']})\n")
                sys.stdout.write(f"  • API URL:       {COLOR_CYAN}{res['api_url']}{COLOR_RESET}\n")
                sys.stdout.write(f"  • Web Dashboard: {COLOR_CYAN}{res['dashboard_url']}{COLOR_RESET}\n")
                sys.stdout.write(f"  • Server Logs:   {COLOR_DIM}{res['log_file']}{COLOR_RESET}\n")

    elif action in ["stop", "down"]:
        res = stop_server_daemon()
        if res.get("status") == "stopped":
            sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server stopped{COLOR_RESET} (PID {res['pid']})\n")
        else:
            sys.stdout.write(f"{COLOR_DIM}No running LMMs Server daemon detected.{COLOR_RESET}\n")

    elif action in ["restart"]:
        stop_server_daemon()
        res = start_server_daemon()
        sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server restarted{COLOR_RESET} (PID {res.get('pid')})\n")

    elif action in ["status", "info"]:
        st = get_server_daemon_status()
        if st["running"]:
            sys.stdout.write(f"{COLOR_GREEN}●{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server Status:{COLOR_RESET} {COLOR_BOLD_GREEN}ACTIVE (PID {st['pid']}){COLOR_RESET}\n")
            sys.stdout.write(f"  • Log File: {COLOR_DIM}{st['log_file']}{COLOR_RESET}\n")
            if st["recent_logs"]:
                sys.stdout.write(f"\n{COLOR_DIM}Recent Logs:{COLOR_RESET}\n")
                for line in st["recent_logs"][-5:]:
                    sys.stdout.write(f"  {COLOR_DIM}{line}{COLOR_RESET}\n")
        else:
            sys.stdout.write(f"{COLOR_RED}○{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server Status:{COLOR_RESET} {COLOR_DIM}OFFLINE (Not running){COLOR_RESET}\n")
            sys.stdout.write(f"  Start with: {COLOR_CYAN}lmms server start{COLOR_RESET}\n")
    else:
        sys.stdout.write(f"{COLOR_RED}Unknown server command:{COLOR_RESET} {action}\n")
        sys.stdout.write(f"Usage: {COLOR_CYAN}lmms server [start|stop|restart|status] [--port 11435] [--engine 1|2|auto] [--foreground]{COLOR_RESET}\n")


def cmd_gui(args: List[str]) -> None:
    """Launch the standalone desktop GUI application."""
    try:
        from lmms.gui.app import run_gui
        run_gui(args)
    except ImportError:
        sys.stderr.write(f"\n{COLOR_RED}✖ GUI component or dependencies missing (PyQt6/qasync).{COLOR_RESET}\n")
        sys.stderr.write(f"  To install GUI requirements, run: {COLOR_CYAN}lmms install --gui{COLOR_RESET}\n\n")
        sys.exit(1)


def cmd_tui(args: List[str]) -> None:
    """Launch the interactive terminal user interface."""
    from lmms.tui.main import launch_tui
    launch_tui(args)


