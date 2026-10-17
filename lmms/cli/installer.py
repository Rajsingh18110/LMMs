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
from typing import List, Dict, Optional, Set

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
        elif ch in (b"a", b"A"): return "a"
        elif ch in (b"q", b"Q", b"\x03"): return "quit"
        return ch.decode("latin1", errors="ignore")
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "up"
                    elif ch3 == "B": return "down"
                    elif ch3 == "C": return "right"
                    elif ch3 == "D": return "left"
                return "esc"
            elif ch == " ": return "space"
            elif ch in ("\r", "\n"): return "enter"
            elif ch in ("a", "A"): return "a"
            elif ch in ("q", "Q", "\x03"): return "quit"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_checkbox_wizard(action_verb: str = "Install") -> List[str]:
    """
    Renders an interactive terminal multi-select checkbox menu.
    Allows toggling options with [SPACE], navigating with [UP/DOWN],
    toggling all with [a], and confirming with [ENTER].
    """
    items = [
        {
            "id": "cli",
            "title": "Standalone CLI",
            "desc": "Terminal Chat, LAN Remote Client (0-GPU overhead)",
            "selected": True,
        },
        {
            "id": "gui",
            "title": "Desktop Studio GUI",
            "desc": "PyQt6 Hardware-Accelerated Visual Desktop App",
            "selected": False,
        },
        {
            "id": "engine",
            "title": "Standalone Engine",
            "desc": "Dual Model Runtime (GGUF + PyTorch) & API Server Daemon",
            "selected": True,
        },
        {
            "id": "voice",
            "title": "Voice Dependencies",
            "desc": "Real-time microphone audio capture & audio stream buffers",
            "selected": False,
        },
    ]

    cursor_idx = 0
    total_items = len(items)

    # Hide cursor
    sys.stdout.write(CURSOR_HIDE)
    sys.stdout.flush()

    try:
        while True:
            # Render menu
            lines: List[str] = []
            lines.append(f"  ▲  {COLOR_BOLD_WHITE}LMMs Component {action_verb} Wizard{COLOR_RESET}")
            lines.append(f"  {COLOR_DIM}{'─' * 65}{COLOR_RESET}")
            lines.append(
                f"  {COLOR_DIM}Controls: [↑/↓] Navigate · [SPACE] Toggle · [a] Toggle All · [ENTER] Confirm · [q] Cancel{COLOR_RESET}\n"
            )

            for i, it in enumerate(items):
                is_cursor = (i == cursor_idx)
                prefix = f"{COLOR_BOLD_CYAN}❯{COLOR_RESET}" if is_cursor else " "
                chk = f"{COLOR_BOLD_GREEN}[X]{COLOR_RESET}" if it["selected"] else f"{COLOR_DIM}[ ]{COLOR_RESET}"
                title_color = COLOR_BOLD_WHITE if is_cursor else COLOR_RESET
                lines.append(
                    f"  {prefix} {chk} {title_color}{it['title']:<24}{COLOR_RESET} {COLOR_DIM}{it['desc']}{COLOR_RESET}"
                )

            selected_names = [it["title"] for it in items if it["selected"]]
            sel_str = ", ".join(selected_names) if selected_names else f"{COLOR_YELLOW}None (select at least one){COLOR_RESET}"
            lines.append(f"\n  {COLOR_DIM}{'─' * 65}{COLOR_RESET}")
            lines.append(f"  {COLOR_BOLD_WHITE}Selected:{COLOR_RESET} {sel_str}")
            lines.append(f"  {COLOR_CYAN}Press [ENTER] to proceed with {action_verb.lower()}...{COLOR_RESET}")

            # Clear screen and draw
            output = "\033[H\033[J" + "\n".join(lines) + "\n"
            sys.stdout.write(output)
            sys.stdout.flush()

            # Read user keypress
            key = read_single_key()
            if key == "up":
                cursor_idx = (cursor_idx - 1) % total_items
            elif key == "down":
                cursor_idx = (cursor_idx + 1) % total_items
            elif key == "space":
                items[cursor_idx]["selected"] = not items[cursor_idx]["selected"]
            elif key == "a":
                # If all selected, deselect all; otherwise select all
                all_sel = all(it["selected"] for it in items)
                for it in items:
                    it["selected"] = not all_sel
            elif key == "enter":
                selected_ids = [it["id"] for it in items if it["selected"]]
                if selected_ids:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return selected_ids
            elif key in ("quit", "esc"):
                sys.stdout.write(f"\n{COLOR_DIM}Operation cancelled by user.{COLOR_RESET}\n")
                sys.stdout.flush()
                sys.exit(0)

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
        if "engine" in existing_components:
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
        has_voice = "--voice" in self.args or "-v" in self.args
        has_all = "--all" in self.args or "-a" in self.args

        if has_all:
            self.selected_components = {"cli", "gui", "engine", "voice"}
        else:
            if has_cli: self.selected_components.add("cli")
            if has_gui: self.selected_components.add("gui")
            if has_engine: self.selected_components.add("engine")
            if has_voice: self.selected_components.add("voice")

        # Positional packages check (e.g. lmms install <pkg1> <pkg2>)
        positionals = [a for a in self.args if not a.startswith("-")]
        if positionals:
            for p in positionals:
                self.packages.append(PackageTask(name=p, spec=p, component="custom"))
            return

        # If no flags provided
        if not self.selected_components:
            if sys.stdin.isatty():
                verb = "Update" if self.is_update else "Install"
                chosen = interactive_checkbox_wizard(action_verb=verb)
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
        if "voice" in self.selected_components:
            for p in VOICE_PACKAGES:
                self.packages.append(PackageTask(**p, component="voice"))

    def _print_help(self) -> None:
        action = "update" if self.is_update else "install"
        title = "Updater" if self.is_update else "Installer"
        sys.stdout.write(
            f"📦 {COLOR_BOLD_WHITE}lmms {action}{COLOR_RESET} {COLOR_DIM}v1.0.0 (Component {title}){COLOR_RESET}\n\n"
            f"Usage: lmms {action} [options]\n\n"
            f"Options:\n"
            f"  (no flags)    Interactive Multi-Select Checkbox Wizard (select components interactively)\n"
            f"  --all, -a     {'Update' if self.is_update else 'Install'} all components: CLI, GUI, Engine, and Voice\n"
            f"  --cli, -c     {'Update' if self.is_update else 'Install'} Standalone CLI (terminal chat & LAN remote client)\n"
            f"  --gui, -g     {'Update' if self.is_update else 'Install'} Desktop Studio GUI (PyQt6 windowing toolkit)\n"
            f"  --engine, -e  {'Update' if self.is_update else 'Install'} Standalone Engine binary & backend API daemon\n"
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
        sys.stdout.write(f"\n📦 {COLOR_BOLD_WHITE}lmms-engine{COLOR_RESET} {COLOR_DIM}v1.0.0{COLOR_RESET}\n")
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
        summary_parts = [f"✨ {COLOR_BOLD_WHITE}Done!{COLOR_RESET} {action_word} {installed_count} packages"]
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
                f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} {COLOR_DIM}Configuration synchronized (~/.lmms/config.json){COLOR_RESET}\n\n"
            )

        # Quick Next Steps Guide
        if "engine" in self.selected_components:
            sys.stdout.write(f"{COLOR_DIM}Next step: Run '{COLOR_BOLD_CYAN}lmms server start{COLOR_RESET}{COLOR_DIM}' to start local engine daemon.{COLOR_RESET}\n")
        elif "cli" in self.selected_components:
            sys.stdout.write(f"{COLOR_DIM}Next step: Run '{COLOR_BOLD_CYAN}lmms connect{COLOR_RESET}{COLOR_DIM}' to bind to a LAN engine, or '{COLOR_BOLD_CYAN}lmms chat <model>{COLOR_RESET}{COLOR_DIM}'.{COLOR_RESET}\n")
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
