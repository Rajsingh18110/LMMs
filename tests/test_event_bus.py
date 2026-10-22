"""
Tests for LMMs Event Bus, RuleRouter execution, ContextCompactor, and Hierarchical AGENTS.md.
"""

import os
import sys
import json
import time
import socket
import shutil
import tempfile
import unittest

from lmms.backend.events.bus import LMMsEventBus, get_event_bus
from lmms.backend.router.rule_router import RuleRouter
from lmms.backend.orchestration.compactor import ContextCompactor
from lmms.backend.context.workspace_rules import load_workspace_rules, find_rule_files


class TestEventBusAndP0Wiring(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="lmms_test_eb_")
        self.sock_path = os.path.join(self.tmp_dir, "test_events.sock")
        self.jsonl_path = os.path.join(self.tmp_dir, "test_events.jsonl")
        self.bus = LMMsEventBus(socket_path=self.sock_path, jsonl_path=self.jsonl_path)

    def tearDown(self):
        self.bus.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_event_bus_jsonl_emission(self):
        # Emit multiple event types
        self.bus.tool_start("terminal.run", {"command": "git status"}, step=1)
        self.bus.tool_end("terminal.run", True, "On branch main", duration_ms=12.5)
        self.bus.patch_applied(["calc.py"], [], diff="@@ -1 +1 @@")
        self.bus.test_result("pytest tests/", 0, True, "5 passed in 0.05s")
        self.bus.error("SyntaxError", "invalid syntax on line 1")

        # Verify JSONL contains all 5 events
        self.assertTrue(os.path.exists(self.jsonl_path))
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]

        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0]["type"], "tool_start")
        self.assertEqual(lines[0]["tool"], "terminal.run")
        self.assertEqual(lines[1]["type"], "tool_end")
        self.assertEqual(lines[1]["success"], True)
        self.assertEqual(lines[2]["type"], "patch_applied")
        self.assertEqual(lines[3]["type"], "test_result")
        self.assertEqual(lines[3]["passed"], True)
        self.assertEqual(lines[4]["type"], "error")
        self.assertEqual(lines[4]["error_type"], "SyntaxError")

    def test_02_event_bus_socket_broadcast(self):
        # Connect a client socket to the bus UNIX domain socket
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        time.sleep(0.1)
        client.connect(self.sock_path)
        time.sleep(0.1)

        # Emit an event
        self.bus.emit("live_pulse", {"status": "active", "node": "Planner"})

        # Client receives JSON line
        client.settimeout(2.0)
        data = client.recv(1024).decode("utf-8")
        client.close()

        self.assertTrue(data.endswith("\n"))
        parsed = json.loads(data.strip())
        self.assertEqual(parsed["type"], "live_pulse")
        self.assertEqual(parsed["status"], "active")

    def test_03_rule_router_deterministic_graph(self):
        router = RuleRouter()
        
        # Test coding intent
        graph_code = router.route("please write a python function to compute fibonacci and test it")
        agents = [s.agent_name for s in graph_code.steps]
        self.assertIn("CodingAgent", agents)
        self.assertIn("TesterAgent", agents)

        # Test workspace file ops
        graph_files = router.route("create a folder named assets and write config.json")
        file_agents = [s.agent_name for s in graph_files.steps]
        self.assertIn("CodingAgent", file_agents)

        # Test general chat
        graph_chat = router.route("hello, what is the capital of France?")
        chat_agents = [s.agent_name for s in graph_chat.steps]
        self.assertIn("ChatAgent", chat_agents)

    def test_04_context_compactor(self):
        compactor = ContextCompactor(recent_turns_to_preserve=2, max_observation_chars=100)
        long_observation = "<observation>\n" + ("x = 1\n" * 50) + "</observation>"
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "run command"},
            {"role": "assistant", "content": "<tool_call>{}</tool_call>"},
            {"role": "user", "content": long_observation},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "next task"},
        ]

        compacted, report = compactor.compact(
            messages=messages,
            usable_budget=100,  # force compaction
            current_prompt_tokens=500
        )

        self.assertGreater(report.tokens_saved_estimate, 0)
        self.assertLessEqual(len(compacted), len(messages))

    def test_05_hierarchical_agents_md(self):
        # Create root AGENTS.md
        root_agents = os.path.join(self.tmp_dir, "AGENTS.md")
        with open(root_agents, "w", encoding="utf-8") as f:
            f.write("# Root Rules: Always write typed code.\n")

        # Create subfolder with sub AGENTS.md
        sub_dir = os.path.join(self.tmp_dir, "backend", "api")
        os.makedirs(sub_dir, exist_ok=True)
        sub_agents = os.path.join(sub_dir, "AGENTS.md")
        with open(sub_agents, "w", encoding="utf-8") as f:
            f.write("# Sub Rules: Use FastAPI and pydantic models.\n")

        # Load rules from sub_dir
        rules = load_workspace_rules(self.tmp_dir, current_dir=sub_dir)
        self.assertIn("Always write typed code", rules)
        self.assertIn("Use FastAPI and pydantic models", rules)

    def test_06_graph_execution_and_rule_injection(self):
        router = RuleRouter()
        graph = router.route("fix the failing unit tests and verify")

        self.assertIn("CodingAgent", [s.agent_name for s in graph.steps])
        self.assertIn("TesterAgent", [s.agent_name for s in graph.steps])

        # workspace rules should be loaded and injected in a usable system prompt fragment
        with open(os.path.join(self.tmp_dir, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# Workspace rules\nDo not ignore verification.\n")

        rule_text = load_workspace_rules(self.tmp_dir)
        self.assertNotEqual(rule_text, "")
        self.assertIn("Do not ignore verification", rule_text)

        exec_out = router.execute_graph(graph)
        self.assertTrue(any("OrchestratorAgent" in line or "CodingAgent" in line or "TesterAgent" in line for line in exec_out))


if __name__ == "__main__":
    unittest.main()
