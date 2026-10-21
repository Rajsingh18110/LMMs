"""
Tests for LMMs TurnCheckpointManager and non-destructive /undo and /redo.
Verifies turn-level file snapshots, creation rollback, modified restore,
uncommitted user work preservation, and ApplyPatch integration.
"""

import os
import shutil
import tempfile
import unittest

from lmms.backend.tools.files import canonical_file_write, canonical_replace_in_file, FileTool, config
from lmms.backend.context.checkpoint import TurnCheckpointManager, get_turn_checkpoint_manager
from lmms.backend.tools.patch import ApplyPatchEngine


class TestUndoCheckpoint(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="lmms_test_undo_")
        self.orig_ws = config.get("workspace_dir")
        config.set("workspace_dir", self.tmp_dir)
        self.mgr = get_turn_checkpoint_manager(self.tmp_dir)

    def tearDown(self):
        config.set("workspace_dir", self.orig_ws)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_undo_restores_modified_file(self):
        # 1. Existing file before turn
        file_path = os.path.join(self.tmp_dir, "calc.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        # 2. Turn starts
        self.mgr.start_turn(turn_id="turn_01", summary="modify calc")
        
        # 3. Tool replaces code in file
        ft = FileTool()
        res = ft.replace_in_file(
            file_path,
            "def add(a, b):\n    return a + b",
            "def add(a, b):\n    return a + b + 100"
        )
        self.assertIn("Successfully modified", res)
        self.mgr.end_turn()

        # Verify modified content is present
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertIn("+ 100", f.read())

        # 4. Perform Undo
        ok, msg = self.mgr.undo()
        self.assertTrue(ok)
        self.assertIn("restored calc.py", msg)

        # 5. Verify restored content matches original
        with open(file_path, "r", encoding="utf-8") as f:
            restored_content = f.read()
        self.assertEqual(restored_content, "def add(a, b):\n    return a + b\n")

    def test_undo_deletes_newly_created_file(self):
        new_file = os.path.join(self.tmp_dir, "generated_service.py")
        self.assertFalse(os.path.exists(new_file))

        self.mgr.start_turn(turn_id="turn_02", summary="create new service")
        canonical_file_write(new_file, "# New service\ndef run():\n    pass\n")
        self.mgr.end_turn()

        self.assertTrue(os.path.exists(new_file))

        # Undo must remove the file because it did not exist before turn
        ok, msg = self.mgr.undo()
        self.assertTrue(ok)
        self.assertIn("removed newly created generated_service.py", msg)
        self.assertFalse(os.path.exists(new_file))

    def test_undo_non_destructive_preserves_other_uncommitted_files(self):
        """Crucial test: User work on other files MUST NOT be destroyed by /undo."""
        # User has uncommitted work in user_script.py
        user_file = os.path.join(self.tmp_dir, "user_script.py")
        with open(user_file, "w", encoding="utf-8") as f:
            f.write("# MY IMPORTANT UNCOMMITTED WORK\ndef my_draft():\n    return 42\n")

        agent_file = os.path.join(self.tmp_dir, "agent_target.py")
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write("# original agent file\n")

        # Agent runs turn on agent_target.py only
        self.mgr.start_turn(turn_id="turn_03", summary="agent edits agent_target")
        ft = FileTool()
        ft.write(agent_file, "# modified by agent\nx = 1\n")
        self.mgr.end_turn()

        # Call undo
        ok, msg = self.mgr.undo()
        self.assertTrue(ok)

        # Check agent file was reverted
        with open(agent_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "# original agent file\n")

        # Check user work was COMPLETELY PRESERVED
        with open(user_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "# MY IMPORTANT UNCOMMITTED WORK\ndef my_draft():\n    return 42\n")

    def test_redo_reapplies_changes(self):
        target = os.path.join(self.tmp_dir, "redo_test.py")
        with open(target, "w", encoding="utf-8") as f:
            f.write("v1 = True\n")

        self.mgr.start_turn(turn_id="turn_04", summary="update v1")
        canonical_file_write(target, "v1 = False\n")
        self.mgr.end_turn()

        # Undo
        ok, _ = self.mgr.undo()
        self.assertTrue(ok)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "v1 = True\n")

        # Redo
        ok, msg = self.mgr.redo()
        self.assertTrue(ok)
        self.assertIn("re-applied redo_test.py", msg)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "v1 = False\n")

    def test_patch_engine_integration_with_undo(self):
        engine = ApplyPatchEngine(workspace_root=self.tmp_dir)
        main_py = os.path.join(self.tmp_dir, "main.py")
        with open(main_py, "w", encoding="utf-8") as f:
            f.write("def start():\n    return 1\n")

        self.mgr.start_turn(turn_id="turn_05", summary="patch apply")
        patch_text = f"""*** Begin Patch
*** Update File: {main_py}
@@
-    return 1
+    return 999
*** End Patch"""
        res = engine.apply_patch(patch_text)
        self.assertTrue(res["success"], f"Patch apply failed: {res}")
        self.mgr.end_turn()

        with open(main_py, "r", encoding="utf-8") as f:
            self.assertIn("999", f.read())

        # Undo
        ok, msg = self.mgr.undo()
        self.assertTrue(ok)
        with open(main_py, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "def start():\n    return 1\n")


if __name__ == "__main__":
    unittest.main()
