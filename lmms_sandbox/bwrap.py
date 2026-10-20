"""
lmms_sandbox.bwrap - Unprivileged Bubblewrap (bwrap) subprocess wrapper.
Constructs and executes containment commands using Linux user namespaces.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union


class BubblewrapSandbox:
    """Wrapper for building and executing unprivileged commands inside bubblewrap."""

    def __init__(self, bwrap_path: Optional[str] = None):
        self.bwrap_bin = bwrap_path or shutil.which("bwrap") or "bwrap"

    def is_available(self) -> bool:
        """Returns True if the bubblewrap binary exists on PATH."""
        return shutil.which(self.bwrap_bin) is not None

    def build_command(
        self,
        command: Union[str, List[str]],
        workspace_dir: str,
        cwd: Optional[str] = None,
        allow_network: bool = False,
        read_only_root: bool = True,
        isolate_home: bool = True,
        allowlisted_home_paths: Optional[List[str]] = None,
        hidden_paths: Optional[List[str]] = None,
        extra_ro_binds: Optional[List[str]] = None,
        extra_rw_binds: Optional[List[str]] = None,
        only_existing: bool = True,
    ) -> List[str]:
        """
        Builds the argv list for unprivileged bwrap execution without root.
        This function does not require root permissions and can be tested safely.
        """
        abs_workspace = os.path.abspath(os.path.expanduser(workspace_dir))
        target_cwd = os.path.abspath(os.path.expanduser(cwd)) if cwd else abs_workspace
        user_home = os.path.abspath(os.path.expanduser("~"))

        cmd_argv: List[str] = [self.bwrap_bin]

        # 1. Mount root read-only
        if read_only_root:
            cmd_argv.extend(["--ro-bind", "/", "/"])

        # 2. Virtual system mount points
        cmd_argv.extend([
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
        ])

        # 3. Process containment flags
        cmd_argv.extend([
            "--die-with-parent",
            "--new-session",
        ])

        # 4. Network isolation
        if not allow_network:
            cmd_argv.append("--unshare-net")

        # 5. Deny-by-default home directory isolation:
        # Mount an empty tmpfs over $HOME so all credentials (~/.ssh, ~/.netrc, etc.)
        # are completely hidden by default.
        if isolate_home and (not only_existing or os.path.exists(user_home)):
            cmd_argv.extend(["--tmpfs", user_home])

        # 6. Re-expose explicit allowlisted directories under home (read-only)
        # e.g., model cache (~/.cache/huggingface, ~/.lmms/models)
        if allowlisted_home_paths:
            for p in allowlisted_home_paths:
                exp_p = os.path.abspath(os.path.expanduser(p))
                if not only_existing or os.path.exists(exp_p):
                    cmd_argv.extend(["--ro-bind", exp_p, exp_p])

        # 7. Mask any additional explicit hidden paths
        if hidden_paths:
            for p in hidden_paths:
                exp_path = os.path.abspath(os.path.expanduser(p))
                if not only_existing or os.path.exists(exp_path):
                    cmd_argv.extend(["--tmpfs", exp_path])

        # 6. Extra read-only binds (avoid mounting over host symlinks like /bin -> usr/bin)
        if extra_ro_binds:
            for ro in extra_ro_binds:
                exp_ro = os.path.abspath(os.path.expanduser(ro))
                if os.path.islink(exp_ro) and only_existing:
                    continue
                if not only_existing or os.path.exists(exp_ro):
                    if not read_only_root or not only_existing:
                        cmd_argv.extend(["--ro-bind", exp_ro, exp_ro])

        # 7. Writable workspace bind (and any extra writable binds)
        if not only_existing or os.path.exists(abs_workspace):
            cmd_argv.extend(["--bind", abs_workspace, abs_workspace])

        if target_cwd != abs_workspace:
            if not only_existing or os.path.exists(target_cwd):
                cmd_argv.extend(["--bind", target_cwd, target_cwd])

        if extra_rw_binds:
            for rw in extra_rw_binds:
                exp_rw = os.path.abspath(os.path.expanduser(rw))
                if not only_existing or os.path.exists(exp_rw):
                    cmd_argv.extend(["--bind", exp_rw, exp_rw])

        # 8. Set working directory inside sandbox
        cmd_argv.extend(["--chdir", target_cwd])

        # 9. Format command execution payload
        if isinstance(command, str):
            cmd_argv.extend(["bash", "-c", command])
        else:
            cmd_argv.extend(command)

        return cmd_argv

    def execute(
        self,
        command: Union[str, List[str]],
        workspace_dir: str,
        cwd: Optional[str] = None,
        allow_network: bool = False,
        timeout: int = 120,
        isolate_home: bool = True,
        allowlisted_home_paths: Optional[List[str]] = None,
        hidden_paths: Optional[List[str]] = None,
        extra_ro_binds: Optional[List[str]] = None,
        extra_rw_binds: Optional[List[str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Executes the command inside bubblewrap.
        Returns (exit_code, stdout, stderr).
        """
        if not self.is_available():
            raise RuntimeError(
                f"Bubblewrap binary '{self.bwrap_bin}' not found on system. "
                "Please install bubblewrap (e.g. apt install bubblewrap)."
            )

        full_cmd = self.build_command(
            command=command,
            workspace_dir=workspace_dir,
            cwd=cwd,
            allow_network=allow_network,
            isolate_home=isolate_home,
            allowlisted_home_paths=allowlisted_home_paths,
            hidden_paths=hidden_paths,
            extra_ro_binds=extra_ro_binds,
            extra_rw_binds=extra_rw_binds,
            only_existing=True,
        )

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = f"Execution timed out after {timeout} seconds."
            return 124, stdout_str, stderr_str
        except Exception as e:
            return 1, "", f"Failed to execute sandboxed command: {e}"
