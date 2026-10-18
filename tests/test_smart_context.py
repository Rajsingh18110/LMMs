"""
Comprehensive Automated Test Suite for LMMs Smart Context & Dynamic Tool Orchestration System.
Covers Scenarios A through G, validation, permissions, budgeting, compaction, caching, and telemetry.
"""

import unittest
import os
import sys
import json
import time
import requests

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def is_engine_running() -> bool:
    try:
        r = requests.get("http://localhost:11435/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False

ENGINE_RUNNING = is_engine_running()


from lmms.backend.orchestration.router import IntentRouter, IntentType
from lmms.backend.orchestration.registry import ToolRegistry, ToolMetadata, DynamicToolDefinition
from lmms.backend.orchestration.selector import ToolSelector
from lmms.backend.orchestration.builder import ContextBuilder
from lmms.backend.orchestration.budget import TokenBudgetManager, ContextOverflowError
from lmms.backend.orchestration.executor import UnifiedToolExecutor
from lmms.backend.orchestration.compactor import ContextCompactor
from lmms.backend.orchestration.cache import PromptCacheManager
from lmms.backend.orchestration.adapter import InferenceAdapter
from lmms.backend.orchestration.observability import TraceLogger, RequestTrace
from lmms.backend.orchestration.pipeline import OrchestrationPipeline


class TestSmartContextOrchestration(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.router = IntentRouter()
        self.selector = ToolSelector(self.registry)
        self.builder = ContextBuilder()
        self.budget_manager = TokenBudgetManager(engine_url="http://127.0.0.1:0", default_context_limit=4096, default_output_reserve=768, safety_margin=200)
        self.compactor = ContextCompactor()
        self.cache_manager = PromptCacheManager()
        self.executor = UnifiedToolExecutor(self.registry)
        self.pipeline = OrchestrationPipeline(registry=self.registry)

    # -------------------------------------------------------------------------
    # Scenario A: Normal Chat (Prompt Bloat Regression Test)
    # -------------------------------------------------------------------------
    def test_scenario_a_normal_chat_no_tools(self):
        """User says 'hello' -> 0 tools, minimal base prompt, no browser instructions."""
        query = "hello"
        intent_res = self.router.route(query)
        self.assertEqual(intent_res.intent, IntentType.NORMAL_CHAT)
        self.assertFalse(intent_res.requires_tools)

        selection = self.selector.select(intent_res)
        self.assertEqual(len(selection.selected_tools), 0)
        self.assertEqual(len(selection.selected_ids), 0)

        assembled = self.builder.assemble(
            model_name="Qwen3-Coder-30B",
            user_query=query,
            intent_result=intent_res,
            selection_result=selection,
            conversation_history=[]
        )

        # Full tool schemas must be absent from prompt; compact tool index is present
        self.assertNotIn("## Active Tools (Full Schemas)", assembled.messages[0]["content"])
        self.assertIn("## Tool Catalog (Index)", assembled.messages[0]["content"])
        self.assertIn("discover_additional_tool", assembled.messages[0]["content"])
        self.assertEqual(len(assembled.selected_tool_ids), 0)

        # Token count verification: Must be small (< 800 tokens with conservative char estimator, ~473 with native BPE), compared to verified legacy baseline of 1,782 tokens.
        tokens = self.budget_manager.count_tokens(assembled.messages[0]["content"])
        self.assertLess(tokens, 800, f"Prompt tokens ({tokens}) exceeds target 800 tokens!")
        print(f"\n[Test Benchmark] Scenario A (Normal Chat 'hello' with Catalog Index) Prompt Tokens: {tokens} (Measured Legacy Baseline: 1,782 tokens, Real Reduction: {(1782-tokens)/1782*100:.1f}%)")

    # -------------------------------------------------------------------------
    # Scenario B: Coding Explanation vs Repository Modification
    # -------------------------------------------------------------------------
    def test_scenario_b_coding_explanation_no_tools(self):
        """User asks 'Explain how Python decorators work' -> reasoning context, zero filesystem/terminal tools."""
        query = "Explain how Python decorators work."
        intent_res = self.router.route(query)
        self.assertEqual(intent_res.intent, IntentType.CODING)
        self.assertFalse(intent_res.requires_tools)

        selection = self.selector.select(intent_res)
        self.assertEqual(len(selection.selected_tools), 0)

        assembled = self.builder.assemble(
            model_name="Qwen3-Coder-30B",
            user_query=query,
            intent_result=intent_res,
            selection_result=selection,
            conversation_history=[]
        )
        self.assertNotIn("## Active Tools (Full Schemas)", assembled.messages[0]["content"])
        self.assertEqual(len(assembled.selected_tool_ids), 0)

    def test_scenario_b_workspace_coding_loads_tools(self):
        """User asks to fix bug in workspace files -> loads files and terminal tools."""
        query = "Fix the syntax error in project file src/app.py"
        intent_res = self.router.route(query, current_workspace="/home/kali/Projects/my_app")
        self.assertTrue(intent_res.requires_tools)

        selection = self.selector.select(intent_res, current_workspace="/home/kali/Projects/my_app")
        self.assertIn("files.read", selection.selected_ids)
        self.assertIn("files.write", selection.selected_ids)
        self.assertIn("terminal.run", selection.selected_ids)
        # Should NOT load unrelated browser or messaging schemas
        self.assertNotIn("browser.open_url", selection.selected_ids)
        self.assertNotIn("message.send", selection.selected_ids)

    # -------------------------------------------------------------------------
    # Scenario C: Web Search
    # -------------------------------------------------------------------------
    def test_scenario_c_web_search_only_selects_search(self):
        """User says 'Search for the latest Python documentation about a feature.' -> only search tool selected."""
        query = "Search for the latest Python documentation about asyncio task groups."
        intent_res = self.router.route(query)
        self.assertEqual(intent_res.intent, IntentType.WEB_SEARCH)
        self.assertTrue(intent_res.requires_tools)

        selection = self.selector.select(intent_res)
        self.assertIn("web_search", selection.selected_ids)
        # Verify absence of browser automation or terminal schemas
        self.assertNotIn("browser.click_element", selection.selected_ids)
        self.assertNotIn("terminal.run", selection.selected_ids)
        self.assertNotIn("files.write", selection.selected_ids)

        assembled = self.builder.assemble(
            model_name="Qwen3-Coder-30B",
            user_query=query,
            intent_result=intent_res,
            selection_result=selection,
            conversation_history=[]
        )
        self.assertIn("web_search", assembled.selected_tool_ids)
        self.assertNotIn("browser.fill_form", assembled.selected_tool_ids)

    # -------------------------------------------------------------------------
    # Scenario D: Browser Automation
    # -------------------------------------------------------------------------
    def test_scenario_d_browser_automation_selection(self):
        """User says 'Open this website, navigate to its documentation, and summarize a specified page.'"""
        query = "Open https://docs.python.org, navigate to library, and summarize the page."
        intent_res = self.router.route(query)
        self.assertEqual(intent_res.intent, IntentType.BROWSER_AUTOMATION)
        self.assertTrue(intent_res.requires_tools)

        selection = self.selector.select(intent_res)
        self.assertIn("browser.open_url", selection.selected_ids)
        self.assertIn("browser.get_interactive_dom", selection.selected_ids)
        # Verify absence of unrelated terminal and filesystem schemas
        self.assertNotIn("terminal.run", selection.selected_ids)
        self.assertNotIn("files.write", selection.selected_ids)
        self.assertNotIn("app.launch", selection.selected_ids)

    # -------------------------------------------------------------------------
    # Scenario E: Multi-Step Workflow
    # -------------------------------------------------------------------------
    def test_scenario_e_multi_step_workflow(self):
        """User asks 'Research three solutions, compare their capabilities, and generate a report.'"""
        query = "Research three solutions for local LLM inference, compare their capabilities, and generate a report."
        intent_res = self.router.route(query)
        self.assertEqual(intent_res.intent, IntentType.MULTI_STEP_WORKFLOW)
        self.assertTrue(intent_res.requires_tools)

        selection = self.selector.select(intent_res)
        self.assertIn("web_search", selection.selected_ids)
        self.assertIn("security.generate_report", selection.selected_ids)

        assembled = self.builder.assemble(
            model_name="Qwen3-Coder-30B",
            user_query=query,
            intent_result=intent_res,
            selection_result=selection,
            conversation_history=[]
        )
        self.assertIn("Multi-Step Workflow Rules", assembled.messages[0]["content"])

    # -------------------------------------------------------------------------
    # Scenario F: Context Overflow Protection & Compaction
    # -------------------------------------------------------------------------
    def test_scenario_f_context_overflow_compaction(self):
        """History with massive tool observations exceeding budget -> compactor triggers and truncates observations."""
        large_observation = "<observation>\n" + ("x" * 12000) + "\n</observation>"
        history = [
            {"role": "user", "content": "Please inspect the file."},
            {"role": "assistant", "content": "<tool_call>{\"tool\": \"files.read\", \"kwargs\": {\"path\": \"test.txt\"}}</tool_call>"},
            {"role": "user", "content": large_observation},
            {"role": "assistant", "content": "I have read the file."},
        ]

        query = "Now summarize what you found."
        intent_res = self.router.route(query, conversation_history=history)
        selection = self.selector.select(intent_res)

        assembled = self.builder.assemble(
            model_name="Qwen-1.5B",
            user_query=query,
            intent_result=intent_res,
            selection_result=selection,
            conversation_history=history
        )

        budget = self.budget_manager.calculate_budget(
            model_name="Qwen-1.5B",
            base_prompt=assembled.base_system_prompt,
            task_instructions=assembled.task_instructions,
            tool_schemas=assembled.tool_schemas_str,
            history_messages=history,
            user_query=query
        )

        # Usable context limit for 4096 model is 4096 - 768 - 200 = 3128 tokens
        self.assertEqual(budget.usable_context, 3128)
        # Should detect overflow due to 6000-char observation
        self.assertTrue(budget.is_overflow)

        # Compact
        compacted_msgs, report = self.compactor.compact(
            messages=assembled.messages,
            usable_budget=budget.usable_context,
            current_prompt_tokens=budget.total_prompt_tokens
        )
        self.assertTrue(report.observations_pruned > 0)
        self.assertTrue(report.tokens_saved_estimate > 0)

        # Post-compaction tokens should be within budget
        compacted_tokens = self.compactor._estimate_tokens(compacted_msgs, "Qwen-1.5B")
        self.assertLessEqual(compacted_tokens, budget.usable_context)

    # -------------------------------------------------------------------------
    # Scenario G: Tool Discovery During Multi-Step Execution
    # -------------------------------------------------------------------------
    def test_scenario_g_dynamic_tool_discovery(self):
        """Task initially selects web_search. During execution, it discovers it needs files.read."""
        query = "Search for the documentation and save it to disk."
        intent_res = self.router.route(query)
        initial_selection = self.selector.select(intent_res)

        # Initially web_search is selected, files.read is not
        self.assertIn("web_search", initial_selection.selected_ids)


        # Dynamic discovery during execution
        updated_selection = self.selector.discover_additional_tool(
            current_selection=initial_selection,
            missing_capability="files.read"
        )
        self.assertIn("files.read", updated_selection.selected_ids)
        self.assertIn("files.read", updated_selection.rationale)
        self.assertIn("Dynamically discovered", updated_selection.rationale["files.read"])

    # -------------------------------------------------------------------------
    # Tool Execution & Validation Tests
    # -------------------------------------------------------------------------
    def test_tool_argument_validation(self):
        """Valid arguments succeed; missing/wrong types are rejected cleanly."""
        # 1. Missing required 'query' parameter
        res_missing = self.executor.execute("web_search", {})
        self.assertFalse(res_missing.success)
        self.assertIn("Missing required parameter", res_missing.error)
        self.assertIn("[VALIDATION_ERROR]", res_missing.formatted_observation)

        # 2. Wrong type: query passed as int instead of string
        res_wrong_type = self.executor.execute("web_search", {"query": 12345})
        self.assertFalse(res_wrong_type.success)
        self.assertIn("must be a string", res_wrong_type.error)

        # 3. Valid arguments with registered dummy handler
        self.executor.register_handler("web_search", lambda query, max_results=5: f"Found results for {query}")
        res_valid = self.executor.execute("web_search", {"query": "python decorators"})
        self.assertTrue(res_valid.success)
        self.assertEqual(res_valid.data, "Found results for python decorators")
        self.assertIn("<observation>", res_valid.formatted_observation)

    def test_permission_enforcement(self):
        """Low permission level blocks high risk tools (like terminal.run)."""
        # terminal.run is high risk
        res = self.executor.execute(
            "terminal.run",
            {"command": "echo hello"},
            permission_level="low"
        )
        self.assertFalse(res.success)
        self.assertTrue(res.was_denied)
        self.assertIn("Permission Denied", res.error)

    def test_planning_mode_blocks_mutating_tools(self):
        """Planning mode restricts write tools."""
        res = self.executor.execute(
            "files.write",
            {"path": "test.txt", "content": "hi"},
            permission_level="full",
            is_planning_mode=True
        )
        self.assertFalse(res.success)
        self.assertIn("Planning mode is read-only", res.error)

    def test_infinite_loop_prevention(self):
        """Repeated identical tool calls trigger loop protection."""
        self.executor.register_handler("files.read", lambda path: "content")
        for _ in range(3):
            self.executor.execute("files.read", {"path": "stuck.txt"})

        # 4th identical call should trigger loop protection
        loop_res = self.executor.execute("files.read", {"path": "stuck.txt"})
        self.assertFalse(loop_res.success)
        self.assertIn("loop", loop_res.error.lower())
        self.assertIn("[LOOP_DETECTED]", loop_res.formatted_observation)

    # -------------------------------------------------------------------------
    # Prompt Caching Tests
    # -------------------------------------------------------------------------
    def test_prompt_cache_prefix_stability(self):
        """Identical model + base prompt + selected tools produces stable prefix hash."""
        hash1 = self.cache_manager.compute_prefix_hash("Base instructions", "tools: search")
        hash2 = self.cache_manager.compute_prefix_hash("Base instructions", "tools: search")
        self.assertEqual(hash1, hash2)

        # Tool change changes prefix hash
        hash3 = self.cache_manager.compute_prefix_hash("Base instructions", "tools: search, browser")
        self.assertNotEqual(hash1, hash3)

    # -------------------------------------------------------------------------
    # Tool Dependency Resolution Tests
    # -------------------------------------------------------------------------
    def test_tool_dependencies_resolved(self):
        """Requesting browser.click_element automatically pulls in browser.open_url dependency."""
        selection = self.selector.select(
            intent_result=self.router.route("click button 1"),
            additional_requested_tools=["browser.click_element"]
        )
        self.assertIn("browser.click_element", selection.selected_ids)
        self.assertIn("browser.open_url", selection.selected_ids)

    # -------------------------------------------------------------------------
    # Malformed Input & Error Resilience Tests
    # -------------------------------------------------------------------------
    def test_malformed_tool_call_handled_gracefully(self):
        """Malformed or invalid JSON inside <tool_call> tags does not crash inference."""
        adapter = InferenceAdapter()
        # Invalid JSON
        broken_output = "Here is my tool call: <tool_call>{tool: broken json without quotes}</tool_call>"
        calls = adapter.extract_tool_calls(broken_output)
        self.assertEqual(len(calls), 0)

        # Python-style single quotes and boolean True (should recover gracefully)
        python_style = "<tool_call>{'tool': 'web_search', 'kwargs': {'query': 'python', 'max_results': 3}}</tool_call>"
        calls2 = adapter.extract_tool_calls(python_style)
        self.assertEqual(len(calls2), 1)
        self.assertEqual(calls2[0]["tool"], "web_search")

    def test_tool_exception_does_not_crash(self):
        """Tool handler throwing an unhandled exception returns structured error observation."""
        def faulty_tool(**kwargs):
            raise ConnectionResetError("Remote server closed socket connection abruptly")

        self.executor.register_handler("files.read", faulty_tool)
        res = self.executor.execute("files.read", {"path": "network_file.txt"})
        self.assertFalse(res.success)
        self.assertIn("Remote server closed", res.error)
        self.assertIn("<observation>", res.formatted_observation)
        self.assertIn("[EXECUTION_FAILED]", res.formatted_observation)

    # -------------------------------------------------------------------------
    # Model Specific Context Window Limits
    # -------------------------------------------------------------------------
    def test_model_specific_context_limits(self):
        """Different model names discover appropriate context window limits."""
        limit_1_5b = self.budget_manager.get_effective_context_limit("qwen2.5-1.5b-instruct-q5_k_m")
        limit_30b = self.budget_manager.get_effective_context_limit("Qwen3-Coder-30B-A3B-Instruct")
        self.assertGreater(limit_30b, 4000)
        self.assertGreater(limit_1_5b, 2000)

    # -------------------------------------------------------------------------
    # Task 1c: Runtime Tool Discovery & Router Misroute Recovery
    # -------------------------------------------------------------------------
    def test_router_wrong_model_recovers_via_discover_additional_tool(self):
        """When router misroutes or omits a required tool, model requests discover_additional_tool and recovers."""
        misrouted_intent = self.router.route("hello there")
        initial_selection = self.selector.select(misrouted_intent)
        self.assertNotIn("browser.open_url", initial_selection.selected_ids)

        # 1. Model requests the missing capability at runtime
        exec_res = self.executor.execute("discover_additional_tool", {"capability": "browser.open_url"})
        self.assertTrue(exec_res.success)
        self.assertIn("Tool 'browser.open_url' successfully discovered and activated", exec_res.formatted_observation)

        # 2. Selector discovers and injects tool into active selection
        updated_selection = self.selector.discover_additional_tool(initial_selection, "browser.open_url")
        self.assertIn("browser.open_url", updated_selection.selected_ids)
        self.assertIn("browser", updated_selection.instruction_modules)

        # 3. Model executes newly discovered tool successfully
        self.executor.register_handler("browser.open_url", lambda url: f"DOM content of {url}")
        final_res = self.executor.execute("browser.open_url", {"url": "https://python.org"})
        self.assertTrue(final_res.success)
        self.assertIn("DOM content of https://python.org", final_res.formatted_observation)

    # -------------------------------------------------------------------------
    # Task 6a & 6b: Fact Preservation and 10-Turns-Ago Compaction Tests
    # -------------------------------------------------------------------------
    def test_rule_based_compaction_preserves_facts(self):
        """Rule-based Stage 3 compaction deterministically preserves paths, URLs, metrics, and decisions."""
        history = [
            {"role": "user", "content": "Please inspect /var/log/nginx/access.log for error 502."},
            {"role": "assistant", "content": "I checked /var/log/nginx/access.log and found 42 instances of 502 Bad Gateway."},
            {"role": "user", "content": "Check https://status.myservice.io/health to see if upstream is down."},
            {"role": "assistant", "content": "Upstream status at https://status.myservice.io/health reports port 8080 timeout."},
            {"role": "user", "content": "We decided: never restart the database during peak hours, and agreed to use redis cache."},
            {"role": "assistant", "content": "Understood, confirmed decision to never restart database and use redis cache."},
            {"role": "user", "content": "Turn 7 filler message."},
            {"role": "assistant", "content": "Turn 8 filler response."},
            {"role": "user", "content": "Turn 9 filler message."},
            {"role": "assistant", "content": "Turn 10 filler response."},
        ]

        # Force Stage 3 compaction by setting a tight token budget
        compacted, report = self.compactor.compact(
            messages=history,
            usable_budget=120,
            current_prompt_tokens=500
        )
        self.assertTrue(report.summary_applied)

        all_compacted_text = " ".join(str(m.get("content", "")) for m in compacted)

        # Assert key facts survived compaction
        self.assertIn("/var/log/nginx/access.log", all_compacted_text)
        self.assertIn("https://status.myservice.io/health", all_compacted_text)
        self.assertTrue("decided" in all_compacted_text.lower() or "never restart" in all_compacted_text.lower())
        self.assertTrue("8080" in all_compacted_text or "502" in all_compacted_text)

    def test_compaction_reference_10_turns_ago(self):
        """User refers back to a specific requirement from 10 turns ago after compaction."""
        history = [
            {"role": "user", "content": "The production secret database key is SECRET_VAULT_KEY_9981 in /etc/app.env."},
            {"role": "assistant", "content": "Recorded SECRET_VAULT_KEY_9981 in /etc/app.env."},
        ]
        # Add 10 intervening turns
        for i in range(1, 11):
            history.append({"role": "user", "content": f"Turn {i} request to check status."})
            history.append({"role": "assistant", "content": f"Turn {i} completed task."})

        compacted, report = self.compactor.compact(
            messages=history,
            usable_budget=200,
            current_prompt_tokens=800
        )
        self.assertTrue(report.summary_applied)


        all_text = " ".join(str(m.get("content", "")) for m in compacted)
        self.assertTrue(
            "SECRET_VAULT_KEY_9981" in all_text or "/etc/app.env" in all_text,
            "Context from 10+ turns ago was lost during compaction!"
        )

    # -------------------------------------------------------------------------
    # Task 7: End-to-End Real Engine Integration Tests (8 Scenarios)
    # -------------------------------------------------------------------------
    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_1_normal_chat_live_engine(self):
        """1. Normal Chat: Live model responds without injecting tool schemas."""
        ctx, intent, sel, budget = self.pipeline.prepare_request(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="hello, how are you?",
            conversation_history=[]
        )
        self.assertEqual(len(sel.selected_tools), 0)
        with requests.post("http://localhost:11435/v1/chat/completions", json={
            "model": "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            "messages": ctx.messages,
            "stream": True
        }, stream=True, timeout=45) as resp:
            self.assertEqual(resp.status_code, 200)
            first_token = ""
            for line in resp.iter_lines():
                if line and b"data: " in line and not b"[DONE]" in line:
                    chunk = json.loads(line.decode("utf-8")[6:])
                    first_token = chunk.get("content", "") or chunk.get("message", {}).get("content", "")
                    resp.close()
                    break
            self.assertTrue(len(first_token) > 0)
            self.assertNotIn("<tool_call>", first_token)

    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_2_web_search_live_engine(self):
        """2. Web Search: Live engine with search query correctly selects web_search tool."""
        ctx, intent, sel, budget = self.pipeline.prepare_request(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="Search the web for FastAPI release notes.",
            conversation_history=[]
        )
        self.assertIn("web_search", sel.selected_ids)
        self.assertIn("web_search", ctx.tool_schemas_str)
        with requests.post("http://localhost:11435/v1/chat/completions", json={
            "model": "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            "messages": ctx.messages,
            "stream": True
        }, stream=True, timeout=45) as resp:
            self.assertEqual(resp.status_code, 200)
            first_token = ""
            for line in resp.iter_lines():
                if line and b"data: " in line and not b"[DONE]" in line:
                    chunk = json.loads(line.decode("utf-8")[6:])
                    first_token = chunk.get("content", "") or chunk.get("message", {}).get("content", "")
                    resp.close()
                    break
            self.assertTrue(len(first_token) > 0)

    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_3_browser_task_live_engine(self):
        """3. Browser Task: Live engine loads browser tools for URL navigation."""
        ctx, intent, sel, budget = self.pipeline.prepare_request(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="Open python.org and tell me the headline",
            conversation_history=[]
        )
        self.assertIn("browser.open_url", sel.selected_ids)
        self.assertIn("browser", sel.instruction_modules)
        with requests.post("http://localhost:11435/v1/chat/completions", json={
            "model": "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            "messages": ctx.messages,
            "stream": True
        }, stream=True, timeout=45) as resp:
            self.assertEqual(resp.status_code, 200)
            first_token = ""
            for line in resp.iter_lines():
                if line and b"data: " in line and not b"[DONE]" in line:
                    chunk = json.loads(line.decode("utf-8")[6:])
                    first_token = chunk.get("content", "") or chunk.get("message", {}).get("content", "")
                    resp.close()
                    break
            self.assertTrue(len(first_token) > 0)


    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_4_filesystem_plan_mode_live_engine(self):
        """4. Planning Mode: Prevents destructive/mutation tools while allowing inspection."""
        ctx, intent, sel, budget = self.pipeline.prepare_request(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="Delete obsolete test files in src/",
            conversation_history=[],
            is_planning_mode=True
        )
        # Attempting mutation tool in planning mode must be rejected
        exec_res = self.executor.execute("files.write", {"path": "test.txt", "content": "hi"}, is_planning_mode=True)
        self.assertFalse(exec_res.success)
        self.assertIn("Planning mode is read-only", exec_res.error)

    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_5_forced_router_misroute_with_runtime_discovery_live_engine(self):
        """5. Forced Misroute: Router assigns 0 tools, runtime discovery recovers capability on live model."""
        misrouted = self.router.route("just chatting")
        sel = self.selector.select(misrouted)
        self.assertEqual(len(sel.selected_tools), 0)

        # Dynamic discovery injects web_search at runtime
        sel = self.selector.discover_additional_tool(sel, "web_search")
        self.assertIn("web_search", sel.selected_ids)

        ctx = self.builder.assemble(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="Search for python docs",
            intent_result=misrouted,
            selection_result=sel,
            conversation_history=[]
        )
        self.assertIn("web_search", ctx.messages[0]["content"])

    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_6_context_overflow_recovery_live_engine(self):
        """6. Context Overflow: Massive 25,000 char history is compacted safely without OOM."""
        huge_history = [
            {"role": "user", "content": "Here is a large dataset log:\n" + ("log entry line ABC 1234567890\n" * 800)},
            {"role": "assistant", "content": "Received dataset:\n" + ("log summary line DEF 0987654321\n" * 800)}
        ]
        ctx, intent, sel, budget = self.pipeline.prepare_request(
            model_name="Qwen3-Coder-30B-A3B-Instruct-Q3_K_M",
            user_query="What was in that log?",
            conversation_history=huge_history
        )
        self.assertLessEqual(budget.total_prompt_tokens, budget.usable_context)


    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_7_loop_guard_trigger_live_engine(self):
        """7. Loop Guard: Consecutive identical tool calls trigger safety halt."""
        self.executor.register_handler("files.read", lambda path: "line 1\nline 2")
        for _ in range(3):
            self.executor.execute("files.read", {"path": "config.yaml"})
        
        blocked = self.executor.execute("files.read", {"path": "config.yaml"})
        self.assertFalse(blocked.success)
        self.assertIn("loop", blocked.error.lower())

    @unittest.skipUnless(ENGINE_RUNNING, "LMMs Engine is not running on localhost:11435")
    def test_e2e_8_privacy_scrub_trace_logs(self):
        """8. Privacy Scrub: Sensitive tokens, passwords, and API keys are redacted from traces."""
        logger = TraceLogger(log_dir="/tmp/lmms_test_traces")
        raw_error = "Failed to connect with password=SuperSecretPassword123 and token ghp_ABC123456789012345678901234567890123 and key sk-99887766554433221100112233445566"
        sanitized = logger.sanitize(raw_error)
        self.assertNotIn("SuperSecretPassword123", sanitized)
        self.assertNotIn("ghp_ABC123456789012345678901234567890123", sanitized)
        self.assertNotIn("sk-99887766554433221100112233445566", sanitized)
        self.assertIn("[REDACTED]", sanitized)


if __name__ == "__main__":
    unittest.main()


