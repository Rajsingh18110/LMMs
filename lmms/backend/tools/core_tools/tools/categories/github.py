import httpx
import subprocess
import os
from lmms.backend.tools.core_tools.tools.base import ToolResult
from lmms.backend.logic.manager import backend_manager

def get_github_token():
    try:
        import sqlite3
        import json
        db_path = os.path.expanduser("~/.lmms/connectors.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT config_json FROM connectors WHERE connector_name = 'github'")
            row = cursor.fetchone()
            conn.close()
            if row:
                config = json.loads(row[0])
                return config.get("token")
    except:
        pass
    return None

async def execute_github_search_repos(params: dict) -> ToolResult:
    query = params.get("query")
    if not query:
        return ToolResult(tool_name="github_search_repos", success=False, error="Missing query", data=None)
        
    token = get_github_token()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=3", headers=headers)
            if r.status_code == 200:
                items = r.json().get("items", [])
                results = []
                for item in items:
                    results.append({
                        "name": item.get("full_name"),
                        "description": item.get("description"),
                        "stars": item.get("stargazers_count"),
                        "url": item.get("html_url")
                    })
                return ToolResult(tool_name="github_search_repos", success=True, data=results)
            return ToolResult(tool_name="github_search_repos", success=False, error=f"Status: {r.status_code}", data=None)
        except Exception as e:
            return ToolResult(tool_name="github_search_repos", success=False, error=str(e), data=None)

async def execute_github_repo_info(params: dict) -> ToolResult:
    repo = params.get("repo")
    if not repo:
        return ToolResult(tool_name="github_repo_info", success=False, error="Missing repo", data=None)
        
    token = get_github_token()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://api.github.com/repos/{repo}", headers=headers)
            if r.status_code == 200:
                data = r.json()
                return ToolResult(tool_name="github_repo_info", success=True, data={
                    "name": data.get("full_name"),
                    "description": data.get("description"),
                    "stars": data.get("stargazers_count"),
                    "forks": data.get("forks_count"),
                    "language": data.get("language"),
                    "open_issues": data.get("open_issues_count")
                })
            return ToolResult(tool_name="github_repo_info", success=False, error=f"Status: {r.status_code}", data=None)
        except Exception as e:
            return ToolResult(tool_name="github_repo_info", success=False, error=str(e), data=None)

async def execute_github_clone_repo(params: dict) -> ToolResult:
    url = params.get("url")
    if not url:
        return ToolResult(tool_name="github_clone_repo", success=False, error="Missing url", data=None)
        
    ws_path = backend_manager.config.get("active_workspace")
    if not ws_path:
        dest_dir = os.path.expanduser("~/.lmms/sandbox")
        os.makedirs(dest_dir, exist_ok=True)
    else:
        dest_dir = ws_path
        
    repo_name = url.split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
        
    clone_path = os.path.join(dest_dir, repo_name)
    
    # Boundary check inside workspace
    if ws_path and not clone_path.startswith(ws_path):
         return ToolResult(tool_name="github_clone_repo", success=False, error="Boundary violation: clone path is outside active workspace", data=None)
         
    try:
        proc = subprocess.run(["git", "clone", url, clone_path], capture_output=True, text=True)
        if proc.returncode == 0:
            return ToolResult(tool_name="github_clone_repo", success=True, data={"message": f"Successfully cloned to {clone_path}"})
        return ToolResult(tool_name="github_clone_repo", success=False, error=f"Git clone failed: {proc.stderr}", data=None)
    except Exception as e:
        return ToolResult(tool_name="github_clone_repo", success=False, error=str(e), data=None)
