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
        sys.stdout.write(f"  {COLOR_BOLD_WHITE}Target:{COLOR_RESET} {info['url']} {COLOR_DIM}({info['mode'].upper()}){COLOR_RESET}\n")
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
        sys.stdout.write(f"  {COLOR_BOLD_WHITE}Target:{COLOR_RESET} {info['url']} {COLOR_DIM}({info['mode'].upper()}){COLOR_RESET}\n")
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
        sys.stdout.write(f"  {COLOR_BOLD_WHITE}Engine Telemetry ({info['url']}):{COLOR_RESET}\n")
        for k, v in stats.items():
            sys.stdout.write(f"  {COLOR_CYAN}{k:<22}{COLOR_RESET} : {COLOR_DIM}{v}{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}Failed to query stats from {info['url']}:{COLOR_RESET} {e}\n")


def cmd_server(args: List[str]) -> None:
    """Manage the local standalone LMMs API backend server (start, stop, status, interactive)."""
    from lmms.api.service import start_server_daemon, stop_server_daemon, get_server_daemon_status
    from lmms.api.server import run_server

    # Parse command action
    action = None
    if args and not args[0].startswith("-"):
        action = args[0].lower()
        sub_args = args[1:]
    else:
        # Default behavior: if no subcommand, run interactive server if requested or status
        # If user explicitly types `lmms server`, run interactive foreground mode with OTP!
        action = "foreground" if not args or any(a in args for a in ["--foreground", "-f"]) else "status"
        sub_args = args

    port = 11435
    host = "0.0.0.0"
    engine_tier = 3
    engine_mode = "auto"
    timeout = 300
    foreground = action in ["foreground", "serve", "run"]

    idx = 0
    while idx < len(sub_args):
        arg = sub_args[idx]
        if arg in ["--port", "-p"] and idx + 1 < len(sub_args):
            try:
                port = int(sub_args[idx + 1])
            except ValueError:
                pass
            idx += 2
        elif arg in ["--host", "-h"] and idx + 1 < len(sub_args):
            host = sub_args[idx + 1]
            idx += 2
        elif arg in ["--tier", "-t"] and idx + 1 < len(sub_args):
            try:
                engine_tier = int(sub_args[idx + 1])
            except ValueError:
                pass
            idx += 2
        elif arg in ["--engine", "-e"] and idx + 1 < len(sub_args):
            val = sub_args[idx + 1].lower()
            if val in ["1", "llama", "llamacpp"]:
                engine_tier = 1
                engine_mode = "1"
            elif val in ["2", "pytorch", "torch"]:
                engine_tier = 2
                engine_mode = "2"
            else:
                engine_tier = 3
                engine_mode = "auto"
            idx += 2
        elif arg in ["--timeout", "-to"] and idx + 1 < len(sub_args):
            try:
                timeout = int(sub_args[idx + 1])
            except ValueError:
                pass
            idx += 2
        elif arg in ["--foreground", "-f"]:
            foreground = True
            idx += 1
        else:
            idx += 1

    if action in ["start", "up"]:
        if foreground:
            sys.stdout.write(f"ℹ {COLOR_DIM}Starting LMMs server in foreground on {host}:{port}...{COLOR_RESET}\n")
            run_server(host=host, port=port, idle_timeout=None, engine_tier=engine_tier)
        else:
            res = start_server_daemon(port=port, host=host, engine_mode=engine_mode, engine_tier=engine_tier, forever=True, initiator="user")
            if res.get("status") == "already_running":
                sys.stdout.write(f"{COLOR_YELLOW}⚠{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server already running{COLOR_RESET} (PID {res['pid']}) at {res['url']}\n")
                sys.stdout.write(f"  • Lifecycle:     {COLOR_CYAN}{'Permanent Daemon' if res.get('forever') else 'Ephemeral Session'}{COLOR_RESET}\n")
            else:
                sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Super Engine Server started in permanent background daemon mode{COLOR_RESET} (PID {res['pid']})\n")
                sys.stdout.write(f"  • Engine Tier:   {COLOR_BOLD_GREEN}{res.get('tier_name')}{COLOR_RESET}\n")
                sys.stdout.write(f"  • API URL:       {COLOR_CYAN}{res['api_url']}{COLOR_RESET}\n")
                sys.stdout.write(f"  • Web Dashboard: {COLOR_CYAN}{res['dashboard_url']}{COLOR_RESET}\n")
                sys.stdout.write(f"  • Lifecycle:     {COLOR_GREEN}Permanent Daemon (Stops only with 'lmms server stop'){COLOR_RESET}\n")
                sys.stdout.write(f"  • Server Logs:   {COLOR_DIM}{res['log_file']}{COLOR_RESET}\n")

    elif action in ["stop", "down"]:
        res = stop_server_daemon(force=True, caller="user")
        if res.get("status") == "stopped":
            sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server stopped{COLOR_RESET} (PID {res['pid']})\n")
        else:
            sys.stdout.write(f"{COLOR_DIM}No running LMMs Server daemon detected.{COLOR_RESET}\n")

    elif action in ["restart"]:
        stop_server_daemon(force=True, caller="user")
        res = start_server_daemon(port=port, host=host, engine_mode=engine_mode, engine_tier=engine_tier, forever=True, initiator="user")
        sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server restarted{COLOR_RESET} (PID {res.get('pid')})\n")
        sys.stdout.write(f"  • Engine Tier: {COLOR_BOLD_GREEN}{res.get('tier_name')}{COLOR_RESET}\n")

    elif action in ["status", "info"]:
        st = get_server_daemon_status()
        if st["running"]:
            lifecycle = f"{COLOR_GREEN}Permanent Daemon (Never auto-exits){COLOR_RESET}" if st.get("forever") else f"{COLOR_YELLOW}Ephemeral Session (Linked to active CLI/GUI){COLOR_RESET}"
            sys.stdout.write(f"{COLOR_GREEN}●{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server Status:{COLOR_RESET} {COLOR_BOLD_GREEN}ACTIVE (PID {st['pid']}){COLOR_RESET}\n")
            sys.stdout.write(f"  • Engine Tier: {COLOR_CYAN}{st.get('tier_name')}{COLOR_RESET}\n")
            sys.stdout.write(f"  • API URL:     {COLOR_CYAN}http://{st.get('host')}:{st.get('port')}{COLOR_RESET}\n")
            sys.stdout.write(f"  • Lifecycle:   {lifecycle}\n")
            sys.stdout.write(f"  • Log File:    {COLOR_DIM}{st['log_file']}{COLOR_RESET}\n")
            if st["recent_logs"]:
                sys.stdout.write(f"\n{COLOR_DIM}Recent Logs:{COLOR_RESET}\n")
                for line in st["recent_logs"][-5:]:
                    sys.stdout.write(f"  {COLOR_DIM}{line}{COLOR_RESET}\n")
        else:
            sys.stdout.write(f"{COLOR_RED}○{COLOR_RESET} {COLOR_BOLD_WHITE}LMMs Server Status:{COLOR_RESET} {COLOR_DIM}OFFLINE (Not running){COLOR_RESET}\n")
            sys.stdout.write(f"  • Start as permanent background daemon: {COLOR_CYAN}lmms server start [--tier 1|2|3]{COLOR_RESET}\n")
            sys.stdout.write(f"  • Start interactive session with OTP:   {COLOR_CYAN}lmms server{COLOR_RESET}\n")

    elif action in ["foreground", "serve", "run"]:
        sys.stdout.write(f"ℹ {COLOR_DIM}Starting interactive LMMs server on {host}:{port}...{COLOR_RESET}\n")
        run_server(host=host, port=port, idle_timeout=timeout, engine_tier=engine_tier)

    else:
        sys.stdout.write(f"{COLOR_RED}Unknown server command:{COLOR_RESET} {action}\n")
        sys.stdout.write(f"Usage: {COLOR_CYAN}lmms server [start|stop|restart|status] [--tier 1|2|3] [--port 11435] [--timeout 300]{COLOR_RESET}\n")
        sys.stdout.write(f"  • {COLOR_BOLD_WHITE}lmms server start{COLOR_RESET} : Starts permanent background daemon (never times out)\n")
        sys.stdout.write(f"  • {COLOR_BOLD_WHITE}lmms server stop{COLOR_RESET}  : Terminates the daemon\n")
        sys.stdout.write(f"  • {COLOR_BOLD_WHITE}lmms server{COLOR_RESET}       : Interactive mode with OTP banner and idle auto-stop\n")


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


def cmd_engine(args: List[str]) -> None:
    """Launch the standalone Dual-Engine console and runtime manager."""
    from lmms.engine.main import run_engine
    run_engine(args)


def cmd_mcp(args: List[str]) -> None:
    """Manage Model Context Protocol (MCP) servers and tools."""
    from lmms_mcp.cli import handle_mcp_cli
    code = handle_mcp_cli(args)
    if code != 0:
        sys.exit(code)
