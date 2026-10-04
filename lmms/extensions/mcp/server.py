import sys
import json
import os
import subprocess
import traceback

class MCPServer:
    """
    A lightweight Model Context Protocol (MCP) server that runs over stdio.
    Exposes basic IDE and file system tools to AI agents.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.running = True

    def run(self):
        # We read from stdin and write to stdout in JSON-RPC format
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
                # Fallback error response
                error_resp = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e), "data": traceback.format_exc()}
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
                "serverInfo": {
                    "name": "lmms-mcp-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        elif method == "tools/list":
            response["result"] = {
                "tools": [
                    {
                        "name": "read_file",
                        "description": "Read the contents of a file in the workspace.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Relative path to file"}
                            },
                            "required": ["path"]
                        }
                    },
                    {
                        "name": "run_command",
                        "description": "Run a shell command in the workspace.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "The shell command to run"}
                            },
                            "required": ["command"]
                        }
                    }
                ]
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result = self.execute_tool(tool_name, tool_args)
                response["result"] = {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                response["result"] = {"isError": True, "content": [{"type": "text", "text": str(e)}]}
        elif method == "shutdown":
            self.running = False
            response["result"] = None
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}
            
        return response

    def execute_tool(self, name: str, args: dict) -> str:
        if name == "read_file":
            filepath = os.path.join(self.workspace_root, args["path"])
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif name == "run_command":
            cmd = args["command"]
            res = subprocess.run(cmd, shell=True, cwd=self.workspace_root, capture_output=True, text=True)
            return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        else:
            raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    server = MCPServer(workspace)
    server.run()
