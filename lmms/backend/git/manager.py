import os
import subprocess
from typing import List, Dict, Optional, Any

from lmms.backend.services.core_services.services.events import EventManager

class GitManager:
    """
    Facade for the LMMs Git Intelligence Layer.
    Handles orchestration of repositories, branches, commits, timeline and watchers.
    """
    def __init__(self, workspace_path: str, event_manager: EventManager):
        self.workspace_path = os.path.abspath(workspace_path)
        self.events = event_manager
        
        # We will initialize sub-components here once created
        self._is_initialized = False

    def initialize(self):
        """Initializes git sub-systems like watchers and timeline."""
        if self._is_initialized:
            return
        # Initialize sub-modules (Repository, Branches, Watchers, etc.)
        self._is_initialized = True
        self.events.publish("GitManagerInitialized", {"path": self.workspace_path})

    def get_current_branch(self) -> str:
        # Stub for branches.py logic
        return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    def get_status(self) -> List[str]:
        # Stub for repository.py logic
        output = self._run_git(["status", "--porcelain"])
        return output.splitlines() if output else []

    def get_diff_summary(self) -> str:
        # Stub for diff.py logic
        return self._run_git(["diff", "--stat", "HEAD"])

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
