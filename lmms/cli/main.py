"""
LMMs Standalone CLI - Main Router & Interface
Decoupled terminal operations client with local and remote Wi-Fi/LAN connectivity.
"""

from __future__ import annotations

import sys
from typing import List, Optional

from lmms.cli.installer import run_installer, run_updater
from lmms.cli.commands import (
    cmd_connect,
    cmd_remote,
    cmd_chat,
    cmd_ps,
    cmd_list,
    cmd_stats,
    cmd_server,
    cmd_tui,
    cmd_engine,
)

# Typography
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_WHITE = "\033[1;37m"


def print_banner() -> None:
    sys.stdout.write(f"\n{COLOR_BOLD_WHITE}lmms-cli{COLOR_RESET} {COLOR_DIM}v1.0.0 (Standalone Remote & Local Client){COLOR_RESET}\n\n")
    sys.stdout.write(f"{COLOR_BOLD_WHITE}Commands:{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine [status|mode|run]{COLOR_RESET}  Standalone dual-engine runner & telemetry\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms server [start|stop|status]{COLOR_RESET} Local API engine service manager\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms tui                        {COLOR_RESET} Launch interactive terminal studio\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms connect [ip:port]{COLOR_RESET}          Connect to LAN engine or auto-discover\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms remote [status|scan|list|use]{COLOR_RESET} Wi-Fi/LAN engine manager\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms chat <model>{COLOR_RESET}               Interactive streaming conversation\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms run <model>{COLOR_RESET}                Run inference on active target\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms ps{COLOR_RESET}                         Active model memory inspection\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms list{COLOR_RESET}                       Available model catalog\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms stats{COLOR_RESET}                      Hardware & system telemetry\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms install [--all|--cli|--engine]{COLOR_RESET} Package resolver & interactive installer\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms update [--all|--cli|--engine]{COLOR_RESET}  Component version updater\n\n")
    sys.stdout.flush()


def main(args: Optional[List[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] in ["-h", "--help", "help"]:
        print_banner()
        return

    cmd = args[0].lower()
    sub_args = args[1:]

    if cmd == "install":
        run_installer(sub_args)
    elif cmd == "update":
        run_updater(sub_args)
    elif cmd in ["engine", "-e", "--engine"]:
        cmd_engine(sub_args)
    elif cmd in ["server", "serve", "daemon"]:
        cmd_server(sub_args)
    elif cmd in ["tui", "-t", "--tui"]:
        cmd_tui(sub_args)
    elif cmd == "connect":
        cmd_connect(sub_args)
    elif cmd == "remote":
        cmd_remote(sub_args)
    elif cmd in ["chat", "run"]:
        cmd_chat(sub_args)
    elif cmd == "ps":
        cmd_ps(sub_args)
    elif cmd in ["list", "ls"]:
        cmd_list(sub_args)
    elif cmd == "stats":
        cmd_stats(sub_args)
    else:
        sys.stdout.write(f"Unknown command: '{cmd}'. Run 'lmms help' for command list.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
