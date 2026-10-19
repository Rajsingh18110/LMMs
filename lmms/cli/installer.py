#!/usr/bin/env python3
"""
LMMs CLI Engine - Dependency Resolution & Installation Interface
Node.js / Yarn / npm-style minimalist dynamic terminal UX.

Features:
- Multi-Select Interactive Checkbox Wizard (Arrow keys, Space to toggle, Enter to confirm).
- Smart-Skip Cache Audit: Automatically detects existing components and skips redundant downloads.
- Component-level granularity: CLI, GUI, Engine, Voice.
- Combined flag support: e.g. lmms install --cli --engine
- Update engine: lmms update [--all|--cli|--gui|--engine|--voice]
- Auto-wiring: Configures ~/.lmms/config.json with active connection mode (local vs remote).
"""

from __future__ import annotations

import importlib.util
import json
import os
import queue
import random
import subprocess
import sys
import threading
import time
import select
from typing import List, Dict, Optional, Set, Any, Union

# --- Typography & ANSI Constants (Node.js/Yarn Blueprint) ---
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_DIM_GREY = "\033[90m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_GREEN = "\033[1;32m"
COLOR_BOLD_WHITE = "\033[1;37m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"

CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
PROGRESS_BAR_WIDTH = 25
MAX_CONCURRENT_WORKERS = 4

# --- Package Dependency Buckets ---
CLI_PACKAGES: List[Dict[str, str]] = [
    {"name": "rich", "spec": "rich", "desc": "Terminal formatting & ANSI telemetry"},
    {"name": "prompt-toolkit", "spec": "prompt_toolkit", "desc": "Interactive shell interface"},
    {"name": "requests", "spec": "requests", "desc": "HTTP network transport layer"},
    {"name": "psutil", "spec": "psutil", "desc": "Hardware profiler & memory map"},
    {"name": "pydantic", "spec": "pydantic", "desc": "Data validation & type schemas"},
]

GUI_PACKAGES: List[Dict[str, str]] = [
    {"name": "PyQt6", "spec": "PyQt6", "desc": "Qt6 desktop windowing bindings"},
    {"name": "PyQt6-Qt6", "spec": "PyQt6-Qt6", "desc": "Prebuilt Qt6 C++ graphics binaries"},
    {"name": "qasync", "spec": "qasync", "desc": "Asyncio loop bridge for Qt"},
    {"name": "Pillow", "spec": "Pillow", "desc": "High-throughput image processing"},
]

ENGINE_PACKAGES: List[Dict[str, str]] = [
    {"name": "fastapi", "spec": "fastapi", "desc": "High-performance ASGI framework"},
    {"name": "uvicorn", "spec": "uvicorn", "desc": "Lightning-fast ASGI server"},
    {"name": "nest-asyncio", "spec": "nest_asyncio", "desc": "Concurrent event loop patcher"},
    {"name": "huggingface-hub", "spec": "huggingface_hub", "desc": "Hugging Face Model Hub API"},
    {"name": "safetensors", "spec": "safetensors", "desc": "Fast & safe tensor serialization"},
    {"name": "psutil", "spec": "psutil", "desc": "Hardware profiler & memory map"},
]

ENGINE1_PACKAGES: List[Dict[str, str]] = [
    {"name": "fastapi", "spec": "fastapi", "desc": "High-performance ASGI framework"},
    {"name": "uvicorn", "spec": "uvicorn", "desc": "Lightning-fast ASGI server"},
    {"name": "nest-asyncio", "spec": "nest_asyncio", "desc": "Concurrent event loop patcher"},
    {"name": "huggingface-hub", "spec": "huggingface_hub", "desc": "Hugging Face Model Hub API"},
    {"name": "psutil", "spec": "psutil", "desc": "Hardware profiler & memory map"},
]

ENGINE2_PACKAGES: List[Dict[str, str]] = [
    {"name": "fastapi", "spec": "fastapi", "desc": "High-performance ASGI framework"},
    {"name": "uvicorn", "spec": "uvicorn", "desc": "Lightning-fast ASGI server"},
    {"name": "nest-asyncio", "spec": "nest_asyncio", "desc": "Concurrent event loop patcher"},
    {"name": "safetensors", "spec": "safetensors", "desc": "Fast & safe tensor serialization"},
    {"name": "transformers", "spec": "transformers", "desc": "PyTorch Transformers runtime"},
    {"name": "psutil", "spec": "psutil", "desc": "Hardware profiler & memory map"},
]

VOICE_PACKAGES: List[Dict[str, str]] = [
    {"name": "numpy", "spec": "numpy", "desc": "High-speed audio tensor arrays"},
    {"name": "sounddevice", "spec": "sounddevice", "desc": "Microphone audio input stream"},
    {"name": "soundfile", "spec": "soundfile", "desc": "Audio file format encoder"},
]


class PackageTask:
    """Represents a discrete tracked package resolution task."""

    def __init__(self, name: str, spec: str, desc: str = "", component: str = "general"):
        self.name = name
        self.spec = spec
        self.desc = desc
        self.component = component
        self.skipped: bool = False
        self.progress: float = 0.0
        self.speed: str = "0.0MB/s"
        self.started: bool = False
        self.completed: bool = False
        self.failed: bool = False
        self.rendered_static: bool = False
        self.duration: float = 0.0
        self.start_time: float = 0.0
        self.error_msg: str = ""


def check_package_installed(spec: str) -> bool:
    """Check if a Python package specification is already satisfied locally."""
    clean_spec = spec.replace("-", "_").split(">=")[0].split("==")[0].split("<")[0].strip()
    try:
        return importlib.util.find_spec(clean_spec) is not None
    except Exception:
        return False


def read_single_key() -> str:
    """Reads a single keypress cleanly across Linux/macOS and Windows."""
    if not sys.stdin.isatty():
        return "enter"
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            if ch2 == b"H": return "up"
            elif ch2 == b"P": return "down"
            elif ch2 == b"K": return "left"
            elif ch2 == b"M": return "right"
            return "unknown"
        elif ch == b" ": return "space"
        elif ch in (b"\r", b"\n"): return "enter"
        elif ch in (b"b", b"B", b"\x08", b"\x1b"): return "back"
        elif ch in (b"q", b"Q", b"\x03"): return "quit"
        return ch.decode("latin1", errors="ignore")
    else:
        import tty
        import termios
        import select
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A": return "up"
                        elif ch3 == "B": return "down"
                        elif ch3 == "C": return "right"
                        elif ch3 == "D": return "left"
                return "back"
            elif ch == " ": return "space"
            elif ch in ("\r", "\n"): return "enter"
            elif ch in ("b", "B", "\x7f", "\x08"): return "back"
            elif ch in ("q", "Q", "\x03"): return "quit"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def render_menu(
    header_subtitle: str,
    prompt_q: str,
    items: List[Dict[str, Any]],
    can_back: bool = False,
    back_hint: str = "Back"
) -> Union[int, str]:
    cursor = 0
    total_slots = len(items) + (1 if can_back else 0)

    while True:
        controls = f"[↑/↓] Navigate  ·  [Enter] Select  ·  [1-{len(items)}] Quick Select"
        if can_back:
            controls += "  ·  [←/B/ESC] Back"
        controls += "  ·  [Q] Exit"

        lines = [
            f"\n  {COLOR_BOLD_WHITE}LMMs Installer{COLOR_RESET} {COLOR_DIM}· {header_subtitle}{COLOR_RESET}",
            f"  {COLOR_CYAN}For more details, visit: https://lmms.markanm.com{COLOR_RESET}",
            f"  {COLOR_DIM}{'─' * 70}{COLOR_RESET}",
            f"  {COLOR_DIM}Controls: {controls}{COLOR_RESET}\n",
            f"  {COLOR_BOLD_CYAN}?{COLOR_RESET} {COLOR_BOLD_WHITE}{prompt_q}{COLOR_RESET}\n",
        ]
        for i, it in enumerate(items):
            is_cur = (i == cursor)
            prefix = f"{COLOR_BOLD_CYAN}❯{COLOR_RESET}" if is_cur else " "
            num_tag = f"{COLOR_CYAN}[{i+1}]{COLOR_RESET}" if is_cur else f"{COLOR_DIM}[{i+1}]{COLOR_RESET}"
            title_col = COLOR_BOLD_WHITE if is_cur else COLOR_RESET
            lines.append(f"  {prefix} {num_tag} {title_col}{it['title']}{COLOR_RESET}")
            lines.append(f"        {COLOR_DIM}{it['desc']}{COLOR_RESET}\n")

        lines.append(f"  {COLOR_DIM}{'─' * 70}{COLOR_RESET}")
        if can_back:
            is_back_cur = (cursor == len(items))
            prefix = f"{COLOR_BOLD_CYAN}❯{COLOR_RESET}" if is_back_cur else " "
            back_tag = f"{COLOR_CYAN}[B]{COLOR_RESET}" if is_back_cur else f"{COLOR_DIM}[B]{COLOR_RESET}"
            back_title = f"{COLOR_BOLD_WHITE}◄ {back_hint}{COLOR_RESET}" if is_back_cur else f"{COLOR_DIM}◄ {back_hint}{COLOR_RESET}"
            lines.append(f"  {prefix} {back_tag} {back_title}\n")

        output = "\033[H\033[J" + "\n".join(lines) + "\n"
        sys.stdout.write(output)
        sys.stdout.flush()

        key = read_single_key()
        if key in ("up", "down"):
            cursor = (cursor + (1 if key == "down" else -1)) % total_slots
        elif key == "left":
            if can_back:
                return "back"
        elif key in [str(i + 1) for i in range(min(9, len(items)))]:
            return int(key) - 1
        elif key == "enter":
            if can_back and cursor == len(items):
                return "back"
            return cursor
        elif key == "back":
            if can_back:
                return "back"
            else:
                sys.stdout.write(f"\n{COLOR_DIM}Operation cancelled.{COLOR_RESET}\n")
                sys.exit(0)
        elif key in ("quit", "q", "Q"):
            sys.stdout.write(f"\n{COLOR_DIM}Operation cancelled.{COLOR_RESET}\n")
            sys.exit(0)


def interactive_flowchart_wizard(action_verb: str = "Install") -> List[str]:
    """
    Renders an interactive terminal wizard matching the architecture flowchart:
    Level 1: Deployment Tier -> [1] Individual Workstation / [2] Enterprise Infrastructure
    Level 2 (Individual): Component Selection ->
      [1] Engine 1 (Lightweight Runtime - llama.cpp + AirEngine)
      [2] Engine 2 (PyTorch Native - PyTorch + AirEngine)
      [3] Super Engine (Unified Runtimes - llama.cpp + PyTorch + AirEngine)
      [4] Desktop Studio (GUI)
      [5] Terminal Studio (CLI)
      [6] Complete Ecosystem Suite
    Level 2 (Enterprise): Vertical Role Selection ->
      [1] Host Server Infrastructure
      [2] Remote Client Studio
    Level 3 (Enterprise Host):
      [1] Dedicated Enterprise Super Host Server (All Engines Unified)
      [2] PyTorch / AirEngine High-Performance Node
      [3] Engine 1 Lightweight Node
    Level 3 (Enterprise Client):
      [1] Enterprise Desktop Client (GUI)
      [2] Enterprise Terminal Client (CLI)
      [3] Complete Client Suite (Desktop GUI + Terminal CLI)
    """
    if not sys.stdin.isatty():
        return ["cli", "gui", "engine", "voice"]

    sys.stdout.write(CURSOR_HIDE)
    sys.stdout.flush()

    persona_items = [
        {
            "id": "individual",
            "title": "Individual Workstation",
            "desc": "Single workstation deployment with local hardware acceleration & offloading.",
        },
        {
            "id": "enterprise",
            "title": "Enterprise Infrastructure",
            "desc": "Distributed client-server infrastructure for teams across LAN/VPC networks.",
        },
    ]

    indiv_items = [
        {
            "id": "engine1",
            "title": "Engine 1 (Lightweight Runtime)",
            "desc": "llama.cpp + AirEngine (GGUF format, low RAM footprint, pure API on port 11435)",
            "components": ["engine1"],
        },
        {
            "id": "engine2",
            "title": "Engine 2 (PyTorch Native)",
            "desc": "PyTorch + Transformers + AirEngine (Full-precision Safetensors model runtime)",
            "components": ["engine2"],
        },
        {
            "id": "engine",
            "title": "Super Engine (Unified Runtimes)",
            "desc": "All runtimes unified (llama.cpp + PyTorch + AirEngine) in a single service",
            "components": ["engine"],
        },
        {
            "id": "gui",
            "title": "Desktop Studio (GUI)",
            "desc": "Monaco Editor + Local Engine Client + Git Integration (gui/ branch)",
            "components": ["gui", "engine"],
        },
        {
            "id": "cli",
            "title": "Terminal Studio (CLI)",
            "desc": "Interactive AI Shell + Developer Toolchain + Local Engine Client (cli/ branch)",
            "components": ["cli", "engine"],
        },
        {
            "id": "all",
            "title": "Complete Ecosystem Suite",
            "desc": "Full installation: Desktop Studio, Terminal CLI, Voice & Super Engine",
            "components": ["gui", "cli", "engine", "voice"],
        },
    ]

    enterprise_role_items = [
        {
            "id": "host",
            "title": "Host Server Infrastructure",
            "desc": "Central inference server daemon listening on 0.0.0.0:11435 for team access",
        },
        {
            "id": "client",
            "title": "Remote Client Studio",
            "desc": "Workstation applications connecting to host via Local->LAN->Global discovery",
        },
    ]

    host_items = [
        {
            "id": "super_host",
            "title": "Dedicated Enterprise Super Host Server (All Engines)",
            "desc": "Central multi-engine daemon listening on 0.0.0.0:11435 for team LAN/VPC access",
            "components": ["engine"],
        },
        {
            "id": "host_node",
            "title": "PyTorch / AirEngine High-Performance Node",
            "desc": "Dedicated heavy cluster inference node for multi-GPU & large model serving",
            "components": ["engine2"],
        },
        {
            "id": "engine1_node",
            "title": "Engine 1 Lightweight Node",
            "desc": "llama.cpp + AirEngine (GGUF format, low RAM footprint, port 11435)",
            "components": ["engine1"],
        },
    ]

    client_items = [
        {
            "id": "client_gui",
            "title": "Enterprise Desktop Client (GUI)",
            "desc": "Desktop Studio client featuring Local -> LAN UDP Beacon -> Global Remote auto-discovery",
            "components": ["gui"],
        },
        {
            "id": "client_cli",
            "title": "Enterprise Terminal Client (CLI)",
            "desc": "Terminal Studio client featuring Local -> LAN UDP Beacon -> Global Remote auto-discovery",
            "components": ["cli"],
        },
        {
            "id": "client_suite",
            "title": "Complete Client Suite (Desktop GUI + Terminal CLI)",
            "desc": "Install both GUI and CLI clients configured for enterprise host auto-discovery",
            "components": ["gui", "cli"],
        },
    ]

    try:
        screen = "level1"
        history: List[str] = []

        while True:
            if screen == "level1":
                res = render_menu(
                    header_subtitle="Architecture Setup Wizard",
                    prompt_q="Select Deployment Architecture:",
                    items=persona_items,
                    can_back=False,
                )
                if res == 0:
                    history.append(screen)
                    screen = "individual"
                elif res == 1:
                    history.append(screen)
                    screen = "enterprise_roles"

            elif screen == "individual":
                res = render_menu(
                    header_subtitle="Individual Workstation Setup",
                    prompt_q="Select Component Configuration:",
                    items=indiv_items,
                    can_back=True,
                    back_hint="Back to Architecture Selection",
                )
                if res == "back":
                    screen = history.pop() if history else "level1"
                elif isinstance(res, int):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return list(indiv_items[res]["components"])

            elif screen == "enterprise_roles":
                res = render_menu(
                    header_subtitle="Enterprise Infrastructure Setup",
                    prompt_q="Select Enterprise Infrastructure Role:",
                    items=enterprise_role_items,
                    can_back=True,
                    back_hint="Back to Architecture Selection",
                )
                if res == "back":
                    screen = history.pop() if history else "level1"
                elif res == 0:
                    history.append(screen)
                    screen = "enterprise_host"
                elif res == 1:
                    history.append(screen)
                    screen = "enterprise_client"

            elif screen == "enterprise_host":
                res = render_menu(
                    header_subtitle="Enterprise Host Server Setup",
                    prompt_q="Select Host Server Configuration:",
                    items=host_items,
                    can_back=True,
                    back_hint="Back to Enterprise Role Selection",
                )
                if res == "back":
                    screen = history.pop() if history else "enterprise_roles"
                elif isinstance(res, int):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return list(host_items[res]["components"])

            elif screen == "enterprise_client":
                res = render_menu(
                    header_subtitle="Enterprise Client Studio Setup",
                    prompt_q="Select Client Studio Configuration:",
                    items=client_items,
                    can_back=True,
                    back_hint="Back to Enterprise Role Selection",
                )
                if res == "back":
                    screen = history.pop() if history else "enterprise_roles"
                elif isinstance(res, int):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return list(client_items[res]["components"])

    finally:
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.flush()


def sync_lmms_config(installed_components: List[str]) -> None:
    """Automatically updates ~/.lmms/config.json with active component bindings."""
    try:
        config_dir = os.path.expanduser("~/.lmms")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        config: Dict[str, object] = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        existing_components = set(config.get("installed_components", []))  # type: ignore
        existing_components.update(installed_components)
        config["installed_components"] = sorted(list(existing_components))

        # Auto-wiring mode
        if any(c in existing_components for c in ("engine", "engine1", "engine2")):
            config.setdefault("mode", "local")
            config.setdefault("engine_host", "127.0.0.1")
            config.setdefault("engine_port", 11435)
        else:
            config.setdefault("mode", "remote")

        config["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    except Exception:
        pass


class CLIInstaller:
    """Core Systems Installer Engine implementing Node.js-style CLI rendering."""

    def __init__(self, args: List[str], is_update: bool = False):
        self.args = args
        self.is_update = is_update
        self.selected_components: Set[str] = set()
        self.packages: List[PackageTask] = []
        self._parse_args()

    def _parse_args(self) -> None:
        """Parse user input arguments into bucketed resolution targets."""
        if "-h" in self.args or "--help" in self.args:
            self._print_help()
            sys.exit(0)

        # Flag detection
        has_cli = "--cli" in self.args or "-c" in self.args
        has_gui = "--gui" in self.args or "-g" in self.args
        has_engine = "--engine" in self.args or "-e" in self.args
        has_engine1 = "--engine1" in self.args
        has_engine2 = "--engine2" in self.args
        has_voice = "--voice" in self.args or "-v" in self.args
        has_all = "--all" in self.args or "-a" in self.args

        if has_all:
            self.selected_components = {"cli", "gui", "engine", "voice"}
        else:
            if has_cli: self.selected_components.add("cli")
            if has_gui: self.selected_components.add("gui")
            if has_engine: self.selected_components.add("engine")
            if has_engine1: self.selected_components.add("engine1")
            if has_engine2: self.selected_components.add("engine2")
            if has_voice: self.selected_components.add("voice")

        # Positional packages check (e.g. lmms install <pkg1> <pkg2>)
        positionals = [a for a in self.args if not a.startswith("-")]
        if positionals:
            for p in positionals:
                self.packages.append(PackageTask(name=p, spec=p, component="custom"))
            return

        # If no flags provided, launch the 2-level architecture flowchart wizard
        if not self.selected_components:
            if sys.stdin.isatty():
                verb = "Update" if self.is_update else "Install"
                chosen = interactive_flowchart_wizard(action_verb=verb)
                self.selected_components = set(chosen)
            else:
                self.selected_components = {"cli", "gui", "engine", "voice"}

        # Assemble package tasks based on selected components
        if "cli" in self.selected_components:
            for p in CLI_PACKAGES:
                self.packages.append(PackageTask(**p, component="cli"))
        if "gui" in self.selected_components:
            for p in GUI_PACKAGES:
                self.packages.append(PackageTask(**p, component="gui"))
        if "engine" in self.selected_components:
            for p in ENGINE_PACKAGES:
                self.packages.append(PackageTask(**p, component="engine"))
        if "engine1" in self.selected_components:
            for p in ENGINE1_PACKAGES:
                self.packages.append(PackageTask(**p, component="engine1"))
        if "engine2" in self.selected_components:
            for p in ENGINE2_PACKAGES:
                self.packages.append(PackageTask(**p, component="engine2"))
        if "voice" in self.selected_components:
            for p in VOICE_PACKAGES:
                self.packages.append(PackageTask(**p, component="voice"))

    def _print_help(self) -> None:
        action = "update" if self.is_update else "install"
        title = "Updater" if self.is_update else "Installer"
        sys.stdout.write(
            f"{COLOR_BOLD_WHITE}lmms {action}{COLOR_RESET} {COLOR_DIM}v2.1.0 (Component {title}){COLOR_RESET}\n\n"
            f"Usage: lmms {action} [options]\n\n"
            f"Options:\n"
            f"  (no flags)    Interactive Architecture Flowchart Wizard (Individual vs Enterprise)\n"
            f"  --all, -a     {'Update' if self.is_update else 'Install'} all components: CLI, GUI, Engine, and Voice\n"
            f"  --cli, -c     {'Update' if self.is_update else 'Install'} Standalone CLI (terminal chat & LAN remote client)\n"
            f"  --gui, -g     {'Update' if self.is_update else 'Install'} Desktop Studio GUI (PyQt6 windowing toolkit)\n"
            f"  --engine, -e  {'Update' if self.is_update else 'Install'} Superpower Engine (llama.cpp + PyTorch + Air Engine + API Daemon)\n"
            f"  --engine1     {'Update' if self.is_update else 'Install'} Engine 1 (llama.cpp + Air Engine GGUF)\n"
            f"  --engine2     {'Update' if self.is_update else 'Install'} Engine 2 (PyTorch + AirEngine Safetensors)\n"
            f"  --voice, -v   {'Update' if self.is_update else 'Install'} Voice input & audio streaming dependencies\n"
            f"  -h, --help    Show this help message\n\n"
            f"Combine options freely: lmms {action} --cli --engine\n"
        )
        sys.stdout.flush()

    def _audit_and_filter_tasks(self) -> queue.Queue[PackageTask]:
        """Performs Smart Skip check for already satisfied components."""
        task_queue: queue.Queue[PackageTask] = queue.Queue()

        for task in self.packages:
            if not self.is_update and check_package_installed(task.spec):
                # Smart Skip: Already satisfied!
                task.skipped = True
                task.completed = True
                task.progress = 1.0
                task.duration = 0.0
            else:
                task_queue.put(task)

        return task_queue

    def _worker(self, task_queue: queue.Queue[PackageTask]) -> None:
        """Background thread executing pip download/install silently."""
        while not task_queue.empty():
            try:
                task = task_queue.get_nowait()
            except queue.Empty:
                break

            task.started = True
            task.start_time = time.time()

            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                task.spec,
                "--quiet",
                "--no-warn-script-location",
            ]
            if self.is_update:
                cmd.append("--upgrade")
            if sys.prefix == sys.base_prefix:
                cmd.append("--break-system-packages")

            proc = None
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except Exception as e:
                task.error_msg = str(e)
                task.failed = True

            if proc is not None:
                while proc.poll() is None:
                    elapsed = time.time() - task.start_time
                    task.progress = min(0.92, elapsed / 1.6)
                    task.speed = f"{random.uniform(8.4, 26.8):.1f}MB/s"
                    time.sleep(0.04)

                _, stderr_data = proc.communicate()

                if proc.returncode == 0:
                    task.failed = False
                else:
                    if check_package_installed(task.spec):
                        task.failed = False
                    else:
                        task.failed = True
                        task.error_msg = stderr_data.strip().split("\n")[-1] if stderr_data else "Install failed"

            while task.progress < 1.0:
                task.progress = min(1.0, task.progress + 0.18)
                time.sleep(0.02)

            task.duration = max(0.2, time.time() - task.start_time)
            task.completed = True
            task_queue.task_done()

    def run(self) -> None:
        """Execute the complete 3-phase installation lifecycle."""
        total_start = time.time()
        action_verb = "Updating" if self.is_update else "Resolving"
        components_label = ", ".join(sorted(list(self.selected_components))) if self.selected_components else "selected targets"

        # Phase 1: Header
        sys.stdout.write(f"\n{COLOR_BOLD_WHITE}lmms{COLOR_RESET} {COLOR_DIM}v2.1.0{COLOR_RESET}\n")
        sys.stdout.write(
            f"{COLOR_CYAN}ℹ{COLOR_RESET} {COLOR_DIM}{action_verb} dependencies for [{COLOR_BOLD_CYAN}{components_label}{COLOR_RESET}{COLOR_DIM}]...{COLOR_RESET}\n\n"
        )
        sys.stdout.flush()

        # Audit and Smart Skip check
        task_queue = self._audit_and_filter_tasks()

        # Phase 2: Concurrent Execution
        num_workers = min(MAX_CONCURRENT_WORKERS, max(1, task_queue.qsize()))
        threads: List[threading.Thread] = []
        for _ in range(num_workers):
            th = threading.Thread(target=self._worker, args=(task_queue,), daemon=True)
            th.start()
            threads.append(th)

        is_tty = sys.stdout.isatty() or os.environ.get("FORCE_ANIMATION") == "1"

        if is_tty:
            self._render_interactive()
        else:
            self._render_non_interactive()

        for th in threads:
            th.join(timeout=1.0)

        # Phase 3: Clean Exit Summary & Config Auto-Wiring
        total_elapsed = time.time() - total_start
        skipped_count = sum(1 for t in self.packages if t.skipped)
        installed_count = sum(1 for t in self.packages if t.completed and not t.skipped and not t.failed)
        failed_count = sum(1 for t in self.packages if t.failed)

        action_word = "Updated" if self.is_update else "Installed"
        summary_parts = [f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}Done:{COLOR_RESET} {action_word} {installed_count} package(s)"]
        if skipped_count > 0:
            summary_parts.append(f"{COLOR_DIM}({skipped_count} skipped - already satisfied){COLOR_RESET}")
        if failed_count > 0:
            summary_parts.append(f"{COLOR_RED}({failed_count} failed){COLOR_RESET}")
        summary_parts.append(f"in {total_elapsed:.1f}s.")

        sys.stdout.write(f"\n{' '.join(summary_parts)}\n")

        # Auto-wire configuration
        if self.selected_components:
            sync_lmms_config(list(self.selected_components))
            sys.stdout.write(
                f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} {COLOR_DIM}Configuration synchronized (~/.lmms/config.json){COLOR_RESET}\n"
            )

        # Quick Next Steps Guide & Continue.dev Configuration Card
        has_any_engine = any(c in self.selected_components for c in ("engine", "engine1", "engine2"))
        if has_any_engine:
            sys.stdout.write(
                f"\n{COLOR_CYAN}╭──────────────────────────────────────────────────────────────────────────────╮{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  {COLOR_BOLD_GREEN}✔ LMMs Inference Engine is Ready!{COLOR_RESET}{' ' * 43}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}{' ' * 78}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  Daemon Endpoint:    {COLOR_BOLD_WHITE}http://127.0.0.1:11435/v1{COLOR_RESET}{' ' * 31}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  Quick Commands:     {COLOR_BOLD_CYAN}lmms server start{COLOR_RESET} {COLOR_DIM}·{COLOR_RESET} {COLOR_BOLD_CYAN}lmms run <model>{COLOR_RESET}{' ' * 23}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}{' ' * 78}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  {COLOR_DIM}Continue.dev / Open-WebUI Configuration:{COLOR_RESET}{' ' * 36}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  {COLOR_DIM}{{\"title\": \"LMMs Engine\", \"provider\": \"openai\", \"model\": \"<model_tag>\",{COLOR_RESET}    {COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}│{COLOR_RESET}  {COLOR_DIM} \"apiBase\": \"http://localhost:11435/v1\"}}{COLOR_RESET}{' ' * 39}{COLOR_CYAN}│{COLOR_RESET}\n"
                f"{COLOR_CYAN}╰──────────────────────────────────────────────────────────────────────────────╯{COLOR_RESET}\n\n"
            )
        elif "gui" in self.selected_components:
            sys.stdout.write(f"\n{COLOR_DIM}Next step: Run '{COLOR_BOLD_CYAN}lmms gui{COLOR_RESET}{COLOR_DIM}' to open Desktop Studio GUI.{COLOR_RESET}\n\n")
        elif "cli" in self.selected_components:
            sys.stdout.write(f"\n{COLOR_DIM}Next step: Run '{COLOR_BOLD_CYAN}lmms{COLOR_RESET}{COLOR_DIM}' or '{COLOR_BOLD_CYAN}lmms run <model>{COLOR_RESET}{COLOR_DIM}' to launch Interactive Shell.{COLOR_RESET}\n\n")
        sys.stdout.flush()

    def _render_interactive(self) -> None:
        """Transient multi-line layout with live Braille spinner and ANSI self-cleaning."""
        spin_idx = 0
        last_lines = 0

        sys.stdout.write(CURSOR_HIDE)
        sys.stdout.flush()

        try:
            while not all(t.rendered_static for t in self.packages):
                # 1. Ephemeral Wipe
                if last_lines > 0:
                    sys.stdout.write(f"\r\033[{last_lines}A\033[J")

                # 2. Persistent Success Mutation
                for task in self.packages:
                    if task.completed and not task.rendered_static:
                        if task.skipped:
                            sys.stdout.write(
                                f"\r\033[K{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                                f"{COLOR_DIM}already satisfied (skipped){COLOR_RESET}\n"
                            )
                        elif task.failed:
                            sys.stdout.write(
                                f"\r\033[K{COLOR_RED}✖{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                                f"{COLOR_DIM}failed ({task.error_msg}){COLOR_RESET}\n"
                            )
                        else:
                            verb = "updated" if self.is_update else "installed"
                            sys.stdout.write(
                                f"\r\033[K{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                                f"{COLOR_DIM}{verb} successfully in {task.duration:.1f}s{COLOR_RESET}\n"
                            )
                        task.rendered_static = True

                # 3. Transient Active Layer
                active = [t for t in self.packages if t.started and not t.rendered_static]
                spinner_char = SPINNER_FRAMES[spin_idx % len(SPINNER_FRAMES)]
                spin_idx += 1

                for task in active:
                    filled_len = int(task.progress * PROGRESS_BAR_WIDTH)
                    unfilled_len = PROGRESS_BAR_WIDTH - filled_len
                    bar = f"{COLOR_CYAN}{'━' * filled_len}{COLOR_DIM_GREY}{'─' * unfilled_len}{COLOR_RESET}"
                    pct = int(task.progress * 100)

                    sys.stdout.write(
                        f"\r\033[K  {COLOR_BOLD_CYAN}{spinner_char}{COLOR_RESET} "
                        f"{COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                        f"[{bar}] {COLOR_DIM}{pct:>3}% {task.speed}{COLOR_RESET}\n"
                    )

                last_lines = len(active)
                sys.stdout.flush()
                time.sleep(0.045)

            if last_lines > 0:
                sys.stdout.write(f"\r\033[{last_lines}A\033[J")
                sys.stdout.flush()

        finally:
            sys.stdout.write(CURSOR_SHOW)
            sys.stdout.flush()

    def _render_non_interactive(self) -> None:
        """Piped / CI rendering: clean line-by-line mutation without ANSI repositioning."""
        while not all(t.rendered_static for t in self.packages):
            for task in self.packages:
                if task.completed and not task.rendered_static:
                    if task.skipped:
                        sys.stdout.write(
                            f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                            f"{COLOR_DIM}already satisfied (skipped){COLOR_RESET}\n"
                        )
                    elif task.failed:
                        sys.stdout.write(
                            f"{COLOR_RED}✖{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                            f"{COLOR_DIM}failed ({task.error_msg}){COLOR_RESET}\n"
                        )
                    else:
                        verb = "updated" if self.is_update else "installed"
                        sys.stdout.write(
                            f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                            f"{COLOR_DIM}{verb} successfully in {task.duration:.1f}s{COLOR_RESET}\n"
                        )
                    task.rendered_static = True
                    sys.stdout.flush()
            time.sleep(0.05)


def run_installer(args: Optional[List[str]] = None) -> None:
    """Entry point for the LMMs CLI installer."""
    if args is None:
        args = sys.argv[1:]
    installer = CLIInstaller(args, is_update=False)
    installer.run()


def run_updater(args: Optional[List[str]] = None) -> None:
    """Entry point for the LMMs CLI updater."""
    if args is None:
        args = sys.argv[1:]
    updater = CLIInstaller(args, is_update=True)
    updater.run()


if __name__ == "__main__":
    run_installer(sys.argv[1:])
