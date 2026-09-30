"""Diff previews and read-only Git review helpers for the CLI."""

import difflib
import os
import subprocess


READ_ONLY_COMMANDS = {"cat", "find", "git", "grep", "head", "ls", "pwd", "rg", "sed", "tail", "tree"}
READ_ONLY_GIT_SUBCOMMANDS = {"diff", "log", "show", "status"}


def preview_file_change(path: str, new_content: str) -> str:
    old_content = ""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as existing_file:
                old_content = existing_file.read()
        except (OSError, UnicodeDecodeError) as exc:
            return f"Unable to preview {path}: {exc}"

    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{os.path.basename(path)}" if old_content else "/dev/null",
        tofile=f"b/{os.path.basename(path)}",
    )
    return "".join(diff) or "No file changes."


def is_read_only_command(command: str) -> bool:
    parts = command.strip().split()
    if not parts or parts[0] not in READ_ONLY_COMMANDS:
        return False
    return parts[0] != "git" or len(parts) > 1 and parts[1] in READ_ONLY_GIT_SUBCOMMANDS


def git_review(workspace: str) -> dict:
    if not workspace or workspace == "None" or not os.path.isdir(os.path.join(workspace, ".git")):
        return {"available": False, "message": "No active Git workspace."}

    stat = subprocess.run(["git", "diff", "--stat"], cwd=workspace, capture_output=True, text=True, check=False)
    check = subprocess.run(["git", "diff", "--check"], cwd=workspace, capture_output=True, text=True, check=False)
    return {
        "available": True,
        "stat": stat.stdout.strip() or "No unstaged changes.",
        "check": check.stdout.strip() or "No whitespace errors.",
        "clean": check.returncode == 0,
    }
