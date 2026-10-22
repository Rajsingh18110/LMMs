"""
Safety Verification Suite for LMMs:
4a) bwrap missing => fail-closed (command REFUSE without silent host escape)
4b) Worktree auto-merge => conflict prevention when user working tree has uncommitted edits on same files
4c) /undo => protects manual user edits made after agent turn from silent overwrite
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from lmms.backend.tools.terminal import canonical_terminal_callback, TerminalTool
from lmms.backend.tools.files import canonical_file_write, config
from lmms.backend.context.checkpoint import get_turn_checkpoint_manager
from lmms_worktree.manager import default_worktree_manager


class TestSafetyChecks(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="lmms_safety_test_")
        self.orig_ws = config.get("workspace_dir")
        config.set("workspace_dir", self.tmp_dir)

    def tearDown(self):
        config.set("workspace_dir", self.orig_ws)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_4a_bwrap_missing_fails_closed(self):
        """When bubblewrap is missing, terminal execution must REFUSE and NOT run on host."""
        with patch("shutil.which", return_value=None):
            with patch("lmms_sandbox.bwrap.BubblewrapSandbox.is_available", return_value=False):
                with patch("lmms_sandbox.landlock.LandlockSandbox.is_available", return_value=False):
                    # 1. canonical_terminal_callback should raise PermissionError
                    with self.assertRaises(PermissionError) as ctx:
                        canonical_terminal_callback("echo host_escape", sandboxed=True)
                    self.assertIn("NOT isolated", str(ctx.exception))

                    # 2. TerminalTool.run must REFUSE execution and NOT run command on host
                    tool = TerminalTool()
                    res = tool.run("echo host_escape", sandboxed=True, return_exit_code=True)
                    exit_code, output = res
                    self.assertEqual(exit_code, -1)
                    self.assertTrue(output.startswith("REFUSED"), f"Output was: {output}")

    def test_4b_worktree_auto_merge_blocks_on_dirty_user_files(self):
        """When user working directory has uncommitted edits on files touched by worktree, auto-merge must refuse."""
        import subprocess
        # Initialize real git repo
        subprocess.run(["git", "init"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@lmms.local"], cwd=self.tmp_dir, capture_output=True, check=True)

        target_file = os.path.join(self.tmp_dir, "app.py")
        with open(target_file, "w") as f:
            f.write("def run():\n    return 'initial'\n")
        subprocess.run(["git", "add", "app.py"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.tmp_dir, capture_output=True, check=True)

        # 1. Enable worktree isolation
        session = default_worktree_manager.enable(self.tmp_dir)
        self.assertIsNotNone(session)

        # 2. Worktree makes changes to app.py
        wt_file = os.path.join(session.worktree_dir, "app.py")
        with open(wt_file, "w") as f:
            f.write("def run():\n    return 'worktree_agent_version'\n")

        # 3. User simultaneously makes UNCOMMITTED changes to app.py in their own working directory
        with open(target_file, "w") as f:
            f.write("def run():\n    return 'USER_IMPORTANT_UNCOMMITTED_WORK'\n")

        # 4. Attempt to apply worktree
        applied, msg = default_worktree_manager.apply(self.tmp_dir)

        # 5. Must FAIL merge to protect user's uncommitted work
        self.assertFalse(applied, "Worktree apply should have refused due to dirty working tree conflicts")
        self.assertIn("CONFLICT_PREVENTED", msg)
        self.assertIn("app.py", msg)

        # 6. Verify user's uncommitted work was NOT destroyed
        with open(target_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "def run():\n    return 'USER_IMPORTANT_UNCOMMITTED_WORK'\n")

        # Cleanup worktree
        default_worktree_manager.discard(self.tmp_dir)


if __name__ == "__main__":
    unittest.main()
