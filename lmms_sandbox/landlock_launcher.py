"""
lmms_sandbox.landlock_launcher - Tiny helper launcher for Landlock LSM child execution.
Runs in a separate child process before execve, eliminating preexec_fn deadlock risks in multi-threaded programs.
"""

import ctypes
import json
import os
import sys
from typing import List

from lmms_sandbox.landlock import LandlockSandbox, PR_SET_NO_NEW_PRIVS, libc


def main() -> None:
    # Arguments structure:
    # --ro <json_list> --rw <json_list> [--cwd <path>] -- <cmd_args...>
    args = sys.argv[1:]
    if "--" not in args:
        sys.stderr.write("Usage: python3 -m lmms_sandbox.landlock_launcher --ro <json> --rw <json> [--cwd <dir>] -- <cmd...>\n")
        sys.exit(1)

    dash_idx = args.index("--")
    flag_args = args[:dash_idx]
    target_cmd = args[dash_idx + 1:]

    if not target_cmd:
        sys.stderr.write("landlock_launcher: no target command specified\n")
        sys.exit(1)

    ro_paths: List[str] = []
    rw_paths: List[str] = []
    cwd_path: str = ""

    i = 0
    while i < len(flag_args):
        if flag_args[i] == "--ro" and i + 1 < len(flag_args):
            try:
                ro_paths = json.loads(flag_args[i + 1])
            except Exception:
                ro_paths = flag_args[i + 1].split(":")
            i += 2
        elif flag_args[i] == "--rw" and i + 1 < len(flag_args):
            try:
                rw_paths = json.loads(flag_args[i + 1])
            except Exception:
                rw_paths = flag_args[i + 1].split(":")
            i += 2
        elif flag_args[i] == "--cwd" and i + 1 < len(flag_args):
            cwd_path = flag_args[i + 1]
            i += 2
        else:
            i += 1

    # 1. Change cwd if specified
    if cwd_path and os.path.isdir(cwd_path):
        try:
            os.chdir(cwd_path)
        except OSError as e:
            sys.stderr.write(f"landlock_launcher: chdir failed: {e}\n")
            sys.exit(1)

    # 2. Set PR_SET_NO_NEW_PRIVS before applying restrictions
    if libc is not None and hasattr(libc, "prctl"):
        prctl_res = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        if prctl_res != 0:
            sys.stderr.write("landlock_launcher: prctl(PR_SET_NO_NEW_PRIVS) failed\n")
            sys.exit(1)

    # 3. Apply Landlock restrictions
    sandbox = LandlockSandbox()
    if sandbox.is_available():
        ok = sandbox.apply_restriction(read_paths=ro_paths, write_paths=rw_paths)
        if not ok:
            sys.stderr.write("landlock_launcher: Landlock restriction failed\n")
            sys.exit(1)

    # 4. Replace current process with target command via os.execvp
    try:
        os.execvp(target_cmd[0], target_cmd)
    except FileNotFoundError:
        sys.stderr.write(f"landlock_launcher: {target_cmd[0]}: command not found\n")
        sys.exit(127)
    except PermissionError:
        sys.stderr.write(f"landlock_launcher: {target_cmd[0]}: permission denied\n")
        sys.exit(126)
    except Exception as e:
        sys.stderr.write(f"landlock_launcher: execvp failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
