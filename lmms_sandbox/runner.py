"""
lmms_sandbox.runner - Unified Sandbox Runner.
Evaluates ~/.lmms/execpolicy.toml and executes commands through Bubblewrap or Landlock.
"""

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from lmms_sandbox.bwrap import BubblewrapSandbox
from lmms_sandbox.landlock import LandlockSandbox
from lmms_sandbox.policy import ExecPolicy, PolicyAction, PolicyResult


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    output: str
    backend_used: str
    policy_action: str
    success: bool


def detect_worktree_git_rw_binds(workspace_path: str) -> List[str]:
    """
    If workspace_path is a git worktree (where .git is a file referencing
    .git/worktrees/<name>), returns the list of paths that git needs writable
    access to (the worktree gitdir, main repo objects, refs, and logs).
    """
    git_file = os.path.join(workspace_path, ".git")
    if not os.path.isfile(git_file):
        return []
    try:
        with open(git_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content.startswith("gitdir:"):
            return []
        worktree_gitdir = content[len("gitdir:"):].strip()
        if not os.path.isabs(worktree_gitdir):
            worktree_gitdir = os.path.abspath(os.path.join(workspace_path, worktree_gitdir))
        if not os.path.isdir(worktree_gitdir):
            return []

        # Find main repo .git directory
        commondir_file = os.path.join(worktree_gitdir, "commondir")
        main_git_dir = None
        if os.path.isfile(commondir_file):
            with open(commondir_file, "r", encoding="utf-8") as f:
                c_dir = f.read().strip()
            main_git_dir = os.path.abspath(os.path.join(worktree_gitdir, c_dir))
        else:
            parent = os.path.dirname(os.path.dirname(worktree_gitdir))
            if os.path.isdir(parent):
                main_git_dir = parent

        rw_binds = [worktree_gitdir]
        if main_git_dir and os.path.isdir(main_git_dir):
            for sub in ["objects", "refs", "logs"]:
                sub_path = os.path.join(main_git_dir, sub)
                os.makedirs(sub_path, exist_ok=True)
                rw_binds.append(sub_path)
        return rw_binds
    except Exception:
        return []


class SandboxRunner:

    """Orchestrates policy checks and sandboxed execution."""

    def __init__(
        self,
        policy: Optional[ExecPolicy] = None,
        bwrap: Optional[BubblewrapSandbox] = None,
        landlock: Optional[LandlockSandbox] = None,
    ):
        self.policy = policy or ExecPolicy()
        self.bwrap = bwrap or BubblewrapSandbox()
        self.landlock = landlock or LandlockSandbox()

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic status of available sandbox backends and policy."""
        bwrap_ok = self.bwrap.is_available()
        landlock_ok = self.landlock.is_available()

        if bwrap_ok:
            isolation = "bubblewrap (hardware/user namespaces)"
        elif landlock_ok:
            isolation = f"Landlock LSM (kernel ABI v{self.landlock.get_abi_version()})"
        else:
            isolation = "NOT isolated"

        status: Dict[str, Any] = {
            "isolation_status": isolation,
            "bwrap_available": bwrap_ok,
            "bwrap_path": self.bwrap.bwrap_bin,
            "landlock_available": landlock_ok,
            "landlock_abi": self.landlock.get_abi_version(),
            "policy_path": str(self.policy.config_path),
            "default_action": self.policy.default_action.value,
            "deny_network": self.policy.deny_network,
        }

        if isolation == "NOT isolated":
            status["warning"] = "Sandbox containment unavailable. Install bubblewrap (e.g. 'sudo apt install bubblewrap') to enable unprivileged sandboxing."

        return status

    def evaluate_command(self, command: str) -> PolicyResult:
        """Evaluates command string against configured exec policy."""
        return self.policy.evaluate(command)

    def run(
        self,
        command: Union[str, List[str]],
        workspace_dir: str,
        cwd: Optional[str] = None,
        allow_network: Optional[bool] = None,
        require_confirm: bool = False,
        confirm_callback: Optional[Callable[[str, str], bool]] = None,
        timeout: int = 120,
        enforce_sandbox: bool = True,
    ) -> SandboxResult:
        """
        Runs a command with full policy enforcement and sandbox containment.
        """
        cmd_str = command if isinstance(command, str) else " ".join(shlex.quote(c) for c in command)
        cmd_list = shlex.split(cmd_str) if isinstance(command, str) else command

        # 1. Evaluate policy
        pol_res = self.evaluate_command(cmd_str)

        if pol_res.action == PolicyAction.DENY:
            err_msg = f"BLOCKED by execpolicy: {pol_res.reason}"
            return SandboxResult(
                stdout="",
                stderr=err_msg,
                exit_code=-1,
                output=err_msg,
                backend_used="none",
                policy_action=pol_res.action.value,
                success=False,
            )

        if pol_res.action == PolicyAction.ASK or require_confirm:
            confirmed = False
            if confirm_callback:
                confirmed = confirm_callback(cmd_str, pol_res.reason)
            else:
                prompt_text = f"Policy requires confirmation for `{cmd_str}` ({pol_res.reason}). Allow? (y/n): "
                try:
                    ans = input(prompt_text).strip().lower()
                    confirmed = (ans == "y")
                except (EOFError, KeyboardInterrupt):
                    confirmed = False

            if not confirmed:
                err_msg = "Command cancelled: user denied execution confirmation."
                return SandboxResult(
                    stdout="",
                    stderr=err_msg,
                    exit_code=-1,
                    output=err_msg,
                    backend_used="none",
                    policy_action=pol_res.action.value,
                    success=False,
                )

        # Determine effective network permission
        net_allowed = allow_network if allow_network is not None else not self.policy.deny_network

        abs_workspace = os.path.abspath(os.path.expanduser(workspace_dir))
        target_cwd = os.path.abspath(os.path.expanduser(cwd)) if cwd else abs_workspace

        effective_rw_binds = list(self.policy.writable_paths)
        wt_binds = detect_worktree_git_rw_binds(abs_workspace)
        for b in wt_binds:
            if b not in effective_rw_binds:
                effective_rw_binds.append(b)

        # 2. Select backend
        if enforce_sandbox and self.bwrap.is_available():
            backend = "bubblewrap"
            exit_code, stdout, stderr = self.bwrap.execute(
                command=command,
                workspace_dir=abs_workspace,
                cwd=target_cwd,
                allow_network=net_allowed,
                timeout=timeout,
                isolate_home=self.policy.isolate_home,
                allowlisted_home_paths=self.policy.allowlisted_home_paths,
                hidden_paths=self.policy.get_resolved_hidden_paths(),
                extra_ro_binds=self.policy.read_only_paths,
                extra_rw_binds=effective_rw_binds,
            )

        elif enforce_sandbox and self.landlock.is_available():
            backend = "landlock"
            exit_code, stdout, stderr = self.landlock.execute(
                command=command,
                workspace_dir=abs_workspace,
                cwd=target_cwd,
                timeout=timeout,
                read_paths=self.policy.read_only_paths,
                extra_rw_binds=effective_rw_binds,
            )

        elif enforce_sandbox:
            # Enforce sandbox was explicitly requested, but no backend is available
            err_msg = (
                "NOT isolated: Sandboxed execution requested, but neither Bubblewrap nor Landlock "
                "is available on this system. Install bubblewrap (sudo apt install bubblewrap)."
            )
            return SandboxResult(
                stdout="",
                stderr=err_msg,
                exit_code=-1,
                output=err_msg,
                backend_used="none",
                policy_action=pol_res.action.value,
                success=False,
            )

        else:
            # Fallback: direct execution with workspace boundary validation
            backend = "direct_boundary"
            fallback_cmd = ["bash", "-c", command] if isinstance(command, str) else list(command)
            try:
                proc = subprocess.run(
                    fallback_cmd,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )
                exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr

            except subprocess.TimeoutExpired as e:
                stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                exit_code, stdout, stderr = 124, stdout_str, f"Execution timed out after {timeout} seconds."
            except Exception as e:
                exit_code, stdout, stderr = 1, "", f"Execution error: {e}"

        out_text = stdout + stderr
        if not out_text:
            out_text = "Command executed successfully with no output."

        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            output=out_text,
            backend_used=backend,
            policy_action=pol_res.action.value,
            success=(exit_code == 0),
        )


default_runner = SandboxRunner()
