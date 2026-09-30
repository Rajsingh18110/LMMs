"""Shared filesystem boundary checks for tools that operate on a workspace."""

import os


def is_within_workspace(path: str, workspace: str) -> bool:
    """Return whether path resolves inside workspace, including symlink resolution."""
    if not path or not workspace:
        return False

    resolved_path = os.path.realpath(os.path.abspath(path))
    resolved_workspace = os.path.realpath(os.path.abspath(workspace))
    try:
        return os.path.commonpath([resolved_path, resolved_workspace]) == resolved_workspace
    except ValueError:
        return False


def require_workspace_path(path: str, workspace: str) -> str:
    if not is_within_workspace(path, workspace):
        raise PermissionError(f"Path {path} is outside the allowed workspace boundary.")
    return os.path.realpath(os.path.abspath(path))
