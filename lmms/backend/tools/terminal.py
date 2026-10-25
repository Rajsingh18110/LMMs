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
    env_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
    if env_ws and os.path.isdir(env_ws):
        return env_ws
    ws = config.get("workspace_dir", os.getcwd())
    base_ws = str(ws) if ws and os.path.isdir(str(ws)) else os.getcwd()
    try:
        from lmms_worktree.manager import default_worktree_manager
        return default_worktree_manager.get_active_workspace(base_ws)
    except Exception:
        return base_ws

def canonical_terminal_callback(command: str, cwd: Optional[str] = None, sandboxed: Optional[bool] = None, permission_level: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a terminal shell command according to the active permission tier and sandbox policy.

    Security Contract:
    - In restricted tiers ('sandboxed', 'low', 'medium'), execution is strictly sandboxed.
      Filesystem writes are constrained to the workspace boundary via OS container isolation.
      Shell redirection ('>') or chaining ('cd .. && ...') outside the workspace is denied.
      If OS sandbox isolation is unavailable, execution fails closed.
    - In 'full' tier, execution is privileged and unconfined on the host when sandboxed=False.
      Validating cwd sets the initial process directory, but does NOT provide filesystem isolation.
      Full tier execution returns backend='unconfined_host' and sandboxed=False.
    """
    # Check if dangerous
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            raise PermissionError(f"BLOCKED: Dangerous command '{blocked}' detected.")

    workspace_dir = get_workspace_dir()
    target_cwd = cwd if cwd else workspace_dir
    
    # Boundary enforcement for cwd parameter
    is_valid_cwd = is_within_workspace(target_cwd, workspace_dir)
    if not is_valid_cwd:
        try:
            from lmms_worktree.manager import default_worktree_manager
            for s in default_worktree_manager.active_sessions.values():
                if is_within_workspace(target_cwd, s.worktree_dir):
                    is_valid_cwd = True
                    workspace_dir = s.worktree_dir
                    break
        except Exception:
            pass

    if not is_valid_cwd:
        raise PermissionError("CWD is outside the allowed workspace boundary.")

    # Resolve permission level: explicit argument or runtime config, strictly normalized
    raw_perm = permission_level if permission_level is not None else config.get("permission_level", "medium")
    perm_level = raw_perm.lower() if isinstance(raw_perm, str) and raw_perm.lower() in ("sandboxed", "low", "medium", "full") else "medium"

    effective_sandboxed = True if sandboxed is None else bool(sandboxed)
    if perm_level != "full":
        # In restricted modes (sandboxed, low, medium), execution MUST be sandboxed
        effective_sandboxed = True

    if effective_sandboxed:
        from lmms_sandbox.runner import default_runner
        res = default_runner.run(command, workspace_dir=workspace_dir, cwd=target_cwd, enforce_sandbox=True)
        if not res.success and res.exit_code == -1 and res.backend_used == "none":
            raise PermissionError(
                "REFUSED: Sandbox isolation unavailable (bubblewrap/bwrap not found on system).\n"
                "Reason: LMMS operates in fail-closed security mode; commands will not execute on host without container isolation.\n"
                "Remedy: Install bubblewrap (`sudo apt install bubblewrap`) or explicitly allow host execution via `/perm full`."
            )
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.exit_code,
            "output": res.output,
            "sandboxed": True,
            "backend": res.backend_used,
        }

    # Fail-closed: Direct host execution blocked unless permission level is 'full'
    if perm_level != "full":
        raise PermissionError(
            "REFUSED: Direct un-sandboxed execution on host is blocked.\n"
            "Reason: Unsandboxed execution can mutate host environment.\n"
            "Remedy: Enable sandboxing or explicitly set permission tier to full via `/perm full`."
        )

    try:
        if isinstance(command, str):
            shell_meta = any(op in command for op in [">", "<", "|", "&&", "||", ";", "$(", "`"])
            if shell_meta:
                command_args = ["bash", "-c", command]
            else:
                command_args = shlex.split(command)
        else:
            command_args = list(command)

        # Automatically convert interactive commands to batch mode
        if command_args and command_args[0] == "top" and "-b" not in command_args:
            command_args = ["top", "-b", "-n", "1"]
        if command_args and command_args[0] == "sudo" and "-n" not in command_args:
            command_args.insert(1, "-n")

        result = subprocess.run(
            command_args, shell=False, capture_output=True, text=True, timeout=120, cwd=target_cwd, stdin=subprocess.DEVNULL
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "output": result.stdout + result.stderr or "Command executed successfully with no output.",
            "sandboxed": False,
            "backend": "unconfined_host",
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError("Command timed out after 120 seconds.")
    except Exception as e:
        raise Exception(f"Error executing command: {str(e)}")

default_registry.register(ToolDefinition(
    name="system.terminal",
    description="Execute shell commands. In restricted mode (default), commands are strictly isolated to the workspace via container sandbox. In full mode, commands execute with unconfined host privileges.",
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

    def run(self, command: str, require_confirm=False, cwd=None, return_exit_code=False, sandboxed: Optional[bool] = None, permission_level: Optional[str] = None) -> Any:
        """
        Executes a terminal shell command.

        Security Contract:
        - Restricted tiers ('sandboxed', 'low', 'medium'): execution is strictly container-isolated.
          Shell redirection outside the workspace is denied. Fail-closed if sandbox unavailable.
        - 'full' tier: privileged host execution (unconfined_host) when sandboxed=False.
        """
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

        workspace_dir = get_workspace_dir()
        target_cwd = cwd if cwd else workspace_dir

        is_valid_cwd = is_within_workspace(target_cwd, workspace_dir)
        if not is_valid_cwd:
            try:
                from lmms_worktree.manager import default_worktree_manager
                for s in default_worktree_manager.active_sessions.values():
                    if is_within_workspace(target_cwd, s.worktree_dir):
                        is_valid_cwd = True
                        workspace_dir = s.worktree_dir
                        break
            except Exception:
                pass

        if not is_valid_cwd:
            msg = "CWD is outside the allowed workspace boundary."
            return (-1, msg) if return_exit_code else msg

        # Resolve permission level: explicit argument or runtime config, strictly normalized
        raw_perm = permission_level if permission_level is not None else config.get("permission_level", "medium")
        perm_level = raw_perm.lower() if isinstance(raw_perm, str) and raw_perm.lower() in ("sandboxed", "low", "medium", "full") else "medium"

        effective_sandboxed = True if sandboxed is None else bool(sandboxed)
        if perm_level != "full":
            # In restricted modes (sandboxed, low, medium), execution MUST be sandboxed
            effective_sandboxed = True

        if effective_sandboxed:
            from lmms_sandbox.runner import default_runner
            res = default_runner.run(
                command,
                workspace_dir=workspace_dir,
                cwd=target_cwd,
                require_confirm=False,
                confirm_callback=(lambda c, r: True),
                enforce_sandbox=True
            )
            if not res.success and res.exit_code == -1 and res.backend_used == "none":
                msg = (
                    "REFUSED: Sandbox containment unavailable (bubblewrap/bwrap not found on system).\n"
                    "Reason: LMMS operates in fail-closed security mode; commands will not execute on host without container isolation.\n"
                    "Remedy: Install bubblewrap (`sudo apt install bubblewrap`) or explicitly allow host execution via `/perm full`."
                )
                return (-1, msg) if return_exit_code else msg
            if return_exit_code:
                return (res.exit_code, res.output)
            return res.output

        # Fail-closed: refusing un-sandboxed execution unless permission_level is explicitly 'full'
        if perm_level != "full":
            msg = (
                "REFUSED: Direct un-sandboxed execution on host is blocked.\n"
                "Reason: Unsandboxed execution can mutate host environment.\n"
                "Remedy: Enable sandboxing or explicitly set permission tier to full via `/perm full`."
            )
            return (-1, msg) if return_exit_code else msg

        try:
            if isinstance(command, str):
                shell_meta = any(op in command for op in [">", "<", "|", "&&", "||", ";", "$(", "`"])
                if shell_meta:
                    command_args = ["bash", "-c", command]
                else:
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
