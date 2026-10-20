"""
lmms_worktree - Git Worktree Isolation for LMMs.
Provides temporary isolated working trees so agent file edits and commands
do not touch the user's working tree until approved.
"""

from lmms_worktree.manager import (
    WorktreeManager,
    WorktreeSession,
    WorktreeStatus,
    default_worktree_manager,
)
from lmms_worktree.cli import handle_worktree_cli

__all__ = [
    "WorktreeManager",
    "WorktreeSession",
    "WorktreeStatus",
    "default_worktree_manager",
    "handle_worktree_cli",
]
