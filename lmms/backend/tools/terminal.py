import subprocess
import os
import shlex
from typing import Dict, Any, Optional

from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission
from lmms.backend.config.config import ConfigManager
from lmms.backend.tools.boundaries import is_within_workspace

BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "chmod 777 /",
    ":(){ :|:& };:",
    "fork bomb",
]

config = ConfigManager()

def get_workspace_dir() -> str:
    # Resolve the workspace from the existing LMMs config architecture
    ws = config.get("workspace_dir", os.getcwd())
    base_ws = str(ws) if ws else os.getcwd()
    try:
        from lmms_worktree.manager import default_worktree_manager
        return default_worktree_manager.get_active_workspace(base_ws)
    except Exception:
        return base_ws

def canonical_terminal_callback(command: str, cwd: Optional[str] = None, sandboxed: bool = True) -> Dict[str, Any]:
    # Check if dangerous
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            raise PermissionError(f"BLOCKED: Dangerous command '{blocked}' detected.")

    workspace_dir = get_workspace_dir()
    target_cwd = cwd if cwd else workspace_dir
    
    # Boundary enforcement
    if not is_within_workspace(target_cwd, workspace_dir):
        raise PermissionError("CWD is outside the allowed workspace boundary.")

    if sandboxed or config.get("permission_level") == "sandboxed":
        from lmms_sandbox.runner import default_runner
        res = default_runner.run(command, workspace_dir=workspace_dir, cwd=target_cwd, enforce_sandbox=True)
        if not res.success and res.exit_code == -1:
            raise PermissionError(res.stderr)
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.exit_code,
            "output": res.output,
            "sandboxed": True,
            "backend": res.backend_used,
        }

    try:
        if isinstance(command, str):
            command_args = shlex.split(command)
        else:
            command_args = list(command)

        # Automatically convert interactive commands to batch mode
        if command_args and command_args[0] == "top" and "-b" not in command_args:
            command_args = ["top", "-b", "-n", "1"]
        if command_args and command_args[0] == "sudo" and "-n" not in command_args:
            command_args.insert(1, "-n")

        result = subprocess.run(
            command_args, shell=False, capture_output=True, text=True, timeout=15, cwd=target_cwd, stdin=subprocess.DEVNULL
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "output": result.stdout + result.stderr or "Command executed successfully with no output."
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError("Command timed out after 120 seconds.")
    except Exception as e:
        raise Exception(f"Error executing command: {str(e)}")

default_registry.register(ToolDefinition(
    name="system.terminal",
    description="Execute shell commands safely within the workspace boundary.",
    category="system",
    parameters={"command": "str", "cwd": "str"},
    permissions=[Permission.TERMINAL],
    risk_level="medium",
    requires_confirmation=False,
    callback=canonical_terminal_callback
))

class TerminalTool:
    agent: Any = None

    def __init__(self, agent: Any = None):
        self.agent = agent

    def run(self, command: str, require_confirm=False, cwd=None, return_exit_code=False, sandboxed: bool = True) -> Any:
        # Check if dangerous
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                msg = f"BLOCKED: Dangerous command '{blocked}' detected."
                return (-1, msg) if return_exit_code else msg

        # Confirm if needed
        if require_confirm:
            confirm = input(f"Run: `{command}`? (y/n): ")
            if confirm.lower() != "y":
                msg = "Command execution cancelled by user."
                return (-1, msg) if return_exit_code else msg

        if hasattr(self, "agent") and self.agent:
            self.agent.push_action({
                "type": "terminal_command",
                "command": command
            })

        # The configured workspace is the authority boundary. A caller-supplied
        # cwd selects a directory within that boundary; it must never redefine it.
        workspace_dir = get_workspace_dir()
        target_cwd = cwd if cwd else workspace_dir

        if not is_within_workspace(target_cwd, workspace_dir):
            msg = "CWD is outside the allowed workspace boundary."
            return (-1, msg) if return_exit_code else msg

        if sandboxed or config.get("permission_level") == "sandboxed":
            from lmms_sandbox.runner import default_runner
            res = default_runner.run(command, workspace_dir=workspace_dir, cwd=target_cwd, require_confirm=False, enforce_sandbox=True)
            if return_exit_code:
                return (res.exit_code, res.output)
            return res.output

        try:
            if isinstance(command, str):
                command_args = shlex.split(command)
            else:
                command_args = command

            result = subprocess.run(
                command_args, shell=False, capture_output=True, text=True, timeout=120, cwd=target_cwd
            )
            output = result.stdout + result.stderr
            if not output:
                output = "Command executed successfully."
            if return_exit_code:
                return (result.returncode, output)
            if result.returncode != 0:
                output = f"[Command Failed with Exit Code {result.returncode}]\n" + output
            return output
        except subprocess.TimeoutExpired:
            msg = "Command timed out after 120 seconds."
            return (-1, msg) if return_exit_code else msg
        except Exception as e:
            msg = f"Error executing command: {str(e)}"
            return (-1, msg) if return_exit_code else msg
