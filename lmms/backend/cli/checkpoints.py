import os
import json
import uuid
import shutil
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

def get_checkpoints_dir(workspace: str) -> str:
    path = os.path.join(workspace, ".lmms", "checkpoints")
    os.makedirs(path, exist_ok=True)
    return path

def get_metadata_file(workspace: str) -> str:
    return os.path.join(workspace, ".lmms", "checkpoints.json")

def load_checkpoints(workspace: str) -> dict:
    meta_file = get_metadata_file(workspace)
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_checkpoints(workspace: str, data: dict):
    meta_file = get_metadata_file(workspace)
    os.makedirs(os.path.dirname(meta_file), exist_ok=True)
    with open(meta_file, "w") as f:
        json.dump(data, f, indent=2)

def is_git_repo(workspace: str) -> bool:
    return os.path.isdir(os.path.join(workspace, ".git"))

def ensure_git_or_fallback(workspace: str) -> str:
    if is_git_repo(workspace):
        return "git"
    
    ans = Prompt.ask("[bold yellow]Workspace is not a Git repository. Initialize Git for efficient checkpoints? (y/n)[/bold yellow]").lower()
    if ans == "y":
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        # Create an initial commit if empty
        res = subprocess.run(["git", "status"], cwd=workspace, capture_output=True, text=True)
        if "No commits yet" in res.stdout:
            subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=workspace, capture_output=True)
        return "git"
    return "copy"

def create_checkpoint(workspace: str, name: str = "Manual Checkpoint"):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace.[/red]")
        return None
        
    ctype = ensure_git_or_fallback(workspace)
    cid = str(uuid.uuid4())[:8]
    data = load_checkpoints(workspace)
    
    timestamp = datetime.now().isoformat()
    checkpoint_info = {
        "id": cid,
        "name": name,
        "timestamp": timestamp,
        "type": ctype,
        "files": []
    }
    
    if ctype == "git":
        # Create a commit of the current working tree without modifying index
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = os.path.join(workspace, ".git", f"lmms_index_{cid}")
        
        subprocess.run(["git", "add", "-A"], cwd=workspace, env=env, capture_output=True)
        res_tree = subprocess.run(["git", "write-tree"], cwd=workspace, env=env, capture_output=True, text=True)
        tree_hash = res_tree.stdout.strip()
        
        if tree_hash:
            res_commit = subprocess.run(["git", "commit-tree", tree_hash, "-p", "HEAD", "-m", f"Checkpoint: {name}"], cwd=workspace, env=env, capture_output=True, text=True)
            commit_hash = res_commit.stdout.strip()
            checkpoint_info["git_hash"] = commit_hash
            # Tag it so it doesn't get garbage collected
            subprocess.run(["git", "tag", f"lmms-checkpoint-{cid}", commit_hash], cwd=workspace, capture_output=True)
            
        if os.path.exists(env["GIT_INDEX_FILE"]):
            os.remove(env["GIT_INDEX_FILE"])
            
        if not tree_hash or not commit_hash:
            console.print("[red]Failed to create git checkpoint.[/red]")
            return None
            
    else:
        # Copy fallback - just copy all files (excluding .git, node_modules, etc)
        cp_dir = os.path.join(get_checkpoints_dir(workspace), cid)
        
        def ignore_patterns(d, files):
            return [f for f in files if f in [".git", "node_modules", "__pycache__", "venv", "env", ".lmms"]]
            
        try:
            shutil.copytree(workspace, cp_dir, ignore=ignore_patterns, dirs_exist_ok=True)
            checkpoint_info["path"] = cp_dir
        except Exception as e:
            console.print(f"[red]Failed to create copy checkpoint: {e}[/red]")
            return None
            
    data[cid] = checkpoint_info
    save_checkpoints(workspace, data)
    console.print(f"[green]Checkpoint created: {cid} ({name})[/green]")
    return cid

def list_checkpoints(workspace: str):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace.[/red]")
        return
        
    data = load_checkpoints(workspace)
    if not data:
        console.print("[yellow]No checkpoints found for this workspace.[/yellow]")
        return
        
    console.print("\n[bold cyan]=== Workspace Checkpoints ===[/bold cyan]")
    for cid, info in data.items():
        console.print(f"[{cid}] {info['timestamp'][:19]} - {info['name']} ({info['type']})")
    console.print("Use /rollback <id> to restore a checkpoint.\n")

def rollback_checkpoint(workspace: str, cid: str):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace.[/red]")
        return
        
    data = load_checkpoints(workspace)
    if cid not in data:
        console.print(f"[red]Checkpoint ID {cid} not found.[/red]")
        return
        
    info = data[cid]
    ctype = info.get("type", "copy")
    
    console.print(f"[bold cyan]Previewing Rollback for {cid} ({info['name']})[/bold cyan]")
    
    if ctype == "git":
        commit_hash = info.get("git_hash")
        if not commit_hash:
            console.print("[red]Corrupted checkpoint: missing git_hash[/red]")
            return
            
        # Diff between working directory and the checkpoint
        res = subprocess.run(["git", "diff", "--stat", commit_hash], cwd=workspace, capture_output=True, text=True)
        if not res.stdout.strip():
            console.print("[green]Working directory is already identical to the checkpoint.[/green]")
            return
            
        console.print(Panel(res.stdout, title="Affected Files (Current vs Checkpoint)", border_style="yellow"))
        
        ans = Prompt.ask("[bold red]Are you sure you want to rollback to this checkpoint? Unsaved changes may be lost. (y/n)[/bold red]").lower()
        if ans != "y":
            console.print("[yellow]Rollback cancelled.[/yellow]")
            return
            
        # Restore files from the commit
        # We use checkout to overwrite working tree files with the ones from the commit
        res_co = subprocess.run(["git", "checkout", commit_hash, "--", "."], cwd=workspace, capture_output=True, text=True)
        if res_co.returncode == 0:
            console.print("[bold green]Rollback completed successfully.[/bold green]")
        else:
            console.print(f"[bold red]Rollback failed: {res_co.stderr}[/bold red]")
            
    else:
        cp_dir = info.get("path")
        if not cp_dir or not os.path.exists(cp_dir):
            console.print("[red]Corrupted checkpoint: missing backup folder[/red]")
            return
            
        console.print("[yellow]Copy-based rollback will overwrite files in the workspace with the backup.[/yellow]")
        ans = Prompt.ask("[bold red]Are you sure you want to rollback? (y/n)[/bold red]").lower()
        if ans != "y":
            console.print("[yellow]Rollback cancelled.[/yellow]")
            return
            
        try:
            shutil.copytree(cp_dir, workspace, dirs_exist_ok=True)
            console.print("[bold green]Rollback completed successfully.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Rollback failed: {e}[/bold red]")
