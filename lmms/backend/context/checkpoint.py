"""
Turn-level non-destructive snapshot checkpoint manager for LMMs.
Provides instant, atomic undo/redo of AI file modifications without
touching Git history, staging index, or user uncommitted work on other files.
"""

from __future__ import annotations

import os
import time
import json
import uuid
import shutil
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path


class TurnSnapshot:
    """Represents file states before and after a single interaction turn."""

    def __init__(self, turn_id: str, summary: str = "", timestamp: Optional[float] = None):
        self.turn_id = turn_id
        self.summary = summary
        self.timestamp = timestamp or time.time()
        # rel_path -> original bytes (or None if file did not exist before turn)
        self.pre_state: Dict[str, Optional[bytes]] = {}
        # rel_path -> bytes after turn (or None if file was deleted)
        self.post_state: Dict[str, Optional[bytes]] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "files_touched": list(self.pre_state.keys()),
        }


class TurnCheckpointManager:
    """Manages turn-level shadow copies for non-destructive undo and redo."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.active_turn: Optional[TurnSnapshot] = None
        self.undo_stack: List[TurnSnapshot] = []
        self.redo_stack: List[TurnSnapshot] = []
        self.max_history = 50

        # Snapshot storage directory
        self.snapshot_dir = os.path.join(self.workspace_root, ".lmms", "turn_snapshots")
        try:
            os.makedirs(self.snapshot_dir, exist_ok=True)
        except OSError:
            # Fallback to ~/.lmms/turn_snapshots/<hash> if workspace is unwritable
            import hashlib
            h = hashlib.sha256(self.workspace_root.encode("utf-8")).hexdigest()[:16]
            self.snapshot_dir = os.path.expanduser(f"~/.lmms/turn_snapshots/{h}")
            os.makedirs(self.snapshot_dir, exist_ok=True)

    def _to_rel_path(self, path: str) -> str:
        abs_p = os.path.abspath(path if os.path.isabs(path) else os.path.join(self.workspace_root, path))
        return os.path.relpath(abs_p, self.workspace_root)

    def _to_abs_path(self, rel_path: str) -> str:
        return os.path.join(self.workspace_root, rel_path)

    def start_turn(self, turn_id: Optional[str] = None, summary: str = "") -> str:
        """Begin a new turn. Call before AI generates tool calls or edits files."""
        # If previous turn wasn't explicitly ended, end it now
        if self.active_turn is not None:
            self.end_turn()

        tid = turn_id or str(uuid.uuid4())[:8]
        self.active_turn = TurnSnapshot(turn_id=tid, summary=summary)
        return tid

    def record_pre_state(self, path: str):
        """Record the state of a file BEFORE modification in current turn.

        If the file was already recorded in this turn, subsequent writes do NOT
        overwrite the initial pre-turn state.
        """
        if self.active_turn is None:
            # Auto-start an active turn if not already open
            self.start_turn(summary="Auto-tracked turn")

        rel_path = self._to_rel_path(path)
        if rel_path in self.active_turn.pre_state:
            return  # Already captured the pristine pre-turn state

        abs_path = self._to_abs_path(rel_path)
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            try:
                with open(abs_path, "rb") as f:
                    self.active_turn.pre_state[rel_path] = f.read()
            except Exception:
                self.active_turn.pre_state[rel_path] = None
        else:
            # File did not exist before this turn
            self.active_turn.pre_state[rel_path] = None

    def end_turn(self) -> Optional[TurnSnapshot]:
        """Finalize the current turn, record post-state, and push to undo stack."""
        if self.active_turn is None:
            return None

        turn = self.active_turn
        # Record post-state for every touched file
        for rel_path in turn.pre_state.keys():
            abs_path = self._to_abs_path(rel_path)
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                try:
                    with open(abs_path, "rb") as f:
                        turn.post_state[rel_path] = f.read()
                except Exception:
                    turn.post_state[rel_path] = None
            else:
                turn.post_state[rel_path] = None

        # Only store turn if at least one file was actually touched
        if turn.pre_state:
            self.undo_stack.append(turn)
            if len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)
            # A new turn invalidates previous redo history
            self.redo_stack.clear()
            self._persist_turn(turn)

        self.active_turn = None
        return turn

    def _persist_turn(self, turn: TurnSnapshot):
        """Save snapshot metadata to disk for resilience across CLI runs."""
        try:
            turn_dir = os.path.join(self.snapshot_dir, turn.turn_id)
            os.makedirs(turn_dir, exist_ok=True)
            meta = turn.to_dict()
            with open(os.path.join(turn_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            # Save pre copies
            pre_dir = os.path.join(turn_dir, "pre")
            os.makedirs(pre_dir, exist_ok=True)
            for rel_path, data in turn.pre_state.items():
                if data is not None:
                    target = os.path.join(pre_dir, rel_path)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "wb") as f:
                        f.write(data)

            # Save post copies
            post_dir = os.path.join(turn_dir, "post")
            os.makedirs(post_dir, exist_ok=True)
            for rel_path, data in turn.post_state.items():
                if data is not None:
                    target = os.path.join(post_dir, rel_path)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "wb") as f:
                        f.write(data)
        except Exception:
            pass

    def undo(self, target_file: Optional[str] = None) -> Tuple[bool, str]:
        """Undo changes made during the last turn.

        If target_file is provided, only reverts that file from the last turn.
        Otherwise reverts all files modified in the last turn.
        Never touches untouched files, Git index, or uncommitted work.
        """
        # Ensure any active turn is ended first
        if self.active_turn is not None and self.active_turn.pre_state:
            self.end_turn()

        if not self.undo_stack:
            return False, "No actions to undo in turn history."

        turn = self.undo_stack.pop()
        restored = []
        removed = []
        errors = []

        files_to_revert = [self._to_rel_path(target_file)] if target_file else list(turn.pre_state.keys())

        for rel_path in files_to_revert:
            if rel_path not in turn.pre_state:
                continue

            abs_path = self._to_abs_path(rel_path)
            orig_data = turn.pre_state[rel_path]

            try:
                if orig_data is None:
                    # File was newly created in this turn; remove it
                    if os.path.exists(abs_path):
                        if os.path.isfile(abs_path):
                            os.remove(abs_path)
                            removed.append(rel_path)
                else:
                    # Restore original content
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "wb") as f:
                        f.write(orig_data)
                    restored.append(rel_path)
            except Exception as e:
                errors.append(f"{rel_path}: {e}")

        self.redo_stack.append(turn)

        summary_parts = []
        if restored:
            summary_parts.append(f"restored {', '.join(restored)}")
        if removed:
            summary_parts.append(f"removed newly created {', '.join(removed)}")
        if errors:
            summary_parts.append(f"errors: {'; '.join(errors)}")

        action_summary = "; ".join(summary_parts) or "no file changes needed"
        msg = f"Undid turn #{turn.turn_id} ({turn.summary or 'edit'}): {action_summary}."
        return True, msg

    def redo(self, target_file: Optional[str] = None) -> Tuple[bool, str]:
        """Redo changes that were undone.

        Restores the post-turn state of the files.
        """
        if not self.redo_stack:
            return False, "No undone actions to redo."

        turn = self.redo_stack.pop()
        restored = []
        removed = []
        errors = []

        files_to_redo = [self._to_rel_path(target_file)] if target_file else list(turn.post_state.keys())

        for rel_path in files_to_redo:
            if rel_path not in turn.post_state:
                continue

            abs_path = self._to_abs_path(rel_path)
            post_data = turn.post_state[rel_path]

            try:
                if post_data is None:
                    # File was deleted in this turn; re-delete
                    if os.path.exists(abs_path) and os.path.isfile(abs_path):
                        os.remove(abs_path)
                        removed.append(rel_path)
                else:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "wb") as f:
                        f.write(post_data)
                    restored.append(rel_path)
            except Exception as e:
                errors.append(f"{rel_path}: {e}")

        self.undo_stack.append(turn)

        summary_parts = []
        if restored:
            summary_parts.append(f"re-applied {', '.join(restored)}")
        if removed:
            summary_parts.append(f"removed {', '.join(removed)}")
        if errors:
            summary_parts.append(f"errors: {'; '.join(errors)}")

        action_summary = "; ".join(summary_parts) or "no changes"
        msg = f"Redid turn #{turn.turn_id} ({turn.summary or 'edit'}): {action_summary}."
        return True, msg

    def get_history(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.undo_stack]


# Global singleton registry per workspace
_MANAGERS: Dict[str, TurnCheckpointManager] = {}


def get_turn_checkpoint_manager(workspace_root: Optional[str] = None) -> TurnCheckpointManager:
    """Return the TurnCheckpointManager singleton for the given or configured workspace."""
    if not workspace_root or workspace_root == "None":
        from lmms.backend.config import config
        workspace_root = config.get("workspace_dir", os.getcwd())

    ws = os.path.abspath(workspace_root)
    if ws not in _MANAGERS:
        _MANAGERS[ws] = TurnCheckpointManager(ws)
    return _MANAGERS[ws]
