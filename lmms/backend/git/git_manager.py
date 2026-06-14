import os
import subprocess
from typing import List, Dict, Optional
from lmms.backend.db.core_workspace.manager import WorkspaceManager

class GitManager:
    """
    Subprocess-based Git tracking for Workspace Intelligence.
    Tracks branches, status, and incrementally indexes commits into SQLite.
    """
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.manager = WorkspaceManager()
        self.ws_id = self.manager.open(self.workspace_path)
        self.db = self.manager.get_db(self.ws_id)

    def _run_git(self, args: List[str]) -> str:
        """Helper to run a git command and return output string."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def get_current_branch(self) -> str:
        return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    def get_status(self) -> List[str]:
        output = self._run_git(["status", "--porcelain"])
        return output.splitlines() if output else []

    def get_diff_summary(self) -> str:
        return self._run_git(["diff", "--stat", "HEAD"])

    def _get_indexed_hashes(self) -> set:
        rows = self.db.fetchall("SELECT hash FROM git_commits")
        return {row["hash"] for row in rows}

    def index_recent_commits(self) -> int:
        """
        Indexes up to the last 50 commits incrementally.
        """
        output = self._run_git(["log", "-50", "--format=%H|%an|%s|%ai"])
        if not output:
            return 0

        existing_hashes = self._get_indexed_hashes()
        new_commits = 0

        for line in output.splitlines():
            parts = line.split("|", 3)
            if len(parts) != 4:
                continue
                
            hash_val, author, message, date_val = parts
            
            if hash_val in existing_hashes:
                continue

            try:
                self.db.execute("""
                    INSERT OR IGNORE INTO git_commits (hash, author, message, date)
                    VALUES (?, ?, ?, ?)
                """, (hash_val, author, message, date_val))
                new_commits += 1
            except Exception as e:
                print(f"Error indexing commit {hash_val}: {e}")

        return new_commits

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    manager = GitManager(path)
    branch = manager.get_current_branch()
    
    if not branch:
        print("Not a git repository or no commits yet.")
        sys.exit(0)
        
    print(f"Branch: {branch}")
    
    status = manager.get_status()
    print(f"Changed Files: {len(status)}")
    
    diff = manager.get_diff_summary()
    print(f"Diff Summary:\n{diff}")
    
    indexed = manager.index_recent_commits()
    print(f"Newly Indexed Commits: {indexed}")
