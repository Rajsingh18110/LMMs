import subprocess
import os
from lmms.backend.security.models import ToolRequest, ToolResult
from lmms.backend.security.evidence import record_tool_evidence

class SecureExecutor:
    
    def execute(self, request: ToolRequest, permission_result, timeout: int = 120) -> ToolResult:
        # We assume permission manager already vetted the request.
        if not permission_result.allowed:
            record_tool_evidence(request, permission_result, ToolResult("", "", 1, was_denied=True, deny_reason=permission_result.reason))
            return ToolResult("", "", 1, was_denied=True, deny_reason=permission_result.reason)
            
        # Sandbox logic for Terminal commands
        if request.tool_name == "terminal.run":
            cmd = request.kwargs.get("command", "")
            cwd = request.workspace if request.workspace and request.workspace != "None" else None
            
            # Use shell=False if possible, but the command parser already stripped dangerous bash tokens
            # Wait, our parser guarantees no meta-characters. So we can use shell=True safely OR shell=False using shlex
            import shlex
            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()
                
            try:
                # Set a strict timeout to prevent hanging commands (e.g. reverse shells waiting)
                process = subprocess.run(parts, cwd=cwd, capture_output=True, text=True, timeout=timeout)
                result = ToolResult(stdout=process.stdout, stderr=process.stderr, exit_code=process.returncode)
            except subprocess.TimeoutExpired as e:
                stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                result = ToolResult(stdout=stdout_str, stderr=f"Command timed out after {timeout} seconds.", exit_code=124)
            except Exception as e:
                result = ToolResult(stdout="", stderr=str(e), exit_code=1)
                
            record_tool_evidence(request, permission_result, result)
            return result
            
        else:
            # We don't execute internal tools (browser, file) through subprocess. 
            # They are executed natively in main.py, but we record the evidence here.
            # So the caller (main.py) will do the execution and then record.
            return ToolResult("Internal tool execution delegated to main.py", "", 0)

executor = SecureExecutor()
