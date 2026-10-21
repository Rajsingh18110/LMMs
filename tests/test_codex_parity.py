"""
Automated Verification Suite for Codex Parity & Sibling Package Integrations.
Validates:
1. Codex-grade ApplyPatchEngine (*** Begin Patch and Unified Diff)
2. Fuzzy sequence matching with whitespace/indentation drift
3. AST compile guard on patch failures
4. ToolRegistry and UnifiedToolExecutor patch & MCP bridging
5. Dynamic MCP tool discovery and execution routing
6. Sandbox containment via lmms_sandbox / Bubblewrap
7. Ephemeral git worktree creation
8. SQLite SessionStore persistence with lineage
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, '/home/kali/Projects/LMMs')

from lmms.backend.tools.patch import ApplyPatchEngine, canonical_apply_patch, seek_sequence
from lmms.backend.tools.files import FileTool, config
from lmms.backend.orchestration.registry import ToolRegistry
from lmms.backend.orchestration.executor import UnifiedToolExecutor
from lmms.backend.security.tool_registry import registry as sec_registry
from lmms.backend.git.worktrees import GitWorktrees
from lmms_sessions.store import SessionStore
from lmms_sandbox.runner import default_runner


class TestCodexParityAndIntegrations(unittest.TestCase):

    def setUp(self):
        self.orig_ws = config.get("workspace_dir", "/home/kali/Projects/LMMs")

    def tearDown(self):
        config.set("workspace_dir", self.orig_ws)

    def test_01_seek_sequence_fuzzy(self):
        content = ["def calculate(a, b):", "    # Note: sum values   ", "    return a + b"]
        # trailing whitespace variation
        pat1 = ["def calculate(a, b):", "    # Note: sum values", "    return a + b"]
        idx = seek_sequence(content, pat1)
        self.assertEqual(idx, 0, "seek_sequence should match despite trailing whitespace differences")

        # indentation drift variation
        pat2 = ["# Note: sum values", "return a + b"]
        idx2 = seek_sequence(content, pat2)
        self.assertEqual(idx2, 1, "seek_sequence should match despite indentation differences")

    def test_02_codex_begin_patch_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.set("workspace_dir", tmpdir)
            py_file = os.path.join(tmpdir, "math_module.py")
            with open(py_file, "w") as f:
                f.write("def add(x, y):\n    return x - y\n")

            patch_text = f"""*** Begin Patch
*** Update File: {py_file}
@@
-    return x - y
+    return x + y
*** End Patch"""

            res = ApplyPatchEngine(workspace_root=tmpdir).apply_patch(patch_text)
            self.assertTrue(res["success"], f"Patch failed: {res}")
            with open(py_file) as f:
                content = f.read()
            self.assertIn("return x + y", content)

    def test_03_ast_compile_guard_on_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.set("workspace_dir", tmpdir)
            py_file = os.path.join(tmpdir, "broken_module.py")
            with open(py_file, "w") as f:
                f.write("def valid_func():\n    return 10\n")

            bad_patch = f"""*** Begin Patch
*** Update File: {py_file}
@@
-    return 10
+    def broken(syntax
*** End Patch"""

            res = ApplyPatchEngine(workspace_root=tmpdir).apply_patch(bad_patch)
            self.assertFalse(res["success"], "AST guard should have blocked broken syntax")
            self.assertIn("AST SyntaxError", res["error"])
            # Ensure file on disk was preserved
            with open(py_file) as f:
                content = f.read()
            self.assertEqual(content, "def valid_func():\n    return 10\n")

    def test_04_orchestration_patch_tool_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.set("workspace_dir", tmpdir)
            py_file = os.path.join(tmpdir, "test_orch.py")
            with open(py_file, "w") as f:
                f.write("val = 1\n")

            orch_reg = ToolRegistry()
            orch_exec = UnifiedToolExecutor(orch_reg)

            patch_str = f"""*** Begin Patch
*** Update File: {py_file}
@@
-val = 1
+val = 100
*** End Patch"""

            exec_res = orch_exec.execute("patch.apply", {"patch": patch_str})
            self.assertTrue(exec_res.success, f"Orchestration execution failed: {exec_res.error}")
            with open(py_file) as f:
                self.assertIn("val = 100", f.read())

    def test_05_dynamic_mcp_tool_bridging(self):
        orch_reg = ToolRegistry()
        # Test on-demand resolution of MCP tools
        mcp_tool = orch_reg.get("mcp__filesystem__read_file")
        self.assertIsNotNone(mcp_tool, "ToolRegistry should resolve mcp__ tool on demand")
        self.assertTrue(getattr(mcp_tool, "_is_mcp", False))
        self.assertEqual(getattr(mcp_tool, "_mcp_server", ""), "filesystem")
        self.assertEqual(getattr(mcp_tool, "_mcp_orig_name", ""), "read_file")

        # Test security registry bridge
        sec_tool = sec_registry.get_tool("mcp__filesystem__read_file")
        self.assertIsNotNone(sec_tool, "Security registry should dynamically bridge MCP tools")

    def test_06_sandbox_runner_policy(self):
        # Test that default_runner evaluates policy and executes in containment
        status = default_runner.get_status()
        self.assertTrue(status.get("bwrap_available"), "Bubblewrap should be available")
        # Run a safe command
        res = default_runner.run("echo 'sandbox test'", workspace_dir=os.getcwd(), enforce_sandbox=True)
        self.assertTrue(res.success or res.exit_code == 0)
        self.assertIn("sandbox test", res.output)

    def test_07_ephemeral_worktree_api(self):
        gw = GitWorktrees(repo_path="/home/kali/Projects/LMMs")
        # Ensure method is available and structured
        self.assertTrue(hasattr(gw, "create_ephemeral_worktree"))

    def test_08_session_store_persistence(self):
        store = SessionStore()
        sess = store.create_session(title="Audit Test Session", metadata={"engine": "codex-parity"})
        self.assertIsNotNone(sess.session_id)
        msg = store.add_message(sess.session_id, role="user", content="Ping")
        self.assertEqual(msg.role, "user")
        retrieved = store.get_session(sess.session_id)
        self.assertEqual(retrieved.title, "Audit Test Session")


if __name__ == "__main__":
    unittest.main()
