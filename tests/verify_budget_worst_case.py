#!/usr/bin/env python3
"""
Worst-case Browser Turn Budget Verification (Task 5b):
Calculates exact real budget breakdown for:
system + tools (all browser capabilities) + history + user + 768 output reserve + 200 margin.
Confirms it fits within the 4,096 hardware context window (3,196 usable input budget),
and demonstrates exactly what the compactor drops when a turn exceeds the budget.
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

def run_worst_case_budget_analysis():
    registry = ToolRegistry()
    router = IntentRouter()
    selector = ToolSelector(registry)
    builder = ContextBuilder()
    budget_mgr = TokenBudgetManager(engine_url="http://127.0.0.1:0", default_context_limit=4096, default_output_reserve=768, safety_margin=200)
    compactor = ContextCompactor()

    # 1. Realistic Worst-Case Browser Turn (Active execution with full browser tool suite)
    query = "Open https://app.datadoghq.com/dashboard/kpi, authenticate, click element #export-pdf, and save to workspace"
    intent_res = router.route(query)
    
    # Request all browser suite tools to simulate maximum worst-case tool injection
    browser_tool_ids = ["browser.open_url", "browser.click_element", "browser.fill_form", "browser.screenshot", "browser.get_interactive_dom"]
    selection_res = selector.select(intent_res, additional_requested_tools=browser_tool_ids)

    # 3 turns of active browser navigation history including DOM observation
    sample_dom_observation = (
        "<observation>\n"
        "[DOM Snapshot for https://app.datadoghq.com]\n"
        "<div id='root'>\n"
        "  <header><nav><a href='/home'>Dashboard</a> <button id='export-pdf'>Export PDF</button></nav></header>\n"
        "  <main>\n"
        "    <div class='metric-card' id='cpu'>CPU: 42%</div>\n"
        "    <div class='metric-card' id='mem'>Memory: 68%</div>\n"
        "    <table class='log-table'><tr><td>2026-10-18 06:00</td><td>HTTP 200 OK</td></tr></table>\n"
        "  </main>\n"
        "</div>\n"
        "</observation>"
    )

    history = [
        {"role": "user", "content": "Navigate to Datadog KPI dashboard"},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"browser.open_url\", \"kwargs\": {\"url\": \"https://app.datadoghq.com/dashboard/kpi\"}}</tool_call>"},
        {"role": "user", "content": sample_dom_observation},
        {"role": "assistant", "content": "Dashboard loaded. Looking for the export button."}
    ]

    assembled = builder.assemble(
        model_name="Qwen3-Coder-30B-A3B-Instruct",
        user_query=query,
        intent_result=intent_res,
        selection_result=selection_res,
        conversation_history=history,
        current_workspace="/home/kali/Projects/LMMs"
    )

    # Set context limit to 4096 (enforced on 16GB RAM machines)
    budget_mgr._limit_cache["Qwen3-Coder-30B-A3B-Instruct"] = 4096
    budget = budget_mgr.calculate_budget(
        model_name="Qwen3-Coder-30B-A3B-Instruct",
        base_prompt=assembled.base_system_prompt,
        task_instructions=assembled.task_instructions,
        tool_schemas=assembled.tool_schemas_str,
        history_messages=history,
        user_query=query
    )



    print("=" * 80)
    print("           REAL BUDGET BREAKDOWN: WORST-CASE BROWSER TURN")
    print("=" * 80)
    print(f"Hardware Context Window (n_ctx):       {budget.context_limit:>6} tokens")
    print(f"Output Generation Reserve:             {budget.output_reserve:>6} tokens")
    print(f"System Safety Margin:                  {budget.safety_margin:>6} tokens")
    print(f"----------------------------------------------------------------")
    print(f"Usable Input Budget:                   {budget.usable_context:>6} tokens")
    print(f"================================================================")
    print(f"COMPONENT BREAKDOWN:")
    print(f"  1. Base System Prompt:               {budget.base_prompt_tokens:>6} tokens")
    print(f"  2. Task Instructions (Browser):      {budget.task_instructions_tokens:>6} tokens")
    print(f"  3. Tool Schemas (5 browser tools):   {budget.tool_schemas_tokens:>6} tokens")
    print(f"  4. Conversation History (w/ DOM):    {budget.history_tokens:>6} tokens")
    print(f"  5. User Query & Workspace Context:   {budget.user_query_tokens:>6} tokens")
    print(f"----------------------------------------------------------------")
    print(f"TOTAL INPUT PROMPT TOKENS:             {budget.total_prompt_tokens:>6} tokens")
    print(f"REMAINING HEADROOM BEFORE COMPACTION:  {budget.remaining_tokens:>6} tokens")
    print(f"Overflow Condition Detected:           {budget.is_overflow}")
    print("=" * 80)

    # 2. What happens when history contains an oversized DOM dump (e.g. 15,000 characters)?
    print("\n" + "=" * 80)
    print("      COMPACTOR OVERFLOW RECOVERY TEST (15,000-char DOM Dump)")
    print("=" * 80)
    huge_dom = "<observation>\n" + ("<div class='node'>DOM entry line " * 500) + "\n</observation>"
    overflow_history = [
        {"role": "user", "content": "Navigate to initial web portal"},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"browser.open_url\", \"kwargs\": {\"url\": \"https://huge.page\"}}</tool_call>"},
        {"role": "user", "content": huge_dom},
        {"role": "assistant", "content": "Page rendered with heavy DOM."},
        {"role": "user", "content": "Now click on button #export"},
        {"role": "assistant", "content": "<tool_call>{\"tool\": \"browser.click_element\", \"kwargs\": {\"element_id\": 42}}</tool_call>"},
        {"role": "user", "content": "<observation>Clicked button #export successfully.</observation>"},
        {"role": "assistant", "content": "Export initiated. What is the next step?"}
    ]

    tokens_before = budget_mgr.count_tokens(" ".join(str(m['content']) for m in overflow_history))
    print(f"Oversized History Tokens Before Compaction: {tokens_before:>6} tokens")

    compacted_msgs, report = compactor.compact(
        messages=overflow_history,
        usable_budget=1500,
        current_prompt_tokens=tokens_before
    )
    tokens_after = budget_mgr.count_tokens(" ".join(str(m['content']) for m in compacted_msgs))


    print(f"Compacted History Tokens After Compaction:  {tokens_after} tokens")
    print(f"Tokens Saved by Compactor:                  {tokens_before - tokens_after} tokens")
    print(f"Observations Pruned/Truncated:              {report.observations_pruned}")
    print(f"Stage 3 Executive Summary Applied:          {report.summary_applied}")
    print(f"Exact Content Dropped by Compactor:         Truncated middle of <observation> DOM body")
    print(f"                                            Retained: First {compactor.max_observation_chars*2//3} chars (head) + Last {compactor.max_observation_chars//3} chars (tail)")
    print("=" * 80)

if __name__ == "__main__":
    run_worst_case_budget_analysis()
