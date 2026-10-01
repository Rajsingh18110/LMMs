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
        # Ping the engine to see if it's already running
        urllib.request.urlopen("http://localhost:11435/webhook", timeout=1)
    except Exception:
        print("Starting LMMs Engine in the background...")
        import secrets
        if not os.environ.get("LMMS_INTERNAL_TOKEN"):
            os.environ["LMMS_INTERNAL_TOKEN"] = secrets.token_hex(16)
        log_dir = os.path.expanduser("~/.lmms/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "server.log")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
        
        with open(log_file, "a") as f:
            if getattr(sys, 'frozen', False):
                p = subprocess.Popen([sys.executable, "--internal-engine", "server"], stdout=f, stderr=f, env=env, start_new_session=True)
            else:
                cmd = [sys.executable, "-m", "lmms.lmmsengine.main"]
                p = subprocess.Popen([sys.executable, "-m", "lmms.lmmsengine.main", "server"], stdout=f, stderr=f, env=env, start_new_session=True)
        
        # Give it a moment to boot
        time.sleep(2)
        return p


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"default_mode": "cli"}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

def main():
    threading.Thread(target=check_for_updates, daemon=True).start()
    args = sys.argv[1:]
    config = load_config()

    if not args:
        mode = config.get("default_mode", "cli")
        launch(mode)
        return

    if args[0] in ["--help", "-h", "help"]:
        launch("cli", args, ensure_engine=False)
        return

    if args[0] in ["--update", "update"]:
        print("\033[96m[INFO]\033[0m Updating LMMs from source...")
        subprocess.run("git pull origin main && pip install -r requirements.txt", shell=True)
        return
        
    if args[0] in ["--uninstall", "uninstall", "purge"]:
        print("\033[91m[WARNING]\033[0m To completely remove LMMs, please run: pip uninstall LMMs")
        return
        
    if args[0] in ["--install", "install", "rebuild"]:
        print("\033[96m[INFO]\033[0m Rebuilding LMMs from source...")
        subprocess.run(f"{sys.executable} setup.py install", shell=True)
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
    if args[0] in ["gui", "cli", "engine"]:
        launch(args[0], args[1:])
        return
        
    if args[0] in ["gui", "cli", "engine", "-g", "-c", "-e", "--gui", "--cli", "--engine"]:
        mode_map = {"gui": "gui", "cli": "cli", "engine": "engine", "-g": "gui", "-c": "cli", "-e": "engine", "--gui": "gui", "--cli": "cli", "--engine": "engine"}
        launch(mode_map[args[0]], args[1:])
        return

    # Engine commands should be routed directly to the engine
    engine_commands = ["run", "list", "ps", "pull", "info", "benchmark", "rm", "delete", "stop", "search", "doctor", "cache", "air", "registry", "downloads", "create", "server", "-server", "--server"]
    if args[0] in engine_commands or args[0] in ["--air", "-air"]:
        launch("engine", args)
        return

    # Pass everything else to the default mode (e.g. workspace paths)
    mode = config.get("default_mode", "cli")
    launch(mode, args)

def launch(mode, forward_args=None, ensure_engine=True):
    if forward_args is None:
        forward_args = []
        
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

    # In a compiled environment, this would call ./lmms-backend or ./lmms-engine
    # For now, we call the python scripts.
    while True:
        engine_proc = None
        if mode in ["cli", "gui"]:
            if ensure_engine:
                engine_proc = ensure_engine_running()
                env["LMMS_ENGINE_MANAGED"] = "1"
            
            # If gui mode, we could pass an argument to backend to start API + Electron
            if mode == "gui":
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--internal-gui"]
                else:
                    cmd = [sys.executable, os.path.abspath(__file__), "--internal-gui"]
            else:
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--internal-backend"]
                else:
                    cmd = [sys.executable, "-m", "lmms.backend.main"]
                    
            if mode in ["cli", "gui"] and forward_args:
                cmd.extend(forward_args)
        elif mode == "engine":
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--internal-engine"]
            else:
                cmd = [sys.executable, "-m", "lmms.lmmsengine.main"]
                # cmd already set
            
            if forward_args:
                cmd.extend(forward_args)
                
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
                    print("\n\033[96m[INFO]\033[0m Shutting down auto-started Engine...")
                engine_proc.terminate()
                
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
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from lmms.lmmsengine.main import main as engine_main
        engine_main()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--internal-gui":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from gui import main as gui_main
        gui_main()
        sys.exit(0)
        
    # multiprocessing support for windows exes
    import multiprocessing
    multiprocessing.freeze_support()
    main()
