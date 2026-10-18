#!/usr/bin/env python3
"""
True Worst-Case Context Budget & Compaction Verification:
Calculates exact real budget breakdown for the maximum conceivable context load:
- Hardware Context Window (clamped for 16GB RAM): 4,096 tokens
- Output Generation Reserve: 768 tokens
- System Safety Margin: 200 tokens (unified across budget.py, pipeline, and tests)
- Usable Input Context Budget: exactly 3,128 tokens (4096 - 768 - 200)

Simulates the True Worst Case:
1. The largest tool suite (all 16 tools in ToolRegistry: browser, terminal, files, search, security, discovery)
2. A long multi-turn history near the context limit (~2,500+ tokens of DOM, git logs, code outputs)
3. Demonstrates how ContextCompactor stages compress history to guarantee zero context overflow.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.registry import ToolRegistry
from lmms.backend.orchestration.router import IntentRouter, IntentType
from lmms.backend.orchestration.selector import ToolSelector
from lmms.backend.orchestration.builder import ContextBuilder
from lmms.backend.orchestration.budget import TokenBudgetManager
from lmms.backend.orchestration.compactor import ContextCompactor

def run_true_worst_case_analysis():
    registry = ToolRegistry()
    router = IntentRouter()
    selector = ToolSelector(registry)
    builder = ContextBuilder()
    
    # Unified margin: safety_margin=200, reserve=768, limit=4096 -> usable=3128
    SAFETY_MARGIN = 200
    OUTPUT_RESERVE = 768
    CONTEXT_LIMIT = 4096
    USABLE_BUDGET = CONTEXT_LIMIT - OUTPUT_RESERVE - SAFETY_MARGIN  # 3,128

    budget_mgr = TokenBudgetManager(
        engine_url="http://127.0.0.1:0",
        default_context_limit=CONTEXT_LIMIT,
        default_output_reserve=OUTPUT_RESERVE,
        safety_margin=SAFETY_MARGIN
    )
    budget_mgr._limit_cache["Qwen3-Coder-30B-A3B-Instruct"] = CONTEXT_LIMIT
    compactor = ContextCompactor()

    # 1. Inject the LARGEST TOOL SET: All 16 tools registered in ToolRegistry
    all_tool_ids = list(registry._tools.keys())
    query = "Open https://app.datadoghq.com/dashboard/kpi, inspect the DOM, read main.py, check git status, search online for FastAPI release notes, and generate a security report"
    intent_res = router.route(query)
    selection_res = selector.select(intent_res, additional_requested_tools=all_tool_ids)

    # 2. Build a LONG, HEAVY multi-turn history near the context limit (~2,500+ tokens)
    heavy_dom_observation = (
        "<observation>\n"
        "[DOM Snapshot for https://app.datadoghq.com]\n"
        "<div id='root' class='app-container'>\n"
        "  <header><nav><a href='/home'>Dashboard</a> <button id='export-pdf'>Export PDF</button></nav></header>\n"
        "  <main>\n"
        "    <div class='metric-card' id='cpu'>CPU: 42%</div>\n"
        "    <div class='metric-card' id='mem'>Memory: 68%</div>\n"
        "    <table class='log-table'>\n"
        + "".join(f"      <tr><td>2026-10-18 06:{i:02d}</td><td>GET /api/v1/metrics</td><td>200 OK</td><td>latency=42ms</td></tr>\n" for i in range(25))
        + "    </table>\n"
        "  </main>\n"
        "</div>\n"
        "</observation>"
    )

    heavy_git_log = (
        "<observation>\n"
        "commit 4333b78 (HEAD -> main, backendcode) feat(orchestration): harden router\n"
        "commit 4cd29e0 feat: implement smart context management\n"
        "commit 24544c0 fix(engine): optimize AirPlanner Regime 2\n"
        + "".join(f"commit a1b2c3{i:02d} chore: internal update for module {i}\n" for i in range(20))
        + "</observation>"
    )

    heavy_file_content = (
        "<observation>\n"
        "# File: lmms/backend/orchestration/budget.py\n"
        + "".join(f"def helper_method_{i}(self, value: int) -> int:\n    '''Calculates token offset {i}'''\n    return value * {i} + 10\n" for i in range(20))
        + "</observation>"
    )

    raw_history = [
        {"role": "user", "content": "Let's begin auditing the system and dashboard."},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"browser.open_url\", \"kwargs\": {\"url\": \"https://app.datadoghq.com/dashboard/kpi\"}}</tool_call>"},
        {"role": "user", "content": heavy_dom_observation},
        {"role": "assistant", "content": "Dashboard loaded. Now inspecting repository git history."},
        {"role": "user", "content": "Check recent commits."},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"terminal.run\", \"kwargs\": {\"command\": \"git log -n 25\"}}</tool_call>"},
        {"role": "user", "content": heavy_git_log},
        {"role": "assistant", "content": "Git history retrieved. Now inspecting budget manager implementation."},
        {"role": "user", "content": "Read budget.py implementation."},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"files.read\", \"kwargs\": {\"path\": \"lmms/backend/orchestration/budget.py\"}}</tool_call>"},
        {"role": "user", "content": heavy_file_content},
        {"role": "assistant", "content": "Budget manager code reviewed. Now ready for final action."}
    ]

    # Pre-compaction calculation
    assembled_uncompacted = builder.assemble(
        model_name="Qwen3-Coder-30B-A3B-Instruct",
        user_query=query,
        intent_result=intent_res,
        selection_result=selection_res,
        conversation_history=raw_history,
        current_workspace="/home/kali/Projects/LMMs"
    )

    budget_uncompacted = budget_mgr.calculate_budget(
        model_name="Qwen3-Coder-30B-A3B-Instruct",
        base_prompt=assembled_uncompacted.base_system_prompt,
        task_instructions=assembled_uncompacted.task_instructions,
        tool_schemas=assembled_uncompacted.tool_schemas_str,
        history_messages=raw_history,
        user_query=query
    )

    print("=" * 85)
    print("      TRUE WORST-CASE CONTEXT ANALYSIS (Max Tools + Deep Multi-Turn History)")
    print("=" * 85)
    print(f"Hardware Context Window (n_ctx):       {budget_uncompacted.context_limit:>6} tokens")
    print(f"Output Generation Reserve:             {budget_uncompacted.output_reserve:>6} tokens")
    print(f"Unified System Safety Margin:          {budget_uncompacted.safety_margin:>6} tokens")
    print(f"---------------------------------------------------------------------")
    print(f"Usable Input Budget:                   {budget_uncompacted.usable_context:>6} tokens (4096 - 768 - 200)")
    print(f"=====================================================================")
    print(f"UNCOMPACTED COMPONENT BREAKDOWN:")
    print(f"  1. Base System Prompt:               {budget_uncompacted.base_prompt_tokens:>6} tokens")
    print(f"  2. Task Instructions:                {budget_uncompacted.task_instructions_tokens:>6} tokens")
    print(f"  3. Tool Schemas (All 16 tools):      {budget_uncompacted.tool_schemas_tokens:>6} tokens")
    print(f"  4. Heavy Multi-Turn History:         {budget_uncompacted.history_tokens:>6} tokens")
    print(f"  5. User Query & Workspace:           {budget_uncompacted.user_query_tokens:>6} tokens")
    print(f"---------------------------------------------------------------------")
    print(f"TOTAL UNCOMPACTED INPUT TOKENS:        {budget_uncompacted.total_prompt_tokens:>6} tokens")
    print(f"USABLE BUDGET OVERFLOW:                {budget_uncompacted.is_overflow} (Exceeds by {budget_uncompacted.total_prompt_tokens - budget_uncompacted.usable_context} tokens!)")
    print("=" * 85)

    # 3. ENGAGE CONTEXT COMPACTOR (Multi-stage compression)
    # Available budget for history = Usable Budget - mandatory prompt overhead
    mandatory_overhead = (
        budget_uncompacted.base_prompt_tokens +
        budget_uncompacted.task_instructions_tokens +
        budget_uncompacted.tool_schemas_tokens +
        budget_uncompacted.user_query_tokens
    )
    history_target_budget = budget_uncompacted.usable_context - mandatory_overhead

    compacted_history, report = compactor.compact(
        messages=raw_history,
        usable_budget=history_target_budget,
        current_prompt_tokens=budget_uncompacted.total_prompt_tokens
    )

    # Recalculate post-compaction budget
    budget_compacted = budget_mgr.calculate_budget(
        model_name="Qwen3-Coder-30B-A3B-Instruct",
        base_prompt=assembled_uncompacted.base_system_prompt,
        task_instructions=assembled_uncompacted.task_instructions,
        tool_schemas=assembled_uncompacted.tool_schemas_str,
        history_messages=compacted_history,
        user_query=query
    )

    print("\n" + "=" * 85)
    print("           COMPACTOR RECOVERY & COMPRESSION RESULTS")
    print("=" * 85)
    print(f"History Tokens Before Compaction:      {budget_uncompacted.history_tokens:>6} tokens")
    print(f"History Tokens After Compaction:       {budget_compacted.history_tokens:>6} tokens")
    print(f"Tokens Saved by Compactor:             {budget_uncompacted.history_tokens - budget_compacted.history_tokens:>6} tokens")
    print(f"Observations Pruned/Truncated:         {report.observations_pruned}")
    print(f"Stage 3 Rule-Based Summary Applied:    {report.summary_applied}")
    print(f"---------------------------------------------------------------------")
    print(f"FINAL ASSEMBLED INPUT PROMPT TOKENS:   {budget_compacted.total_prompt_tokens:>6} tokens")
    print(f"FINAL REMAINING HEADROOM:              {budget_compacted.remaining_tokens:>6} tokens")
    print(f"Overflow Condition Detected:           {budget_compacted.is_overflow}")
    print("=" * 85)

    # 4. Strict Budget Assertion
    budget_mgr.verify_or_raise(budget_compacted)
    print("\n[VERIFIED] budget_mgr.verify_or_raise() passed cleanly! Context window 100% protected.")
    print(f"Unified Margin Verified: safety_margin={budget_compacted.safety_margin}, output_reserve={budget_compacted.output_reserve}, usable={budget_compacted.usable_context}.")

if __name__ == "__main__":
    run_true_worst_case_analysis()
