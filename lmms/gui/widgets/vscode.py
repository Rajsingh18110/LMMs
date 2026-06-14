import os
import subprocess
import sqlite3
import requests
def check_vscode_running():
    try:
        res = subprocess.run(["pgrep", "-f", "code"], capture_output=True)
        if res.returncode != 0:
            subprocess.Popen(["code", "."])
            return "Launched VS Code."
        return "VS Code is already running."
    except Exception:
        return "Could not determine VS Code status."

def open_file(path):
    subprocess.run(["code", path])

def open_folder(path):
    subprocess.run(["code", path])

def create_and_open(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding="utf-8") as f:
        f.write(content)
    subprocess.run(["code", path])
    return f"✅ Created and opened: {path}"

def get_active_file():
    state_db = os.path.expanduser("~/.config/Code/User/globalStorage/state.vscdb")
    if os.path.exists(state_db):
        try:
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
            row = cursor.fetchone()
            conn.close()
            if row:
                import json
                data = json.loads(row[0])
                entries = data.get("entries", [])
                for entry in entries:
                    if "fileUri" in entry:
                        uri = entry["fileUri"]
                        if uri.startswith("file://"):
                            return uri[7:]
        except Exception:
            pass
    return None

def edit_file(path, old_code, new_code):
    if not os.path.exists(path):
        return f"File not found: {path}"
    with open(path, 'r', encoding="utf-8") as f:
        content = f.read()
    new_content = content.replace(old_code, new_code)
    with open(path, 'w', encoding="utf-8") as f:
        f.write(new_content)
    subprocess.run(["code", path])
    return "✅ File edited and reloaded"

def run_in_vscode_terminal(command):
    subprocess.run([
        "code", "--command", 
        "workbench.action.terminal.sendSequence",
        command
    ])
    return f"✅ Ran in terminal: {command}"

def copilot_mode(file_path):
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
    
    with open(file_path, 'r', encoding="utf-8") as f:
        code = f.read()
    
    try:
        payload = {
            "model_name": "qwen3:8b",
            "messages": [{
                'role': 'user',
                'content': f'''You are a coding assistant.
Improve this code, fix bugs, add missing parts.
Return ONLY the complete improved code.
No explanation. Just code.

FILE: {file_path}
CODE:
{code}'''
            }],
            "stream": False
        }
        
        response = requests.post("http://localhost:11435/v1/chat/completions", json=payload, timeout=60)
        if response.status_code == 200:
            improved = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            return f"Engine error: {response.text}"
        if improved.startswith("```"):
            lines = improved.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            improved = "\n".join(lines)
            
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(improved)
        subprocess.run(['code', file_path])
        return "✅ Code improved and saved"
    except Exception as e:
        return f"Failed to improve code: {e}"
