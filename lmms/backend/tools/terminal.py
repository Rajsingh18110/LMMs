import subprocess
import os
from typing import Dict, Any

from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission
from lmms.backend.config.config import ConfigManager

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
    return config.get("workspace_dir", os.getcwd())

def canonical_terminal_callback(command: str, cwd: str = None) -> Dict[str, Any]:
    # Check if dangerous
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            raise PermissionError(f"BLOCKED: Dangerous command '{blocked}' detected.")

    workspace_dir = get_workspace_dir()
    target_cwd = cwd if cwd else workspace_dir
    
    # Boundary enforcement
    if not os.path.abspath(target_cwd).startswith(os.path.abspath(workspace_dir)):
        raise PermissionError("CWD is outside the allowed workspace boundary.")
        
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120, cwd=target_cwd
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
    permissions=[Permission.SAFE_WRITE],
    risk_level="medium",
    requires_confirmation=False,
    callback=canonical_terminal_callback
))

class TerminalTool:
    def run(self, command: str, require_confirm=False, cwd=None, return_exit_code=False) -> Any:
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

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120, cwd=cwd
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
