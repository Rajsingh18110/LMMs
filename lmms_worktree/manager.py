"""
lmms_worktree.manager - Git Worktree Manager for isolated agent execution.
Provides zero-risk file edits and command execution via temporary git worktrees.
"""

import atexit
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def is_pid_alive(pid: int) -> bool:
    """Returns True if a process with given PID is currently alive on the host system."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


@dataclass
class WorktreeSession:
    workspace: str
    worktree_dir: str
    ephemeral_branch: str
    base_branch: str
    base_commit: str
    session_id: str
    is_detached: bool = False


@dataclass
class WorktreeStatus:
    active: bool
    workspace: str
    worktree_dir: Optional[str] = None
    ephemeral_branch: Optional[str] = None
    base_branch: Optional[str] = None
    base_commit: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)


class WorktreeManager:
    """Manages creation, diff inspection, application, discard, and cleanup of isolated git worktrees."""

    def __init__(self, base_temp_dir: Optional[str] = None):
        self.active_sessions: Dict[str, WorktreeSession] = {}
        self.base_temp_dir = base_temp_dir or os.path.join(tempfile.gettempdir(), "lmms_worktrees")
        os.makedirs(self.base_temp_dir, exist_ok=True)
        atexit.register(self.cleanup_all)
        # Perform startup cleanup of stale crash remnants
        try:
            self.clean_stale_worktrees()
        except Exception:
            pass

    def _run_git(self, args: List[str], cwd: str) -> Tuple[int, str, str]:
        """Runs a git command via subprocess."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def is_git_repo(self, workspace: str) -> bool:
        """Returns True if the directory is inside a Git working tree."""
        code, out, _ = self._run_git(["rev-parse", "--is-inside-work-tree"], cwd=workspace)
        return code == 0 and out == "true"

    def get_head_info(self, workspace: str) -> Tuple[str, str, bool]:
        """
        Returns (commit_hash, branch_or_ref, is_detached).
        """
        code, commit, _ = self._run_git(["rev-parse", "HEAD"], cwd=workspace)
        if code != 0:
            raise RuntimeError(f"Failed to resolve Git HEAD in {workspace}")

        code, branch, _ = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace)
        is_detached = (branch == "HEAD")
        return commit, branch, is_detached

    def is_dirty(self, workspace: str) -> bool:
        """Returns True if the git workspace has uncommitted changes or untracked files."""
        code, out, _ = self._run_git(["status", "--porcelain"], cwd=workspace)
        return code == 0 and bool(out)

    def _meta_path(self, session_id: str) -> str:
        return os.path.join(self.base_temp_dir, f"meta_{session_id}.json")

    def enable(self, workspace: str) -> WorktreeSession:
        """
        Enables git worktree isolation for the given workspace.
        Creates a temporary worktree and sets it as the active session.
        """
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))

        if abs_workspace in self.active_sessions:
            return self.active_sessions[abs_workspace]

        if not self.is_git_repo(abs_workspace):
            raise ValueError(f"Directory '{abs_workspace}' is not a Git repository.")

        # Clean any stale worktrees in this repo before creating new one
        self.clean_stale_worktrees(abs_workspace)

        # Check if dirty and create auto checkpoint if available
        if self.is_dirty(abs_workspace):
            try:
                from lmms.backend.cli.checkpoints import create_checkpoint
                create_checkpoint(abs_workspace, "Auto Checkpoint before Worktree creation")
            except Exception:
                pass

        commit_hash, base_branch, is_detached = self.get_head_info(abs_workspace)
        session_id = uuid.uuid4().hex[:8]
        ephemeral_branch = f"lmms-wt-{session_id}"

        worktree_dir = os.path.join(self.base_temp_dir, f"wt_{session_id}")

        # Create the git worktree
        code, _, err = self._run_git(
            ["worktree", "add", "-b", ephemeral_branch, worktree_dir, commit_hash],
            cwd=abs_workspace,
        )
        if code != 0:
            raise RuntimeError(f"Failed to create git worktree: {err}")

        # Save session metadata outside the worktree for crash-safe cleanup
        meta = {
            "session_id": session_id,
            "pid": os.getpid(),
            "workspace": abs_workspace,
            "worktree_dir": worktree_dir,
            "ephemeral_branch": ephemeral_branch,
            "created_at": time.time(),
        }
        try:
            with open(self._meta_path(session_id), "w", encoding="utf-8") as f:
                json.dump(meta, f)
        except OSError:
            pass

        session = WorktreeSession(
            workspace=abs_workspace,
            worktree_dir=worktree_dir,
            ephemeral_branch=ephemeral_branch,
            base_branch=base_branch,
            base_commit=commit_hash,
            session_id=session_id,
            is_detached=is_detached,
        )
        self.active_sessions[abs_workspace] = session
        return session

    def get_session(self, workspace: str) -> Optional[WorktreeSession]:
        """Returns active worktree session for the workspace, if any."""
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        return self.active_sessions.get(abs_workspace)

    def get_active_workspace(self, workspace: str) -> str:
        """Returns the isolated worktree directory if active, else returns the original workspace."""
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        session = self.active_sessions.get(abs_workspace)
        if session and os.path.exists(session.worktree_dir):
            return session.worktree_dir
        return abs_workspace

    def status(self, workspace: str) -> WorktreeStatus:
        """Returns diagnostic status of worktree isolation for workspace."""
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        session = self.active_sessions.get(abs_workspace)

        if not session or not os.path.exists(session.worktree_dir):
            return WorktreeStatus(active=False, workspace=abs_workspace)

        code, out, _ = self._run_git(["status", "--porcelain"], cwd=session.worktree_dir)
        changed_files = []
        if code == 0 and out:
            for line in out.splitlines():
                if line.strip():
                    changed_files.append(line.strip())

        return WorktreeStatus(
            active=True,
            workspace=abs_workspace,
            worktree_dir=session.worktree_dir,
            ephemeral_branch=session.ephemeral_branch,
            base_branch=session.base_branch,
            base_commit=session.base_commit,
            changed_files=changed_files,
        )

    def diff(self, workspace: str) -> str:
        """Returns unified diff of all changes made inside the worktree compared to base commit."""
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        session = self.active_sessions.get(abs_workspace)
        if not session:
            return "Worktree isolation is not active."

        code, out, _ = self._run_git(["diff", session.base_commit], cwd=session.worktree_dir)
        _, untracked, _ = self._run_git(["ls-files", "--others", "--exclude-standard"], cwd=session.worktree_dir)

        result_parts = []
        if out:
            result_parts.append(out)
        if untracked:
            result_parts.append("\n# Untracked new files in worktree:\n" + "\n".join(f"+ {f}" for f in untracked.splitlines()))

        return "\n".join(result_parts) if result_parts else "No changes in worktree."

    def apply(self, workspace: str) -> Tuple[bool, str]:
        """
        Auto-commits untracked, modified, and deleted files in worktree,
        merges into user branch, and cleans up the worktree on success.
        """
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        session = self.active_sessions.get(abs_workspace)
        if not session:
            return False, "Worktree isolation is not active."

        # 1. Auto-commit all changes in worktree (including untracked and deleted)
        _, status_out, _ = self._run_git(["status", "--porcelain"], cwd=session.worktree_dir)
        if status_out.strip():
            # Ensure git author is configured so commit never fails
            _, user_name, _ = self._run_git(["config", "user.name"], cwd=session.worktree_dir)
            if not user_name:
                self._run_git(["config", "user.name", "LMMs Agent"], cwd=session.worktree_dir)
                self._run_git(["config", "user.email", "agent@lmms.local"], cwd=session.worktree_dir)

            self._run_git(["add", "-A"], cwd=session.worktree_dir)
            code, _, err = self._run_git(
                ["commit", "-m", f"Auto-commit worktree changes before apply ({session.ephemeral_branch})"],
                cwd=session.worktree_dir,
            )
            if code != 0:
                return False, f"Failed to auto-commit changes in worktree: {err}"

        # 1.5. Conflict Prevention Guard: Verify user working tree doesn't have conflicting uncommitted changes
        _, wt_diff_files, _ = self._run_git(["diff", "--name-only", f"{session.base_commit}..HEAD"], cwd=session.worktree_dir)
        touched_files = set(f.strip() for f in wt_diff_files.splitlines() if f.strip())
        _, user_dirty_status, _ = self._run_git(["status", "--porcelain"], cwd=abs_workspace)
        user_dirty_files = set()
        for line in user_dirty_status.splitlines():
            if len(line) > 2:
                user_dirty_files.add(line[2:].strip())

        conflicting = touched_files.intersection(user_dirty_files)
        if conflicting:
            conflicts_list = ", ".join(sorted(conflicting))
            return False, (
                f"CONFLICT_PREVENTED: Cannot merge worktree into working directory. "
                f"You have uncommitted changes on {len(conflicting)} file(s): {conflicts_list}. "
                f"Please commit, stash, or revert your changes before applying the worktree.\n"
                f"The worktree remains safely preserved at: {session.worktree_dir}"
            )

        # 2. Create checkpoint in user workspace before merge
        try:
            from lmms.backend.cli.checkpoints import create_checkpoint
            create_checkpoint(abs_workspace, "Before worktree apply")
        except Exception:
            pass

        # 3. Merge ephemeral branch into the user's working tree
        merge_code, _, merge_err = self._run_git(
            ["merge", "--no-ff", "-m", f"Merge worktree {session.ephemeral_branch}", session.ephemeral_branch],
            cwd=abs_workspace,
        )

        if merge_code != 0:
            self._run_git(["merge", "--abort"], cwd=abs_workspace)
            return False, (
                f"Merge conflict detected! Aborted merge to protect working tree.\n"
                f"Details: {merge_err}\n"
                f"The worktree remains available at: {session.worktree_dir}"
            )

        # 4. Cleanup worktree and ephemeral branch
        self.discard(abs_workspace)
        return True, "Worktree changes successfully merged and applied to working tree."

    def discard(self, workspace: str) -> bool:
        """Discards active worktree and removes its temporary branch, directory, and metadata."""
        abs_workspace = os.path.abspath(os.path.expanduser(workspace))
        session = self.active_sessions.pop(abs_workspace, None)
        if not session:
            return True

        # Remove worktree from git tracking
        self._run_git(["worktree", "remove", "--force", session.worktree_dir], cwd=abs_workspace)
        # Delete ephemeral branch
        self._run_git(["branch", "-D", session.ephemeral_branch], cwd=abs_workspace)

        # Remove directory
        if os.path.exists(session.worktree_dir):
            try:
                shutil.rmtree(session.worktree_dir, ignore_errors=True)
            except OSError:
                pass

        # Remove metadata file
        meta_file = self._meta_path(session.session_id)
        if os.path.exists(meta_file):
            try:
                os.remove(meta_file)
            except OSError:
                pass

        return True

    def clean_stale_worktrees(self, workspace: Optional[str] = None) -> List[str]:
        """
        Cleans up stale worktrees and orphaned branches after crashes (e.g. no atexit):
        1. Runs `git worktree prune`
        2. Removes /tmp/lmms_worktrees entries whose owning PID is dead
        3. Removes orphaned `lmms-wt-*` branches in the repository
        """
        cleaned: List[str] = []

        # 1. Prune git worktree metadata in specified workspace
        if workspace and self.is_git_repo(workspace):
            self._run_git(["worktree", "prune"], cwd=workspace)

        # 2. Scan base_temp_dir for stale session metadata
        if os.path.isdir(self.base_temp_dir):
            for entry in os.listdir(self.base_temp_dir):
                if entry.startswith("meta_") and entry.endswith(".json"):
                    meta_path = os.path.join(self.base_temp_dir, entry)
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        pid = int(data.get("pid", 0))
                        wt_dir = data.get("worktree_dir", "")
                        ws = data.get("workspace", "")
                        branch = data.get("ephemeral_branch", "")

                        # If owning process is dead, clean it up!
                        if not is_pid_alive(pid):
                            if ws and os.path.isdir(ws) and self.is_git_repo(ws):
                                if wt_dir:
                                    self._run_git(["worktree", "remove", "--force", wt_dir], cwd=ws)
                                if branch:
                                    self._run_git(["branch", "-D", branch], cwd=ws)
                                self._run_git(["worktree", "prune"], cwd=ws)

                            if wt_dir and os.path.exists(wt_dir):
                                shutil.rmtree(wt_dir, ignore_errors=True)

                            os.remove(meta_path)
                            cleaned.append(f"stale_worktree:{wt_dir}")

                    except Exception:
                        pass

                # Clean directories that have no metadata and no live session
                elif entry.startswith("wt_"):
                    dir_path = os.path.join(self.base_temp_dir, entry)
                    session_id = entry[3:]
                    meta_file = self._meta_path(session_id)
                    # If directory has no corresponding metadata file and is not active in current process
                    if not os.path.exists(meta_file):
                        is_active = any(s.worktree_dir == dir_path for s in self.active_sessions.values())
                        if not is_active:
                            shutil.rmtree(dir_path, ignore_errors=True)
                            cleaned.append(f"orphaned_dir:{dir_path}")

        # 3. Clean orphaned lmms-wt-* branches in workspace
        if workspace and self.is_git_repo(workspace):
            code, branches_out, _ = self._run_git(["branch", "--list", "lmms-wt-*"], cwd=workspace)
            if code == 0 and branches_out:
                _, wt_list_out, _ = self._run_git(["worktree", "list", "--porcelain"], cwd=workspace)
                active_branches: Set[str] = set()
                for line in wt_list_out.splitlines():
                    if line.startswith("branch refs/heads/"):
                        active_branches.add(line.split("branch refs/heads/")[1].strip())

                for raw_br in branches_out.splitlines():
                    br = raw_br.replace("*", "").strip()
                    if br and br.startswith("lmms-wt-") and br not in active_branches:
                        self._run_git(["branch", "-D", br], cwd=workspace)
                        cleaned.append(f"orphaned_branch:{br}")

            self._run_git(["worktree", "prune"], cwd=workspace)

        return cleaned

    def cleanup_all(self) -> None:
        """Cleans up all active worktrees on normal process exit."""
        workspaces = list(self.active_sessions.keys())
        for ws in workspaces:
            try:
                self.discard(ws)
            except Exception:
                pass


default_worktree_manager = WorktreeManager()
