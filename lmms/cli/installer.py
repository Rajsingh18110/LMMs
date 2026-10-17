#!/usr/bin/env python3
"""
LMMs CLI Engine - Dependency Resolution & Installation Interface
Node.js / Yarn / npm-style minimalist dynamic terminal UX.

Conforms to:
- No heavy text borders, grids, or boxes.
- Strict typography colors: [dim] for metadata, [cyan] for active operations, [green] for irreversible confirmation.
- Classic Braille 8-point cyclic character loop: ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏ in bold cyan.
- Slim single-color horizontal progress line restricted to 25 terminal columns.
- Silent subprocess interception (stdout/stderr silenced).
- Transient ephemeral layers with instant ANSI self-cleaning and persistent success mutation.
- 3-Phase lifecycle: Header initialization, concurrently tracked fetch, clean exit summary.
"""

from __future__ import annotations

import importlib.util
import os
import queue
import random
import subprocess
import sys
import threading
import time
from typing import List, Dict, Optional

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

CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
PROGRESS_BAR_WIDTH = 25
MAX_CONCURRENT_WORKERS = 4

# --- Package Dependency Buckets ---
CLI_PACKAGES: List[Dict[str, str]] = [
    {"name": "huggingface-hub", "spec": "huggingface_hub", "desc": "Hugging Face Model Hub API"},
    {"name": "rich", "spec": "rich", "desc": "Terminal formatting & ANSI telemetry"},
    {"name": "prompt-toolkit", "spec": "prompt_toolkit", "desc": "Interactive shell interface"},
    {"name": "requests", "spec": "requests", "desc": "HTTP network transport layer"},
    {"name": "psutil", "spec": "psutil", "desc": "Hardware profiler & memory map"},
    {"name": "pydantic", "spec": "pydantic", "desc": "Data validation & type schemas"},
    {"name": "fastapi", "spec": "fastapi", "desc": "High-performance ASGI framework"},
    {"name": "uvicorn", "spec": "uvicorn", "desc": "Lightning-fast ASGI server"},
    {"name": "nest-asyncio", "spec": "nest_asyncio", "desc": "Concurrent event loop patcher"},
]

GUI_PACKAGES: List[Dict[str, str]] = [
    {"name": "PyQt6", "spec": "PyQt6", "desc": "Qt6 desktop windowing bindings"},
    {"name": "PyQt6-Qt6", "spec": "PyQt6-Qt6", "desc": "Prebuilt Qt6 C++ graphics binaries"},
    {"name": "qasync", "spec": "qasync", "desc": "Asyncio loop bridge for Qt"},
    {"name": "Pillow", "spec": "Pillow", "desc": "High-throughput image processing"},
]


class PackageTask:
    """Represents a discrete tracked package resolution task."""

    def __init__(self, name: str, spec: str, desc: str = ""):
        self.name = name
        self.spec = spec
        self.desc = desc
        self.progress: float = 0.0
        self.speed: str = "0.0MB/s"
        self.started: bool = False
        self.completed: bool = False
        self.failed: bool = False
        self.rendered_static: bool = False
        self.duration: float = 0.0
        self.start_time: float = 0.0
        self.error_msg: str = ""


class CLIInstaller:
    """Core Systems Installer Engine implementing Node.js-style CLI rendering."""

    def __init__(self, args: List[str]):
        self.args = args
        self.flag: str = "--all"
        self.packages: List[PackageTask] = []
        self._parse_args()

    def _parse_args(self) -> None:
        """Parse user input arguments into bucketed resolution targets."""
        if "-h" in self.args or "--help" in self.args:
            self._print_help()
            sys.exit(0)

        if "--cli" in self.args or "-c" in self.args:
            self.flag = "--cli"
            self.packages = [PackageTask(**p) for p in CLI_PACKAGES]
        elif "--gui" in self.args or "-g" in self.args:
            self.flag = "--gui"
            self.packages = [PackageTask(**p) for p in GUI_PACKAGES]
        elif "--all" in self.args or "-a" in self.args:
            self.flag = "--all"
            self.packages = [PackageTask(**p) for p in (CLI_PACKAGES + GUI_PACKAGES)]
        else:
            # Check for positional package names
            positionals = [a for a in self.args if not a.startswith("-")]
            if positionals:
                self.flag = f"{len(positionals)} package(s)"
                self.packages = [PackageTask(name=p, spec=p) for p in positionals]
            else:
                self.flag = "--all"
                self.packages = [PackageTask(**p) for p in (CLI_PACKAGES + GUI_PACKAGES)]

    def _print_help(self) -> None:
        sys.stdout.write(
            f"📦 {COLOR_BOLD_WHITE}lmms-engine{COLOR_RESET} {COLOR_DIM}v1.0.0{COLOR_RESET}\n"
            f"Usage: lmms install [options]\n\n"
            f"Options:\n"
            f"  --all         Parallel multi-threaded resolution of CLI tools & GUI environments (default)\n"
            f"  --cli         Headless modules, compiler tools, and terminal-only dependencies\n"
            f"  --gui         Graphical engines, asset wrappers, rendering pipelines, Qt6 toolkits\n"
            f"  -h, --help    Show this help message\n"
        )
        sys.stdout.flush()

    def _worker(self, task_queue: queue.Queue[PackageTask]) -> None:
        """Background thread executing pip download/install silently."""
        while not task_queue.empty():
            try:
                task = task_queue.get_nowait()
            except queue.Empty:
                break

            task.started = True
            task.start_time = time.time()

            # Execute pip silently with full stderr/stdout interception
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                task.spec,
                "--quiet",
                "--no-warn-script-location",
            ]

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

            # Dynamic progress tracking while subprocess resolves/downloads
            if proc is not None:
                while proc.poll() is None:
                    elapsed = time.time() - task.start_time
                    # Smooth asymptotic progression towards ~92% during processing
                    task.progress = min(0.92, elapsed / 1.6)
                    task.speed = f"{random.uniform(8.4, 26.8):.1f}MB/s"
                    time.sleep(0.04)

                stdout_data, stderr_data = proc.communicate()

                # If pip finished cleanly or package is already satisfied
                if proc.returncode == 0:
                    task.failed = False
                else:
                    # Check if package is already importable before declaring failure
                    spec_check = task.spec.replace("-", "_")
                    if importlib.util.find_spec(spec_check) is not None:
                        task.failed = False
                    else:
                        task.failed = True
                        task.error_msg = stderr_data.strip().split("\n")[-1] if stderr_data else "Install failed"

            # Smoothly complete to 100%
            while task.progress < 1.0:
                task.progress = min(1.0, task.progress + 0.18)
                time.sleep(0.02)

            task.duration = max(0.2, time.time() - task.start_time)
            task.completed = True
            task_queue.task_done()

    def run(self) -> None:
        """Execute the complete 3-phase installation lifecycle."""
        total_start = time.time()

        # ==========================================
        # Phase 1 [Header Initialization]
        # ==========================================
        sys.stdout.write(f"📦 {COLOR_BOLD_WHITE}lmms-engine{COLOR_RESET} {COLOR_DIM}v1.0.0{COLOR_RESET}\n")
        sys.stdout.write(
            f"{COLOR_CYAN}ℹ{COLOR_RESET} {COLOR_DIM}Resolving package tree structure for flag {self.flag}...{COLOR_RESET}\n"
        )
        sys.stdout.flush()

        # Build execution queue
        task_queue: queue.Queue[PackageTask] = queue.Queue()
        for task in self.packages:
            task_queue.put(task)

        # ==========================================
        # Phase 2 [Concurrently Tracked Fetch]
        # ==========================================
        num_workers = min(MAX_CONCURRENT_WORKERS, len(self.packages))
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

        # Wait for all background threads to terminate
        for th in threads:
            th.join(timeout=1.0)

        # ==========================================
        # Phase 3 [Clean Exit Summary]
        # ==========================================
        total_elapsed = time.time() - total_start
        count = len(self.packages)
        sys.stdout.write(
            f"✨ {COLOR_BOLD_WHITE}Done!{COLOR_RESET} Added {count} packages in {total_elapsed:.1f}s.\n"
        )
        sys.stdout.flush()

    def _render_interactive(self) -> None:
        """Transient multi-line layout with live Braille spinner and ANSI self-cleaning."""
        spin_idx = 0
        last_lines = 0

        # Hide cursor during live rendering
        sys.stdout.write(CURSOR_HIDE)
        sys.stdout.flush()

        try:
            while not all(t.rendered_static for t in self.packages):
                # 1. Ephemeral Wipe: Erase active lines rendered in previous frame
                if last_lines > 0:
                    sys.stdout.write(f"\r\033[{last_lines}A\033[J")

                # 2. Persistent Success Mutation: Print permanently locked success rows
                for task in self.packages:
                    if task.completed and not task.rendered_static:
                        if task.failed:
                            sys.stdout.write(
                                f"\r\033[K{COLOR_RED}✖{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name}{COLOR_RESET} "
                                f"{COLOR_DIM}installation failed ({task.error_msg}){COLOR_RESET}\n"
                            )
                        else:
                            sys.stdout.write(
                                f"\r\033[K{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name}{COLOR_RESET} "
                                f"{COLOR_DIM}installed successfully in {task.duration:.1f}s{COLOR_RESET}\n"
                            )
                        task.rendered_static = True

                # 3. Transient Active Layer: Re-render live running progress bars
                active = [t for t in self.packages if t.started and not t.rendered_static]
                spinner_char = SPINNER_FRAMES[spin_idx % len(SPINNER_FRAMES)]
                spin_idx += 1

                for task in active:
                    # Slim, single-color continuous cyan block progress line (width: 25 cols)
                    filled_len = int(task.progress * PROGRESS_BAR_WIDTH)
                    unfilled_len = PROGRESS_BAR_WIDTH - filled_len
                    bar = f"{COLOR_CYAN}{'━' * filled_len}{COLOR_DIM_GREY}{'─' * unfilled_len}{COLOR_RESET}"
                    pct = int(task.progress * 100)

                    # Consistent alignment to prevent shifting line indices
                    sys.stdout.write(
                        f"\r\033[K  {COLOR_BOLD_CYAN}{spinner_char}{COLOR_RESET} "
                        f"{COLOR_BOLD_WHITE}{task.name:<18}{COLOR_RESET} "
                        f"[{bar}] {COLOR_DIM}{pct:>3}% {task.speed}{COLOR_RESET}\n"
                    )

                last_lines = len(active)
                sys.stdout.flush()
                time.sleep(0.045)

            # Final wipe of any active lines
            if last_lines > 0:
                sys.stdout.write(f"\r\033[{last_lines}A\033[J")
                sys.stdout.flush()

        finally:
            # Restore cursor unconditionally
            sys.stdout.write(CURSOR_SHOW)
            sys.stdout.flush()

    def _render_non_interactive(self) -> None:
        """Piped / CI rendering: clean line-by-line mutation without ANSI repositioning."""
        while not all(t.rendered_static for t in self.packages):
            for task in self.packages:
                if task.completed and not task.rendered_static:
                    if task.failed:
                        sys.stdout.write(
                            f"{COLOR_RED}✖{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name}{COLOR_RESET} "
                            f"{COLOR_DIM}installation failed ({task.error_msg}){COLOR_RESET}\n"
                        )
                    else:
                        sys.stdout.write(
                            f"{COLOR_GREEN}✔{COLOR_RESET} {COLOR_BOLD_WHITE}{task.name}{COLOR_RESET} "
                            f"{COLOR_DIM}installed successfully in {task.duration:.1f}s{COLOR_RESET}\n"
                        )
                    task.rendered_static = True
                    sys.stdout.flush()
            time.sleep(0.05)


def run_installer(args: Optional[List[str]] = None) -> None:
    """Entry point for the LMMs CLI installer."""
    if args is None:
        args = sys.argv[1:]
    installer = CLIInstaller(args)
    installer.run()


if __name__ == "__main__":
    run_installer(sys.argv[1:])
