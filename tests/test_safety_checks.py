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
                    self.assertIn("REFUSED: Sandbox isolation unavailable", str(ctx.exception))
                    self.assertIn("/perm full", str(ctx.exception))

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

    def test_4c_undo_warns_and_preserves_post_agent_user_manual_edits(self):
        """When user manually modifies a file after the agent turn, /undo must warn and NOT overwrite."""
        svc_file = os.path.join(self.tmp_dir, "service.py")
        with open(svc_file, "w") as f:
            f.write("# Initial file version\nPORT = 8000\n")

        mgr = get_turn_checkpoint_manager(self.tmp_dir)
        mgr.start_turn(turn_id="turn_agent_work", summary="agent edits port")

        # Agent modifies file
        canonical_file_write(svc_file, "# Agent version\nPORT = 9000\n")
        mgr.end_turn()

        # User now manually edits the file post-agent turn
        with open(svc_file, "w") as f:
            f.write("# USER MANUAL WORK POST-AGENT\nPORT = 7777\n")

        # Attempt to undo without force
        ok, msg = mgr.undo(force=False)

        # Must refuse / warn to protect manual user edits
        self.assertFalse(ok, f"Undo should have refused due to post-turn manual edits, but got msg: {msg}")
        self.assertIn("modified after agent turn", msg)
        self.assertIn("service.py", msg)

        # Verify file on disk still contains the user's manual edits!
        with open(svc_file, "r") as f:
            disk_content = f.read()
        self.assertEqual(disk_content, "# USER MANUAL WORK POST-AGENT\nPORT = 7777\n")

        # With explicit force=True, it should allow overwriting AND create a reversible .pre_force.bak backup
        ok_force, msg_force = mgr.undo(force=True)
        self.assertTrue(ok_force)
        with open(svc_file, "r") as f:
            restored_content = f.read()
        self.assertEqual(restored_content, "# Initial file version\nPORT = 8000\n")

        # Verify .pre_force.bak was created and holds user's manual edits
        bak_file = svc_file + ".pre_force.bak"
        self.assertTrue(os.path.exists(bak_file), f"Expected backup file {bak_file} to exist")
        with open(bak_file, "r") as f:
            bak_content = f.read()
        self.assertEqual(bak_content, "# USER MANUAL WORK POST-AGENT\nPORT = 7777\n")
        self.assertIn("backed up manual edits to service.py.pre_force.bak", msg_force)

    def test_worktree_edge_untracked_file_collision(self):
        """(a) Agent creates new file and user has untracked file of same name -> REFUSE merge and retain worktree."""
        import subprocess
        subprocess.run(["git", "init"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@lmms.local"], cwd=self.tmp_dir, capture_output=True, check=True)

        base_file = os.path.join(self.tmp_dir, "base.py")
        with open(base_file, "w") as f:
            f.write("# base\n")
        subprocess.run(["git", "add", "base.py"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.tmp_dir, capture_output=True, check=True)

        session = default_worktree_manager.enable(self.tmp_dir)
        wt_new_file = os.path.join(session.worktree_dir, "feature.py")
        with open(wt_new_file, "w") as f:
            f.write("def feature(): return 'agent'\n")

        # User creates untracked file of same name in main workspace
        user_file = os.path.join(self.tmp_dir, "feature.py")
        with open(user_file, "w") as f:
            f.write("# User untracked local draft\n")

        applied, msg = default_worktree_manager.apply(self.tmp_dir)
        self.assertFalse(applied, "Merge should be refused due to untracked file collision")
        self.assertIn("CONFLICT_PREVENTED", msg)
        self.assertIn("feature.py", msg)

        # Verify worktree is retained and user file is unharmed
        self.assertIn(os.path.abspath(self.tmp_dir), default_worktree_manager.active_sessions)
        self.assertTrue(os.path.exists(session.worktree_dir))
        with open(user_file, "r") as f:
            self.assertEqual(f.read(), "# User untracked local draft\n")

        default_worktree_manager.discard(self.tmp_dir)

    def test_worktree_edge_rename_collision(self):
        """(b) Rename collision: agent renames file while user modified original -> REFUSE merge and retain worktree."""
        import subprocess
        subprocess.run(["git", "init"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@lmms.local"], cwd=self.tmp_dir, capture_output=True, check=True)

        mod_file = os.path.join(self.tmp_dir, "data_model.py")
        with open(mod_file, "w") as f:
            f.write("class Model: pass\n")
        subprocess.run(["git", "add", "data_model.py"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init model"], cwd=self.tmp_dir, capture_output=True, check=True)

        session = default_worktree_manager.enable(self.tmp_dir)
        # Agent renames data_model.py to models.py in worktree
        subprocess.run(["git", "mv", "data_model.py", "models.py"], cwd=session.worktree_dir, capture_output=True, check=True)

        # User modifies data_model.py in working directory
        with open(mod_file, "a") as f:
            f.write("# User added field\n")

        applied, msg = default_worktree_manager.apply(self.tmp_dir)
        self.assertFalse(applied, "Merge should be refused due to rename collision with dirty working tree")
        self.assertIn("CONFLICT_PREVENTED", msg)
        self.assertIn("data_model.py", msg)

        # Verify worktree retained
        self.assertIn(os.path.abspath(self.tmp_dir), default_worktree_manager.active_sessions)
        self.assertTrue(os.path.exists(session.worktree_dir))
        default_worktree_manager.discard(self.tmp_dir)

    def test_worktree_edge_delete_collision(self):
        """(c) Delete collision: agent modifies file while user deleted it locally -> REFUSE merge and retain worktree."""
        import subprocess
        subprocess.run(["git", "init"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@lmms.local"], cwd=self.tmp_dir, capture_output=True, check=True)

        cfg_file = os.path.join(self.tmp_dir, "settings.json")
        with open(cfg_file, "w") as f:
            f.write('{"env": "dev"}\n')
        subprocess.run(["git", "add", "settings.json"], cwd=self.tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init settings"], cwd=self.tmp_dir, capture_output=True, check=True)

        session = default_worktree_manager.enable(self.tmp_dir)
        # Agent edits settings.json in worktree
        wt_cfg = os.path.join(session.worktree_dir, "settings.json")
        with open(wt_cfg, "w") as f:
            f.write('{"env": "agent_prod"}\n')

        # User deletes settings.json in working tree
        os.remove(cfg_file)

        applied, msg = default_worktree_manager.apply(self.tmp_dir)
        self.assertFalse(applied, "Merge should be refused when agent-touched file is deleted locally by user")
        self.assertIn("CONFLICT_PREVENTED", msg)
        self.assertIn("settings.json", msg)

        # Verify worktree retained
        self.assertIn(os.path.abspath(self.tmp_dir), default_worktree_manager.active_sessions)
        self.assertTrue(os.path.exists(session.worktree_dir))
        default_worktree_manager.discard(self.tmp_dir)


if __name__ == "__main__":
    unittest.main()
