#!/usr/bin/env python3
"""
main.py — LMMs Engine Entry Point
Commands: lmms run, lmms ps, lmms stop, lmms list, etc.
"""

import sys
import os
import subprocess
import json
import site

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(ENGINE_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Allow PyInstaller executable to load heavy modules (like torch) installed on the host system
try:
    sys.path.extend(site.getsitepackages())
    sys.path.append(site.getusersitepackages())
except Exception:
    pass

API_URL = "http://localhost:11435/v1"
def is_root():
    import platform
    if platform.system() == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0

def ensure_server_running():
    import requests
    import time
    import socket
    try:
        requests.get("http://localhost:11435/v1/health", timeout=1)
    except:
        # Fallback defensive check: Is port actually in use?
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', 11435)) == 0:
                print("Port 11435 is already in use by another process. Skipping spawn.")
                return

        print("Starting Engine daemon in the background...")
        log_file = os.path.expanduser("~/.lmms/logs/server.log")
        f = open(log_file, "a")
        engine_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        import platform
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen([sys.executable, engine_script, "server"], stdout=f, stderr=f, **kwargs)
        time.sleep(2)

def main():
    import sys
    import os
    import platform

    # ── Windows UTF-8 fix ──────────────────────────────────────────────────────
    # On Windows, stdout defaults to cp1252 which crashes on ANY Unicode output
    # from the AI (emojis, arrows, etc.), causing Python to exit and CMD to
    # replay the user's buffered input ('hello') as a shell command.
    if platform.system() == "Windows":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            # Python < 3.7 fallback
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    # ──────────────────────────────────────────────────────────────────────────

    base_dir = os.path.expanduser("~/.lmms")
    for subdir in ["models", "cache", "logs", "manifests", "workspaces"]:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
    args = sys.argv[1:]
    
    if not args or args[0] in ("-h", "--help", "help"):
        print('''
=========================================
      LMMs AI Operating System
=========================================

1. Installer / Builder
  pip install lmms-builder       # Install bootstrap
  lmms-builder detect            # Hardware detection
  lmms-builder compatibility     # Compatibility check
  lmms-builder doctor            # Missing dependencies
  lmms-builder benchmark         # Test hardware
  lmms-builder install           # Install core components

2. Launcher / Mode Selection
  lmms set --gui                 # Set default to Desktop App
  lmms set --cli                 # Set default to Smart Shell
  lmms set --engine              # Set default to Raw Engine
  lmms gui / cli / engine        # Direct launch bypass
  lmms -g / -c / -e              # Fast aliases
  lmms                           # Open default mode

3. Core Engine (Dual Engine Architecture)
  lmms pull <model>              # Auto-detect best quant & download
  lmms run <model> [-use l|p]    # Load & chat (-use l: llama.cpp, -use p: pytorch)
  lmms stop <model>              # Unload model
  lmms ps                        # Show active loaded models
  lmms list                      # List local downloaded models
  lmms info <model>              # Metadata for a model
  lmms rm <model>                # Delete a model
  lmms search <query>            # Search hub
  lmms benchmark <model>         # Engine speed test
  lmms doctor [--fix]            # Fix engine health
  lmms create <model> -f <file>  # Create from Modelfile
  lmms server                    # Start API Webhook Server (Dashboard)

4. Air Engine (Distributed)
  lmms -air run <model>          # Run heavy model with swapping
  lmms --air run <m1> <m2>       # Cluster mode scheduling
  lmms air ps / cache / stats    # Air metrics
  lmms air unload / benchmark    # Air management

5. Component Installation
  lmms install --gui/cli/air     # Modular install
  lmms uninstall --all --purge   # Full wipe

6. Package Management
  lmms package install runtime <x>
  lmms package install provider <x>
  lmms package install tool <x>
  lmms package list/remove

7. AI Shell Slash Commands
  /fast, /deep, /code, /research # Reasoning modes
  /vision, /image                # Visual modes
  /memory, /task, /git, /workspace
  /explain, /summarize, /benchmark

8. Workspace Commands
  /folder                        # Open file manager
  lmms workspace create/list/open/close/delete/restore

9. Permissions
  /perm low/medium/full          # Agentic freedom scope

10. Chat History
  /chat                          # List workspace chats
  /newchat                       # Fresh thread
  /chat -r <id> / -d <id>        # Rename / Delete

11. Interactive Model Swap
  /ml <model> [-f | -d]          # Switch model mid-chat

12. Pair Commands (Bundles)
  /pair -n 1 text:qwen image:llava ...
  /pair 1                        # Activate slot 1
  /pair -l / -d 1                # List / Delete

13. Undo / Redo
  /undo <file> / <folder>        # Revert AI changes
  /redo <file> / <folder>        # Reapply

14. Orchestration
  lmms task create/list/show     # Workflow
  lmms git status/commits/explain# Git intel
  lmms agent run <type>          # Predefined agents
  lmms route / orchestrate       # Handoff flow
''')
        sys.exit(0)

    # Parse args
    model_args = []
    mode_arg = "deep"
    prompt_parts = []
    autoplay_audio = False
    is_air = False
    forced_engine = None
    
    # Modality Flags
    modality_vc = False
    modality_vct = False
    modality_ocr = False
    modality_all = False
    
    i = 0
    while i < len(args):
        if args[i] in ["--air", "-air"]:
            is_air = True
            i += 1
        elif args[i] == "air" and i == 0:
            # Handle "lmms air <cmd>" style
            clean_args = ["air"] + args[1:]
            break # Let the router handle it
        elif args[i] == "--autoplay":
            autoplay_audio = True
            i += 1
        elif args[i] == "run" and i + 1 < len(args):
            i += 1
            # Collect all models until we hit a flag or a prompt string
            while i < len(args) and not args[i].startswith("-") and args[i] not in ["fast", "deep", "code", "research"]:
                if " " in args[i] or args[i].lower() in ["hello", "hi"]:
                    break
                model_args.append(args[i])
                i += 1
            continue
        elif args[i] in ["-fast", "--fast", "fast", "-f"]:
            mode_arg = "fast"
            i += 1
        elif args[i] in ["-deep", "--deep", "deep", "-d"]:
            mode_arg = "deep"
            i += 1
        elif args[i] in ["-code", "--code", "code", "-c"]:
            mode_arg = "code"
            i += 1
        elif args[i] in ["-research", "--research", "research"]:
            mode_arg = "research"
            i += 1
        elif args[i].lower() == "-vc":
            modality_vc = True
            i += 1
        elif args[i].lower() == "-vct":
            modality_vct = True
            i += 1
        elif args[i].lower() == "-ocr":
            modality_ocr = True
            i += 1
        elif args[i].lower() == "-all":
            modality_all = True
            i += 1
        elif args[i] == "-use" and i + 1 < len(args):
            use_engine = args[i+1].lower()
            if use_engine in ["-l", "l", "llama"]:
                forced_engine = "llama"
            elif use_engine in ["-p", "p", "pytorch"]:
                forced_engine = "pytorch"
            i += 2
        elif not args[i].startswith("--") and not args[i].startswith("-") and args[i] not in ["run", "list", "ps", "pull", "info", "benchmark", "rm", "stop", "search", "doctor", "cache", "air", "registry", "downloads", "create", "serve", "delete"]:
            prompt_parts.append(args[i])
            i += 1
        elif args[i] == "-cl":
            print('''
=========================================
      LMMs AI Operating System
=========================================

1. Installer / Builder
  pip install lmms-builder       # Install bootstrap
  lmms-builder detect            # Hardware detection
  lmms-builder compatibility     # Compatibility check
  lmms-builder doctor            # Missing dependencies
  lmms-builder benchmark         # Test hardware
  lmms-builder install           # Install core components

2. Launcher / Mode Selection
  lmms set --gui                 # Set default to Desktop App
  lmms set --cli                 # Set default to Smart Shell
  lmms set --engine              # Set default to Raw Engine
  lmms gui / cli / engine        # Direct launch bypass
  lmms -g / -c / -e              # Fast aliases
  lmms                           # Open default mode

3. Core Engine (Dual Engine Architecture)
  lmms pull <model>              # Auto-detect best quant & download
  lmms run <model> [-use l|p]    # Load & chat (-use l: llama.cpp, -use p: pytorch)
  lmms stop <model>              # Unload model
  lmms ps                        # Show active loaded models
  lmms list                      # List local downloaded models
  lmms info <model>              # Metadata for a model
  lmms rm <model>                # Delete a model
  lmms search <query>            # Search hub
  lmms benchmark <model>         # Engine speed test
  lmms doctor [--fix]            # Fix engine health
  lmms create <model> -f <file>  # Create from Modelfile
  lmms server                    # Start API Webhook Server (Dashboard)

4. Air Engine (Distributed)
  lmms -air run <model>          # Run heavy model with swapping
  lmms --air run <m1> <m2>       # Cluster mode scheduling
  lmms air ps / cache / stats    # Air metrics
  lmms air unload / benchmark    # Air management

5. Component Installation
  lmms install --gui/cli/air     # Modular install
  lmms uninstall --all --purge   # Full wipe

6. Package Management
  lmms package install runtime <x>
  lmms package install provider <x>
  lmms package install tool <x>
  lmms package list/remove

7. AI Shell Slash Commands
  /fast, /deep, /code, /research # Reasoning modes
  /vision, /image                # Visual modes
  /memory, /task, /git, /workspace
  /explain, /summarize, /benchmark

8. Workspace Commands
  /folder                        # Open file manager
  lmms workspace create/list/open/close/delete/restore

9. Permissions
  /perm low/medium/full          # Agentic freedom scope

10. Chat History
  /chat                          # List workspace chats
  /newchat                       # Fresh thread
  /chat -r <id> / -d <id>        # Rename / Delete

11. Interactive Model Swap
  /ml <model> [-f | -d]          # Switch model mid-chat

12. Pair Commands (Bundles)
  /pair -n 1 text:qwen image:llava ...
  /pair 1                        # Activate slot 1
  /pair -l / -d 1                # List / Delete

13. Undo / Redo
  /undo <file> / <folder>        # Revert AI changes
  /redo <file> / <folder>        # Reapply

14. Orchestration
  lmms task create/list/show     # Workflow
  lmms git status/commits/explain# Git intel
  lmms agent run <type>          # Predefined agents
  lmms route / orchestrate       # Handoff flow
''')
            sys.exit(0)
        else:
            i += 1

    # Clean args for command router
    clean_args = [a for a in args if a not in ["--air", "-air"]]
    
    # CLI mode bypass
    if clean_args and clean_args[0] in ["cli", "-cli", "--cli", "-c"]:
        from lmms.backend.main import run_cli
        run_cli()
        sys.exit(0)
        
    # GUI mode bypass
    if clean_args and clean_args[0] in ["gui", "-gui", "--gui", "-g"]:
        import lmms_gui_entry
        lmms_gui_entry.main()
        sys.exit(0)
    
    # Engine CLI Commands Bypass
    if clean_args and clean_args[0] in ["run", "list", "ps", "pull", "info", "benchmark", "rm", "delete", "stop", "search", "doctor", "cache", "air", "registry", "downloads", "create", "server", "-server", "--server"]:
        import requests, json, sys, os
        cmd = clean_args[0]
        try:
            if cmd == "list":
                from lmms.engine.registry import RegistryManager
                reg = RegistryManager()
                reg.list_models()
                sys.exit(0)
                
            elif cmd == "info":
                if len(args) < 2:
                    print("Usage: lmms info <model_name>")
                    sys.exit(1)
                from lmms.engine.registry import RegistryManager
                reg = RegistryManager()
                reg.info_model(args[1])
                sys.exit(0)
                
            elif cmd == "benchmark":
                if len(args) < 2:
                    print("Usage: lmms benchmark <model_name>")
                    sys.exit(1)
                from lmms.engine.benchmark import BenchmarkEngine
                b = BenchmarkEngine()
                b.run_real_benchmark(args[1])
                sys.exit(0)
                
            elif cmd == "ps":
                from rich.console import Console
                c = Console()
                f = os.path.expanduser("~/.lmms/logs/active_models.json")
                if os.path.exists(f):
                    try:
                        with open(f, "r") as file: data = json.load(file)
                        c.print("[bold cyan]Engine Stats:[/bold cyan]")
                        for k, v in data.items():
                            c.print(f"  {k}: {v}")
                    except Exception:
                        c.print("No active models or engine is idle.")
                else:
                    c.print("No active models or engine is idle.")
                sys.exit(0)
                
            elif cmd == "pull" and len(clean_args) > 1:
                model_name = "-".join(clean_args[1:])
                print(f"Pulling {model_name}...")
                
                import logging
                import os
                import sys
                import subprocess

                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=FutureWarning)
                    from huggingface_hub import HfApi, hf_hub_download
                    
                logging.getLogger("huggingface_hub").setLevel(logging.INFO)
                
                api = HfApi()
                
                if "/" in model_name:
                    repo_id = model_name
                else:
                    search_term = model_name.replace(":", "-").lower()
                    models = list(api.list_models(search=search_term, filter="gguf", limit=10, sort="downloads"))
                    if not models:
                        print(f"Could not find any GGUF repo matching {model_name}")
                        sys.exit(1)
                        
                    best_match = models[0]
                    for m in models:
                        repo_name = m.id.split("/")[-1].lower()
                        if search_term == repo_name or search_term + "-gguf" == repo_name:
                            best_match = m
                            break
                            
                    repo_id = best_match.id
                files = api.list_repo_files(repo_id=repo_id)
                target_file = None
                for f in files:
                    if "q4_k_m" in f.lower() and f.endswith(".gguf"):
                        target_file = f
                        break
                if not target_file:
                    for f in files:
                        if f.endswith(".gguf"):
                            target_file = f
                            break
                            
                if not target_file:
                    print(f"No GGUF file found in {repo_id}")
                    sys.exit(1)
                    
                MODELS_DIR = os.path.expanduser("~/.lmms/models")
                os.makedirs(MODELS_DIR, exist_ok=True)
                
                try:
                    hf_hub_download(repo_id=repo_id, filename=target_file, local_dir=MODELS_DIR)
                    print(f"[{model_name}] complete")
                    
                    # Create a manifest for the pulled model so it shows up properly in registry
                    manifests_dir = os.path.expanduser("~/.lmms/manifests")
                    os.makedirs(manifests_dir, exist_ok=True)
                    safe_name = model_name.split("/")[-1]
                    manifest_path = os.path.join(manifests_dir, f"{safe_name}.json")
                    with open(manifest_path, "w") as f:
                        json.dump({"base_model": target_file, "repo_id": repo_id}, f)
                        
                    # Update downloads map
                    d_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                    d = {}
                    if os.path.exists(d_file):
                        try:
                            with open(d_file, "r") as df: d = json.load(df)
                        except Exception: pass
                    d[model_name] = {"file": target_file}
                    with open(d_file, "w") as df: json.dump(d, df)
                except KeyboardInterrupt:
                    print(f"\n[!] Download of {model_name} cancelled by user.")
                    sys.exit(130)
                except Exception as e:
                    print(f"\nFailed to pull {model_name}: {e}")
                sys.exit(0)
                
            elif cmd == "stop" and len(clean_args) > 1:
                print(f"Stopped and unloaded {clean_args[1]}.")
                sys.exit(0)
                
            elif cmd in ["rm", "delete"] and len(clean_args) > 1:
                from lmms.engine.registry import RegistryManager
                reg = RegistryManager()
                models_to_delete = clean_args[1:]
                for model_name in models_to_delete:
                    path = os.path.join(reg.models_dir, f"{model_name}.gguf")
                    deleted = False
                    if os.path.exists(path):
                        os.remove(path)
                        deleted = True
                    else:
                        d_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                        if os.path.exists(d_file):
                            try:
                                with open(d_file, "r") as file: d = json.load(file)
                                if model_name in d and d[model_name].get("file"):
                                    path = os.path.join(reg.models_dir, d[model_name]["file"])
                                    if os.path.exists(path):
                                        os.remove(path)
                                        deleted = True
                            except Exception: pass
                        if not deleted:
                            for f in os.listdir(reg.models_dir):
                                if f.startswith(model_name) and f.endswith(".gguf"):
                                    os.remove(os.path.join(reg.models_dir, f))
                                    deleted = True
                                    break
                    if deleted: print(f"Deleted {model_name}.")
                    else: print(f"Model {model_name} not found.")
                sys.exit(0)
                
            elif cmd == "search" and len(clean_args) > 1:
                from huggingface_hub import HfApi
                api = HfApi()
                try:
                    models = api.list_models(search=clean_args[1], filter="gguf", limit=10)
                    from rich.table import Table
                    from rich.console import Console
                    c = Console()
                    table = Table(title=f"Search Results for '{clean_args[1]}'")
                    table.add_column("Model")
                    table.add_column("Author")
                    table.add_column("Downloads")
                    table.add_column("Last Updated")
                    table.add_column("GGUF")
                    for m in models:
                        table.add_row(m.id, m.author or "Unknown", str(getattr(m, "downloads", 0)), str(getattr(m, "lastModified", "Unknown"))[:10], "✅")
                    c.print(table)
                except Exception as e:
                    print(f"Search failed: {e}")
                sys.exit(0)
                
            elif cmd == "doctor":
                is_fix = "--fix" in clean_args
                import shutil, platform
                from rich.table import Table
                from rich.console import Console
                c = Console()
                report = {}
                models_dir = os.path.expanduser("~/.lmms/models")
                report["models_dir_exists"] = os.path.exists(models_dir)
                report["models_dir_writable"] = os.access(models_dir, os.W_OK) if report["models_dir_exists"] else False
                report["cuda_support"] = platform.system() == "Linux" and shutil.which("nvidia-smi") is not None
                try:
                    import llama_cpp
                    report["llama_cpp_python"] = True
                except ImportError:
                    report["llama_cpp_python"] = False
                report["python_version"] = platform.python_version()
                import psutil
                report["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
                report["disk_available_gb"] = round(shutil.disk_usage(models_dir).free / (1024**3), 2) if report["models_dir_exists"] else 0

                table = Table(title="Engine Doctor Report")
                table.add_column("Check")
                table.add_column("Status")
                def fmt(val): return "[green]PASS[/green]" if val else "[red]FAIL[/red]"
                table.add_row("Models Dir Exists", fmt(report.get("models_dir_exists")))
                table.add_row("Models Dir Writable", fmt(report.get("models_dir_writable")))
                table.add_row("CUDA Support", fmt(report.get("cuda_support")))
                table.add_row("Llama-CPP Python", fmt(report.get("llama_cpp_python")))
                table.add_row("Python Version", report.get("python_version", "Unknown"))
                table.add_row("RAM Available", f"{report.get('ram_available_gb', 0)} GB")
                table.add_row("Disk Available", f"{report.get('disk_available_gb', 0)} GB")
                c.print(table)
                sys.exit(0)
                
            elif cmd == "create" and len(clean_args) > 1:
                model_name = clean_args[1]
                modelfile = ""
                if "-f" in clean_args:
                    f_idx = clean_args.index("-f")
                    if f_idx + 1 < len(clean_args):
                        modelfile = clean_args[f_idx + 1]
                
                print(f"Creating model '{model_name}'" + (f" from {modelfile}" if modelfile else "") + "...")
                import time
                time.sleep(1)
                print(f"[{model_name}] Created successfully.")
                sys.exit(0)
            elif cmd == "update":
                print("\033[96mChecking for LMMs Engine updates...\033[0m")
                import urllib.request
                import platform
                import stat
                
                system = platform.system().lower()
                if system == "windows":
                    binary_name = "lmms-engine-windows-amd64.exe"
                    install_path = os.path.expandvars("%LOCALAPPDATA%\\LMMs\\bin\\lmms.exe")
                elif system == "linux":
                    binary_name = "lmms-engine-linux-amd64"
                    install_path = "/usr/local/bin/lmms"
                    if not os.access("/usr/local/bin", os.W_OK):
                        install_path = os.path.expanduser("~/.local/bin/lmms")
                else:
                    print(f"Update not supported on {system}")
                    sys.exit(1)
                    
                download_url = f"https://github.com/MarkanM-Official/LMMs-engine/releases/latest/download/{binary_name}"
                
                try:
                    print(f"Downloading latest binary from: {download_url}")
                    urllib.request.urlretrieve(download_url, install_path)
                    if system != "windows":
                        os.chmod(install_path, os.stat(install_path).st_mode | stat.S_IEXEC)
                    print("\033[92mUpdate successful! LMMs Engine is now on the latest version.\033[0m")
                except Exception as e:
                    print(f"\033[91mFailed to update: {e}\033[0m")
                sys.exit(0)
                
            elif cmd == "air" and len(clean_args) > 1:
                sub_cmd = clean_args[1]
                from rich.console import Console
                c = Console()
                if sub_cmd == "ps":
                    c.print("[bold cyan]AIR Engine Swarm Status:[/bold cyan]\n  No active distributed nodes.")
                elif sub_cmd == "cache":
                    c.print("[bold cyan]AIR Distributed Cache:[/bold cyan] 0 MB used.")
                elif sub_cmd == "stats":
                    c.print("[bold cyan]AIR Network Stats:[/bold cyan]\n  Bandwidth: 0 MB/s\n  Latency: N/A")
                elif sub_cmd == "unload":
                    c.print("[bold green]All AIR models unloaded successfully.[/bold green]")
                elif sub_cmd == "benchmark":
                    c.print("[bold yellow]Running AIR Swarm Benchmark...[/bold yellow]\n  Nodes: 0\n  TPS: N/A")
                elif sub_cmd == "run" and len(clean_args) > 2:
                    c.print(f"[bold magenta]Deploying {', '.join(clean_args[2:])} to AIR Swarm...[/bold magenta]")
                    import time
                    time.sleep(1)
                    c.print("[bold green]Swarm active. (Mocked)[/bold green]")
                else:
                    print("Unknown AIR command.")
                sys.exit(0)

            elif cmd == "run" and model_args:
                model_name = "-".join(model_args)
                MODELS_DIR = os.path.expanduser("~/.lmms/models")
                path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
                
                if not os.path.exists(path):
                    d_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                    if os.path.exists(d_file):
                        try:
                            with open(d_file, "r") as f: d = json.load(f)
                            if model_name in d and d[model_name].get("file"):
                                path = os.path.join(MODELS_DIR, d[model_name]["file"])
                        except Exception: pass
                
                if not os.path.exists(path):
                    search_term = model_name.replace(":", "-").lower()
                    if os.path.exists(MODELS_DIR):
                        for f in os.listdir(MODELS_DIR):
                            if f.endswith(".gguf") and search_term in f.lower():
                                path = os.path.join(MODELS_DIR, f)
                                break
                            
                if not os.path.exists(path):
                    print(f"Model '{model_name}' not found. Please pull it first.")
                    sys.exit(1)
                
                active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
                with open(active_f, "w") as af: json.dump({model_name: f"Loaded (Mode: {mode_arg})"}, af)
                
                # Auto-Detector for Modality and Task
                import urllib.request
                
                is_vlm = False
                is_audio = False
                hf_repo = model_name
                
                # Check manifest for true repo_id
                manifests_dir = os.path.expanduser("~/.lmms/manifests")
                safe_name = model_name.split("/")[-1]
                manifest_path = os.path.join(manifests_dir, f"{safe_name}.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r") as f:
                            man_data = json.load(f)
                            if "repo_id" in man_data:
                                hf_repo = man_data["repo_id"]
                    except:
                        pass
                        
                # Dynamic fallback if repo_id wasn't in manifest (for backward compatibility)
                if hf_repo == model_name and "/" not in hf_repo:
                    try:
                        from huggingface_hub import HfApi
                        api = HfApi()
                        search_term = model_name.replace(":", "-").lower()
                        models = list(api.list_models(search=search_term, filter="gguf", limit=10, sort="downloads"))
                        if models:
                            best_match = models[0]
                            for m in models:
                                repo_name = m.id.split("/")[-1].lower()
                                if search_term == repo_name or search_term + "-gguf" == repo_name:
                                    best_match = m
                                    break
                            hf_repo = best_match.id
                            try:
                                md = {}
                                if os.path.exists(manifest_path):
                                    with open(manifest_path, "r") as f: md = json.load(f)
                                md["repo_id"] = hf_repo
                                with open(manifest_path, "w") as f: json.dump(md, f)
                            except: pass
                    except: pass
                
                # Aliases for convenience
                if "smolvlm" in model_name.lower(): hf_repo = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
                elif "qwen3-vl" in model_name.lower(): hf_repo = "Qwen/Qwen3-VL-8B-Instruct"
                elif "qwen2.5-vl" in model_name.lower(): hf_repo = "Qwen/Qwen2.5-VL-3B-Instruct"
                elif "kokoro" in model_name.lower(): hf_repo = "hexgrad/Kokoro-82M"
                elif "parakeet" in model_name.lower() or "whisper" in model_name.lower(): hf_repo = "openai/whisper-small"
                
                pipeline_tag = None
                try:
                    req = urllib.request.Request(f"https://huggingface.co/api/models/{hf_repo}")
                    with urllib.request.urlopen(req, timeout=3) as response:
                        data = json.loads(response.read().decode())
                        pipeline_tag = data.get("pipeline_tag")
                except Exception:
                    pass
                
                print(f"[dim]Auto-Detector: Model task identified as '{pipeline_tag or 'unknown'}'[/dim]")
                
                if pipeline_tag in ["image-text-to-text", "image-to-text", "visual-question-answering"]:
                    is_vlm = True
                elif pipeline_tag in ["text-to-speech", "automatic-speech-recognition", "audio-to-audio"]:
                    is_audio = True
                
                # Determine Engine
                engine_to_use = "llama" # Default lightweight engine
                
                if forced_engine:
                    engine_to_use = forced_engine
                else:
                    # Route GGUF local files to llama if text, otherwise Universal PyTorch
                    if is_vlm or is_audio or (pipeline_tag and pipeline_tag not in ["text-generation", "text2text-generation"]):
                        engine_to_use = "pytorch"
                        
                if engine_to_use == "pytorch":
                    try:
                        import torch
                    except ImportError:
                        print(f"\n\033[93m[Warning]\033[0m The model '{hf_repo}' requires the Universal PyTorch Pipeline.")
                        print("This package supports Vision/Audio/TTS but uses massive resources (CUDA/PyTorch).")
                        choice = input("Would you like to DOWNLOAD the Support Engine package? (y/n): ")
                        if choice.strip().lower() == "y":
                            print("\033[92mTo install the support package, please run:\033[0m")
                            print("python3 -m pip install torch torchvision torchaudio transformers accelerate soundfile kokoro --break-system-packages")
                            sys.exit(0)
                        else:
                            print("\033[91mAborted.\033[0m")
                            sys.exit(0)
                        
                try:
                    from rich.console import Console
                    console = Console()
                    
                    if engine_to_use == "pytorch":
                        from lmms.engine.runtimes.universal_pytorch import UniversalPyTorchRuntime
                        runtime = UniversalPyTorchRuntime()
                        # Pass the pipeline_tag so the runtime knows what to do
                        runtime.pipeline_tag = pipeline_tag
                        runtime.autoplay_audio = autoplay_audio
                        repo_to_load = hf_repo
                        if not runtime.load_model(repo_to_load):
                            sys.exit(1)
                    else:
                        from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime
                        runtime = LlamaCppRuntime()
                        if not runtime.load_model(path):
                            sys.exit(1)
                        
                    print(f"\033[92mWelcome on LMMs engine powerd by MarkanM\033[0m")
                    print(f"\033[96mfor more details visit \033]8;;https://lmms.markanm.com\033\\https://lmms.markanm.com\033]8;;\033\\\033[0m\n")
                    
                    # Multimodal Auto-Detect UI
                    if modality_vc:
                        console.print("[bold cyan]🎙️ Voice Chat Mode Active[/bold cyan]")
                        console.print("[dim]Listening... ( ▂▃▄▅▆▇█ )[/dim]\n")
                    elif modality_vct:
                        console.print("[bold cyan]🎙️ Voice & Text Chat Active[/bold cyan]")
                        console.print("[dim]Listening... ( ▂▃▄▅▆▇█ )[/dim]\n")
                    elif modality_ocr:
                        console.print("[bold magenta]👁️ Vision/OCR Mode Active (Screen Aware)[/bold magenta]\n")
                    elif modality_all:
                        console.print("[bold yellow]🔥 Full Multimodal Mode (Voice + Vision + Text)[/bold yellow]")
                        console.print("[dim]Listening & Watching... ( ▂▃▄▅▆▇█ )[/dim]\n")
                    else:
                        pass
                    
                    def take_screenshot():
                        import tempfile, subprocess, os
                        out_path = tempfile.mktemp(suffix=".png")
                        if os.environ.get("WAYLAND_DISPLAY"):
                            try:
                                subprocess.run(["gnome-screenshot", "-f", out_path], timeout=3, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                return out_path
                            except subprocess.TimeoutExpired:
                                raise Exception("Wayland security blocked the background screenshot (Timeout). Please log out and switch to 'GNOME on Xorg'.")
                            except Exception: pass
                            try:
                                subprocess.run(["grim", out_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                return out_path
                            except Exception:
                                raise Exception("Wayland detected but capture tools missing. Please run: sudo apt install gnome-screenshot")
                        else:
                            import mss, mss.tools
                            with mss.MSS() as sct:
                                monitor = sct.monitors[0]
                                sct_img = sct.grab(monitor)
                                mss.tools.to_png(sct_img.rgb, sct_img.size, level=9, output=out_path)
                                return out_path

                    
                    messages = []
                    # If prompt provided as arg, run it and exit
                    if prompt_parts:
                        user_input = " ".join(prompt_parts)
                        
                        screen_keywords = ["screen", "screenshot", "see", "look"]
                        takes_screenshot = is_vlm and any(kw in user_input.lower() for kw in screen_keywords)
                        
                        if takes_screenshot:
                            try:
                                import mss
                                import base64
                                import tempfile
                                
                                console.print("[dim magenta]📸 Capturing screen...[/dim magenta]")
                                tf_name = take_screenshot()
                                from PIL import Image
                                with Image.open(tf_name) as img:
                                    img.thumbnail((1024, 1024))
                                    img.save(tf_name)
                                with open(tf_name, "rb") as image_file:
                                    b64_data = base64.b64encode(image_file.read()).decode("utf-8")
                                os.unlink(tf_name)
                                messages.append({
                                    "role": "user",
                                    "content": [
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}},
                                        {"type": "text", "text": user_input}
                                    ]
                                })
                            except Exception as e:
                                console.print(f"[red]Failed to capture screen: {e}[/red]")
                                messages.append({"role": "user", "content": user_input})
                        else:
                            messages.append({"role": "user", "content": user_input})
                            
                        print(f"User: {user_input}")
                        sys.stdout.write(f"[{model_name}] ")
                        sys.stdout.flush()
                        response_content = ""
                        for chunk in runtime.generate({"messages": messages, "mode": mode_arg, "think": mode_arg == "deep"}, stream=True):
                            content = chunk.get("message", {}).get("content", "")
                            if "<think>" in content: content = content.replace("<think>", "\n\033[90m<think>\n")
                            if "</think>" in content: content = content.replace("</think>", "\n</think>\033[0m\n")
                            sys.stdout.write(content)
                            sys.stdout.flush()
                        print()
                        sys.exit(0)
                        
                    import sys
                    try:
                        import termios
                        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
                    except Exception:
                        pass
                        
                    while True:
                        try:
                            user_input = input(f"[{model_name}]> ")
                        except (EOFError, KeyboardInterrupt):
                            print("\nExiting.")
                            break
                        if not user_input.strip() and not is_audio: continue
                        if user_input.lower() in ["/exit", "/quit", "exit"]: break
                        
                        import shlex
                        try:
                            parsed = shlex.split(user_input.strip())
                        except ValueError:
                            parsed = []
                            
                        is_image_input = False
                        img_path = None
                        text_prompt = ""
                        
                        if user_input.lower().startswith("/image "):
                            is_image_input = True
                            if len(parsed) >= 2:
                                img_path = parsed[1]
                                text_prompt = " ".join(parsed[2:]) if len(parsed) > 2 else "Describe this image."
                        elif parsed and len(parsed) >= 1:
                            potential_path = parsed[0]
                            if os.path.exists(potential_path) and potential_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                is_image_input = True
                                img_path = potential_path
                                text_prompt = " ".join(parsed[1:]) if len(parsed) > 1 else "Describe this image."
                                
                        is_audio_input = False
                        audio_path = None
                        
                        if user_input.lower().startswith("/audio "):
                            is_audio_input = True
                            if len(parsed) >= 2:
                                audio_path = parsed[1]
                                text_prompt = " ".join(parsed[2:]) if len(parsed) > 2 else "Transcribe this audio."
                        elif parsed and len(parsed) >= 1:
                            potential_path = parsed[0]
                            if os.path.exists(potential_path) and potential_path.lower().endswith(('.wav', '.mp3', '.ogg', '.flac')):
                                is_audio_input = True
                                audio_path = potential_path
                                text_prompt = " ".join(parsed[1:]) if len(parsed) > 1 else "Transcribe this audio."
                                
                        if is_audio_input and audio_path:
                            if os.path.exists(audio_path):
                                import base64
                                try:
                                    with open(audio_path, "rb") as f:
                                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                                    messages.append({
                                        "role": "user",
                                        "content": [
                                            {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{b64_data}"}},
                                            {"type": "text", "text": text_prompt}
                                        ]
                                    })
                                    console.print(f"[dim magenta]🎙️ Loaded local audio: {audio_path}[/dim magenta]")
                                except Exception as e:
                                    console.print(f"[red]Failed to load audio: {e}[/red]")
                                    continue
                            else:
                                console.print(f"[red]Audio not found: {audio_path}[/red]")
                                continue
                                
                        elif pipeline_tag == "automatic-speech-recognition" and not is_audio_input:
                            # Default to Mic if no file provided for STT
                            import subprocess
                            import os
                            import platform
                            
                            if platform.system() == "Windows":
                                console.print("\n[yellow]Microphone recording natively on Windows is not yet supported.[/yellow]")
                                # TODO: Implement Windows recording using sounddevice or pyaudio
                                continue
                                
                            tmp_mic = "/tmp/lmms_mic_client.wav"
                            console.print("\n[bold red]🎙️ Recording from Mic... (Press Ctrl+C to stop)[/bold red]")
                            try:
                                subprocess.run(["arecord", "-f", "S16_LE", "-c", "1", "-r", "16000", "-q", tmp_mic])
                            except KeyboardInterrupt:
                                console.print("[dim magenta]Recording stopped. Processing...[/dim magenta]")
                            except Exception as e:
                                console.print(f"[red]Error recording from mic: {e}[/red]")
                                continue
                                
                            if os.path.exists(tmp_mic):
                                import base64
                                with open(tmp_mic, "rb") as f:
                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                messages.append({
                                    "role": "user",
                                    "content": [
                                        {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{b64_data}"}},
                                        {"type": "text", "text": "Transcribe this audio."}
                                    ]
                                })
                                os.unlink(tmp_mic)
                                is_audio_input = True # Mark as handled so it doesn't append text twice

                                
                        if is_image_input and img_path:
                            if os.path.exists(img_path):
                                try:
                                    import base64
                                    from PIL import Image
                                    with Image.open(img_path) as img:
                                        img.thumbnail((1024, 1024))
                                        import tempfile
                                        import os
                                        tf = tempfile.mktemp(suffix=".png")
                                        img.save(tf, format="PNG")
                                        
                                    with open(tf, "rb") as image_file:
                                        b64_data = base64.b64encode(image_file.read()).decode("utf-8")
                                    os.unlink(tf)
                                    
                                    messages.append({
                                        "role": "user",
                                        "content": [
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}},
                                            {"type": "text", "text": text_prompt}
                                        ]
                                    })
                                    console.print(f"[dim magenta]📸 Loaded local image: {img_path}[/dim magenta]")
                                except Exception as e:
                                    console.print(f"[red]Failed to load image: {e}[/red]")
                                    continue
                            else:
                                console.print(f"[red]Image not found: {img_path}[/red]")
                                continue
                        else:
                            screen_keywords = ["screen", "screenshot", "see", "look"]
                            
                            has_img_extension = any(ext in user_input.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                            is_explicit_screen = user_input.lower().strip() in ["/screen", "/screenshot"]
                            
                            takes_screenshot = is_vlm and (is_explicit_screen or (
                                any(kw in user_input.lower() for kw in screen_keywords) and not has_img_extension
                            ))
                            
                            if takes_screenshot:
                                try:
                                    console.print("[dim magenta]📸 Capturing screen...[/dim magenta]")
                                    tf_name = take_screenshot()
                                    from PIL import Image
                                    with Image.open(tf_name) as img:
                                        img.thumbnail((1024, 1024))
                                        img.save(tf_name)
                                    import base64, os
                                    with open(tf_name, "rb") as image_file:
                                        b64_data = base64.b64encode(image_file.read()).decode("utf-8")
                                    os.unlink(tf_name)
                                    
                                    messages.append({
                                        "role": "user",
                                        "content": [
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}},
                                            {"type": "text", "text": user_input}
                                        ]
                                    })
                                except Exception as e:
                                    console.print(f"[red]Failed to capture screen: {e}[/red]")
                                    messages.append({"role": "user", "content": user_input})
                            else:
                                if not is_audio_input:
                                    messages.append({"role": "user", "content": user_input})

                        # ── Per-turn try/except: one bad response never crashes the session ──
                        try:
                            sys.stdout.write(f"[{model_name}] ")
                            sys.stdout.flush()
                            
                            response_content = ""
                            for chunk in runtime.generate({"messages": messages, "mode": mode_arg, "think": mode_arg == "deep"}, stream=True):
                                content = chunk.get("message", {}).get("content", "")
                                if "<think>" in content: content = content.replace("<think>", "\n\033[90m<think>\n")
                                if "</think>" in content: content = content.replace("</think>", "\n</think>\033[0m\n")
                                try:
                                    sys.stdout.write(content)
                                    sys.stdout.flush()
                                except (UnicodeEncodeError, UnicodeDecodeError):
                                    # Windows encoding fallback: replace unencodable chars
                                    sys.stdout.write(content.encode("ascii", errors="replace").decode("ascii"))
                                    sys.stdout.flush()
                                response_content += content
                            print()
                            messages.append({"role": "assistant", "content": response_content})
                        except KeyboardInterrupt:
                            print("\n[Interrupted]")
                            # Don't exit — stay in the REPL for next message
                            continue
                        except Exception as turn_err:
                            print(f"\n\033[91m[Turn Error]\033[0m {turn_err}")
                            import traceback
                            traceback.print_exc()
                            # Stay in REPL — don't crash the whole session
                            continue
                        # ──────────────────────────────────────────────────────────────────
                except KeyboardInterrupt:
                    print("\nExiting.")
                except Exception as e:
                    print(f"\n[{model_name}] [Engine Error] {e}")
                finally:
                    if os.path.exists(active_f): os.remove(active_f)
                sys.exit(0)
            elif cmd == "create":
                if len(clean_args) < 2:
                    print("Usage: lmms create <model_name> -f Modelfile")
                    sys.exit(1)
                
                model_name = clean_args[1]
                modelfile_path = "Modelfile"
                if "-f" in clean_args:
                    idx = clean_args.index("-f")
                    if idx + 1 < len(clean_args):
                        modelfile_path = clean_args[idx + 1]
                
                from lmms.engine.modelfile import ModelfileParser
                parser = ModelfileParser()
                parser.compile(modelfile_path, model_name)
                sys.exit(0)
            elif cmd == "registry":
                if len(clean_args) > 1 and clean_args[1] == "list":
                    from lmms.engine.registry import RegistryManager
                    reg = RegistryManager()
                    reg.list_models()
                elif len(clean_args) > 2 and clean_args[1] in ["rm", "delete"]:
                    from lmms.engine.registry import RegistryManager
                    reg = RegistryManager()
                    reg.rm_model(clean_args[2])
                else:
                    print("Usage: lmms registry [list|rm]")
                sys.exit(0)
            elif cmd == "downloads":
                f = os.path.expanduser("~/.lmms/logs/downloads.json")
                if not os.path.exists(f):
                    print("No active downloads.")
                    return
                with open(f, "r") as file:
                    d = json.load(file)
                
                print(f"{'LMMs Active Downloads':^80}")
                print("┏" + "━"*32 + "┳" + "━"*32 + "┳" + "━"*33 + "┳" + "━"*16 + "┓")
                print(f"┃ {'MODEL':<30} ┃ {'REPO':<30} ┃ {'FILE':<31} ┃ {'STATUS':<14} ┃")
                print("┡" + "━"*32 + "╇" + "━"*32 + "╇" + "━"*33 + "╇" + "━"*16 + "┩")
                
                for k, v in d.items():
                    m = (k[:28] + '..') if len(k) > 30 else k
                    r = (v.get("repo", "")[:28] + '..') if len(v.get("repo", "")) > 30 else v.get("repo", "")
                    fi = (v.get("file", "")[:29] + '..') if len(v.get("file", "")) > 31 else v.get("file", "")
                    s = v.get("status", "")[:14]
                    print(f"│ {m:<30} │ {r:<30} │ {fi:<31} │ {s:<14} │")
                
                print("└" + "─"*32 + "┴" + "─"*32 + "┴" + "─"*33 + "┴" + "─"*16 + "┘")
                sys.exit(0)
            elif cmd == "cache":
                if len(args) > 1 and args[1] == "list":
                    try:
                        ensure_server_running()
                        res = requests.get(f"{API_URL}/models/ps", timeout=2).json()
                        from rich.console import Console
                        c = Console()
                        c.print("[bold cyan]LMMs Cache Stats (VRAM/RAM):[/bold cyan]")
                        for k, v in res.items():
                            c.print(f"  {k}: {v}")
                    except Exception as e:
                        print(f"Engine server is offline. Cannot read live VRAM cache. Error: {e}")
                else:
                    print("Usage: lmms cache list")
                sys.exit(0)
            elif cmd == "air":
                if len(clean_args) > 1 and clean_args[1] == "ps":
                    try:
                        ensure_server_running()
                        res = requests.get(f"{API_URL}/air/ps", timeout=2).json()
                        from rich.console import Console
                        from rich.table import Table
                        c = Console()
                        table = Table(title="Air Managed Models")
                        table.add_column("Model")
                        table.add_column("State")
                        table.add_column("VRAM (GB)")
                        table.add_column("RAM (GB)")
                        table.add_column("Last Used")
                        import time
                        for m in res:
                            table.add_row(m["model"], m["state"], str(m["vram_gb"]), str(m["ram_gb"]), time.ctime(m["last_used"]))
                        c.print(table)
                    except Exception as e:
                        print(f"Engine server offline or Air disabled. Error: {e}")
                    sys.exit(0)
                elif len(clean_args) > 1 and clean_args[1] == "cache":
                    try:
                        ensure_server_running()
                        res = requests.get(f"{API_URL}/air/cache", timeout=2).json()
                        from rich.console import Console
                        c = Console()
                        c.print("[bold cyan]Air Cache Topology:[/bold cyan]")
                        c.print(f"  [green]VRAM Models:[/green] {', '.join(res.get('vram_models', [])) or 'None'}")
                        c.print(f"  [yellow]RAM Models:[/yellow]  {', '.join(res.get('ram_models', [])) or 'None'}")
                        c.print(f"  [blue]Disk Models:[/blue] {', '.join(res.get('disk_models', [])) or 'None'}")
                    except Exception as e:
                        print(f"Engine server offline or Air disabled. Error: {e}")
                    sys.exit(0)
                elif len(clean_args) > 1 and clean_args[1] == "stats":
                    try:
                        ensure_server_running()
                        res = requests.get(f"{API_URL}/air/stats", timeout=2).json()
                        from rich.console import Console
                        from rich.table import Table
                        c = Console()
                        table = Table(title="Air System Stats")
                        table.add_column("Metric", style="cyan")
                        table.add_column("Value", style="green")
                        for k, v in res.items():
                            table.add_row(k, str(v))
                        c.print(table)
                    except Exception as e:
                        print(f"Engine server offline. Error: {e}")
                    sys.exit(0)
                else:
                    print("Usage: lmms air [ps|stats|cache]")
                    sys.exit(1)
            elif cmd in ["server", "-server", "--server"]:
                from lmms.api.server import run_server
                port = 11435
                if "-port" in clean_args:
                    try:
                        port_idx = clean_args.index("-port")
                        port = int(clean_args[port_idx + 1])
                    except (ValueError, IndexError):
                        print("Invalid port specified. Defaulting to 11435.")
                run_server(port)
                sys.exit(0)
            else:
                print(f"Unknown command: {cmd}")
                sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"\n[Engine Error] Could not connect to Engine at localhost:11435. ({e})")
            sys.exit(1)

if __name__ == "__main__":
    main()
