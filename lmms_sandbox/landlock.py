"""
lmms_sandbox.landlock - Fallback unprivileged filesystem sandbox via Linux Landlock LSM.
Uses ctypes to invoke SYS_landlock_create_ruleset, landlock_add_rule, and landlock_restrict_self.
"""

import ctypes
import os
import platform
import subprocess
from typing import List, Optional, Tuple, Union

libc = None
try:
    if platform.system() == "Linux":
        libc = ctypes.CDLL(None, use_errno=True)
except Exception:
    libc = None

# Landlock syscall constants
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446
PR_SET_NO_NEW_PRIVS = 38

LANDLOCK_CREATE_RULESET_VERSION = 1 << 0
LANDLOCK_RULE_PATH_BENEATH = 1

# Filesystem access rights (ABI v1-v3)
LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14

ACCESS_FS_RO = (
    LANDLOCK_ACCESS_FS_EXECUTE
    | LANDLOCK_ACCESS_FS_READ_FILE
    | LANDLOCK_ACCESS_FS_READ_DIR
)

ACCESS_FS_RW = (
    ACCESS_FS_RO
    | LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SYM
    | LANDLOCK_ACCESS_FS_TRUNCATE
)


class LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


class LandlockSandbox:
    """Provides unprivileged Landlock filesystem restriction via ctypes."""

    def __init__(self):
        self._abi_version: Optional[int] = None

    def get_abi_version(self) -> int:
        """Probes the kernel for supported Landlock ABI version. Returns 0 if unsupported."""
        if self._abi_version is not None:
            return self._abi_version

        if libc is None or not hasattr(libc, "syscall"):
            self._abi_version = 0
            return 0

        try:
            res = libc.syscall(SYS_LANDLOCK_CREATE_RULESET, None, 0, LANDLOCK_CREATE_RULESET_VERSION)
            self._abi_version = max(0, int(res))
        except Exception:
            self._abi_version = 0

        return self._abi_version

    def is_available(self) -> bool:
        """Returns True if the running kernel supports Landlock (ABI >= 1)."""
        return self.get_abi_version() >= 1

    def apply_restriction(self, read_paths: List[str], write_paths: List[str]) -> bool:
        """
        Applies Landlock restrictions to the current process.
        Should typically be called in a child process before exec.
        """
        if not self.is_available() or libc is None:
            return False

        # Build ruleset attribute
        attr = LandlockRulesetAttr(handled_access_fs=ACCESS_FS_RW)
        ruleset_fd = libc.syscall(
            SYS_LANDLOCK_CREATE_RULESET,
            ctypes.byref(attr),
            ctypes.sizeof(attr),
            0,
        )
        if ruleset_fd < 0:
            return False

        try:
            # 1. Add read-only paths
            for p in read_paths:
                if not os.path.exists(p):
                    continue
                try:
                    fd = os.open(p, os.O_PATH | os.O_CLOEXEC)
                except OSError:
                    continue
                try:
                    pb = LandlockPathBeneathAttr(allowed_access=ACCESS_FS_RO, parent_fd=fd)
                    libc.syscall(SYS_LANDLOCK_ADD_RULE, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(pb), 0)
                finally:
                    os.close(fd)

            # 2. Add read-write paths (e.g. workspace, /tmp)
            for p in write_paths:
                if not os.path.exists(p):
                    continue
                try:
                    fd = os.open(p, os.O_PATH | os.O_CLOEXEC)
                except OSError:
                    continue
                try:
                    pb = LandlockPathBeneathAttr(allowed_access=ACCESS_FS_RW, parent_fd=fd)
                    libc.syscall(SYS_LANDLOCK_ADD_RULE, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(pb), 0)
                finally:
                    os.close(fd)

            # 3. Restrict current process and future children
            prctl_res = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
            if prctl_res != 0:
                return False

            restrict_res = libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0)
            return restrict_res == 0

        finally:
            os.close(ruleset_fd)

    def execute(
        self,
        command: Union[str, List[str]],
        workspace_dir: str,
        cwd: Optional[str] = None,
        timeout: int = 120,
        read_paths: Optional[List[str]] = None,
        extra_rw_binds: Optional[List[str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Executes a command restricted by Landlock filesystem sandbox.
        Uses a helper launcher child process to set PR_SET_NO_NEW_PRIVS and apply restrictions,
        avoiding risky preexec_fn deadlocks in multi-threaded programs.
        """
        import json
        import sys

        if not self.is_available():
            raise RuntimeError("Landlock is not supported by the host Linux kernel.")

        abs_workspace = os.path.abspath(os.path.expanduser(workspace_dir))
        target_cwd = os.path.abspath(os.path.expanduser(cwd)) if cwd else abs_workspace

        effective_ro = list(read_paths) if read_paths else ["/usr", "/bin", "/lib", "/lib64", "/etc"]
        if sys.prefix not in effective_ro:
            effective_ro.append(sys.prefix)
        py_bin_dir = os.path.dirname(sys.executable)
        if py_bin_dir not in effective_ro:
            effective_ro.append(py_bin_dir)

        effective_rw = [abs_workspace, "/tmp"]
        if extra_rw_binds:
            for p in extra_rw_binds:
                if p not in effective_rw:
                    effective_rw.append(p)


        if isinstance(command, str):
            cmd_args = ["bash", "-c", command]
        else:
            cmd_args = list(command)

        launcher_cmd = [
            sys.executable,
            "-m",
            "lmms_sandbox.landlock_launcher",
            "--ro",
            json.dumps(effective_ro),
            "--rw",
            json.dumps(effective_rw),
            "--cwd",
            target_cwd,
            "--",
        ] + cmd_args

        # Ensure PYTHONPATH includes repo root if running from within repo
        env = dict(os.environ)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        current_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{repo_root}:{current_pp}" if current_pp else repo_root

        try:
            res = subprocess.run(
                launcher_cmd,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env=env,
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired as e:
            stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            return 124, stdout_str, f"Execution timed out after {timeout} seconds."
        except Exception as e:
            return 1, "", f"Landlock execution error: {e}"

