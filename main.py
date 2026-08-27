#!/usr/bin/env python3
"""
main.py — LMMs Entry Point (Full Rewrite)
Commands: LMMs, LMMs --status, LMMs --doctor, LMMs --autoset
Sudo: sudo LMMs  →  full system power, passwordless sudo
Shortcut: Configurable hotkey to launch LMMs
"""

import sys
import os
import subprocess
import json

# ─────────────────────────────────────────────────────────────
# SUDO SETUP
# ─────────────────────────────────────────────────────────────

def setup_passwordless_sudo():
    """Add LMMs to sudoers for passwordless sudo. Requires root."""
    sudoers_line = f"{os.environ.get('USER', 'kali')} ALL=(ALL) NOPASSWD: /usr/local/bin/LMMs, {sys.executable}\n"
    sudoers_path = "/etc/sudoers.d/lmms"
    try:
        with open(sudoers_path, "w") as f:
            f.write(sudoers_line)
        os.chmod(sudoers_path, 0o440)
        return True
    except Exception as e:
        return False


def is_root():
    return os.geteuid() == 0


def request_privilege_escalation():
    """Ask user to confirm before running with elevated privileges."""
    from rich.console import Console
    from rich.panel import Panel
    c = Console()
    c.print(Panel(
        "[bold yellow]⚡ FULL POWER MODE[/bold yellow]\n"
        "[white]LMMs is running as root/sudo.[/white]\n"
        "[dim]All system operations will execute without restriction.[/dim]\n"
        "[bold red]This gives LMMs full system access.[/bold red]",
        border_style="red",
        title="[bold red]Privilege Escalation[/bold red]"
    ))
    confirm = input("Allow LMMs full system access? (yes/cancel): ").strip().lower()
    if confirm != "yes":
        c.print("[dim]Cancelled. Run without sudo for restricted mode.[/dim]")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────
# AUTO-INSTALL
# ─────────────────────────────────────────────────────────────

def check_and_install():
    req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_path):
        return
    with open(req_path) as f:
        packages = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    import_map = {
        "ddgs": "duckduckgo_search", "playwright": "playwright",
        "prompt_toolkit": "prompt_toolkit", "pathspec": "pathspec",
        "plotext": "plotext", "textual": "textual",
        "huggingface_hub": "huggingface_hub", "watchdog": "watchdog",
        "transformers": "transformers", "airllm": "airllm",
        "anthropic": "anthropic", "openai": "openai", "rich": "rich",
        "click": "click", "requests": "requests",
    }
    for pkg in packages:
        import_name = import_map.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            pass  # Will be handled by /autoset or --autoset


def run_autoset(verbose=True):
    """Scan all imports and install missing packages."""
    import ast
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    c = Console()
    c.print("[cyan]🔍 Scanning project for missing packages...[/cyan]")

    imports = set()
    project_dir = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(project_dir):
        if any(skip in root for skip in ["venv", "__pycache__", "env", ".git"]):
            continue
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for n in node.names:
                                imports.add(n.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split(".")[0])
                except Exception:
                    pass

    import sysconfig
    stdlib = set(sys.builtin_module_names)
    stdlib_path = sysconfig.get_paths()["stdlib"]
    if os.path.exists(stdlib_path):
        for name in os.listdir(stdlib_path):
            stdlib.add(name.split(".")[0])

    skip = {"lmms", "main", "patch_agent", "patch_main", "rewrite_agent", "rewrite_models"}
    INTERNAL_MODULES = {
        'lmms', 'canvas', 'models', 'memory', 
        'ui', 'agent', 'tools', 'search', 'vision',
        'browser', 'terminal', 'files', 'watcher',
        'vscode', 'main', 'setup'
    }
    missing = []
    for imp in imports:
        if imp in stdlib or imp in skip or imp in INTERNAL_MODULES:
            continue
        try:
            __import__(imp)
        except ImportError:
            missing.append(imp)

    if not missing:
        c.print("[green]✅ All packages are installed![/green]")
        return

    c.print(f"\n[yellow]Missing packages:[/yellow]")
    for m in missing:
        c.print(f"  [red]•[/red] {m}")

    ans = input("\nInstall all missing packages? (y/n): ").strip().lower()
    if ans != "y":
        c.print("[dim]Skipped.[/dim]")
        return

    pip_cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages"]

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), transient=True) as progress:
        task = progress.add_task("[cyan]Installing...", total=len(missing))
        for pkg in missing:
            progress.update(task, description=f"[cyan]Installing {pkg}...")
            result = subprocess.run(pip_cmd + [pkg], capture_output=True, text=True)
            if result.returncode != 0:
                c.print(f"[red]Failed to install {pkg}: {result.stderr[:100]}[/red]")
            progress.advance(task)

    # Special: install playwright browsers
    if "playwright" in missing:
        c.print("[cyan]Installing Playwright browsers...[/cyan]")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=not verbose)

    c.print("\n[green]✅ Done! Restarting LMMs...[/green]")
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ─────────────────────────────────────────────────────────────
# STATUS COMMAND
# ─────────────────────────────────────────────────────────────

def show_status():
    """LMMs --status: Full system overview."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        from lmms.backend.models import ModelManager
        import platform, shutil
    except ImportError as e:
        print(f"Import error: {e}. Run: LMMs --autoset")
        sys.exit(1)

    c = Console()
    mm = ModelManager()

    # Header
    c.print(Panel(
        "[bold cyan]LMMs STATUS DASHBOARD[/bold cyan]\n"
        f"[dim]User: {os.environ.get('USER', 'unknown')} | "
        f"Host: {platform.node()} | "
        f"OS: {platform.system()} {platform.release()} | "
        f"Python: {platform.python_version()}[/dim]\n"
        f"[{'bold green' if is_root() else 'yellow'}]"
        f"{'⚡ RUNNING AS ROOT (FULL POWER)' if is_root() else '○ Normal Mode (sudo LMMs for full power)'}[/]",
        border_style="cyan",
        title="[bold]LMMs by MarkanM Team[/bold]",
    ))

    # Model table
    c.print("\n[bold magenta]━━ MODELS ━━[/bold magenta]")
    c.print(mm.get_model_status_table())

    # System info table
    c.print("\n[bold magenta]━━ SYSTEM ━━[/bold magenta]")
    sys_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    sys_table.add_column("Resource", style="bold", min_width=18)
    sys_table.add_column("Info")

    # Disk
    try:
        disk = shutil.disk_usage(os.path.expanduser("~"))
        used_gb = disk.used / 1e9
        total_gb = disk.total / 1e9
        pct = disk.used / disk.total * 100
        color = "green" if pct < 70 else "yellow" if pct < 90 else "red"
        sys_table.add_row("Disk (~)", f"[{color}]{used_gb:.1f}GB / {total_gb:.1f}GB ({pct:.0f}%)[/{color}]")
    except Exception:
        pass

    # RAM
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {l.split(":")[0]: int(l.split()[1]) for l in lines if ":" in l and len(l.split()) >= 2}
        total_ram = mem.get("MemTotal", 0) / 1024 / 1024
        avail_ram = mem.get("MemAvailable", 0) / 1024 / 1024
        used_ram = total_ram - avail_ram
        pct_ram = used_ram / total_ram * 100 if total_ram > 0 else 0
        color = "green" if pct_ram < 70 else "yellow" if pct_ram < 90 else "red"
        sys_table.add_row("RAM", f"[{color}]{used_ram:.1f}GB / {total_ram:.1f}GB ({pct_ram:.0f}%)[/{color}]")
    except Exception:
        sys_table.add_row("RAM", "[dim]unavailable[/dim]")

    # GPU
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                parts = line.split(", ")
                if len(parts) == 3:
                    sys_table.add_row("GPU", f"[cyan]{parts[0]}[/cyan] | VRAM: {parts[1]}/{parts[2]}")
    except Exception:
        sys_table.add_row("GPU", "[dim]No NVIDIA GPU detected[/dim]")

    # Engine status
    if mm.is_engine_running():
        sys_table.add_row("LMMS Engine", "[green]✅ running[/green] at http://localhost:11435")
    else:
        sys_table.add_row("LMMS Engine", "[red]❌ offline[/red] — run: lmms engine")

    # Sudo
    sys_table.add_row("Permissions", "[bold red]ROOT[/bold red]" if is_root() else "[yellow]user (limited)[/yellow]")

    # VS Code
    try:
        r = subprocess.run(["code", "--version"], capture_output=True, text=True, timeout=3)
        ver = r.stdout.strip().split("\n")[0] if r.returncode == 0 else "not found"
        status = "[green]✅" if r.returncode == 0 else "[red]❌"
        sys_table.add_row("VS Code", f"{status} {ver}[/]")
    except Exception:
        sys_table.add_row("VS Code", "[red]❌ not installed[/red]")

    # Cloud connectors
    connectors = mm.list_connectors()
    sys_table.add_row("Cloud APIs", f"[green]{len(connectors)} connected[/green]: {', '.join(connectors)}" if connectors else "[dim]none[/dim]")

    c.print(sys_table)

    # Permissions breakdown
    c.print("\n[bold magenta]━━ PERMISSIONS ━━[/bold magenta]")
    perm_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    perm_table.add_column("Feature", min_width=22)
    perm_table.add_column("Status", min_width=10)
    perm_table.add_column("Note")

    perms = [
        ("File Read/Write", "✅ always", "Any accessible path"),
        ("Terminal Commands", "✅ always", "Blocked: rm -rf /, mkfs, etc."),
        ("Web Search", "✅ always", "DuckDuckGo"),
        ("Browser Automation", "✅ always", "Playwright/Chromium"),
        ("VS Code Integration", "✅ always", "code CLI required"),
        ("System Commands (sudo)", "✅ ROOT" if is_root() else "⚠ limited", "sudo LMMs for full access"),
        ("Model Download (HF)", "✅ always", "Background thread"),
        ("Passwordless Sudo", "✅ active" if is_root() else "○ not set", "Run: sudo LMMs --setup-sudo"),
    ]
    for feature, status, note in perms:
        color = "green" if "✅" in status else "yellow" if "⚠" in status else "dim"
        perm_table.add_row(feature, f"[{color}]{status}[/{color}]", f"[dim]{note}[/dim]")
    c.print(perm_table)

    c.print("\n[dim]Run [bold]LMMs --doctor[/bold] for detailed health check | [bold]LMMs --autoset[/bold] to install missing packages[/dim]\n")


# ─────────────────────────────────────────────────────────────
# DOCTOR COMMAND
# ─────────────────────────────────────────────────────────────

def show_doctor():
    """LMMs --doctor: Detailed health check of all features."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from lmms.backend.models import ModelManager
    except ImportError as e:
        print(f"Import error: {e}. Run: LMMs --autoset")
        sys.exit(1)

    c = Console()
    mm = ModelManager()

    c.print(Panel(
        "[bold cyan]🩺 LMMs DOCTOR[/bold cyan]\n"
        "[dim]Checking all features and dependencies...[/dim]",
        border_style="cyan"
    ))

    results = mm.doctor_check()

    table = Table(show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("Feature", style="bold", min_width=22)
    table.add_column("Status", min_width=18)
    table.add_column("Action / Info")

    all_ok = True
    for feature, status, detail in results:
        if "❌" in status:
            all_ok = False
            color = "red"
        elif "⚠" in status:
            color = "yellow"
        else:
            color = "green"
        table.add_row(feature, f"[{color}]{status}[/{color}]", f"[dim]{detail}[/dim]" if detail else "")

    c.print(table)

    if all_ok:
        c.print("\n[bold green]✅ All systems healthy! LMMs is fully operational.[/bold green]\n")
    else:
        c.print("\n[yellow]⚠ Some features need attention. Run [bold]LMMs --autoset[/bold] to fix.[/yellow]\n")


# ─────────────────────────────────────────────────────────────
# KEYBOARD SHORTCUT SETUP
# ─────────────────────────────────────────────────────────────

def setup_keyboard_shortcut():
    """
    Setup a keyboard shortcut to launch LMMs.
    On Kali/Debian/XFCE/GNOME — maps a free key (e.g. the Copilot key / F13) to launch LMMs terminal.
    """
    from rich.console import Console
    from rich.panel import Panel
    c = Console()

    c.print(Panel(
        "[bold cyan]⌨ Keyboard Shortcut Setup[/bold cyan]\n"
        "[white]This will map a key to launch LMMs in a terminal window.[/white]\n"
        "[dim]Works on: XFCE, GNOME, KDE, i3wm[/dim]",
        border_style="cyan"
    ))

    lmms_bin = subprocess.run(["which", "LMMs"], capture_output=True, text=True).stdout.strip()
    if not lmms_bin:
        lmms_bin = os.path.abspath(__file__)

    launch_cmd = f"bash -c 'cd ~ && {lmms_bin}'"

    # Detect DE
    de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()

    c.print(f"\n[dim]Detected DE: {de or session or 'unknown'}[/dim]")
    c.print(f"[dim]LMMs binary: {lmms_bin}[/dim]")

    c.print("\n[bold]Which key do you want to use?[/bold]")
    c.print("  [1] F13 (Copilot key on Victus / special keyboards)")
    c.print("  [2] Super+L (Windows+L)")
    c.print("  [3] Ctrl+Alt+A")
    c.print("  [4] Custom")

    choice = input("\nChoice (1-4): ").strip()
    key_map = {
        "1": ("F13", "XF86CopilotKey"),
        "2": ("Super+L", "<Super>l"),
        "3": ("Ctrl+Alt+A", "<Control><Alt>a"),
    }

    if choice in key_map:
        key_name, key_code = key_map[choice]
    elif choice == "4":
        key_name = input("Key name (e.g. F10): ").strip()
        key_code = key_name
    else:
        c.print("[dim]Cancelled.[/dim]")
        return

    terminal_cmds = ["xterm", "kitty", "alacritty", "gnome-terminal", "xfce4-terminal"]
    terminal = None
    for t in terminal_cmds:
        if subprocess.run(["which", t], capture_output=True).returncode == 0:
            terminal = t
            break

    if not terminal:
        c.print("[red]No terminal emulator found. Install xterm: sudo apt install xterm[/red]")
        return

    # Build terminal launch command
    if terminal == "gnome-terminal":
        full_launch = f"gnome-terminal -- bash -c '{lmms_bin}; bash'"
    elif terminal == "xfce4-terminal":
        full_launch = f"xfce4-terminal -e '{lmms_bin}'"
    else:
        full_launch = f"{terminal} -e bash -c '{lmms_bin}; bash'"

    c.print(f"\n[dim]Will bind {key_name} → {full_launch}[/dim]")
    confirm = input("Set shortcut? (y/n): ").strip().lower()
    if confirm != "y":
        c.print("[dim]Cancelled.[/dim]")
        return

    success = False

    # XFCE
    if "xfce" in (de + session):
        try:
            # Check existing shortcuts
            result = subprocess.run(
                ["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-l"],
                capture_output=True, text=True
            )
            subprocess.run([
                "xfconf-query", "-c", "xfce4-keyboard-shortcuts",
                "-p", f"/commands/custom/{key_code}",
                "-n", "-t", "string", "-s", full_launch
            ])
            success = True
            c.print(f"[green]✅ XFCE shortcut set: {key_name} → LMMs[/green]")
        except Exception as e:
            c.print(f"[red]XFCE shortcut failed: {e}[/red]")

    # GNOME
    elif "gnome" in (de + session) or "ubuntu" in session:
        try:
            schema = "org.gnome.settings-daemon.plugins.media-keys"
            path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/lmms/"
            subprocess.run(["gsettings", "set", f"{schema}.custom-keybinding:{path}", "name", "LMMs AI"])
            subprocess.run(["gsettings", "set", f"{schema}.custom-keybinding:{path}", "command", full_launch])
            subprocess.run(["gsettings", "set", f"{schema}.custom-keybinding:{path}", "binding", key_code])
            success = True
            c.print(f"[green]✅ GNOME shortcut set: {key_name} → LMMs[/green]")
        except Exception as e:
            c.print(f"[red]GNOME shortcut failed: {e}[/red]")

    # KDE
    elif "kde" in (de + session) or "plasma" in session:
        shortcut_script = f"""[Desktop Entry]
Name=LMMs AI
Exec={full_launch}
Type=Application

[Desktop Action LaunchLMMs]
Name=Launch LMMs
Exec={full_launch}
"""
        shortcut_path = os.path.expanduser(f"~/.local/share/kglobalaccel/lmms.desktop")
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        with open(shortcut_path, "w") as f:
            f.write(shortcut_script)
        success = True
        c.print(f"[yellow]⚠ KDE: Created desktop file. Manually set shortcut in System Settings → Shortcuts[/yellow]")

    # xbindkeys fallback (works everywhere with X11)
    if not success:
        try:
            xbindkeys_conf = os.path.expanduser("~/.xbindkeysrc")
            entry = f'\n"{full_launch}"\n  {key_name}\n'
            existing = ""
            if os.path.exists(xbindkeys_conf):
                with open(xbindkeys_conf) as f:
                    existing = f.read()
            if "LMMs" not in existing:
                with open(xbindkeys_conf, "a") as f:
                    f.write(entry)
            # Restart xbindkeys
            subprocess.run(["pkill", "xbindkeys"], capture_output=True)
            subprocess.Popen(["xbindkeys"])
            c.print(f"[green]✅ xbindkeys shortcut set: {key_name} → LMMs[/green]")
            c.print("[dim]Install xbindkeys if not working: sudo apt install xbindkeys[/dim]")
        except Exception as e:
            c.print(f"[red]xbindkeys fallback failed: {e}[/red]")
            c.print(f"\n[yellow]Manual setup:[/yellow]\nAdd this to your DE keyboard shortcuts:\nCommand: {full_launch}\nKey: {key_name}")

    c.print(f"\n[dim]Tip: To launch LMMs as root with shortcut, use:[/dim]")
    c.print(f"[dim]pkexec env DISPLAY=$DISPLAY {lmms_bin}[/dim]")


# ─────────────────────────────────────────────────────────────
# VS CODE SETUP
# ─────────────────────────────────────────────────────────────

def configure_vscode():
    """Configure Continue.dev extension to use LMMs/Ollama."""
    config_path = os.path.expanduser("~/.continue/config.json")
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path) as f:
            config = json.load(f)
        models = config.get("models", [])
        has_lmms = any(m.get("title", "").startswith("LMMs") for m in models)
        if not has_lmms:
            models.insert(0, {
                "title": "LMMs Auto (Engine)",
                "provider": "openai",
                "model": "qwen3:8b",
                "apiBase": "http://localhost:11435/v1",
            })
            config["models"] = models
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# INTENT DETECTION
# ─────────────────────────────────────────────────────────────

def detect_intent_main(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["graph", "chart", "plot", "visualize"]):
        return "graph"
    if any(w in t for w in ["browse", "visit", "http", ".com", ".org"]):
        return "browse"
    if any(w in t for w in ["open", "launch", "start"]) and any(w in t for w in ["chrome", "firefox", "vscode", "code", "terminal"]):
        return "open_app"
    if any(w in t for w in ["create", "make", "build", "write"]) and any(w in t for w in ["html", "css", "js", "python", "file", "app", "website"]):
        return "create_file"
    return "chat"


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    import sys
    import os
    base_dir = os.path.expanduser("~/.lmms")
    for subdir in ["models", "cache", "logs", "manifests", "workspaces"]:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
    args = sys.argv[1:]

    if "--air" in args or "-air" in args:
        from lmms.engine.air.runtime import AirRuntime
        from lmms.backend.logic.manager import backend_manager
        backend_manager.register_runtime(AirRuntime())

    if args and args[0] == "engine":
        from lmms.api.server import run_server
        print("Starting LMMs Engine on port 11435...")
        run_server(11435)
        return

    if "--server" in args:
        from lmms.server import run_server
        print("Starting LMMs API Server on port 8080...")
        run_server(8080)
        return

    if "--autoset" in args:
        run_autoset(verbose=True)
        return

    if "--status" in args:
        show_status()
        return

    if "--doctor" in args:
        show_doctor()
        return

    if "--setup-sudo" in args:
        if not is_root():
            print("Run: sudo LMMs --setup-sudo")
            sys.exit(1)
        if setup_passwordless_sudo():
            print("✅ Passwordless sudo configured for LMMs.")
        else:
            print("❌ Failed. Make sure you're root.")
        return

    if "--shortcut" in args:
        setup_keyboard_shortcut()
        return

    # If running as sudo, show escalation warning ONCE
    if is_root():
        request_privilege_escalation()

    # Now import heavy modules
    check_and_install()

    try:
        import click
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.completion import Completer, Completion
        from lmms.backend.core.agent import HexAgent
        from lmms.gui.core.ui import show_welcome, show_error, show_info, show_help
        from lmms.backend.models import ModelManager
        from rich.console import Console
    except ImportError as e:
        print(f"⚠ Missing dependencies: {e}")
        print("Run: LMMs --autoset")
        sys.exit(1)

    c = Console()

    # Watcher
    try:
        from lmms.backend.monitoring.watcher import start_watcher
        start_watcher()
    except Exception:
        pass

    configure_vscode()

    # Determine if we should run Web GUI
    run_gui = "/gui" in args

    if run_gui:
        try:
            import sys
            
            # Initialization Guard to prevent duplicate execution
            if getattr(sys, '_lmms_gui_initialized', False):
                return
            sys._lmms_gui_initialized = True
            
            import qasync
            import asyncio
            from PyQt6.QtWidgets import QApplication
            import lmms.gui.core.ui
            
            # --- STARTUP DIAGNOSTICS ---
            import platform
            try:
                from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
                pyqt_ver = PYQT_VERSION_STR
                qt_ver = QT_VERSION_STR
            except ImportError:
                pyqt_ver = "Unknown"
                qt_ver = "Unknown"
                
            from lmms.gui.core.main_window import QFileSystemModel
            fs_status = "Available" if QFileSystemModel is not None else "Missing"
            
            from lmms.backend.core.commands import CommandRegistry
            from lmms.backend.services.workspace_service import WorkspaceService
            
            registered_commands = len(CommandRegistry._commands)
            
            print("\n[LMMs GUI Diagnostics]")
            print(f"Python version: {platform.python_version()}")
            print(f"PyQt6 version: {pyqt_ver}")
            print(f"Qt version: {qt_ver}")
            print(f"QFileSystemModel: {fs_status}")
            print(f"Menus registered: {registered_commands}")
            print(f"Actions connected: {registered_commands}")
            print(f"Services available: WorkspaceService (Active)\n")
            # ---------------------------
            
            from lmms.gui.core.main_window import MainWindow
            
            # Suppress the XKB logging errors
            os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
            
            # Tell the UI module to stop printing to terminal
            lmms.gui.core.ui.GUI_MODE = True
            
            # Start the PyQt6 GUI
            app = QApplication(sys.argv)
            app.setApplicationName("LMMs")
            app.setApplicationDisplayName("LMMs - Local Machine Model Studio")
            
            # Set application-wide icon to fix Linux dock/taskbar logos
            from PyQt6.QtGui import QIcon
            icon_path = os.path.join(os.path.dirname(__file__), "lmms", "gui", "assets", "lmms_logo.png")
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                app.setDesktopFileName("lmms.desktop")
            
            # Load dark theme
            theme_path = os.path.join(os.path.dirname(__file__), "lmms", "gui", "themes", "dark.qss")
            try:
                with open(theme_path, "r") as f:
                    app.setStyleSheet(f.read())
            except Exception as e:
                print(f"Warning: Could not load dark theme: {e}")

            loop = qasync.QEventLoop(app)
            asyncio.set_event_loop(loop)
            
            window = MainWindow()
            
            # Print Layout Diagnostics
            from PyQt6.QtWidgets import QDockWidget
            docks = window.findChildren(QDockWidget)
            print("\n[Layout System Diagnostics]")
            print(f"Total Registered Docks: {len(docks)}")
            for dock in docks:
                state = "Floating" if dock.isFloating() else "Docked"
                vis = "Visible" if dock.isVisible() else "Hidden"
                print(f"  - {dock.objectName()}: {vis} | {state}")
            print("---------------------------\n")

            window.show()
            
            # Use qasync to run the loop so we can do async UI operations
            with loop:
                sys.exit(loop.run_forever())
        except Exception as e:
            print(f"GUI launch failed: {e}")
            sys.exit(1)

    show_welcome()

    # Parse click-style args manually (for --model, --mode, --image)
    model_arg = None
    mode_arg = "deep"
    image_arg = None
    prompt_parts = []

    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model_arg = args[i + 1]; i += 2
        elif args[i] == "--mode" and i + 1 < len(args):
            mode_arg = args[i + 1]; i += 2
        elif args[i] == "--image" and i + 1 < len(args):
            image_arg = args[i + 1]; i += 2
        elif args[i] == "run" and i + 1 < len(args):
            model_arg = args[i + 1]; i += 2
        elif not args[i].startswith("--") and not args[i].startswith("-"):
            prompt_parts.append(args[i]); i += 1
        else:
            i += 1

    manager = ModelManager()
    if not manager.is_engine_running():
        show_error("LMMS Engine is not running! Start it: lmms engine")
        show_error("Or use cloud mode: /connector to add an API key")
        # Don't exit — cloud mode might still work

    # Engine CLI Commands Bypass
    if args and args[0] in ["run", "list", "ps", "pull", "info", "benchmark", "rm", "stop", "search", "doctor"]:
        import requests, json, sys
        cmd = args[0]
        try:
            if cmd == "list":
                res = requests.get("http://localhost:11435/v1/models/list", timeout=5).json()
                from rich.table import Table
                from rich.console import Console
                c = Console()
                table = Table(title="LMMS Local Models")
                table.add_column("Model Name")
                table.add_column("Size (GB)")
                for m in res.get("models", []):
                    table.add_row(m["name"], str(m["size_gb"]))
                c.print(table)
                sys.exit(0)
            elif cmd == "ps":
                res = requests.get("http://localhost:11435/v1/models/ps", timeout=5).json()
                from rich.console import Console
                c = Console()
                c.print("[bold cyan]Engine Stats:[/bold cyan]")
                for k, v in res.items():
                    c.print(f"  {k}: {v}")
                sys.exit(0)
            elif cmd == "pull" and len(args) > 1:
                res = requests.post("http://localhost:11435/v1/models/pull", json={"model_name": args[1]}, timeout=5).json()
                print(f"Pulling {args[1]}... Check engine logs for progress.")
                sys.exit(0)
            elif cmd == "stop" and len(args) > 1:
                res = requests.post("http://localhost:11435/v1/models/unload", json={"model_name": args[1]}, timeout=5).json()
                print(f"Stopped and unloaded {args[1]}.")
                sys.exit(0)
            elif cmd == "rm" and len(args) > 1:
                res = requests.delete(f"http://localhost:11435/v1/models/delete/{args[1]}", timeout=5).json()
                print(f"Deleted {args[1]}.")
                sys.exit(0)
            elif cmd == "search" and len(args) > 1:
                res = requests.get(f"http://localhost:11435/v1/models/search?q={args[1]}", timeout=15).json()
                from rich.table import Table
                from rich.console import Console
                c = Console()
                table = Table(title=f"Search Results for '{args[1]}'")
                table.add_column("Model")
                table.add_column("Author")
                table.add_column("Downloads")
                table.add_column("Last Updated")
                table.add_column("GGUF")
                for m in res.get("results", []):
                    table.add_row(m["modelId"], m["author"], str(m["downloads"]), m["last_updated"][:10], "✅" if m["gguf_available"] else "❌")
                c.print(table)
                sys.exit(0)
            elif cmd == "doctor":
                is_fix = "--fix" in args
                res = requests.post("http://localhost:11435/v1/doctor", json={"fix": is_fix}, timeout=15).json()
                from rich.table import Table
                from rich.console import Console
                c = Console()
                report = res.get("report", {})
                table = Table(title="Engine Doctor Report")
                table.add_column("Check")
                table.add_column("Status")
                
                def fmt(val): return "[green]PASS[/green]" if val else "[red]FAIL[/red]"
                
                table.add_row("Engine Reachable", fmt(report.get("engine_reachable")))
                table.add_row("Models Dir Exists", fmt(report.get("models_dir_exists")))
                table.add_row("Models Dir Writable", fmt(report.get("models_dir_writable")))
                table.add_row("CUDA Support", fmt(report.get("cuda_support")))
                table.add_row("Llama-CPP Python", fmt(report.get("llama_cpp_python")))
                table.add_row("Python Version", report.get("python_version", "Unknown"))
                table.add_row("RAM Available", f"{report.get('ram_available_gb', 0)} GB")
                table.add_row("Disk Available", f"{report.get('disk_available_gb', 0)} GB")
                c.print(table)
                
                if res.get("fixes"):
                    c.print("\n[bold yellow]Applied Fixes & Suggestions:[/bold yellow]")
                    for f in res["fixes"]:
                        c.print(f" - {f}")
                sys.exit(0)
            elif cmd == "info" and len(args) > 1:
                res = requests.get(f"http://localhost:11435/v1/models/info/{args[1]}", timeout=5).json()
                from rich.console import Console
                c = Console()
                c.print(f"[bold cyan]Model Info: {args[1]}[/bold cyan]")
                for k, v in res.items():
                    c.print(f"  {k}: {v}")
                sys.exit(0)
            elif cmd == "benchmark":
                print("Running benchmarks...")
                res = requests.get("http://localhost:11435/v1/benchmark", timeout=30).json()
                from rich.console import Console
                c = Console()
                c.print("[bold green]Benchmark Results:[/bold green]")
                for k, v in res.get("benchmarks", {}).items():
                    c.print(f"  {k}: {v}")
                sys.exit(0)
            elif cmd == "run" and model_arg:
                if prompt_parts:
                    messages = [{"role": "user", "content": " ".join(prompt_parts)}]
                    print(f"User: {messages[0]['content']}")
                    print("Assistant: ", end="", flush=True)
                    res = requests.post("http://localhost:11435/v1/chat/completions", json={"model_name": model_arg, "messages": messages, "stream": True}, stream=True, timeout=120)
                    for line in res.iter_lines():
                        if line:
                            decoded = line.decode('utf-8')
                            if decoded.startswith("data: "):
                                data_str = decoded[6:]
                                if data_str == "[DONE]": break
                                try:
                                    data = json.loads(data_str)
                                    token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    print(token, end="", flush=True)
                                except Exception: pass
                    print()
                    sys.exit(0)
                # If no prompt_parts, we let it fall through to the interactive REPL below.
        except requests.exceptions.RequestException as e:
            print(f"\n[Engine Error] Could not connect to Engine at localhost:11435. ({e})")
            sys.exit(1)

    agent = HexAgent(model=model_arg, mode=mode_arg)

    initial_prompt = " ".join(prompt_parts)
    if initial_prompt or image_arg:
        agent.chat(initial_prompt or "Describe this image.", image_path=image_arg)

    # Autocomplete
    ALL_COMMANDS = [
        "fast", "deep", "dual", "qwen", "gemma", "model", "help", "history",
        "clear", "attach", "file", "folder", "connector", "download", "airllm",
        "undo", "redo", "copy", "paste", "models", "autoset", "vscode",
        "canvas", "code", "smart", "screenshot", "status", "doctor",
        "cloud", "routing",
    ]

    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            word = text[1:]
            for cmd in ALL_COMMANDS:
                if cmd.startswith(word):
                    yield Completion("/" + cmd, start_position=-len(text))

    bindings = KeyBindings()

    @bindings.add("c-v")
    def _paste(event):
        try:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                                    capture_output=True, text=True)
            if "image/png" in result.stdout:
                img_path = "/tmp/lmms_paste.png"
                subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                               stdout=open(img_path, "wb"))
                event.app.current_buffer.insert_text(f"[IMAGE:{img_path}]")
            else:
                data = event.app.clipboard.get_data()
                event.app.current_buffer.paste_clipboard_data(data)
        except Exception:
            pass

    session = PromptSession(
        history=InMemoryHistory(),
        key_bindings=bindings,
        completer=SlashCompleter(),
        complete_while_typing=True,
    )

    # ─────────────────────────────────────────────────────────────
    # REPL LOOP
    # ─────────────────────────────────────────────────────────────

    power_indicator = "[bold red]⚡ROOT[/bold red]" if is_root() else ""

    try:
        while True:
            try:
                prompt_str = f"\n[LMMs|{agent.models.text_model}{'|ROOT' if is_root() else ''}]> "
                user_input = session.prompt(prompt_str).strip()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
                c.print("[dim]Bye![/dim]")
                break

            # ── COMMANDS ──────────────────────────────────────────

            if user_input.lower() == "/help":
                show_help()
                continue

            elif user_input.lower() == "/status":
                show_status()
                continue

            elif user_input.lower() == "/doctor":
                show_doctor()
                continue

            elif user_input.lower() == "/autoset":
                run_autoset()
                continue

            elif user_input.lower() in ["/fast", "/search", "/dual"]:
                agent.current_mode = user_input[1:].lower()
                show_info(f"Mode: {agent.current_mode.upper()}")
                continue

            elif user_input.lower() == "/qwen":
                agent.models.set_model("qwen3:8b")
                agent.backend = "lmms_engine"
                show_info("Switched to qwen3:8b")
                continue

            elif user_input.lower() == "/gemma":
                agent.models.set_model("gemma4")
                agent.backend = "lmms_engine"
                show_info("Switched to gemma4")
                continue

            elif user_input.lower().startswith("/model "):
                m = user_input[7:].strip()
                agent.models.set_model(m)
                agent.backend = "lmms_engine"
                show_info(f"Switched to {m}")
                continue

            elif user_input.lower().startswith("/cloud "):
                # /cloud <connector_name>
                name = user_input[7:].strip()
                connectors = agent.models.list_connectors()
                if name in connectors:
                    agent.backend = f"cloud:{name}"
                    show_info(f"☁ Backend: {name}")
                elif name == "off":
                    agent.backend = "lmms_engine"
                    show_info("Backend: LMMS Engine (local)")
                else:
                    show_error(f"Unknown connector: {name}. Available: {connectors}")
                continue

            elif user_input.lower() == "/smart":
                show_info("Smart routing ON — complex tasks auto-routed to cloud if available.")
                original_chat = agent.chat
                agent.chat = agent.smart_chat
                continue

            elif user_input.lower() == "/routing":
                show_info(f"Current backend: {agent.backend} | Mode: {agent.current_mode}")
                connectors = agent.models.list_connectors()
                show_info(f"Cloud connectors: {connectors or 'none'}")
                continue

            elif user_input.lower() == "/models":
                c.print(agent.models.get_model_status_table())
                continue

            elif user_input.lower().startswith("/airllm"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    agent.models.set_model(parts[1])
                agent.backend = "airllm"
                show_info(f"AirLLM mode: {agent.models.text_model}")
                continue

            elif user_input.lower().startswith("/download "):
                query = user_input[10:].strip()
                agent.models.download_huggingface_model(query)
                continue

            elif user_input.lower().startswith("/file "):
                path = user_input[6:].strip()
                agent.attach_files([path])
                continue

            elif user_input.lower().startswith("/folder "):
                path = user_input[8:].strip()
                count = agent.attach_folder(path)
                show_info(f"Attached {count} files")
                continue

            elif user_input.lower() == "/attach":
                try:
                    res = subprocess.run(
                        ["zenity", "--file-selection", "--multiple", "--separator=|", "--title=Select files"],
                        capture_output=True, text=True
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        paths = res.stdout.strip().split("|")
                        agent.attach_files(paths)
                except Exception:
                    path = input("File path: ").strip()
                    if path:
                        agent.attach_files([path.strip("'")])
                continue

            elif user_input.lower() == "/connector":
                c.print("[bold]Add Cloud API Connector[/bold]")
                name = input("  Name (e.g. OpenAI): ").strip()
                if not name:
                    continue
                api_key = input("  API Key: ").strip()
                base_url = input("  Base URL (e.g. https://api.openai.com): ").strip()
                api_type = input("  Type (openai/anthropic): ").strip() or "openai"
                model_name = input("  Model name (e.g. gpt-4o): ").strip()
                if api_key and base_url and model_name:
                    agent.models.add_connector(name, api_key, base_url, api_type, model_name)
                    show_info(f"✅ Connector '{name}' added!")
                else:
                    show_error("Missing fields. Cancelled.")
                continue

            elif user_input.lower().startswith("/connector remove "):
                name = user_input[18:].strip()
                if agent.models.remove_connector(name):
                    show_info(f"Removed connector: {name}")
                else:
                    show_error(f"Connector not found: {name}")
                continue

            elif user_input.lower() == "/history":
                history = agent.memory.get_history(agent.session_id, limit=20)
                for msg in history:
                    role_color = "cyan" if msg["role"] == "user" else "green"
                    c.print(f"[{role_color}]{msg['role']}:[/{role_color}] {msg['content'][:120]}")
                continue

            elif user_input.lower() == "/clear":
                agent.memory.clear_session(agent.session_id)
                show_info("Memory cleared.")
                continue

            elif user_input.lower() == "/canvas":
                agent.canvas.show_history()
                continue

            elif user_input.lower() == "/canvas clear":
                agent.canvas.clear()
                continue
                
            elif user_input.lower() in ["/gui", "/tui"]:
                try:
                    import subprocess
                    subprocess.Popen([sys.executable, sys.argv[0], "/gui"])
                    show_info("Launched PyQt6 GUI.")
                except Exception as e:
                    show_error(f"Failed to launch GUI: {e}")
                continue

            elif user_input.lower() == "/undo":
                agent.undo_action()
                continue

            elif user_input.lower() == "/redo":
                agent.redo_action()
                continue

            elif user_input.lower() == "/copy":
                history = agent.memory.get_history(agent.session_id, limit=2)
                if history:
                    last = history[-1]["content"]
                    try:
                        subprocess.run(["xclip", "-selection", "clipboard"], input=last.encode())
                        show_info("Last response copied to clipboard.")
                    except Exception:
                        show_error("xclip not found. Install: sudo apt install xclip")
                continue

            elif user_input.lower() == "/screenshot":
                img_path = "/tmp/lmms_screen.png"
                subprocess.run(["scrot", img_path])
                show_info("Screenshot taken, analyzing...")
                user_input = f"[IMAGE:{img_path}] What do you see in this screenshot?"

            elif user_input.lower() == "/shortcut":
                setup_keyboard_shortcut()
                continue

            elif user_input.lower().startswith("/code"):
                # /code [path]  — Claude Code mode
                parts = user_input.split(maxsplit=1)
                project_path = parts[1].strip() if len(parts) > 1 else "."
                task = input("What do you want to do? (describe the coding task): ").strip()
                if task:
                    agent.code_mode(task, project_path)
                continue

            elif user_input.lower().startswith("/vscode"):
                # VS Code integration
                from lmms.gui.widgets.vscode import (
                    open_file, open_folder, get_active_file, copilot_mode,
                    create_and_open, edit_file, check_vscode_running
                )
                parts = user_input.split()
                if len(parts) < 2:
                    show_info("Usage: /vscode open|improve|fix|explain|new|status")
                    continue

                subcmd = parts[1].lower()
                if subcmd == "status":
                    show_info(check_vscode_running())
                elif subcmd == "open":
                    path = parts[2].strip() if len(parts) >= 3 else "."
                    if os.path.isdir(path):
                        open_folder(path)
                    else:
                        open_file(path)
                    show_info(f"Opened {path}")
                elif subcmd in ["improve", "fix", "explain"]:
                    target = parts[2].strip() if len(parts) >= 3 else get_active_file()
                    if not target:
                        show_error("No file specified. Usage: /vscode improve <path>")
                    elif subcmd == "improve":
                        res = copilot_mode(target)
                        show_info(res)
                    else:
                        task_map = {"fix": "Find and fix all bugs in", "explain": "Explain the code in"}
                        agent.chat(f"{task_map[subcmd]}: {target}")
                elif subcmd == "new":
                    description = user_input.replace("/vscode new", "").strip()
                    if not description:
                        description = input("Describe what to create: ").strip()
                    
                    original_mode = agent.current_mode
                    agent.current_mode = "fast"
                    
                    projects_dir = os.path.expanduser("~/Projects")
                    os.makedirs(projects_dir, exist_ok=True)

                    res = agent._engine_chat(
                        model="qwen3:8b",
                        messages=[{"role": "user", "content": f"Best filename with extension for: {description}. Output ONLY filename."}],
                        stream=False
                    )
                    content_str = res.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if not content_str: content_str = res.get("message", {}).get("content", "")
                    filename = content_str.strip().split()[-1]
                    filepath = os.path.join(projects_dir, filename)

                    stream = agent._engine_chat(
                        model="qwen3:8b",
                        messages=[{"role": "user", "content": f"Write complete code for: {description}\nOutput ONLY the code."}],
                        stream=True
                    )
                    content = ""
                    with open(filepath, "w") as f:
                        for chunk in stream:
                            token = chunk.get("message", {}).get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if not token: continue
                            content += token
                            f.write(token)
                            f.flush()
                            c.print(token, end="", markup=False)

                    subprocess.Popen(["code", filepath])
                    c.print(f"\n[green]✅ Saved and opened in VS Code: {filepath}[/green]")
                    
                    agent.current_mode = original_mode
                continue

            # ── IMAGE HANDLING ────────────────────────────────────

            img_path = None
            if "[IMAGE:" in user_input:
                import re, base64
                match = re.search(r"\[IMAGE:(.*?)\]", user_input)
                if match:
                    img_path = match.group(1)
                    desc = agent._process_image_vram_safe(img_path)
                    user_input = user_input.replace(f"[IMAGE:{img_path}]", f"[Image: {desc}]")

            if "--image" in user_input:
                parts = user_input.split("--image")
                before = parts[0].strip()
                after = parts[1].strip().split(" ", 1)
                img_path = after[0].strip("'\"")
                user_input = before + (" " + after[1] if len(after) > 1 else "")

            # ── INTENT-BASED ROUTING ──────────────────────────────

            intent = detect_intent_main(user_input)

            if intent == "graph":
                _handle_graph(user_input, agent, c)

            elif intent == "create_file":
                _handle_create_file(user_input, agent, c)

            elif intent == "browse":
                _handle_browse(user_input, agent, c, show_info, show_error)

            elif intent == "open_app":
                _handle_open_app(user_input, agent, c, show_info, show_error)

            else:
                agent.chat(user_input, image_path=img_path)

    except KeyboardInterrupt:
        c.print("\n[dim]Bye![/dim]")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────
# INTENT HANDLERS
# ─────────────────────────────────────────────────────────────

def _handle_graph(user_input, agent, c):
    from lmms.gui.widgets.canvas import get_canvas
    import requests, json, re
    c.print("[cyan]📊 Generating graph...[/cyan]")

    # Use REST API directly
    try:
        res = requests.post(
            "http://localhost:11435/v1/chat/completions",
            json={
                "model_name": "qwen3:8b",
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a data assistant. Output ONLY a JSON object. No thinking. No explanation. No markdown."
                    },
                    {
                        "role": "user",
                        "content": f'Give me COMPLETE data for: {user_input}\nInclude ALL available data points, not just start and end.\nFor India population 1947-2000, include ALL census years.\nReturn ONLY JSON:\n{{"title":"India Population 1947-2000",\n"type":"bar",\n"xlabel":"Year",\n"ylabel":"Population (millions)",\n"x":["1947","1951","1961","1971","1981","1991","2001"],\n"y":[350,361,439,548,683,846,1028]}}'
                    }
                ]
            },
            timeout=60
        )
        data_raw = res.json()
        content = data_raw.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        content = content.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        c.print(f"[red]API error: {e}[/red]")
        return

    data = None
    try:
        data = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                pass

    if data and "x" in data and "y" in data:
        get_canvas().render_graph(data)
    else:
        c.print(f"[red]Could not parse graph. Raw: {content[:200]}[/red]")


def _handle_create_file(user_input, agent, c):
    original_mode = agent.current_mode
    agent.current_mode = "fast"
    
    import pathlib, subprocess
    
    projects_dir = os.path.expanduser("~/Projects")
    os.makedirs(projects_dir, exist_ok=True)

    res = agent._engine_chat(model="qwen3:8b",
                      messages=[{"role": "user", "content": f"Best filename (with extension) for: {user_input}. ONLY filename."}],
                      stream=False)
    content_str = res.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content_str: content_str = res.get("message", {}).get("content", "")
    filename = content_str.strip().split()[-1]
    filepath = os.path.join(projects_dir, filename)
    pathlib.Path(filepath).touch()
    subprocess.Popen(["code", filepath])
    c.print(f"[green]✅ VS Code opened: {filepath}[/green]")

    stream = agent._engine_chat(
        model="qwen3:8b",
        messages=[{"role": "user", "content": f"Write complete code for: {user_input}\nOutput ONLY the code."}],
        stream=True
    )
    content = ""
    with open(filepath, "w") as f:
        for chunk in stream:
            token = chunk.get("message", {}).get("choices", [{}])[0].get("delta", {}).get("content", "")
            if not token: continue
            content += token
            f.write(token)
            f.flush()
            c.print(token, end="", markup=False)
    c.print(f"\n[green]✅ Done! Saved to {filepath}[/green]")
    
    agent.current_mode = original_mode


def _handle_browse(user_input, agent, c, show_info, show_error):
    res = agent._engine_chat(model="qwen3:8b",
                      messages=[{"role": "user", "content": f"Extract URL from: {user_input}. If no URL, make DuckDuckGo search URL. Output ONLY the raw URL starting with http."}],
                      stream=False)
    content_str = res.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content_str: content_str = res.get("message", {}).get("content", "")
    url = content_str.strip()
    try:
        text = agent.browser_tool.open_url(url)
        show_info(f"✅ Browsed: {url}")
        c.print(text[:2000])
    except Exception as e:
        show_error(f"Browse error: {e}")


def _handle_open_app(user_input, agent, c, show_info, show_error):
    res = agent._engine_chat(model="qwen3:8b",
                      messages=[{"role": "user", "content": f"Extract the Linux app/command name from: {user_input}. Output ONLY the command (e.g. google-chrome, code, firefox)."}],
                      stream=False)
    content_str = res.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content_str: content_str = res.get("message", {}).get("content", "")
    app_name = content_str.strip()
    try:
        subprocess.Popen([app_name])
        show_info(f"✅ Launched: {app_name}")
    except Exception as e:
        show_error(f"Failed to launch {app_name}: {e}")


if __name__ == "__main__":
    main()
