#!/usr/bin/env python3
"""
End-to-End Test for UnifiedToolExecutor:
Runs 10 real emitted tool calls (including name and argument aliases)
through UnifiedToolExecutor and verifies actual execution.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.registry import ToolRegistry
from lmms.backend.orchestration.executor import UnifiedToolExecutor


class TestUnifiedToolExecutorEndToEnd(unittest.TestCase):

    def setUp(self):
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self._orig_env_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        os.environ["LMMS_ACTIVE_WORKSPACE"] = self.workspace_root
        self.registry = ToolRegistry()
        self.executor = UnifiedToolExecutor(self.registry)

    def tearDown(self):
        if self._orig_env_ws is not None:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = self._orig_env_ws
        else:
            os.environ.pop("LMMS_ACTIVE_WORKSPACE", None)

    def test_01_files_read_canonical(self):
        res = self.executor.execute("files.read", {"path": "README.md"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "files.read")
        self.assertTrue(len(res.data) > 0)
        self.assertTrue("LMMs" in res.data or "content" in res.data)
        self.assertIn("<observation>", res.formatted_observation)

    def test_02_files_read_alias_and_argument_normalizer(self):
        # Alias 'read_file' with 'file_path' kwarg
        res = self.executor.execute("read_file", {"file_path": "README.md"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "files.read")
        self.assertTrue(len(res.data) > 0)
        self.assertTrue("LMMs" in res.data or "content" in res.data)

    def test_03_terminal_run_canonical(self):
        res = self.executor.execute("terminal.run", {"command": "echo 'EXECUTOR_TEST_CANONICAL'"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "terminal.run")
        self.assertIn("EXECUTOR_TEST_CANONICAL", str(res.data))

    def test_04_terminal_run_alias_normalizer(self):
        # Alias 'run_terminal' with 'cmd' kwarg
        res = self.executor.execute("run_terminal", {"cmd": "echo 'ALIAS_NORMALIZER_TEST'"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "terminal.run")
        self.assertIn("ALIAS_NORMALIZER_TEST", str(res.data))

    def test_05_app_list(self):
        res = self.executor.execute("app.list", {"filter_query": ""})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "app.list")
        self.assertIn("installed desktop application", str(res.data).lower())

    def test_06_message_send_desktop(self):
        res = self.executor.execute("message.send", {"message": "Test notification", "platform": "desktop"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "message.send")
        self.assertIn("desktop notification", str(res.data).lower())

    def test_07_security_generate_report(self):
        res = self.executor.execute("security.generate_report", {"findings_summary": "Zero critical vulnerabilities found."})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "security.generate_report")
        self.assertIn("Security Audit Report", res.formatted_observation)

    def test_08_discover_additional_tool(self):
        res = self.executor.execute("discover_additional_tool", {"capability": "web_search"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "discover_additional_tool")
        self.assertIn("web_search", res.data.get("tool_id", ""))

    def test_09_files_list(self):
        res = self.executor.execute("files.list", {"path": "."})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "files.list")
        self.assertIn("README.md", str(res.data))

    def test_10_raw_qwen_style_emitted_call(self):
        # Emitted string with <tool_call> tags and 'name' / 'arguments'
        raw_output = "<tool_call>\n{\"name\": \"terminal.run\", \"arguments\": {\"command\": \"whoami\"}}\n</tool_call>"
        res = self.executor.execute_raw(raw_output)
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "terminal.run")
        self.assertIn("<observation>", res.formatted_observation)
        self.assertTrue(len(res.formatted_observation) > 15)


if __name__ == "__main__":
    unittest.main()
