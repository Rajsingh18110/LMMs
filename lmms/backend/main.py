import os
import sys
import threading
import requests
import secrets
import subprocess
import asyncio
import nest_asyncio
import websockets
import json
import re
from datetime import datetime
nest_asyncio.apply()
from lmms.backend.memory.persona import get_persona, auto_extract_persona
from lmms.backend.tools.search import web_search
from lmms.backend.tools.browser import BrowserTool
from lmms.backend.tools.files import FileTool
from lmms.backend.tools.terminal import TerminalTool
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from lmms.backend.memory.embeddings.faiss_provider import VectorDB
from fastapi import FastAPI
import uvicorn


app = FastAPI(title="LMMs Backend OS")

ENGINE_URL = "http://localhost:11435"

def check_engine_health():
    try:
        resp = requests.get(f"{ENGINE_URL}/webhook", timeout=5)
        return resp.status_code == 200
    except:
        return False

@app.get("/v1/health")
def health_check():
    return {"status": "Backend OS is running", "engine_connected": check_engine_health()}


def auto_start_engine():
    if check_engine_health():
        return True
        
    internal_token = os.environ.get("LMMS_INTERNAL_TOKEN")
    if not internal_token:
        internal_token = secrets.token_hex(16)
        os.environ["LMMS_INTERNAL_TOKEN"] = internal_token
        
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        # Suppress PyTorch and Engine logs from spilling into the CLI
        subprocess.Popen(["python3", "-m", "lmms.engine.server", "--internal-start"], 
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import time
        for _ in range(15):
            if check_engine_health():
                break
            time.sleep(0.5)
        return True
    except Exception as e:
        return False

async def ipc_handshake():
    token = os.environ.get("LMMS_INTERNAL_TOKEN")
    if not token:
        return False
        
    try:
        uri = "ws://localhost:11435/v1/internal/ws"
        async with websockets.connect(uri) as websocket:
            await websocket.send(token)
            response = await websocket.recv()
            if response == "HANDSHAKE_SUCCESS":
                print("[IPC] Successfully merged with Engine!")
                return True
            else:
                print(f"[IPC] Handshake failed: {response}")
                return False
    except Exception as e:
        # Engine might not have the WS endpoint up yet or at all
        pass
    return False

def start_api():
    print("Starting Backend OS API on port 11436...")
    uvicorn.run(app, host="0.0.0.0", port=11436, log_level="warning")



def run_cli():
    console = Console()
    console.clear()
    
    engine_started = auto_start_engine()
    if engine_started and os.environ.get("LMMS_INTERNAL_TOKEN"):
        asyncio.run(ipc_handshake())
        
    status = "[bold green]ONLINE[/bold green]" if check_engine_health() else "[bold red]OFFLINE[/bold red]"
    
    # State tracking
    current_workspace = "None"
    last_ws_file = os.path.expanduser("~/.lmms/config/last_workspace.txt")
    if os.path.exists(last_ws_file):
        try:
            with open(last_ws_file, "r") as f:
                saved_ws = f.read().strip()
                if os.path.exists(saved_ws):
                    current_workspace = saved_ws
        except: pass
        
    current_model = "None"
    
    # Auto-detect current model
    if check_engine_health():
        try:
            r = requests.get(f"{ENGINE_URL}/v1/models/ps", timeout=2)
            stats = r.json()
            if stats.get("models"):
                current_model = list(stats["models"].keys())[0]
            else:
                config_path = os.path.expanduser("~/.lmms/config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r") as f:
                            cfg = json.load(f)
                            if cfg.get("default_model"):
                                current_model = cfg["default_model"]
                    except: pass
                
                if current_model == "None":
                    r_list = requests.get(f"{ENGINE_URL}/v1/models/list", timeout=2)
                    models_list = r_list.json().get("models", [])
                    if models_list:
                        # Ensure default_model is loaded instead of randomly picking one
                        current_model = models_list[0]["name"]
        except Exception:
            pass

    current_pair = "None"
    current_mode = "/fast"
    current_permission_level = "medium"
    show_thoughts = False
    
    # Init config files
    CONFIG_DIR = os.path.expanduser("~/.lmms/config")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    WORKSPACES_FILE = os.path.join(CONFIG_DIR, "workspaces.json")
    PAIRS_FILE = os.path.join(CONFIG_DIR, "pairs.json")
    if not os.path.exists(WORKSPACES_FILE):
        with open(WORKSPACES_FILE, "w") as f: json.dump({}, f)
    if not os.path.exists(PAIRS_FILE):
        with open(PAIRS_FILE, "w") as f: json.dump({}, f)
        
    # Tools Initialization
    browser_tool = BrowserTool()
    file_tool = FileTool()
    terminal_tool = TerminalTool()
    
    def check_permission(tool_name: str, kwargs: dict, current_workspace: str, current_perm_level: str) -> bool:
        # 1. Global Path Denylist (Applies to all tools, all permission levels)
        protected_paths = ["/.ssh/", "/etc/", "/boot/", "/.aws/", "/.config/gh/", "/.config/google-chrome/", "/.mozilla/", "/.lmms/config/"]
        
        target_path = ""
        if tool_name in ["files.read", "files.write"]:
            target_path = kwargs.get("path", "")
        elif tool_name == "terminal.run":
            target_path = kwargs.get("command", "")
            
        if target_path:
            # Add trailing slash for exact boundary matching
            tp_check = target_path if target_path.endswith("/") else target_path + "/"
            for p_path in protected_paths:
                if p_path in tp_check:
                    return Prompt.ask(f"[bold red]AI wants to access PROTECTED path ({p_path}) in {tool_name}. Allow? (y/n)[/bold red]").lower() == "y"
                    
        # 2. Terminal specific logic (Git & Destructive Commands)
        if tool_name == "terminal.run":
            cmd = kwargs.get("command", "").strip()
            
            # Git logic
            if cmd.startswith("git"):
                if cmd.startswith("git status") or cmd.startswith("git diff") or cmd.startswith("git log"):
                    return True # Auto-allow read-only git
                if cmd.startswith("git push"):
                    if re.search(r'(--force\b|-f\b)', cmd) or re.search(r'\b(main|master)\b', cmd):
                        return Prompt.ask(f"[bold red]DANGER: AI wants to FORCE PUSH or push to MAIN: {cmd}. Allow? (y/n)[/bold red]").lower() == "y"
                    return Prompt.ask(f"[bold yellow]AI wants to GIT PUSH: {cmd}. Allow? (y/n)[/bold yellow]").lower() == "y"
                if current_perm_level in ["medium", "full"] and (cmd.startswith("git add") or cmd.startswith("git commit")):
                    return True
            
            # Destructive denylist
            denylist = ["rm -rf", "mkfs", "dd", ":(){:|:&};:", "fork", "wget -O-", "curl | bash"]
            for bad in denylist:
                if bad in cmd:
                    return Prompt.ask(f"[bold red]AI wants to run DESTRUCTIVE command: {cmd}. Allow? (y/n)[/bold red]").lower() == "y"

        # 3. Standard Permission Levels
        if current_perm_level == "full":
            return True
            
        if current_perm_level == "low":
            if tool_name in ["web_search", "browser.open_url", "files.read"]:
                return True
            return Prompt.ask(f"[bold yellow]AI wants to run {tool_name} with {kwargs}. Allow? (y/n)[/bold yellow]").lower() == "y"
            
        if current_perm_level == "medium":
            if tool_name in ["web_search", "browser.open_url", "files.read"]:
                return True
            if tool_name == "files.write":
                # Only allow if inside current workspace
                path = kwargs.get("path", "")
                if current_workspace != "None" and current_workspace in os.path.abspath(path):
                    return True
                return Prompt.ask(f"[bold yellow]AI wants to write to {path} outside workspace. Allow? (y/n)[/bold yellow]").lower() == "y"
            if tool_name == "terminal.run":
                cmd = kwargs.get("command", "")
                safelist = ["ls", "cat", "curl", "pwd", "echo", "tree"]
                if any(cmd.strip().startswith(s) for s in safelist):
                    return True
                return Prompt.ask(f"[bold yellow]AI wants to run unverified command: {cmd}. Allow? (y/n)[/bold yellow]").lower() == "y"
            if tool_name in ["browser.click_element", "browser.fill_form"]:
                return Prompt.ask(f"[bold red]AI wants to modify DOM state: {tool_name} {kwargs}. Allow? (y/n)[/bold red]").lower() == "y"
                
        return Prompt.ask(f"[bold yellow]AI wants to run {tool_name} with {kwargs}. Allow? (y/n)[/bold yellow]").lower() == "y"

    import uuid
    import base64
    import re
    from rich._spinners import SPINNERS
    SPINNERS["lmms_wave"] = {
        "interval": 120,
        "frames": [
            ".  ", "·  ", "'  ", "·  ", ".  ",
            " . ", " · ", " ' ", " · ", " . ",
            "  .", "  ·", "  '", "  ·", "  .",
            " ◜ ", " ◝ ", " ◞ ", " ◟ ", " ◯ ",
            "  .", "  ·", "  '", "  ·", "  .",
            " . ", " · ", " ' ", " · ", " . ",
            ".  ", "·  ", "'  ", "·  ", ".  "
        ]
    }
    
    CHATS_DIR = os.path.expanduser("~/.lmms/chats")
    os.makedirs(CHATS_DIR, exist_ok=True)
    
    current_chat_id = str(uuid.uuid4())
    current_chat_name = "Untitled"
    chat_history = []
    
    def print_banner():
        console.print("[bold cyan]" + "="*50 + "[/bold cyan]")
        console.print("[bold cyan]       ██╗     ███╗   ███╗███╗   ███╗███████╗[/bold cyan]")
        console.print("[bold cyan]       ██║     ████╗ ████║████╗ ████║██╔════╝[/bold cyan]")
        console.print("[bold cyan]       ██║     ██╔████╔██║██╔████╔██║███████╗[/bold cyan]")
        console.print("[bold cyan]       ██║     ██║╚██╔╝██║██║╚██╔╝██║╚════██║[/bold cyan]")
        console.print("[bold cyan]       ███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║███████║[/bold cyan]")
        console.print("[bold cyan]       ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝[/bold cyan]")
        console.print("[bold cyan]" + "="*50 + "[/bold cyan]")
        console.print("[bold blue]      Powered by MarkanM | [link=https://lmms.markanm.com]lmms.markanm.com[/link][/bold blue]")
        console.print("[bold cyan]" + "="*50 + "[/bold cyan]")
        console.print(f" ⚙️  Engine Status : {status}")
        console.print(f" 📁 Workspace     : [bold yellow]{current_workspace}[/bold yellow]")
        console.print(f" 🧠 Active Model  : [bold green]{current_model}[/bold green]")
        console.print(f" 🤝 Active Pair   : [bold magenta]{current_pair}[/bold magenta]")
        console.print(f" ⚡ AI Mode       : [bold blue]{current_mode}[/bold blue]")
        console.print(f" 🛡️  Permission    : [bold cyan]{current_permission_level}[/bold cyan]")
        console.print("[dim]Type 'exit' to quit. Type '/cl' for the full command list.[/dim]\n")

    def count_tokens(text: str, model_name: str) -> int:
        try:
            r = requests.post(f"{ENGINE_URL}/v1/tokenize", json={"model_name": model_name, "text": text}, timeout=2)
            if r.status_code == 200:
                return r.json().get("token_count", len(text) // 3)
        except: pass
        return len(text) // 3

    def get_context_budget(model_name: str):
        try:
            r = requests.get(f"{ENGINE_URL}/v1/model/context", params={"model_name": model_name}, timeout=2)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    n_ctx = data.get("context_length", 8192)
                    reserve = int(n_ctx * 0.18)
                    return n_ctx, reserve, n_ctx - reserve
        except: pass
        return 8192, int(8192 * 0.18), int(8192 * 0.82)

    print_banner()
    
    while True:
        try:
            cmd = prompt(HTML('<ansimagenta>user:</ansimagenta> ')).strip()

            # --- Audio & Mic Logic ---
            if not cmd:
                console.print("[bold red]🎙️  Recording from Mic... Press ENTER to stop.[/bold red]")
                import speech_recognition as sr
                # Start arecord in background
                p = subprocess.Popen(["arecord", "-f", "cd", "-t", "wav", "-q", "/tmp/lmms_mic.wav"])
                try:
                    input() # Wait for user to press Enter again
                except EOFError:
                    pass
                p.terminate()
                p.wait()
                console.print("[dim]Transcribing audio...[/dim]")
                r = sr.Recognizer()
                try:
                    with sr.AudioFile("/tmp/lmms_mic.wav") as source:
                        audio_data = r.record(source)
                    cmd = r.recognize_google(audio_data)
                    console.print(f"[bold cyan]Transcribed:[/bold cyan] {cmd}")
                except Exception as e:
                    console.print(f"[red]Could not understand audio: {e}[/red]")
                    continue
            elif cmd.strip("'\"").endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a")):
                file_path = cmd.strip("'\"")
                import speech_recognition as sr
                if os.path.exists(file_path):
                    console.print(f"[dim]Transcribing audio file: {file_path}...[/dim]")
                    r = sr.Recognizer()
                    try:
                        with sr.AudioFile(file_path) as source:
                            audio_data = r.record(source)
                        cmd = r.recognize_google(audio_data)
                        console.print(f"[bold cyan]Transcribed:[/bold cyan] {cmd}")
                    except Exception as e:
                        console.print(f"[red]Could not transcribe audio (ensure it's a valid WAV/FLAC/AIFF): {e}[/red]")
                        continue
            # --------------------------

            if not cmd:
                continue
                
            if cmd.startswith("lmms "):
                cmd = cmd[5:].strip()

            parts = cmd.split()
            base_cmd = parts[0]

            if cmd in ["exit", "quit", "clear"]:
                if cmd == "clear":
                    console.clear()
                    print_banner()
                    continue
                break
                
            elif base_cmd == "/thinking":
                show_thoughts = not show_thoughts
                state_str = "ENABLED" if show_thoughts else "DISABLED"
                console.print(f"[bold green]Thought process visibility is now {state_str}.[/bold green]")

            elif base_cmd == "/cl":
                console.print("\n[bold yellow]=== LMMs Complete Command List ===[/bold yellow]")
                console.print("""
[bold cyan]1) Installer / Builder[/bold cyan]
lmms-builder detect | compatibility | doctor | benchmark | install
[bold cyan]2) Launcher / Modes[/bold cyan]
lmms set --gui | --cli | --engine
lmms -g | -c | -e
[bold cyan]3) Model Management[/bold cyan]
lmms pull <model> | run <model> | stop <model> | ps | list | info <model> | rm <model> | search <model> | benchmark <model> | doctor [--fix]
[bold cyan]4) Air Engine[/bold cyan]
lmms -air run <model> | lmms --air run <m1> <m2>
lmms air ps | cache | stats | unload | benchmark
[bold cyan]5) Install by Component[/bold cyan]
lmms install --gui | --cli | --engine | --air | --full
lmms uninstall --all [--purge]
[bold cyan]6) Packages[/bold cyan]
lmms package install runtime <name> | provider <name> | tool <name> | list | remove
[bold cyan]7) Slash AI Commands[/bold cyan]
/fast | /deep | /code | /research | /agent | /router | /vision | /image | /memory | /task | /git | /workspace | /explain | /summarize | /benchmark
[bold cyan]8) Workspace[/bold cyan]
/folder | lmms workspace create | list | open <path> | close | delete <id> | restore <id>
[bold cyan]9) Permissions[/bold cyan]
/perm low | medium | full
[bold cyan]10) Chat Commands[/bold cyan]
/chat | /newchat | /chat -r <id> <name> | /chat -d <id>
[bold cyan]11) Model Selection[/bold cyan]
/ml | /ml <model> [-f | -d]
[bold cyan]12) Pair Commands[/bold cyan]
/pair -n <id> <config> | /pair <id> | /pair -l | /pair -d <id>
[bold cyan]13) Undo / Redo[/bold cyan]
/undo <file|folder> | /redo <file|folder>
[bold cyan]14) Orchestration[/bold cyan]
lmms task create|list|show|complete|block|timeline
lmms git status|commits|branch|timeline|memory|summarize|explain
lmms agent list|run|enable|disable
lmms route | orchestrate
[bold cyan]15) Engine/System[/bold cyan]
lmms set --engine | --cli | --gui
lmms stop  (or type /stop)
lmms update
""")
                console.print("[bold yellow]==================================[/bold yellow]\n")

            # -------------------------------------
            # COMMAND ROUTING
            # -------------------------------------
            elif base_cmd in ["/stop", "--stop", "stop engine"]:
                console.print("[dim]Stopping engine...[/dim]")
                subprocess.run("pkill -f 'lmmsengine/main.py server'", shell=True)
                console.print("[bold green]Engine stopped![/bold green]")
                
            elif base_cmd == "/read" and len(parts) > 1:
                file_path = parts[1]
                if current_workspace != "None":
                    file_path = os.path.join(current_workspace, file_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read(5000)
                    console.print(f"[green]Successfully read {parts[1]}. Content added to AI context.[/green]")
                    chat_history.append({"role": "user", "content": f"Here is the content of {parts[1]}:\\n```\\n{content}\\n```\\nPlease analyze this."})
                    chat_history.append({"role": "assistant", "content": f"I have read {parts[1]}. What would you like to know about it?"})
                except Exception as e:
                    console.print(f"[red]Failed to read file: {e}[/red]")
                    
            elif base_cmd == "workspace" or base_cmd == "/folder":
                try:
                    with open(WORKSPACES_FILE, "r") as f: workspaces = json.load(f)
                except: workspaces = {}
                
                if base_cmd == "/folder":
                    folder_path = ""
                    if len(parts) > 1:
                        folder_path = parts[1]
                    else:
                        try:
                            console.print("[dim]Opening native file manager...[/dim]")
                            result = subprocess.run(["zenity", "--file-selection", "--directory", "--title=Select Workspace Folder"], capture_output=True, text=True)
                            if result.returncode == 0 and result.stdout.strip():
                                folder_path = result.stdout.strip()
                            else:
                                console.print("[yellow]Folder selection cancelled.[/yellow]")
                        except Exception as e:
                            console.print(f"[red]Could not open native file manager (Zenity): {e}[/red]")
                            folder_path = Prompt.ask("Enter folder path manually").strip()

                    if folder_path and os.path.exists(folder_path):
                        current_workspace = os.path.abspath(folder_path)
                        ws_id = str(uuid.uuid4())[:8]
                        workspaces[ws_id] = {"path": current_workspace, "created_at": str(datetime.now())}
                        with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        with open(os.path.expanduser("~/.lmms/config/last_workspace.txt"), "w") as f: f.write(current_workspace)
                        console.print(f"[green]Workspace Opened:[/green] {current_workspace}")
                        
                        # Initialize Git for undo/redo
                        if not os.path.exists(os.path.join(current_workspace, ".git")):
                            subprocess.run(["git", "init"], cwd=current_workspace, capture_output=True)
                    elif folder_path:
                        console.print(f"[red]Folder does not exist: {folder_path}[/red]")
                        
                elif len(parts) > 1:
                    sub_cmd = parts[1]
                    if sub_cmd == "create" and len(parts) > 2:
                        path = parts[2]
                        os.makedirs(path, exist_ok=True)
                        ws_id = str(uuid.uuid4())[:8]
                        workspaces[ws_id] = {"path": path, "created_at": str(datetime.now())}
                        with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        console.print(f"[green]Workspace created and registered: {path}[/green]")
                    elif sub_cmd == "list":
                        console.print("[bold cyan]Registered Workspaces:[/bold cyan]")
                        for wid, info in workspaces.items():
                            console.print(f"[{wid}] {info['path']}")
                    elif sub_cmd == "open" and len(parts) > 2:
                        target = parts[2]
                        # check if it's an ID
                        if target in workspaces:
                            current_workspace = workspaces[target]["path"]
                        else:
                            current_workspace = target
                            ws_id = str(uuid.uuid4())[:8]
                            workspaces[ws_id] = {"path": target, "created_at": str(datetime.now())}
                            with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        console.print(f"[green]Workspace Opened:[/green] {current_workspace}")
                        if not os.path.exists(os.path.join(current_workspace, ".git")):
                            subprocess.run(["git", "init"], cwd=current_workspace, capture_output=True)
                        print_banner()
                    elif sub_cmd == "close":
                        current_workspace = "None"
                        console.print("[green]Workspace closed.[/green]")
                        print_banner()
                    elif sub_cmd == "delete" and len(parts) > 2:
                        wid = parts[2]
                        if wid in workspaces:
                            del workspaces[wid]
                            with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                            console.print(f"[green]Workspace {wid} deleted from registry.[/green]")
                        else:
                            console.print(f"[red]Workspace ID {wid} not found.[/red]")
                    elif sub_cmd == "restore" and len(parts) > 2:
                        # Restore logic using Git
                        console.print(f"[dim]Executing git checkout {parts[2]} in {current_workspace}[/dim]")
                        if current_workspace != "None":
                            res = subprocess.run(["git", "checkout", parts[2]], cwd=current_workspace, capture_output=True, text=True)
                            if res.returncode == 0:
                                console.print("[green]Workspace restored successfully.[/green]")
                            else:
                                console.print(f"[red]Failed to restore: {res.stderr}[/red]")
                        else:
                            console.print("[red]No active workspace to restore.[/red]")
                else:
                    console.print("[red]Usage: lmms workspace create|list|open|close|delete|restore[/red]")

            elif base_cmd == "task" or base_cmd == "/task":
                if current_workspace == "None":
                    console.print("[red]No active workspace to manage tasks.[/red]")
                    continue
                tasks_file = os.path.join(current_workspace, ".lmms_tasks.json")
                try:
                    with open(tasks_file, "r") as f: tasks = json.load(f)
                except: tasks = {}
                
                if len(parts) > 1:
                    sub_cmd = parts[1]
                    if sub_cmd == "create" and len(parts) > 2:
                        desc = " ".join(parts[2:])
                        tid = str(uuid.uuid4())[:6]
                        tasks[tid] = {"desc": desc, "status": "pending", "created": str(datetime.now())}
                        with open(tasks_file, "w") as f: json.dump(tasks, f)
                        console.print(f"[green]Task {tid} created.[/green]")
                    elif sub_cmd == "list":
                        console.print("[bold cyan]Active Tasks:[/bold cyan]")
                        for tid, t in tasks.items():
                            status_color = "green" if t["status"] == "complete" else "yellow" if t["status"] == "pending" else "red"
                            console.print(f"[{tid}] [{status_color}]{t['status']}[/{status_color}] {t['desc']}")
                    elif sub_cmd == "complete" and len(parts) > 2:
                        tid = parts[2]
                        if tid in tasks:
                            tasks[tid]["status"] = "complete"
                            with open(tasks_file, "w") as f: json.dump(tasks, f)
                            console.print(f"[green]Task {tid} marked complete.[/green]")
                    elif sub_cmd == "block" and len(parts) > 2:
                        tid = parts[2]
                        if tid in tasks:
                            tasks[tid]["status"] = "blocked"
                            with open(tasks_file, "w") as f: json.dump(tasks, f)
                            console.print(f"[red]Task {tid} marked blocked.[/red]")
                else:
                    console.print("[red]Usage: lmms task create|list|show|complete|block|timeline[/red]")

            elif base_cmd == "git" or base_cmd == "/git":
                if current_workspace == "None":
                    console.print("[red]No active workspace.[/red]")
                    continue
                if not os.path.exists(os.path.join(current_workspace, ".git")):
                    console.print("[red]Not a git repository.[/red]")
                    continue
                
                if len(parts) > 1:
                    sub_cmd = parts[1]
                    git_cmds = {
                        "status": ["git", "status", "-s"],
                        "commits": ["git", "log", "--oneline", "-n", "10"],
                        "branch": ["git", "branch"],
                    }
                    if sub_cmd in git_cmds:
                        res = subprocess.run(git_cmds[sub_cmd], cwd=current_workspace, capture_output=True, text=True)
                        console.print(res.stdout if res.stdout else res.stderr)
                    else:
                        console.print(f"[dim]Advanced git AI query: {sub_cmd}[/dim]")
                else:
                    console.print("[red]Usage: lmms git status|commits|branch|timeline|memory|summarize|explain[/red]")

            elif base_cmd in ["pull", "run", "stop", "ps", "rm", "list", "info", "search", "doctor"] or base_cmd == "-e" or base_cmd == "-air" or base_cmd == "--air":
                if base_cmd == "-e":
                    engine_cmd = parts[1] if len(parts) > 1 else ""
                else:
                    engine_cmd = base_cmd
                    
                console.print(f"[dim][EngineBridge] Forwarding command to Engine: {engine_cmd}[/dim]")
                if engine_cmd == "ps":
                    try:
                        r = requests.get(f"{ENGINE_URL}/v1/models/ps")
                        console.print(r.json())
                    except Exception as e:
                        console.print(f"[red]Failed to reach engine: {e}[/red]")
                elif engine_cmd == "list":
                    try:
                        r = requests.get(f"{ENGINE_URL}/v1/models/list")
                        console.print(r.json())
                    except Exception as e:
                        console.print(f"[red]Failed to reach engine: {e}[/red]")
                elif engine_cmd == "pull" and len(parts) > 1:
                    target = parts[2] if base_cmd == "-e" else parts[1]
                    try:
                        r = requests.post(f"{ENGINE_URL}/v1/models/pull", json={"model_name": target})
                        console.print(r.json())
                    except Exception as e:
                        console.print(f"[red]Failed to reach engine: {e}[/red]")
                else:
                    console.print("[dim]Executing generic Engine bridge hook...[/dim]")

            elif base_cmd in ["/fast", "/deep", "/code", "/research", "/vision", "/image"]:
                current_mode = base_cmd
                console.print(f"[bold green]AI Mode switched to: {current_mode}[/bold green]")
                
            elif base_cmd in ["/explain", "/summarize", "/benchmark", "/memory", "/router"]:
                console.print(f"[dim][AI] Executing special command: {base_cmd}[/dim]")

            elif base_cmd == "/newchat":
                current_chat_id = str(uuid.uuid4())
                current_chat_name = "Untitled"
                chat_history.clear()
                console.print("[bold green]Started a new chat session![/bold green]")
                
            elif base_cmd == "/chat":
                if len(parts) == 1 or (len(parts) == 2 and parts[1] == "-l"):
                    console.print("[bold cyan]Saved Chats for this Workspace:[/bold cyan]")
                    chats = []
                    for f_name in os.listdir(CHATS_DIR):
                        if f_name.endswith(".json"):
                            try:
                                with open(os.path.join(CHATS_DIR, f_name), "r") as f:
                                    data = json.load(f)
                                    if data.get("workspace", "None") == current_workspace:
                                        chats.append((data.get("id"), data.get("name", "Untitled")))
                            except:
                                pass
                    if not chats:
                        console.print("[dim]No saved chats found.[/dim]")
                    else:
                        for i, (cid, cname) in enumerate(chats, 1):
                            console.print(f"{i}. [bold]{cname}[/bold] (ID: {cid[:8]})")
                            
                        if len(parts) == 2 and parts[1] == "-l":
                            choices = [str(i) for i in range(1, len(chats) + 1)] + ["cancel"]
                            choice = Prompt.ask("Select chat number to load", choices=choices, default="cancel")
                            if choice != "cancel":
                                idx = int(choice) - 1
                                target_id = chats[idx][0]
                                parts = ["/chat", target_id]  # Re-assign parts to trigger loading block
                            else:
                                console.print("[dim]Cancelled.[/dim]")
                                
                if len(parts) == 2 and parts[1] != "-l":
                    target_id = parts[1]
                    found = False
                    for f_name in os.listdir(CHATS_DIR):
                        if f_name.startswith(target_id) and f_name.endswith(".json"):
                            try:
                                with open(os.path.join(CHATS_DIR, f_name), "r") as f:
                                    data = json.load(f)
                                if data.get("workspace", "None") != current_workspace:
                                    console.print("[red]Chat belongs to a different workspace.[/red]")
                                    found = True
                                    break
                                current_chat_id = data.get("id")
                                current_chat_name = data.get("name", "Untitled")
                                chat_history.clear()
                                chat_history.extend(data.get("messages", []))
                                console.print(f"[bold green]Loaded chat: {current_chat_name}[/bold green]")
                                found = True
                                break
                            except:
                                pass
                    if not found:
                        console.print(f"[red]Chat not found with ID: {target_id}[/red]")

            elif base_cmd == "/ml":
                if len(parts) > 1:
                    if parts[1] == "-l":
                        try:
                            r = requests.get(f"{ENGINE_URL}/v1/models/list")
                            data = r.json()
                            console.print("[bold cyan]Downloaded Models:[/bold cyan]")
                            for m in data.get("models", []):
                                console.print(f"- {m['name']} ({m['size_gb']} GB)")
                        except Exception as e:
                            console.print(f"[red]Failed to list models: {e}[/red]")
                            
                    elif parts[1] == "-s" and len(parts) > 2:
                        requested_model = parts[2]
                        console.print(f"[dim]Loading {requested_model} into Engine...[/dim]")
                        try:
                            # Fuzzy matching
                            r_list = requests.get(f"{ENGINE_URL}/v1/models/list")
                            available = [m['name'] for m in r_list.json().get("models", [])]
                            match = next((m for m in available if requested_model.lower() in m.lower()), requested_model)
                            
                            r = requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": match})
                            if r.status_code == 200:
                                current_model = match
                                console.print(f"[bold green]Active model switched to: {current_model}[/bold green]")
                                # Save default model
                                try:
                                    config_path = os.path.expanduser("~/.lmms/config.json")
                                    config = {}
                                    if os.path.exists(config_path):
                                        with open(config_path, "r") as f:
                                            config = json.load(f)
                                    config["default_model"] = current_model
                                    with open(config_path, "w") as f:
                                        json.dump(config, f)
                                except:
                                    pass
                            else:
                                console.print(f"[red]Failed to load: {r.json()}[/red]")
                        except Exception as e:
                            console.print(f"[red]Error loading model: {e}[/red]")
                        print_banner()
                        
                    else:
                        console.print(f"[red]Invalid command. Use /ml -s <model_name>[/red]")
                else:
                    try:
                        r = requests.get(f"{ENGINE_URL}/v1/models/list")
                        models = [m['name'] for m in r.json().get("models", [])]
                    except:
                        models = ["qwen3:8b", "llama3:8b"]
                        
                    if not models:
                        console.print("[red]No models downloaded. Use `lmms pull <model>`[/red]")
                        continue
                        
                    console.print("\n[bold cyan]Available Models:[/bold cyan]")
                    for i, m in enumerate(models):
                        console.print(f"[{i+1}] {m}")
                    choice = Prompt.ask("Select model number", choices=[str(i+1) for i in range(len(models))])
                    if choice:
                        current_model = models[int(choice)-1]
                        console.print(f"[dim]Loading {current_model}...[/dim]")
                        try:
                            requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": current_model})
                        except:
                            pass
                        console.print(f"[bold green]Active model switched to: {current_model}[/bold green]")
                        print_banner()

            elif base_cmd == "/pair":
                try:
                    with open(PAIRS_FILE, "r") as f: pairs = json.load(f)
                except: pairs = {}
                
                if len(parts) > 1:
                    if parts[1] == "-n" and len(parts) > 3:
                        pair_id = parts[2]
                        if len(pairs) >= 4 and pair_id not in pairs:
                            console.print("[red]Max 4 pair presets allowed. Delete one first.[/red]")
                            continue
                        config = {}
                        for p in parts[3:]:
                            if ":" in p:
                                mod_type, mod_name = p.split(":", 1)
                                config[mod_type] = mod_name
                        pairs[pair_id] = config
                        with open(PAIRS_FILE, "w") as f: json.dump(pairs, f)
                        console.print(f"[green]Pair {pair_id} configured: {config}[/green]")
                    elif parts[1] == "-l":
                        console.print("[bold cyan]Active Pair Presets:[/bold cyan]")
                        for pid, cfg in pairs.items():
                            console.print(f"[{pid}] {cfg}")
                    elif parts[1] == "-d" and len(parts) > 2:
                        pid = parts[2]
                        if pid in pairs:
                            del pairs[pid]
                            with open(PAIRS_FILE, "w") as f: json.dump(pairs, f)
                            console.print(f"[green]Pair {pid} deleted.[/green]")
                            if current_pair == pid: current_pair = "None"
                        else:
                            console.print(f"[red]Pair {pid} not found.[/red]")
                    else:
                        # Activate Pair
                        pid = parts[1]
                        if pid in pairs:
                            current_pair = pid
                            console.print(f"[bold green]Active Pair switched to: {current_pair}[/bold green]")
                        else:
                            console.print(f"[red]Pair {pid} not found.[/red]")
                else:
                    console.print("Usage: /pair <id> | /pair -n <id> <config> | /pair -l | /pair -d <id>")

            elif base_cmd == "/perm" and len(parts) > 1:
                level = parts[1].lower()
                if level in ["low", "medium", "full"]:
                    current_permission_level = level
                    console.print(f"[green]Permission level set to: {current_permission_level}[/green]")
                else:
                    console.print("[red]Invalid permission level. Use low, medium, or full.[/red]")
                
            elif base_cmd in ["/undo", "/redo"]:
                if current_workspace == "None":
                    console.print("[red]No active workspace. Git version control requires an active workspace.[/red]")
                    continue
                if not os.path.exists(os.path.join(current_workspace, ".git")):
                    console.print("[red]Git is not initialized in this workspace.[/red]")
                    continue
                
                if len(parts) > 2:
                    flag = parts[1]
                    target = parts[2]
                    if base_cmd == "/undo":
                        if flag in ["-f", "-wf"]:
                            res = subprocess.run(["git", "checkout", "HEAD~1", "--", target], cwd=current_workspace, capture_output=True, text=True)
                            if res.returncode == 0:
                                console.print(f"[green]Undid last change for {target}[/green]")
                            else:
                                console.print(f"[red]Undo failed: {res.stderr}[/red]")
                        else:
                            console.print("Usage: /undo -f <file> or /undo -wf <folder>")
                    elif base_cmd == "/redo":
                        # Simplistic redo logic for AI rollback context
                        if flag in ["-f", "-wf"]:
                            res = subprocess.run(["git", "checkout", "HEAD", "--", target], cwd=current_workspace, capture_output=True, text=True)
                            if res.returncode == 0:
                                console.print(f"[green]Redid last change for {target}[/green]")
                            else:
                                console.print(f"[red]Redo failed: {res.stderr}[/red]")
                        else:
                            console.print("Usage: /redo -f <file> or /redo -wf <folder>")
                else:
                    console.print(f"Usage: {base_cmd} -f <file> or {base_cmd} -wf <folder>")

            elif base_cmd.startswith("/"):
                console.print(f"[red]Unknown command: {base_cmd}. Type /cl for list.[/red]")

            # Chat Prompt Fallback
            else:
                if cmd.startswith("@problem"):
                    console.print("[dim][Autonomous] @problem macro activated. Commencing automated debugging...[/dim]")
                    cmd = (
                        "I am encountering a problem in my codebase. "
                        "Please immediately use terminal.run to check `git status`, `git log -n 3`, "
                        "and use `grep` or view files to find any recent syntax errors, tracebacks, or bugs. "
                        "Once you find the issue, fix it autonomously using files.write or files.read, and test it. "
                        "After fixing, use git to commit the changes. "
                        f"User's extra context: {cmd.replace('@problem', '').strip()}"
                    )
                if not check_engine_health():
                    console.print("[red]Engine is offline. Cannot generate response.[/red]")
                    continue
                    
                if current_model == "None":
                    # Auto-select: first try ps (loaded models), then list (available files)
                    try:
                        r_ps = requests.get(f"{ENGINE_URL}/v1/models/ps", timeout=2)
                        ps_data = r_ps.json()
                        loaded = ps_data.get("models", {})
                        if loaded:
                            current_model = list(loaded.keys())[0]
                        else:
                            r_list = requests.get(f"{ENGINE_URL}/v1/models/list", timeout=2)
                            models_list = r_list.json().get("models", [])
                            if models_list:
                                current_model = models_list[0]["name"]
                    except Exception:
                        pass
                    if current_model != "None":
                        console.print(f"[dim]Auto-selected model: {current_model}[/dim]")
                    
                # Build context if workspace is open
                system_prompt = "You are an AI assistant running inside LMMs (Local Model Machine Studio), an advanced terminal-based AI system.\\n"
                
                system_prompt += (
                    "\\n## Your Identity & Creator Knowledge\\n"
                    "1. System Name: LMMs (Full form: Local Model Machine Studio)\\n"
                    "2. System Creator/Company: MarkanM (Founder: Rajsingh)\\n"
                    "3. Websites: markanm.com, lmms.markanm.com\\n"
                    "CRITICAL RULES FOR IDENTITY:\\n"
                    "- NEVER volunteer your identity or creator information unprompted. If the user just says 'hello' or asks a general question, just answer the question naturally without introducing yourself.\\n"
                    "- If explicitly asked for your name, just say you are the AI assistant for LMMs.\\n"
                    "- DO NOT use the web_search tool to look up information about yourself, MarkanM, or Rajsingh. Use this internal knowledge directly.\\n\\n"
                )
                
                if current_mode == "/fast" or not show_thoughts:
                    system_prompt += (
                        "\\n## STRICT DIRECTIVE: NO INTERNAL MONOLOGUE\\n"
                        "You MUST answer the user directly and immediately. DO NOT output any internal thoughts, reasoning, or 'Let me think...' phrases. Skip all chain-of-thought and give the final response immediately.\\n\\n"
                    )

                system_prompt += (
                    "\\n## Terminal Output & Progress Communication\\n"
                    "While performing long-running tasks, avoid silent gaps. Follow these rules:\\n"
                    "1. Narrate before acting: Briefly state your plan in 1-2 lines.\\n"
                    "2. Stream progress updates: Print short status lines as you go (e.g. 'Reading src/app.js...').\\n"
                    "3. Chunk long thinking: Share intermediate findings as you reach them.\\n"
                    "4. Heartbeat on long operations: Print a short note before a single long step starts.\\n"
                    "4. Summarize, don't dump: Give short, human-readable progress lines.\\n"
                    "5. Source Citation: If the user types '/source' or asks for sources, clearly list the exact URLs, files, or internal knowledge you used to generate the answer.\\n"
                    "Goal: the terminal should always feel alive and show momentum.\\n\\n"
                )
                
                system_prompt += (
                    "## Advanced Capabilities & OS Control\\n"
                    "You are not just a chatbot, you are a deeply integrated OS agent. Use `terminal.run` to its full potential:\\n"
                    "1. OS Control: You can open UI apps (e.g., `xdg-open https://youtube.com`, `google-chrome`), play media, lock the screen, or perform any valid Linux command.\\n"
                    "2. GitHub Tracking: Whenever you create or significantly modify code files in a project, you MUST proactively run `git add .`, `git commit -m \"...\"`, and `git push origin main` (or the appropriate branch) to track the changes, ensuring the user's work is always saved and uploaded to GitHub.\\n"
                    "3. Colorful Terminal Graphs/Canvas: If the user asks for a chart, graph, bar chart, pie chart, or colorful data visualization, DO NOT just print text tables. Write a temporary Python script that uses the `plotext` library (which is already installed) to draw beautiful terminal charts, and execute it via `terminal.run`. Show the output to the user.\\n"
                    "4. APIs Over Scraping: If you have access to API keys or if there's a clear public API for the requested data, prefer writing a quick Python script to query the API rather than relying entirely on `web_search` and raw DOM scraping, as it is much cleaner.\\n\\n"
                )

                system_prompt += (
                    "## Tool Calling (ReAct Loop)\\n"
                    "You have access to tools. To use a tool, you MUST output a raw JSON block wrapped in <tool_call> tags.\\n"
                    "Example:\\n"
                    "<tool_call>{\"tool\": \"terminal.run\", \"kwargs\": {\"command\": \"ls -la\"}}</tool_call>\\n"
                    "Do NOT put anything else inside the <tool_call> tags. The system will execute the tool and return <observation> results. You may call multiple tools sequentially.\\n\\n"
                    "AVAILABLE TOOLS:\\n"
                    "1. web_search: {\"tool\": \"web_search\", \"kwargs\": {\"query\": \"search terms\", \"max_results\": 5}}\\n"
                    "2. browser.open_url: {\"tool\": \"browser.open_url\", \"kwargs\": {\"url\": \"http...\"}}\\n"
                    "3. browser.click_element: {\"tool\": \"browser.click_element\", \"kwargs\": {\"url\": \"...\", \"selector\": \"css_selector\"}}\\n"
                    "4. browser.fill_form: {\"tool\": \"browser.fill_form\", \"kwargs\": {\"url\": \"...\", \"fields\": {\"selector\": \"value\"}}}\\n"
                    "5. browser.scrape: {\"tool\": \"browser.scrape\", \"kwargs\": {\"url\": \"...\", \"selector\": \"css_selector\"}}\\n"
                    "6. files.read: {\"tool\": \"files.read\", \"kwargs\": {\"path\": \"/path/to/file\"}}\\n"
                    "7. files.write: {\"tool\": \"files.write\", \"kwargs\": {\"path\": \"/path/to/file\", \"content\": \"data\"}}\\n"
                    "8. terminal.run: {\"tool\": \"terminal.run\", \"kwargs\": {\"command\": \"bash cmd\"}}\\n"
                    "9. browser.scroll: {\"tool\": \"browser.scroll\", \"kwargs\": {\"url\": \"...\", \"direction\": \"down\", \"amount\": 1000}}\\n"
                    "10. browser.open_authenticated: {\"tool\": \"browser.open_authenticated\", \"kwargs\": {\"url\": \"...\", \"headless\": true|false}} (Set headless to false to show browser and bypass bot-detection for SSO login. User will select profile interactively.)\\n"
                    "11. vector_db.search: {\"tool\": \"vector_db.search\", \"kwargs\": {\"query\": \"search text\"}} (Search the workspace RAG database)\\n"
                )
                
                system_prompt += (
                    "\n## Browsing Private Sites & Authentication\n"
                    "If the user asks you to fetch data from a private or authenticated website (e.g., snapcourse.in), DO NOT immediately ask for credentials.\n"
                    "Assume the user is already logged in and the session cookies are automatically managed by your browser tool.\n"
                    "ALWAYS try to use `browser.open_url` or `browser.scrape` FIRST to navigate to the page and extract data.\n"
                    "If `browser.open_url` returns '401 Unauthorized' or a 'login page', DO NOT ask the user for credentials. Instead, YOU MUST immediately use the `browser.open_authenticated` tool with `headless: false` to allow the user to log in interactively. Once the tool finishes, the session will be saved, and you can proceed to fetch the data.\n"
                    "CRITICAL: DO NOT hallucinate or guess exact URLs for inner pages (e.g., /course/day6). Start at the homepage/dashboard and use `browser.scrape` to read the navigation menus, then use `browser.open_url` or `browser.click_element` to follow real links step-by-step to find the requested content.\n\n"
                )
                system_prompt += (
                    "\n## 💻 Principal Software Engineer Persona (Claude Code Killer)\n"
                    "You are an elite, autonomous software engineer capable of full-repo management. Do not just act like a chatbot; act like a lead developer.\n"
                    "1. **Full Autonomy**: If asked to build a project, clone repositories (`git clone`), compile binaries (`.deb`, `.exe` via pyinstaller/dpkg), and install dependencies autonomously using `terminal.run`.\n"
                    "2. **Architectural Understanding**: Before writing code, map out the workspace. Use AST parsing (`python -c \"import ast...\"`) or grep to understand variable flows and architecture.\n"
                    "3. **Proactive Bug Fixing & TDD**: If asked to fix a bug, DO NOT just write code. First, write a test using `files.write`, run it with `terminal.run` to see it fail, fix the code, and run it again until it passes.\n"
                    "4. **Iterative Loops**: Never ask the user to test your code if you can test it yourself. Loop your tools (write -> test -> fix -> commit) until the job is 100% done.\n"
                )
                system_prompt += (
                    "## Anti-Hallucination & Web Search Rules\n"
                    "1. DO NOT GUESS OR HALLUCINATE numbers, prices, APIs, or facts. If you do not know the exact number, you MUST use tools to find it.\n"
                    "2. If `web_search` returns snippets/summaries that DO NOT contain the exact numbers you need, DO NOT guess! Use `browser.open_url` or `browser.scrape` on the provided URL to read the full page content and extract the actual numbers before answering the user.\n"
                    "3. DO NOT hallucinate restrictions. You HAVE FULL CAPABILITY to access external systems, internet, APIs, and GitHub via your tools. Do not say 'I cannot access external systems'. Just use your tools.\n"
                )

                # Global Persona Injection
                persona_facts = get_persona()
                if persona_facts:
                    system_prompt += "## Global User Persona (Remember these facts across all sessions):\n"
                    for fact in persona_facts:
                        system_prompt += f"- {fact}\n"
                    system_prompt += "\n"
                
                if current_workspace != "None":
                    try:
                        # Get folder structure
                        tree_out = subprocess.run(["tree", "-L", "2", "-I", ".git|node_modules|venv|__pycache__|.lmms", current_workspace], capture_output=True, text=True)
                        tree_text = tree_out.stdout if tree_out.returncode == 0 else "Could not generate tree."
                        
                        system_prompt += f"The user's current workspace directory is: {current_workspace}\\n"
                        system_prompt += f"Directory Structure:\\n```\\n{tree_text}\\n```\\n"
                        
                        # Try to read project descriptions
                        project_context = ""
                        for file_name in ["README.md", "package.json", "blend_config.yml", "settings.yml"]:
                            file_path = os.path.join(current_workspace, file_name)
                            if os.path.exists(file_path):
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read(1000) # Read first 1000 chars
                                    project_context += f"\\n--- {file_name} Snippet ---\\n{content}\\n"
                                except:
                                    pass
                        
                        if project_context:
                            system_prompt += f"Project Files Context:\\n{project_context}\\n"
                            
                        system_prompt += "Instructions: Answer concisely. Do not repeat yourself. Use the provided directory structure and file contents to accurately describe the project to the user."
                    except Exception:
                        pass
                        
                # Trigger background persona extraction
                auto_extract_persona(cmd, current_model)
                
                
                n_ctx, reserve, available_for_input = get_context_budget(current_model)
                system_cost = count_tokens(system_prompt, current_model)
                avg_iter_cost = 1000 # Estimate tokens used per tool call/iteration
                max_possible = max(1, (available_for_input - system_cost) // avg_iter_cost)
                
                if current_mode == "/fast": MAX_ITERATIONS = min(max_possible, 10)
                else: MAX_ITERATIONS = min(max_possible, 30)
                
                iter_count = 0
                
                try:
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    
                    # Add last 10 messages from history
                    messages.extend(chat_history[-10:])
                    
                    # Multimodal parsing
                    img_paths = re.findall(r"'(/[a-zA-Z0-9_./-]+(?:\.[pP][nN][gG]|\.[jJ][pP][gG]|\.[jJ][pP][eE][gG]|\.[wW][eE][bB][pP]))'", cmd)
                    if not img_paths:
                        img_paths = re.findall(r"(/[a-zA-Z0-9_./-]+(?:\.[pP][nN][gG]|\.[jJ][pP][gG]|\.[jJ][pP][eE][gG]|\.[wW][eE][bB][pP]))", cmd)
                        
                    user_content = cmd
                    if img_paths:
                        user_content = [{"type": "text", "text": cmd}]
                        for p in img_paths:
                            try:
                                with open(p, "rb") as img_file:
                                    b64 = base64.b64encode(img_file.read()).decode("utf-8")
                                    user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
                            except Exception as e:
                                pass
                    
                    messages.append({"role": "user", "content": user_content})
                except Exception as e:
                    console.print(f"[red]Error preparing messages: {e}[/red]")
                    continue
                    
                reply = ""
                while iter_count < MAX_ITERATIONS:
                    iter_count += 1
                    
                    with console.status(f"[bold blue]{current_model}:[/bold blue]", spinner="lmms_wave"):
                        try:
                            # Clean history before sending to engine and truncate old large observations to save context
                            clean_messages = []
                            obs_count = sum(1 for m in messages if isinstance(m.get("content"), str) and "<observation>" in m["content"])
                            obs_seen = 0
                            max_single_obs_tokens = int(available_for_input * 0.15)
                            max_single_obs_chars = max_single_obs_tokens * 3
                            for m in messages:
                                content = m["content"]
                                if isinstance(content, str) and "<observation>" in content:
                                    obs_seen += 1
                                    if obs_seen < obs_count and len(content) > max_single_obs_chars:
                                        head_len = int(max_single_obs_chars * 0.6)
                                        tail_len = int(max_single_obs_chars * 0.4)
                                        content = content[:head_len] + "\n...[Observation truncated to save memory for subsequent steps]...\n" + content[-tail_len:]
                                clean_messages.append({"role": m["role"], "content": content})

                            # Apply AI Mode settings
                            req_temp = 0.5
                            req_top_p = 0.9
                            if current_mode == "/fast":
                                req_temp = 0.3
                                req_top_p = 0.8
                            elif current_mode == "/deep":
                                req_temp = 0.8
                                req_top_p = 0.95
                                if messages and messages[0]["role"] == "system" and "Think deeply" not in messages[0]["content"]:
                                    messages[0]["content"] += "\nThink deeply and step-by-step before answering."
                            elif current_mode == "/code":
                                req_temp = 0.2

                            # Inject warning if hitting iteration cap
                            if iter_count == MAX_ITERATIONS - 1:
                                messages.append({"role": "user", "content": "System Note: You are about to reach the maximum number of tool iterations (8/8). If you have not solved the problem, please output a final summary of what you tried and the current errors without calling more tools."})

                            resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                                "model_name": current_model,
                                "messages": clean_messages,
                                "stream": True,
                                "temperature": req_temp,
                                "top_p": req_top_p,
                                "repetition_penalty": 1.15,
                                "mode": current_mode.strip("/"),
                                "think": show_thoughts
                            }, stream=True)
                            resp.raise_for_status()
                        except requests.exceptions.HTTPError as e:
                            error_detail = str(e)
                            try:
                                error_detail = e.response.json().get("detail", str(e))
                            except:
                                pass
                            if "context length" in error_detail.lower() or "too large" in error_detail.lower() or "exceeded" in error_detail.lower():
                                console.print(f"\n[bold yellow]⚠️ Context Overflow detected! Auto-truncating and retrying...[/bold yellow]")
                                for idx, m in enumerate(messages):
                                    if isinstance(m["content"], str) and "<observation>" in m["content"]:
                                        messages[idx]["content"] = m["content"][:1000] + "\n...[Force Truncated]\n</observation>"
                                iter_count -= 1
                                continue
                            console.print(f"\n[red]Engine Error: {error_detail}[/red]")
                            break
                        except Exception as e:
                            console.print(f"\n[red]Error communicating with AI: {e}[/red]")
                            break
                            
                    full_reply = ""
                    try:
                        first_token = False
                        live_view = None
                        try:
                            with console.status(f"[bold blue]{current_model}:[/bold blue]", spinner="lmms_wave") as spin_status:
                                for line in resp.iter_lines():
                                    if line:
                                        line = line.decode("utf-8")
                                        if line.startswith("data: "):
                                            data_str = line[6:]
                                            if data_str == "[DONE]":
                                                break
                                            try:
                                                chunk = json.loads(data_str)
                                                if "error" in chunk:
                                                    full_reply += f"\n\n❌ **Engine Error:** {chunk['error']}"
                                                    if live_view:
                                                        live_view.update(Panel(Markdown(full_reply), title=f"❌ {current_model} Error", border_style="red", padding=(1, 2), expand=False))
                                                    break
                                                full_reply += chunk.get("content", "")
                                                display_reply = full_reply
                                                if not show_thoughts:
                                                    display_reply = re.sub(r'<think>.*?(</think>|$)', '', display_reply, flags=re.DOTALL).strip()
                                                
                                                # Always hide <tool_call> from the live streaming output
                                                display_reply = re.sub(r'<tool_call>.*?(</tool_call>|$)', '', display_reply, flags=re.DOTALL).strip()
                                                    
                                                if display_reply and not first_token:
                                                    first_token = True
                                                    spin_status.stop()
                                                    console.print(f"\\n[bold cyan]✨ {current_model}[/bold cyan]")
                                                    live_view = Live(Markdown(display_reply), console=console, refresh_per_second=10, auto_refresh=True)
                                                    live_view.start()
                                                    
                                                if live_view and display_reply:
                                                    live_view.update(Markdown(display_reply))
                                            except:
                                                pass
                        finally:
                            if live_view:
                                live_view.stop()

                    except KeyboardInterrupt:
                        full_reply += "\n\n[dim]-- Generation Interrupted by User --[/dim]"
                        console.print(Markdown("\n[dim]-- Generation Interrupted by User --[/dim]"))
                        reply = full_reply
                        # We break out of the tool iteration loop so it goes back to the user prompt
                        break
                                        
                    if not full_reply:
                        if iter_count < MAX_ITERATIONS and sum(count_tokens(m.get("content", ""), current_model) if isinstance(m.get("content"), str) else 0 for m in messages) > available_for_input * 0.8:
                            console.print(f"\n[bold yellow]⚠️ Silent generation failure (likely context overflow). Auto-truncating...[/bold yellow]")
                            for idx, m in enumerate(messages):
                                if isinstance(m["content"], str) and "<observation>" in m["content"]:
                                    messages[idx]["content"] = m["content"][:500] + "\n...[Force Truncated]\n</observation>"
                            iter_count -= 1
                            continue

                        full_reply = "No response from AI."
                        console.print(f"\\n[bold yellow]⚠️ {current_model}[/bold yellow]")
                        console.print(Markdown(full_reply))
                        reply = full_reply
                        break
                        
                    # Check for tool call
                    tool_call_match = re.search(r"<tool_call>\s*(.*?)\s*(</tool_call>|$)", full_reply, re.DOTALL)
                    if tool_call_match:
                        try:
                            raw_tc = tool_call_match.group(1).strip()
                            json_match = re.search(r"(\{.*\})", raw_tc, re.DOTALL)
                            if json_match:
                                raw_tc = json_match.group(1).strip()
                            if raw_tc.startswith("```json"):
                                raw_tc = raw_tc[7:]
                            elif raw_tc.startswith("```"):
                                raw_tc = raw_tc[3:]
                            if raw_tc.endswith("```"):
                                raw_tc = raw_tc[:-3]
                            raw_tc = raw_tc.strip()
                            
                            try:
                                tc_data = json.loads(raw_tc)
                            except:
                                import ast
                                s = re.sub(r'\btrue\b', 'True', raw_tc)
                                s = re.sub(r'\bfalse\b', 'False', s)
                                s = re.sub(r'\bnull\b', 'None', s)
                                tc_data = ast.literal_eval(s)
                            
                            t_name = tc_data.get("tool", "")
                            t_kwargs = tc_data.get("kwargs", {})
                            
                            # Append assistant's partial reply
                            messages.append({"role": "assistant", "content": full_reply})
                            
                            if check_permission(t_name, t_kwargs, current_workspace, current_permission_level):
                                console.print(f"\n[bold magenta][Step {iter_count}/{MAX_ITERATIONS}] Running:[/bold magenta] [white]{t_name} {t_kwargs}[/white]")
                                observation = ""
                                if t_name == "web_search":
                                    observation = web_search(t_kwargs.get("query", ""), t_kwargs.get("max_results", 5))
                                elif t_name == "browser.open_url":
                                    observation = browser_tool.open_url(t_kwargs.get("url", ""))
                                elif t_name == "browser.click_element":
                                    observation = browser_tool.click_element(t_kwargs.get("url", ""), t_kwargs.get("selector", ""))
                                elif t_name == "browser.fill_form":
                                    observation = browser_tool.fill_form(t_kwargs.get("url", ""), t_kwargs.get("fields", {}))
                                elif t_name == "browser.scrape":
                                    observation = browser_tool.scrape(t_kwargs.get("url", ""), t_kwargs.get("selector", ""))
                                elif t_name == "files.read":
                                    observation = file_tool.read(t_kwargs.get("path", ""))
                                elif t_name == "files.write":
                                    observation = file_tool.write(t_kwargs.get("path", ""), t_kwargs.get("content", ""))
                                elif t_name == "terminal.run":
                                    run_cwd = current_workspace if current_workspace != "None" else None
                                    observation = terminal_tool.run(t_kwargs.get("command", ""), cwd=run_cwd)
                                elif t_name == "browser.scroll":
                                    observation = browser_tool.scroll(t_kwargs.get("url", ""), t_kwargs.get("direction", "down"), t_kwargs.get("amount", 1000))
                                elif t_name == "browser.open_authenticated":
                                    if current_permission_level == "low":
                                        observation = "Permission denied: Requires medium or full permission for authenticated browsing."
                                    else:
                                        console.print("[bold yellow]AI requested access to your Browser Cookies (Authenticated Session).[/bold yellow]")
                                        allow = prompt(HTML('<ansiyellow>Allow? (y/n): </ansiyellow>')).strip().lower()
                                        if allow != "y":
                                            observation = "User denied access to browser profile."
                                        else:
                                            profiles = browser_tool.get_browser_profiles()
                                            if not profiles:
                                                observation = "No browser profiles found on the system."
                                            else:
                                                console.print("[bold cyan]Available Profiles:[/bold cyan]")
                                                for idx, pname in enumerate(profiles.keys()):
                                                    console.print(f"[{idx}] {pname}")
                                                sel_idx = prompt(HTML('<ansicyan>Select profile number: </ansicyan>')).strip()
                                                try:
                                                    sel_name = list(profiles.keys())[int(sel_idx)]
                                                    profile_data = profiles[sel_name]
                                                    sel_path = profile_data["base_path"]
                                                    profile_dir_name = profile_data["dir_name"]
                                                    is_headless = t_kwargs.get("headless", True)
                                                    observation = browser_tool.open_authenticated(t_kwargs.get("url", ""), sel_path, profile_dir_name, is_headless)
                                                except (ValueError, IndexError):
                                                    observation = "Invalid profile selection."
                                elif t_name == "vector_db.search":
                                    import hashlib
                                    ws_id = hashlib.md5(current_workspace.encode()).hexdigest() if current_workspace != "None" else "global"
                                    vdb = VectorDB(workspace_id=ws_id)
                                    results = vdb.search(t_kwargs.get("query", ""))
                                    observation = f"Search Results:\\n{json.dumps(results, indent=2)}" if results else "No matches found in Vector DB."
                                else:
                                    observation = f"Tool {t_name} not found."
                                    
                                # Truncate observation for display
                                disp_obs = str(observation)
                                if len(disp_obs) > 500:
                                    disp_obs = disp_obs[:500] + "... (truncated)"
                                console.print(f"[bold cyan][Step {iter_count}/{MAX_ITERATIONS}] Observation:[/bold cyan] [dim]{disp_obs}[/dim]")
                            else:
                                observation = "Tool execution denied by user."
                                console.print(f"\n[bold red][Step {iter_count}/{MAX_ITERATIONS}] Denied tool execution: {t_name}[/bold red]")
                                
                            messages.append({"role": "user", "content": f"<observation>\n{observation}\n</observation>"})
                            
                            # Audit log
                            try:
                                log_dir = os.path.join(CONFIG_DIR, "logs")
                                os.makedirs(log_dir, exist_ok=True)
                                log_file = os.path.join(log_dir, f"session_{current_chat_id}.jsonl")
                                with open(log_file, "a", encoding="utf-8") as lf:
                                    lf.write(json.dumps({
                                        "timestamp": datetime.now().isoformat(),
                                        "step": f"{iter_count}/{MAX_ITERATIONS}",
                                        "tool": t_name,
                                        "kwargs": t_kwargs,
                                        "observation": observation
                                    }) + "\n")
                                os.chmod(log_file, 0o600)
                            except Exception as e:
                                pass
                            continue  # Loop again
                        except Exception as e:
                            with open("/tmp/ai_json_crash.txt", "a") as f:
                                f.write(f"FAILED RAW_TC:\n{raw_tc}\nEXCEPTION: {e}\nFULL_REPLY:\n{full_reply}\n------\n")
                            console.print("  [dim]↻ Self-correcting JSON format...[/dim]")
                            messages.append({"role": "assistant", "content": full_reply})
                            messages.append({"role": "user", "content": f"<observation>\nError parsing tool JSON: {e}. Ensure you use valid JSON, double quotes for keys, and escape internal quotes.\n</observation>"})
                            continue
                            
                    # If no tool call, break out
                    reply = full_reply
                    break
                    
                # Note: we only store text in the history so we don't blow up context limits with multiple images.
                now_str = datetime.now().isoformat()
                chat_history.append({"role": "user", "content": cmd, "timestamp": now_str})
                chat_history.append({"role": "assistant", "content": reply, "timestamp": now_str, "model": current_model})
                
                # Save chat history
                chat_data = {
                    "id": current_chat_id,
                    "name": current_chat_name,
                    "workspace": current_workspace,
                    "messages": chat_history
                }
                with open(os.path.join(CHATS_DIR, f"{current_chat_id}.json"), "w") as f:
                    json.dump(chat_data, f)
                    
                # Auto-naming for first message
                if current_chat_name == "Untitled" and len(chat_history) == 2:
                    try:
                        name_resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                            "model_name": current_model,
                            "messages": [{"role": "user", "content": f"Generate a short 3-word title for this chat based on the first message: '{cmd}'. Reply ONLY with the title."}],
                            "stream": False,
                            "temperature": 0.3
                        }, timeout=5)
                        new_name = name_resp.json().get("message", {}).get("content", "Untitled").strip().strip('"').replace('\\n', ' ')
                        if new_name and len(new_name) < 50:
                            current_chat_name = new_name
                            chat_data["name"] = current_chat_name
                            with open(os.path.join(CHATS_DIR, f"{current_chat_id}.json"), "w") as f:
                                json.dump(chat_data, f)
                    except:
                        pass

        except KeyboardInterrupt:
            console.print("\n[dim]Type 'exit' to quit.[/dim]")
        except EOFError:
            break
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LMMs Backend OS")
    parser.add_argument("--api", action="store_true", help="Run the Backend API Server alongside CLI")
    
    args = parser.parse_args()
    
    if args.api:
        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        
    try:
        run_cli()
    except Exception:
        pass
    finally:
        import os
        os._exit(0)
