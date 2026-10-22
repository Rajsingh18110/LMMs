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


def verify_workspace_state(workspace: str) -> dict:
    """Verifies workspace syntax and git diff status before emitting final completion."""
    review = git_review(workspace)
    syntax_errors = []
    if workspace and workspace != "None" and os.path.isdir(workspace):
        try:
            diff_proc = subprocess.run(
                ["git", "diff", "--name-only"], cwd=workspace, capture_output=True, text=True, check=False
            )
            untracked_proc = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"], cwd=workspace, capture_output=True, text=True, check=False
            )
            diff_files = set(diff_proc.stdout.splitlines() + untracked_proc.stdout.splitlines())
            for rel in diff_files:
                if rel.endswith(".py"):
                    full_p = os.path.join(workspace, rel)
                    if os.path.isfile(full_p):
                        try:
                            import ast
                            with open(full_p, "r", encoding="utf-8") as f:
                                ast.parse(f.read(), filename=rel)
                        except SyntaxError as syn_err:
                            syntax_errors.append(f"{rel}:{syn_err.lineno}: {syn_err.msg}")
        except Exception:
            pass

    return {
        "git": review,
        "syntax_clean": len(syntax_errors) == 0,
        "syntax_errors": syntax_errors,
        "passed": review.get("clean", True) and len(syntax_errors) == 0,
    }
