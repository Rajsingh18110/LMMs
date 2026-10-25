import subprocess
import os
from lmms.backend.security.models import ToolRequest, ToolResult
from lmms.backend.security.evidence import record_tool_evidence

class SecureExecutor:
    
    def execute(self, request: ToolRequest, permission_result, timeout: int = 120) -> ToolResult:
        # We assume permission manager already vetted the request.
        if not permission_result.allowed:
            denial_msg = f"[TOOL_DENIED] {permission_result.reason}\nNotice: The command was NOT executed on the host."
            record_tool_evidence(request, permission_result, ToolResult("", denial_msg, 1, was_denied=True, deny_reason=permission_result.reason))
            return ToolResult("", denial_msg, 1, was_denied=True, deny_reason=permission_result.reason)
            
        # Sandbox logic for Terminal commands
        if request.tool_name == "terminal.run":
            cmd = request.kwargs.get("command", "")
            cwd = request.workspace if request.workspace and request.workspace != "None" else None
            workspace_dir = cwd or os.getcwd()

            # Enforce sandbox containment for restricted permission tiers (sandboxed, low, medium)
            if request.permission_level in ("sandboxed", "low", "medium"):
                from lmms_sandbox.runner import default_runner
                # Caller has already validated or user confirmed permission, so confirm_callback auto-accepts
                s_res = default_runner.run(
                    cmd,
                    workspace_dir=workspace_dir,
                    cwd=cwd,
                    timeout=timeout,
                    enforce_sandbox=True,
                    confirm_callback=lambda cmd_str, reason: True
                )
                if not s_res.success and s_res.exit_code == -1 and s_res.backend_used == "none":
                    result = ToolResult(stdout="", stderr=s_res.stderr, exit_code=-1, was_denied=True, deny_reason=s_res.stderr)
                else:
                    result = ToolResult(stdout=s_res.stdout, stderr=s_res.stderr, exit_code=s_res.exit_code)
                record_tool_evidence(request, permission_result, result)
                return result

            # Full permission tier: explicit administrative override allows unconfined host execution
            import shlex
            try:
                shell_meta = any(op in cmd for op in [">", "<", "|", "&&", "||", ";", "$(", "`"])
                if shell_meta:
                    parts = ["bash", "-c", cmd]
                else:
                    parts = shlex.split(cmd)
            except ValueError:
                parts = ["bash", "-c", cmd]
                
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
