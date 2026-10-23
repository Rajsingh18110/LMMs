import os
import sys
import json
import subprocess
import time
import urllib.request
import threading
import site

# Allow PyInstaller executable to load heavy modules (like torch) installed on the host system
try:
    sys.path.extend(site.getsitepackages())
    sys.path.append(site.getusersitepackages())
except Exception:
    pass

# FIX for CUDA 12 libcudart.so.12 missing in llama_cpp
cuda_paths = ["/usr/local/cuda-12.6/lib64", "/usr/local/cuda-12.4/lib64", "/usr/local/lib/ollama/cuda_v12"]
for cuda_path in cuda_paths:
    if os.path.exists(cuda_path):
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if cuda_path not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{cuda_path}:{current_ld}" if current_ld else cuda_path

def check_for_updates():
    # Note: LMMs handles updates natively via git pull now
    pass

CONFIG_PATH = os.path.expanduser("~/.lmms/config.json")

def ensure_engine_running():
    try:
        from lmms.common.discovery import get_engine_url, is_engine_alive
        active_url = get_engine_url(interactive=False)
        if is_engine_alive(active_url, timeout=0.5):
            return {"status": "connected", "url": active_url}
        if not ("127.0.0.1" in active_url or "localhost" in active_url):
            print(f"\033[1;33m[LMMs]\033[0m Configured remote engine at {active_url} is not responding.")
    except Exception:
        pass

    try:
        from lmms.api.service import wait_for_server_healthy, start_server_daemon, is_server_running
        if wait_for_server_healthy(timeout=0.6):
            return {"status": "connected", "url": "http://localhost:11435"}

        print("Starting LMMs Super Engine in the background...")
        res = start_server_daemon(host="0.0.0.0", port=11435, engine_tier=3, forever=False, initiator="cli")
        wait_for_server_healthy(timeout=8.0)
        return res
    except Exception as e:
        print(f"\033[1;31m[LMMs Engine Error]\033[0m Failed to auto-start daemon: {e}")
        return None


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"default_mode": "cli"}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

def uninstall_main():
    args = [a.lower() for a in sys.argv[1:]]
    src_dir = os.path.expanduser("~/.lmms/app/src")
    if "--purge" in args or "-purge" in args or "purge" in args:
        print("\033[91m[WARNING]\033[0m Factory reset initiated. Deleting all data, models, and code...")
        subprocess.run("rm -rf ~/.lmms", shell=True)
        print("\033[92m[SUCCESS]\033[0m Total Purge complete. LMMs is fully uninstalled.")
    else:
        if not os.path.exists(src_dir):
            print("\033[92m[SUCCESS]\033[0m LMMs source code is already uninstalled. Nothing to remove.")
            return
        print("\033[91m[WARNING]\033[0m Removing LMMs source code. User data (models, chats) is kept safe.")
        subprocess.run(f"rm -rf {src_dir}", shell=True)
        reg_path = os.path.expanduser("~/.lmms/config/installed_components.json")
        if os.path.exists(reg_path):
            try:
                with open(reg_path, "w") as f:
                    json.dump({"all": False, "cli": False, "gui": False, "engine": False, "engine1": False, "engine2": False}, f, indent=2)
            except Exception:
                pass
        cfg_file = os.path.expanduser("~/.lmms/config/config.json")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r") as f:
                    cfg = json.load(f)
                cfg.pop("default_mode", None)
                cfg.pop("engine_variant", None)
                with open(cfg_file, "w") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
        print("\033[92m[SUCCESS]\033[0m LMMs code uninstalled successfully.")

def run_system_check():
    import platform
    import shutil
    
    c_cyan = "\033[1;36m"
    c_white = "\033[1;37m"
    c_green = "\033[1;32m"
    c_dim = "\033[2m"
    c_reset = "\033[0m"
    c_yellow = "\033[1;33m"
    
    print(f"\n{c_white}LMMs OS{c_reset} {c_dim}· System & Hardware Diagnostics{c_reset}")
    print(f"{c_dim}{'─' * 62}{c_reset}")
    
    # OS
    os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
    print(f"  {c_cyan}OS:{c_reset}        {os_name}")
    
    # Python
    py_info = f"Python {platform.python_version()} ({sys.executable})"
    print(f"  {c_cyan}Python:{c_reset}    {py_info}")
    
    # CPU
    cpu_cores = os.cpu_count() or 1
    cpu_model = platform.processor() or "Unknown"
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
    print(f"  {c_cyan}CPU:{c_reset}       {cpu_model} ({cpu_cores} threads)")
    
    # RAM
    ram_str = "Unknown"
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_str = f"{mem.total / (1024**3):.1f} GB Total ({mem.available / (1024**3):.1f} GB Available)"
    except ImportError:
        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            kb = int(line.split()[1])
                            ram_str = f"{kb / (1024**2):.1f} GB Total"
                            break
            except Exception:
                pass
    print(f"  {c_cyan}RAM:{c_reset}       {ram_str}")
    
    # GPU & VRAM
    gpu_found = False
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.strip().split("\n")
                for i, g in enumerate(lines):
                    parts = [p.strip() for p in g.split(",")]
                    name = parts[0] if len(parts) > 0 else "NVIDIA GPU"
                    vram_total = parts[1] if len(parts) > 1 else ""
                    vram_free = parts[2] if len(parts) > 2 else ""
                    driver = parts[3] if len(parts) > 3 else ""
                    gpu_found = True
                    print(f"  {c_cyan}GPU [{i}]:{c_reset}   {name} ({vram_total} VRAM, {vram_free} Free) [Driver {driver}]")
        except Exception:
            pass
    
    if not gpu_found:
        print(f"  {c_cyan}GPU:{c_reset}       {c_yellow}No dedicated NVIDIA GPU detected (CPU/mmap DDR5 mode active){c_reset}")
    
    # LMMs Core Status
    print(f"{c_dim}{'─' * 62}{c_reset}")
    llama_ok = False
    try:
        import importlib.util
        llama_ok = importlib.util.find_spec("llama_cpp") is not None
    except Exception:
        pass
    llama_status = f"{c_green}Available{c_reset}" if llama_ok else f"{c_yellow}Not installed (run 'lmms install --engine'){c_reset}"
    print(f"  {c_cyan}llama.cpp:{c_reset} {llama_status}")
    print(f"{c_dim}{'─' * 62}{c_reset}\n")

def get_installed_components():
    p = os.path.expanduser("~/.lmms/config/installed_components.json")
    installed = {}
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                installed = json.load(f)
        except Exception:
            installed = {}

    repo_root = os.path.dirname(os.path.abspath(__file__))
    has_gui = os.path.isdir(os.path.join(repo_root, "lmms", "gui")) or os.path.exists(os.path.join(repo_root, "gui.py"))
    has_cli = os.path.isdir(os.path.join(repo_root, "lmms", "cli")) or os.path.exists(os.path.join(repo_root, "main.py"))
    has_engine = (
        os.path.isdir(os.path.join(repo_root, "lmms", "engine"))
        or os.path.isdir(os.path.join(repo_root, "lmms", "lmmsengine"))
        or os.path.isdir(os.path.join(repo_root, "lmms", "api"))
    )

    if has_gui:
        installed["gui"] = True
    if has_cli:
        installed["cli"] = True
    if has_engine:
        installed["engine"] = True

    if has_gui and has_cli and has_engine:
        installed["all"] = True

    return installed

def main():
    threading.Thread(target=check_for_updates, daemon=True).start()
    args = sys.argv[1:]
    config = load_config()

    if not args:
        installed = get_installed_components()
        mode = config.get("default_mode")
        if not mode or (mode == "cli" and not (installed.get("cli") or installed.get("all"))):
            if installed.get("engine") or installed.get("engine1") or installed.get("engine2"):
                mode = "engine"
            elif installed.get("cli") or installed.get("all"):
                mode = "cli"
            else:
                mode = "engine"
        launch(mode)
        return

    if args[0] in ["--help", "-h", "help"]:
        launch("cli", args, ensure_engine=False)
        return

    if args[0] in ["-check", "--check", "check"]:
        run_system_check()
        return

    if args[0] in ["--update", "update"]:
        from lmms.cli.installer import run_updater
        run_updater(args[1:])
        return
        
    if args[0] in ["--uninstall", "uninstall", "purge"]:
        uninstall_main()
        return
        
    if args[0] in ["--install", "install", "rebuild"]:
        from lmms.cli.installer import run_installer
        run_installer(args[1:])
        return
        
    if args[0] in ["--stop", "stop"]:
        print("\033[96m[INFO]\033[0m Stopping LMMs Engine...")
        subprocess.run("pkill -f 'lmms.lmmsengine.main server'", shell=True)
        print("\033[92m[SUCCESS]\033[0m Engine stopped.")
        return

    if args[0] == "set":
        if "--gui" in args:
            config["default_mode"] = "gui"
            print("Default mode set to GUI")
        elif "--cli" in args:
            config["default_mode"] = "cli"
            print("Default mode set to CLI")
        elif "--engine" in args:
            config["default_mode"] = "engine"
            print("Default mode set to Engine")
        else:
            print("Usage: lmms set --gui | --cli | --engine")
        save_config(config)
        return

    # Direct launch overrides
    if args[0] in ["gui", "cli", "tui", "engine", "-g", "-c", "-t", "-e", "--gui", "--cli", "--tui", "--engine"]:
        mode_map = {
            "gui": "gui", "cli": "cli", "tui": "tui", "engine": "engine",
            "-g": "gui", "-c": "cli", "-t": "tui", "-e": "engine",
            "--gui": "gui", "--cli": "cli", "--tui": "tui", "--engine": "engine"
        }
        resolved_mode = mode_map[args[0]]
        # If 'engine' is followed by a subcommand (e.g. 'engine pull <model>'), forward to engine runtime
        if resolved_mode == "engine" and len(args) > 1 and args[1] in [
            "run", "list", "ls", "ps", "pull", "info", "benchmark", "bench",
            "rm", "delete", "stop", "search", "doctor", "cache", "air",
            "registry", "downloads", "create", "package", "packages",
            "status", "mode", "unload", "purge"
        ]:
            if not getattr(sys, 'frozen', False):
                from lmms.engine.main import run_engine
                run_engine(args[1:])
                return
        launch(resolved_mode, args[1:])
        return

    if args[0] in ["connect", "remote"]:
        from lmms.cli.commands import cmd_connect, cmd_remote
        if args[0] == "connect":
            cmd_connect(args[1:])
        else:
            cmd_remote(args[1:])
        return

    if args[0] in ["server", "serve", "daemon"]:
        from lmms.cli.commands import cmd_server
        cmd_server(args[1:])
        return

    if args[0] == "mcp":
        from lmms_mcp.cli import handle_mcp_cli
        sys.exit(handle_mcp_cli(args[1:]))

    if args[0] == "app-server":
        from lmms_server.server import run_app_server_cli
        sys.exit(run_app_server_cli(args[1:]))

    if args[0] == "audit":
        from lmms_server.audit_cli import handle_audit_cli
        sys.exit(handle_audit_cli(args[1:]))

    # Engine commands should be routed directly to the engine
    engine_commands = [
        "run", "list", "ls", "ps", "pull", "info", "benchmark", "bench",
        "rm", "delete", "stop", "search", "doctor", "cache", "air",
        "registry", "downloads", "create", "package", "packages",
        "status", "mode", "unload", "purge"
    ]
    if any(a in ["--air", "-air"] for a in args) or (len(args) > 0 and args[0] in engine_commands):
        if not getattr(sys, 'frozen', False):
            from lmms.engine.main import run_engine
            run_engine(args)
            return
        launch("engine", args)
        return

    # Pass everything else to the default mode (e.g. workspace paths)
    mode = config.get("default_mode", "cli")
    launch(mode, args)

def launch(mode, forward_args=None, ensure_engine=True):
    if forward_args is None:
        forward_args = []

    installed = get_installed_components()
    has_all = installed.get("all", False)

    if mode == "cli":
        if not (has_all or installed.get("cli", False)):
            print("\n\033[1;31m[ERROR]\033[0m Terminal Studio (CLI) is not installed on this workstation.")
            print("\033[2mCurrently installed configuration: Engine Runtime only.\033[0m")
            print("\nTo install Terminal Studio (CLI), run:")
            print("  \033[1;36mlmms install --cli\033[0m")
            print("or install the complete suite:")
            print("  \033[1;36mlmms install --all\033[0m\n")
            return

    elif mode == "gui":
        if not (has_all or installed.get("gui", False)):
            print("\n\033[1;31m[ERROR]\033[0m Desktop Studio (GUI) is not installed on this workstation.")
            print("\033[2mCurrently installed configuration: Engine Runtime only.\033[0m")
            print("\nTo install Desktop Studio (GUI), run:")
            print("  \033[1;36mlmms install --gui\033[0m")
            print("or install the complete suite:")
            print("  \033[1;36mlmms install --all\033[0m\n")
            return

    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

    try:
        from lmms.api.service import get_ai_python_executable
        py_exe = get_ai_python_executable()
    except Exception:
        venv_py = os.path.expanduser("~/.lmms/app/venv/bin/python")
        py_exe = venv_py if os.path.exists(venv_py) else sys.executable

    # In a compiled environment, this calls ./lmms-backend or ./lmms-engine
    while True:
        engine_proc = None
        cmd: list[str] = []
        if mode in ["cli", "tui", "gui"]:
            if ensure_engine:
                engine_proc = ensure_engine_running()
                env["LMMS_ENGINE_MANAGED"] = "1"
            
            if mode == "gui":
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--internal-gui"]
                else:
                    cmd = [py_exe, os.path.abspath(__file__), "--internal-gui"]
            elif mode == "tui":
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--internal-backend"]
                else:
                    cmd = [py_exe, "-m", "lmms.tui.main"]
            else:
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--internal-backend"]
                else:
                    cmd = [py_exe, "-m", "lmms.backend.main"]
                    
            if forward_args:
                cmd.extend(forward_args)
        elif mode == "engine":
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--internal-engine"]
            else:
                cmd = [py_exe, "-m", "lmms.engine.main"]
            
            if forward_args:
                cmd.extend(forward_args)
                
        if not cmd:
            break

        should_reboot = False
        try:
            result = subprocess.run(cmd, env=env)
            if result.returncode == 42:
                should_reboot = True
        except KeyboardInterrupt:
            pass
        finally:
            if engine_proc:
                if should_reboot:
                    print("\n\033[96m[INFO]\033[0m Rebooting system (Engine & CLI)...")
                else:
                    try:
                        from lmms.api.service import stop_server_daemon
                        stop_res = stop_server_daemon(force=False, caller="cli")
                        if stop_res.get("status") == "stopped":
                            print("\n\033[96m[INFO]\033[0m Shut down auto-started Engine daemon.")
                    except Exception:
                        pass
        if not should_reboot:
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--internal-backend":
        import argparse
        import threading
        from lmms.backend.main import run_cli, start_api
        
        parser = argparse.ArgumentParser(description="LMMs Backend OS")
        parser.add_argument("--internal-backend", action="store_true", help=argparse.SUPPRESS)
        parser.add_argument("--api", action="store_true", help="Run the Backend API Server alongside CLI")
        args, unknown = parser.parse_known_args()
        
        if args.api:
            api_thread = threading.Thread(target=start_api, daemon=True)
            api_thread.start()
            
        run_cli()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--internal-engine":
        # Modify argv to strip internal flag
        try:
            from lmms.engine.main import run_engine as engine_main
        except ImportError:
            from lmms.lmmsengine.main import main as engine_main
        engine_main()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--internal-gui":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        try:
            from lmms.gui.app import run_gui
            run_gui()
        except ImportError:
            try:
                from gui import main as gui_main
                gui_main()
            except ImportError:
                print("\n\033[91m[ERROR]\033[0m GUI component not found!")
                print("It looks like you only installed the CLI or Engine. To use the GUI, please run:")
                print("\033[96m  lmms install --gui\033[0m  (or \033[96mlmms install --all\033[0m for everything)\n")
        sys.exit(0)
        
    # multiprocessing support for windows exes
    import multiprocessing
    multiprocessing.freeze_support()
    main()
