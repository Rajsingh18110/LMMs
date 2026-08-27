import subprocess
import os
import shutil
from typing import Dict, Any

from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission
from lmms.backend.config.config import ConfigManager

config = ConfigManager()

def get_workspace_dir() -> str:
    return config.get("workspace_dir", os.getcwd())

def enforce_boundary(path: str):
    workspace = get_workspace_dir()
    if not os.path.abspath(path).startswith(os.path.abspath(workspace)):
        raise PermissionError(f"Path {path} is outside the allowed workspace boundary.")

def canonical_file_read(path: str) -> Dict[str, Any]:
    enforce_boundary(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content, "path": path}

def canonical_file_write(path: str, content: str) -> Dict[str, Any]:
    enforce_boundary(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "success", "path": path}

default_registry.register(ToolDefinition(
    name="file.read",
    description="Read content from a file.",
    category="fs",
    parameters={"path": "str"},
    permissions=[Permission.READ_FILE],
    callback=canonical_file_read
))

default_registry.register(ToolDefinition(
    name="file.write",
    description="Write content to a file.",
    category="fs",
    parameters={"path": "str", "content": "str"},
    permissions=[Permission.WRITE_FILE],
    callback=canonical_file_write
))

class FileTool:
    def read(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write(self, path: str, content: str) -> str:
        old_content = None
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_content = f.read()
            except Exception:
                pass

        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            if hasattr(self, "agent") and self.agent:
                self.agent.push_action({
                    "type": "file_write",
                    "path": path,
                    "old_content": old_content,
                    "new_content": content
                })
            
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def edit_in_vscode(self, path: str) -> str:
        # Open file live in VS Code for user to see
        try:
            # Need to use shell=True or ensure 'code' is in PATH.
            # Using subprocess.Popen to not block
            subprocess.Popen(["code", path])
            return f"Opened {path} in VS Code."
        except Exception as e:
            return f"Failed to open in VS Code: {str(e)}"

    def list_folder(self, path: str) -> str:
        # Return folder tree structure
        try:
            if not os.path.exists(path):
                return f"Path {path} does not exist."

            result = []
            for root, dirs, files in os.walk(path):
                level = root.replace(path, "").count(os.sep)
                indent = " " * 4 * (level)
                result.append(f"{indent}{os.path.basename(root)}/")
                subindent = " " * 4 * (level + 1)
                for f in files:
                    result.append(f"{subindent}{f}")

                # Limit depth or number of files to prevent massive outputs
                if len(result) > 200:
                    result.append(f"{subindent}... (truncated)")
                    break
            return "\n".join(result)
        except Exception as e:
            return f"Error listing folder: {str(e)}"

    def create_folder(self, path: str) -> str:
        try:
            os.makedirs(path, exist_ok=True)
            return f"Created folder {path}"
        except Exception as e:
            return f"Error creating folder: {str(e)}"

    def delete(self, path: str, confirm: bool = False) -> str:
        # Safe delete with confirmation check handled by agent
        if not confirm:
            return f"Delete operation requires confirm=True to execute. Path: {path}"

        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                return f"Path {path} not found."
            return f"Deleted {path}"
        except Exception as e:
            return f"Error deleting: {str(e)}"

    def search_in_files(self, folder: str, query: str) -> str:
        # Search text across all files in folder
        try:
            results = []
            for root, _, files in os.walk(folder):
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                if query in line:
                                    results.append(f"{filepath}:{i+1}: {line.strip()}")
                                    if len(results) > 50:
                                        results.append("... (truncated)")
                                        return "\n".join(results)
                    except Exception:
                        pass  # Skip files that can't be read as text
            if not results:
                return "No matches found."
            return "\n".join(results)
        except Exception as e:
            return f"Error searching files: {str(e)}"
