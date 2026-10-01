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
        
        f = open(log_file, "a")
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

def uninstall_main():
    args = sys.argv[1:]
    if "-all" in args:
        if "--purge" in args:
            print("\033[91m[WARNING]\033[0m Factory reset initiated. Deleting all data, models, and code...")
            subprocess.run("rm -rf ~/.lmms", shell=True)
            subprocess.run(f"{sys.executable} -m pip uninstall -y LMMs", shell=True)
            print("\033[92m[SUCCESS]\033[0m Total Purge complete. LMMs is fully uninstalled.")
        else:
            print("\033[91m[WARNING]\033[0m Removing LMMs source code. User data (models, chats) is kept safe.")
            subprocess.run("rm -rf ~/.lmms/LMMs", shell=True)
            subprocess.run(f"{sys.executable} -m pip uninstall -y LMMs", shell=True)
            print("\033[92m[SUCCESS]\033[0m LMMs code uninstalled successfully.")
    else:
        print("Usage: LMMs-uninstall -all [--purge]")

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

    if args[0] in ["-check", "--check"]:
        print("\033[96m[INFO]\033[0m Hardware Profiler & System Check: (Feature coming soon...)")
        return

    if args[0] in ["--update", "update"]:
        branch = config.get("installed_branch", "main")
        if "--gui" in args:
            branch = "gui"
        elif "--cli" in args:
            branch = "cli"
            
        print(f"\033[96m[INFO]\033[0m Force Updating LMMs ecosystem from GitHub (branch: {branch})...")
        lmms_dir = os.path.expanduser("~/.lmms/LMMs")
        if not os.path.exists(lmms_dir):
            subprocess.run(f"git clone https://github.com/Rajsingh18110/LMMs.git {lmms_dir}", shell=True)
            
        subprocess.run(f"cd {lmms_dir} && git fetch --all && git checkout {branch} && git pull origin {branch} && pip install -r requirements.txt", shell=True)
        return
        
    if args[0] in ["--uninstall", "uninstall", "purge"]:
        uninstall_main()
        return
        
    if args[0] in ["--install", "install", "rebuild"]:
        branch = None
        if "--all" in args:
            branch = "main"
        elif "--gui" in args:
            branch = "gui"
        elif "--cli" in args:
            branch = "cli"
            
        if branch:
            print(f"\033[96m[INFO]\033[0m Installing LMMs ecosystem from source (branch: {branch})...")
            # Save the installed branch state
            config["installed_branch"] = branch
            save_config(config)
            
            lmms_dir = os.path.expanduser("~/.lmms/LMMs")
            if not os.path.exists(lmms_dir):
                print("\033[96m[INFO]\033[0m Cloning repository...")
                subprocess.run(f"git clone https://github.com/Rajsingh18110/LMMs.git {lmms_dir}", shell=True)
            
            subprocess.run(f"cd {lmms_dir} && git fetch --all && git checkout {branch} && git pull origin {branch} && {sys.executable} setup.py install", shell=True)
        else:
            print("Usage: LMMs install --all | --gui | --cli")
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
            print("Usage: lmms set --cli | --engine")
        save_config(config)
        return

    # Intercept missing GUI
    if args[0] in ["gui", "-g", "--gui"]:
        print("\n\033[91m[ERROR]\033[0m GUI component not found!")
        print("It looks like you only installed the CLI or Engine. To use the GUI, please run:")
        print("\033[96m  lmms install --gui\033[0m  (or \033[96mlmms install --all\033[0m for everything)\n")
        return

    # Direct launch overrides
    if args[0] in ["cli", "engine"]:
        launch(args[0], args[1:])
        return
        
    if args[0] in ["cli", "engine", "-c", "-e", "--cli", "--engine"]:
        mode_map = {"cli": "cli", "engine": "engine", "-c": "cli", "-e": "engine", "--cli": "cli", "--engine": "engine"}
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
        if mode == "cli":
            if ensure_engine:
                engine_proc = ensure_engine_running()
                env["LMMS_ENGINE_MANAGED"] = "1"
            
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--internal-backend"]
            else:
                cmd = [sys.executable, "-m", "lmms.backend.main"]
                
            if forward_args:
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
        
    # multiprocessing support for windows exes
    import multiprocessing
    multiprocessing.freeze_support()
    main()
