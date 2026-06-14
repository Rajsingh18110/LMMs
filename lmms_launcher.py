import os
import sys
import json
import subprocess
import time
import urllib.request
import threading

# FIX for CUDA 12 libcudart.so.12 missing in llama_cpp
cuda_paths = ["/usr/local/cuda-12.6/lib64", "/usr/local/cuda-12.4/lib64", "/usr/local/lib/ollama/cuda_v12"]
for cuda_path in cuda_paths:
    if os.path.exists(cuda_path):
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if cuda_path not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{cuda_path}:{current_ld}" if current_ld else cuda_path

def check_for_updates():
    try:
        engine_dir = os.path.join(os.getcwd(), "lmms", "lmmsengine")
        if os.path.exists(engine_dir):
            subprocess.run(["git", "fetch", "origin", "main"], cwd=engine_dir, capture_output=True, timeout=3)
            res = subprocess.run(["git", "status", "-sb"], cwd=engine_dir, capture_output=True, text=True)
            if "behind" in res.stdout:
                print("\n\033[93m[Update Available]\033[0m A new version of LMMs Engine is available on GitHub!")
                print("Run 'lmms --update' or 'python3 lmms_launcher.py --update' to install it.\n")
    except Exception:
        pass

CONFIG_PATH = os.path.expanduser("~/.lmms/config.json")

def ensure_engine_running():
    try:
        # Ping the engine to see if it's already running
        urllib.request.urlopen("http://localhost:11435/webhook", timeout=1)
    except Exception:
        print("Starting LMMs Engine in the background...")
        log_dir = os.path.expanduser("~/.lmms/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "server.log")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        
        with open(log_file, "a") as f:
            if getattr(sys, 'frozen', False):
                p = subprocess.Popen([sys.executable, "--internal-engine", "server"], stdout=f, stderr=f, env=env, start_new_session=True)
            else:
                engine_script = os.path.join(os.getcwd(), "lmms", "lmmsengine", "main.py")
                p = subprocess.Popen([sys.executable, engine_script, "server"], stdout=f, stderr=f, env=env, start_new_session=True)
        
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

    if args[0] in ["--update", "update"]:
        print("\033[96m[INFO]\033[0m Checking for updates...")
        subprocess.run(["git", "pull", "origin", "main"], cwd=os.getcwd())
        engine_dir = os.path.join(os.getcwd(), "lmms", "lmmsengine")
        if os.path.exists(engine_dir):
            print("\033[96m[INFO]\033[0m Updating LMMs Engine...")
            subprocess.run(["git", "pull", "origin", "main"], cwd=engine_dir)
        print("\033[92m[SUCCESS]\033[0m Update complete! Please restart LMMs.")
        return
        
    if args[0] in ["--stop", "stop"]:
        print("\033[96m[INFO]\033[0m Stopping LMMs Engine...")
        subprocess.run("pkill -f 'lmmsengine/main.py server'", shell=True)
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
        
    if args[0] in ["-g", "-c", "-e"]:
        mode_map = {"-g": "gui", "-c": "cli", "-e": "engine"}
        launch(mode_map[args[0]], args[1:])
        return

    # Pass everything else to the CLI (Backend OS)
    launch("cli", args)

def launch(mode, forward_args=None):
    if forward_args is None:
        forward_args = []
        
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    # In a compiled environment, this would call ./lmms-backend or ./lmms-engine
    # For now, we call the python scripts.
    engine_proc = None
    if mode in ["cli", "gui"]:
        engine_proc = ensure_engine_running()
        
        # If gui mode, we could pass an argument to backend to start API + Electron
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--internal-backend"]
        else:
            cmd = [sys.executable, "-m", "lmms.backend.main"]
        
        if mode == "gui":
            cmd.append("--api")
        cmd.extend(forward_args)
    elif mode == "engine":
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--internal-engine"]
        else:
            engine_script = os.path.join(os.getcwd(), "lmms", "lmmsengine", "main.py")
            cmd = [sys.executable, engine_script]
        
        if forward_args:
            cmd.extend(forward_args)
        else:
            cmd.append("server")
            
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        pass
    finally:
        if engine_proc:
            print("\n\033[96m[INFO]\033[0m Shutting down auto-started Engine...")
            engine_proc.terminate()

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
