import sys
import json
import os
import subprocess
import traceback
from glob import glob


class AgentToolBridge:
    """Workspace and shell tool adapter for AI agents inside LMMs."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())

    def _safe_path(self, user_path: str) -> str:
        if not user_path:
            return self.workspace_root
        abs_path = os.path.abspath(os.path.join(self.workspace_root, user_path))
        resolved_root = os.path.realpath(self.workspace_root)
        resolved_target = os.path.realpath(abs_path)
        if os.path.commonpath([resolved_root, resolved_target]) != resolved_root:
            raise ValueError(f"Path escapes workspace root: {user_path}")
        return resolved_target

    def get_tool_specs(self):
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file inside the current workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write or overwrite a file inside the current workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_dir",
                "description": "List files and folders in a workspace directory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "search_files",
                "description": "Search for files matching a glob pattern.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "pattern": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["path", "pattern"],
                },
            },
            {
                "name": "run_command",
                "description": "Run a shell command in the workspace context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "git_status",
                "description": "Get git status for the current workspace.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def read_file(self, path: str) -> str:
        resolved = self._safe_path(path)
        with open(resolved, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> str:
        resolved = self._safe_path(path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {path}"

    def list_dir(self, path: str = ".") -> list[str]:
        resolved = self._safe_path(path)
        entries = []
        for name in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, name)
            entries.append(name if os.path.isfile(full) else f"{name}/")
        return entries

    def search_files(self, path: str = ".", pattern: str = "**/*", max_results: int = 100) -> list[str]:
        resolved = self._safe_path(path)
        matches = []
        for match in sorted(glob(os.path.join(resolved, pattern), recursive=True)):
            if os.path.isfile(match):
                matches.append(os.path.relpath(match, self.workspace_root))
            if len(matches) >= max_results:
                break
        return matches

    def run_command(self, command: str, timeout: int = 120000) -> str:
        result = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=max(1, timeout / 1000),
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        return "\n\n".join(output) if output else "Command completed successfully with no output."

    def git_status(self) -> str:
        result = subprocess.run(
            ["git", "-C", self.workspace_root, "status", "--short"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout or "Working tree clean."
        return result.stderr or "Git status failed."

    def call_tool(self, name: str, args: dict):
        if name == "read_file":
            return self.read_file(args.get("path", "."))
        if name == "write_file":
            return self.write_file(args["path"], args.get("content", ""))
        if name == "list_dir":
            return self.list_dir(args.get("path", "."))
        if name == "search_files":
            return self.search_files(args.get("path", "."), args.get("pattern", "**/*"), int(args.get("max_results", 100)))
        if name == "run_command":
            return self.run_command(args["command"], int(args.get("timeout", 120000)))
        if name == "git_status":
            return self.git_status()
        raise ValueError(f"Unknown tool: {name}")


class AgentExecutionAdapter:
    """Structured adapter for agent-driven execution of workspace operations."""

    def __init__(self, workspace_root: str, bridge: AgentToolBridge | None = None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.bridge = bridge or AgentToolBridge(self.workspace_root)

    def execute(self, tool_name: str, arguments: dict | None = None):
        if not tool_name:
            raise ValueError("tool_name is required")
        return self.bridge.call_tool(tool_name, arguments or {})

    def run_task(self, task: dict | str):
        if isinstance(task, str):
            return self.execute("run_command", {"command": task})
        if not isinstance(task, dict):
            raise ValueError("task must be a dict or string")

        tool_name = task.get("tool") or task.get("name")
        arguments = task.get("arguments") or task.get("params") or {}
        return self.execute(tool_name, arguments)

    def read_file(self, path: str):
        return self.execute("read_file", {"path": path})

    def write_file(self, path: str, content: str):
        return self.execute("write_file", {"path": path, "content": content})

    def list_dir(self, path: str = "."):
        return self.execute("list_dir", {"path": path})

    def search_files(self, path: str = ".", pattern: str = "**/*", max_results: int = 100):
        return self.execute("search_files", {"path": path, "pattern": pattern, "max_results": max_results})

    def run_command(self, command: str, timeout: int = 120000):
        return self.execute("run_command", {"command": command, "timeout": timeout})

    def git_status(self):
        return self.execute("git_status", {})


class MCPServer:
    """A lightweight Model Context Protocol server exposing LMMs workspace tools."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.bridge = AgentToolBridge(workspace_root)
        self.execution = AgentExecutionAdapter(workspace_root, self.bridge)
        self.running = True

    def run(self):
        while self.running:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                error_resp = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e), "data": traceback.format_exc()},
                }
                sys.stdout.write(json.dumps(error_resp) + "\n")
                sys.stdout.flush()

    def handle_request(self, request: dict) -> dict:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        response = {"jsonrpc": "2.0"}
        if req_id is not None:
            response["id"] = req_id

        if method == "initialize":
            response["result"] = {
                "serverInfo": {"name": "lmms-mcp-server", "version": "1.1.0"},
                "capabilities": {"tools": {}},
            }
        elif method == "tools/list":
            response["result"] = {"tools": self.bridge.get_tool_specs()}
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result = self.bridge.call_tool(tool_name, tool_args)
                response["result"] = {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                response["result"] = {"isError": True, "content": [{"type": "text", "text": str(e)}]}
        elif method == "agent/execute":
            try:
                result = self.execution.run_task(params)
                response["result"] = {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                response["result"] = {"isError": True, "content": [{"type": "text", "text": str(e)}]}
        elif method == "shutdown":
            self.running = False
            response["result"] = None
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}

        return response


if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    server = MCPServer(workspace)
    server.run()
