import subprocess
import os
from typing import List, Dict, Any, Optional

class GitBranches:
    """
    Production-ready git branch manager.
    Handles branch detection, switching, creation, and state tracking.
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

    def get_current_branch(self) -> str:
        """Returns name of current active branch."""
        proc = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if proc.returncode == 0:
            return proc.stdout.strip()
        return "HEAD"

    def list_branches(self, include_remote: bool = False) -> List[str]:
        """Lists local (and optionally remote) branches."""
        args = ["branch"]
        if include_remote:
            args.append("-a")
        proc = self._run_git(args)
        if proc.returncode != 0:
            return []

        branches = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("*"):
                line = line[1:].strip()
            branches.append(line)
        return branches

    def create_branch(self, branch_name: str, checkout: bool = True) -> Dict[str, Any]:
        """Creates a new branch and optionally checks it out."""
        args = ["checkout", "-b", branch_name] if checkout else ["branch", branch_name]
        proc = self._run_git(args)
        if proc.returncode == 0:
            return {"status": "success", "branch": branch_name}
        return {"status": "error", "error": proc.stderr.strip()}

    def checkout(self, branch_name: str) -> Dict[str, Any]:
        """Switches to the specified branch."""
        proc = self._run_git(["checkout", branch_name])
        if proc.returncode == 0:
            return {"status": "success", "branch": branch_name}
        return {"status": "error", "error": proc.stderr.strip()}

    def delete_branch(self, branch_name: str, force: bool = False) -> Dict[str, Any]:
        """Deletes a branch."""
        flag = "-D" if force else "-d"
        proc = self._run_git(["branch", flag, branch_name])
        if proc.returncode == 0:
            return {"status": "success", "branch": branch_name}
        return {"status": "error", "error": proc.stderr.strip()}
