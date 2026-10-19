#!/usr/bin/env python3
"""
LMMs Engine Centralized Multi-Branch Synchronization Tool.
Automatically propagates engine changes from 'main' to distribution branches:
- engine (Standalone Engine)
- cli (Terminal Studio)
- gui (Desktop Studio)
- backendcode, clicode, enginecode, guicode (Enterprise sync)
"""

import sys
import subprocess

def run_cmd(cmd, check=True):
    print(f"\033[1;36m>\033[0m \033[2m{cmd}\033[0m")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and res.returncode != 0:
        print(f"\033[1;31m✖ Error executing: {cmd}\033[0m\n{res.stderr.strip()}")
        sys.exit(res.returncode)
    return res

def main():
    args = sys.argv[1:]
    should_push = "--push" in args

    print("\n\033[1;37mLMMs Centralized Engine Synchronization\033[0m")
    print("\033[2m──────────────────────────────────────────────────────────────\033[0m")

    # 1. Verify on main
    res = run_cmd("git rev-parse --abbrev-ref HEAD")
    current_branch = res.stdout.strip()
    if current_branch != "main":
        print(f"\033[1;33m⚠ You are currently on branch '{current_branch}'. Please switch to 'main' first.\033[0m")
        sys.exit(1)

    # 2. Sync local distribution branches
    branches = ["cli", "gui", "engine", "backendcode", "clicode", "enginecode", "guicode"]
    for b in branches:
        run_cmd(f"git branch -f {b} main")
        print(f"  \033[1;32m✔\033[0m Synchronized branch \033[1m{b}\033[0m with main")

    # 3. Push if requested
    if should_push:
        push_targets = "main " + " ".join(branches)
        print(f"\n\033[1;36mPushing branches to origin: {push_targets}\033[0m")
        run_cmd(f"git push origin {push_targets}")
        print("\033[1;32m✔ Successfully pushed all branches to origin!\033[0m\n")
    else:
        print("\n\033[2mLocal branches synchronized. Run with '--push' to deploy to GitHub remote.\033[0m\n")

if __name__ == "__main__":
    main()
