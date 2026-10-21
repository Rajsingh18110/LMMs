import subprocess
import os
from typing import List, Dict, Any, Optional

class GitWorktrees:
    """
    Production-ready git worktree manager.
    Executes real git operations to create, remove, and list worktrees safely.
    """
    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False
        )

    def list_worktrees(self) -> List[Dict[str, str]]:
        """Parses git worktree list into structured dictionaries."""
        proc = self._run_git(["worktree", "list", "--porcelain"])
        if proc.returncode != 0:
            return []

        worktrees = []
        current_wt: Dict[str, str] = {}

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                if current_wt:
                    worktrees.append(current_wt)
                    current_wt = {}
                continue

            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                key, val = parts[0], parts[1]
                if key == "worktree":
                    current_wt["path"] = val
                elif key == "HEAD":
                    current_wt["commit"] = val
                elif key == "branch":
                    current_wt["branch"] = val.replace("refs/heads/", "")
            elif len(parts) == 1 and parts[0] == "bare":
                current_wt["bare"] = "true"

        if current_wt:
            worktrees.append(current_wt)

        return worktrees

    def create_worktree(self, path: str, branch: Optional[str] = None, commit: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new worktree at the specified path."""
        args = ["worktree", "add", path]
        if branch:
            args.append(branch)
        elif commit:
            args.append(commit)

        proc = self._run_git(args)
        if proc.returncode == 0:
            return {"status": "success", "path": path, "branch": branch, "message": proc.stdout.strip()}
        else:
            return {"status": "error", "error": proc.stderr.strip() or proc.stdout.strip()}

    def remove_worktree(self, path: str, force: bool = False) -> Dict[str, Any]:
        """Removes a worktree directory."""
        args = ["worktree", "remove", path]
        if force:
            args.append("--force")

        proc = self._run_git(args)
        if proc.returncode == 0:
            return {"status": "success", "path": path}
        else:
            return {"status": "error", "error": proc.stderr.strip()}

    def prune_worktrees(self) -> Dict[str, Any]:
        """Prunes stale worktree information."""
        proc = self._run_git(["worktree", "prune"])
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "message": proc.stdout.strip() or proc.stderr.strip()
        }

    def create_ephemeral_worktree(self, base_workspace: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates an ephemeral git worktree using lmms_worktree manager with PID tracking,
        safe lease locks, and automatic branch derivation.
        """
        try:
            from lmms_worktree.manager import default_worktree_manager
            target_ws = base_workspace or self.repo_path
            wt = default_worktree_manager.create_worktree(target_ws)
            return {
                "status": "success",
                "worktree_dir": wt.worktree_dir,
                "ephemeral_branch": wt.ephemeral_branch,
                "base_branch": wt.base_branch,
                "is_ephemeral": True
            }
        except Exception as e:
            import uuid
            ephemeral_id = uuid.uuid4().hex[:8]
            wt_path = os.path.join(self.repo_path, ".git", "worktrees", f"ephemeral-{ephemeral_id}")
            return self.create_worktree(wt_path, branch=f"lmms-ephemeral-{ephemeral_id}")
