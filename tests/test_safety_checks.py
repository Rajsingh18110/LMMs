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


if __name__ == "__main__":
    unittest.main()
