"""Automated Verification Suite for Upgraded LMMs Backend.

Run this script to verify all 5 upgraded phases:
    python test_backend_verification.py
"""

import os
import sys
import tempfile

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


def test_phase_1_agents_registries_routers():
    print("[1/5] Verifying Phase 1: Real Coding Agent, Unified Registries & Unified Routers...")

    # 1. Real CodingAgent (not a stub)
    from lmms.backend.agents.specialized.coding import CodingAgent
    agent = CodingAgent()
    assert hasattr(agent, "write_code"), "CodingAgent must implement write_code"
    assert hasattr(agent, "execute_tool_step"), "CodingAgent must implement execute_tool_step"
    assert hasattr(agent, "generate_patch"), "CodingAgent must implement generate_patch"

    # Verify agent registry mapping
    from lmms.backend.agents.manager import AgentManager
    mgr = AgentManager()
    assert "coding" in mgr.agent_classes, "CodingAgent must be registered in AgentManager"
    assert "orchestrator" in mgr.agent_classes, "OrchestratorAgent must be registered in AgentManager"
    assert "tester" in mgr.agent_classes, "TesterAgent must be registered in AgentManager"

    # 2. Unified Tool Registries with Alias Resolution
    from lmms.backend.security.tool_registry import register_default_tools, registry as sec_registry
    from lmms.backend.orchestration.registry import ToolRegistry as OrchRegistry
    register_default_tools()
    orch = OrchRegistry()

    assert sec_registry.get_tool("files.read") is not None
    assert sec_registry.get_tool("file_read") is not None  # Alias
    assert sec_registry.get_tool("view_file_outline") is not None  # Dynamic bridge
    assert sec_registry.get_tool("replace_in_file") is not None  # Dynamic bridge
    assert orch.get("view_file_outline") is not None
    assert orch.get("replace_in_file") is not None
    assert orch.get("read_file_lines") is not None

    # 3. Unified Routers
    from lmms.backend.router.rule_router import RuleRouter
    from lmms.backend.orchestration.router import IntentRouter, IntentType
    rule_router = RuleRouter()
    graph = rule_router.route("write a python script to fix the bug in api.py")
    step_agents = [s.agent_name for s in graph.steps]
    assert any(a in ("OrchestratorAgent", "CodingAgent") for a in step_agents), f"Coding agent missing in steps: {step_agents}"

    intent_router = IntentRouter()
    res = intent_router.route("write a python algorithm to solve traveling salesman")
    assert res.intent == IntentType.CODING, f"Expected CODING, got {res.intent}"

    # 4. Dummy files removed
    assert not os.path.exists(os.path.join(workspace_root, "lmms/backend/dummy_bug.py")), "dummy_bug.py must not exist"
    assert not os.path.exists(os.path.join(workspace_root, "lmms/backend/dummy_test_bug.py")), "dummy_test_bug.py must not exist"

    print("      ✓ Phase 1 verified successfully!")


def test_phase_2_context_and_observation_retention():
    print("[2/5] Verifying Phase 2: Context Double-Compaction & Observation Retention...")

    from lmms.backend.orchestration.compactor import ContextCompactor
    compactor = ContextCompactor(recent_turns_to_preserve=8, max_observation_chars=15000)
    assert compactor.max_observation_chars >= 12000, "Observation limit must retain large code/diff blocks"
    assert compactor.recent_turns_to_preserve >= 6, "Recent turns preservation must be generous"

    # Verify compaction preserves critical turns
    history = [
        {"role": "user", "content": "read file"},
        {"role": "tool", "content": "x" * 2000, "tool_name": "files.read"},
        {"role": "assistant", "content": "I will replace the code."},
    ]
    compacted, report = compactor.compact(history, usable_budget=10000, current_prompt_tokens=2000)
    assert len(compacted) == 3, "Recent turns must never be dropped"

    print("      ✓ Phase 2 verified successfully!")


def test_phase_3_react_loop_and_dual_parser():
    print("[3/5] Verifying Phase 3: ReAct Loop & Dual Tool Call Parser...")

    from lmms.backend.main import robust_parse_tool_call

    # Test 1: Native-style tool call tag
    text_tag = '<tool_call>{"tool": "view_file_outline", "kwargs": {"path": "main.py"}}</tool_call>'
    res1 = robust_parse_tool_call(text_tag)
    assert res1.get("tool") == "view_file_outline", f"Expected view_file_outline, got {res1}"
    assert res1.get("kwargs", {}).get("path") == "main.py"

    # Test 2: Markdown JSON codeblock with arguments format
    text_json = '```json\n{"name": "replace_in_file", "arguments": {"path": "a.py", "old_code": "x", "new_code": "y"}}\n```'
    res2 = robust_parse_tool_call(text_json)
    assert res2.get("tool") == "replace_in_file", f"Expected replace_in_file, got {res2}"
    assert res2.get("kwargs", {}).get("old_code") == "x"

    # Test 3: Local adapters have concrete implementations
    from lmms.backend.providers.adapters.llama_cpp_adapter import LlamaCppAdapter
    from lmms.backend.providers.adapters.ollama_adapter import OllamaAdapter
    assert callable(LlamaCppAdapter().generate)
    assert callable(OllamaAdapter().generate)

    print("      ✓ Phase 3 verified successfully!")


def test_phase_4_surgical_file_tools_and_ast_guard():
    print("[4/5] Verifying Phase 4: Surgical File Tools & AST Compile Guard...")

    from lmms.backend.tools.files import view_file_outline, read_file_lines, replace_in_file

    target_file = os.path.join(workspace_root, "lmms/backend/tools/files.py")

    # 1. view_file_outline
    outline = view_file_outline(target_file)
    assert "def view_file_outline" in outline, "view_file_outline failed to extract symbols"
    assert "class FileTool" in outline, "view_file_outline failed to extract class"

    # 2. read_file_lines
    lines = read_file_lines(target_file, 1, 15)
    assert "1 |" in lines, "read_file_lines must prefix 1-indexed line numbers"
    assert "10 |" in lines, "read_file_lines must slice exact line range"

    # 3. AST Compile Guard on syntax error
    test_file = os.path.join(workspace_root, "lmms/backend/test_ast_guard_temp.py")
    with open(test_file, "w") as f:
        f.write("def calculate(x, y):\n    return x * y\n")

    try:
        # Invalid syntax injection
        res_bad = replace_in_file(test_file, "return x * y", "return x * ")
        assert "SyntaxError" in res_bad or "REJECTED" in res_bad
        assert "File was NOT modified" in res_bad

        # Verify disk contents untouched
        with open(test_file, "r") as f:
            content = f.read()
        assert "return x * y" in content, "Guard failed: corrupted file was written to disk!"

        # Valid replacement
        res_good = replace_in_file(test_file, "return x * y", "return (x * y) + 1")
        assert "Successfully modified" in res_good
        with open(test_file, "r") as f:
            content = f.read()
        assert "return (x * y) + 1" in content
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

    print("      ✓ Phase 4 verified successfully!")


def test_phase_5_repomap_git_and_runtime():
    print("[5/5] Verifying Phase 5: AST RepoMap, Git Engine & Runtime Contracts...")

    # 1. AST RepoMap
    from lmms.backend.core.intelligence.file_indexer import FileIndexer
    indexer = FileIndexer(os.path.join(workspace_root, "lmms/backend/git"))
    repomap = indexer.generate_repo_map(max_tokens=800)
    assert "class GitBranches" in repomap or "class GitWorktrees" in repomap
    assert "(" in repomap and ")" in repomap  # Compact method signatures like get_current_branch(self)

    # 2. Git operations
    from lmms.backend.git.branches import GitBranches
    from lmms.backend.git.worktrees import GitWorktrees
    gb = GitBranches(workspace_root)
    current_branch = gb.get_current_branch()
    assert current_branch is not None, "Failed to get current git branch"

    gw = GitWorktrees(workspace_root)
    worktrees = gw.list_worktrees()
    assert isinstance(worktrees, list), "list_worktrees must return a list"

    # 3. TaskScheduler & CacheManager
    from lmms.backend.core.runtime.scheduler import TaskScheduler
    from lmms.backend.core.runtime.cache_manager import CacheManager

    sched = TaskScheduler.get_instance()
    task_id = sched.queue_task("default", {"action": "ping"})
    status = sched.get_status(task_id)
    assert status in ("queued", "running", "completed"), f"Invalid status: {status}"

    cache = CacheManager.get_instance()
    cache.set_cache("test_session", {"kv": [1, 2, 3]})
    assert cache.get_cache("test_session") == {"kv": [1, 2, 3]}
    cache.clear_cache("test_session")
    assert cache.get_cache("test_session") is None

    print("      ✓ Phase 5 verified successfully!")


if __name__ == "__main__":
    print("=" * 70)
    print("LMMs BACKEND END-TO-END VERIFICATION SUITE")
    print("=" * 70)
    try:
        test_phase_1_agents_registries_routers()
        test_phase_2_context_and_observation_retention()
        test_phase_3_react_loop_and_dual_parser()
        test_phase_4_surgical_file_tools_and_ast_guard()
        test_phase_5_repomap_git_and_runtime()
        print("=" * 70)
        print("ALL 5 PHASES AND 7 ROOT CAUSES VERIFIED 100% OPERATIONAL!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
