#!/usr/bin/env python3
"""
Full 31-Prompt Benchmark (Task 4):
Compares LEGACY Monolithic Prompt vs NEW Smart Context Pipeline with Compact Tool Catalog Index.
Measures:
1. Exact prompt tokens (counted via Qwen3 tokenizer)
2. Cold TTFT (Run 1: first run after switching to a new prompt scenario)
3. Warm TTFT Run 2 (with 1 turn of prior conversation history)
4. Warm TTFT Run 3 (with 2 turns of prior conversation history)
5. Tool call emission and correctness across all tool scenarios
6. Strict separation of Cold vs Warm TTFT (never averaged together).
"""

import os
import sys
import json
import time
import statistics
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.pipeline import OrchestrationPipeline
from lmms.backend.orchestration.registry import ToolRegistry
from llama_cpp import Llama

MODEL_PATH = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")

BENCHMARK_PROMPTS = [
    # Scenario A: Normal Chat (5)
    {"id": "A1", "scenario": "Normal Chat", "query": "hello", "needs_tool": False, "target_tool": None},
    {"id": "A2", "scenario": "Normal Chat", "query": "Hi there, good morning!", "needs_tool": False, "target_tool": None},
    {"id": "A3", "scenario": "Normal Chat", "query": "How are you doing today?", "needs_tool": False, "target_tool": None},
    {"id": "A4", "scenario": "Normal Chat", "query": "Thank you for the explanation.", "needs_tool": False, "target_tool": None},
    {"id": "A5", "scenario": "Normal Chat", "query": "Namaste, kaise ho?", "needs_tool": False, "target_tool": None},

    # Scenario B: Coding Explanation (5)
    {"id": "B1", "scenario": "Coding Explanation", "query": "Explain how Python decorators work.", "needs_tool": False, "target_tool": None},
    {"id": "B2", "scenario": "Coding Explanation", "query": "What is a closure in JavaScript?", "needs_tool": False, "target_tool": None},
    {"id": "B3", "scenario": "Coding Explanation", "query": "Explain the quicksort algorithm with a python example.", "needs_tool": False, "target_tool": None},
    {"id": "B4", "scenario": "Coding Explanation", "query": "How does Rust ownership and borrowing work?", "needs_tool": False, "target_tool": None},
    {"id": "B5", "scenario": "Coding Explanation", "query": "Explain difference between list and tuple in Python.", "needs_tool": False, "target_tool": None},

    # Scenario C: Web Search (5)
    {"id": "C1", "scenario": "Web Search", "query": "Search for the latest Python documentation about asyncio.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "C2", "scenario": "Web Search", "query": "Search the web for FastAPI release notes.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "C3", "scenario": "Web Search", "query": "Find online what is the current price of bitcoin.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "C4", "scenario": "Web Search", "query": "Google pe search karo latest AI news.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "C5", "scenario": "Web Search", "query": "Search online for weather in San Francisco.", "needs_tool": True, "target_tool": "web_search"},

    # Scenario D: Browser Automation (5)
    {"id": "D1", "scenario": "Browser Automation", "query": "Open python.org and tell me the headline.", "needs_tool": True, "target_tool": "browser.open_url"},
    {"id": "D2", "scenario": "Browser Automation", "query": "Open https://news.ycombinator.com and list top stories.", "needs_tool": True, "target_tool": "browser.open_url"},
    {"id": "D3", "scenario": "Browser Automation", "query": "Browse to https://github.com/trending and extract top repos.", "needs_tool": True, "target_tool": "browser.open_url"},
    {"id": "D4", "scenario": "Browser Automation", "query": "Take a screenshot of the current website in browser.", "needs_tool": True, "target_tool": "browser.screenshot"},
    {"id": "D5", "scenario": "Browser Automation", "query": "Browser me open karo https://example.com", "needs_tool": True, "target_tool": "browser.open_url"},

    # Scenario E: Multi-Step Workflow (4)
    {"id": "E1", "scenario": "Multi-Step Workflow", "query": "Research three solutions, compare their capabilities, and generate a report.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "E2", "scenario": "Multi-Step Workflow", "query": "Compare llama.cpp vs vLLM vs Ollama and write a report.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "E3", "scenario": "Multi-Step Workflow", "query": "Investigate three vector databases, compare them, and generate a summary report.", "needs_tool": True, "target_tool": "web_search"},
    {"id": "E4", "scenario": "Multi-Step Workflow", "query": "Multi-step audit of repository dependencies and produce a security report.", "needs_tool": True, "target_tool": "security.generate_report"},

    # Scenario F: Workspace File Operations (4)
    {"id": "F1", "scenario": "Workspace File Ops", "query": "Read file lmms/backend/main.py", "needs_tool": True, "target_tool": "files.read"},
    {"id": "F2", "scenario": "Workspace File Ops", "query": "Git status", "needs_tool": True, "target_tool": "terminal.run"},
    {"id": "F3", "scenario": "Workspace File Ops", "query": "List files in src/ directory", "needs_tool": True, "target_tool": "files.read"},
    {"id": "F4", "scenario": "Workspace File Ops", "query": "Ye file open karo aur check karo", "needs_tool": True, "target_tool": "files.read"},

    # Scenario G: Tool Research & Follow-Up (3)
    {"id": "G1", "scenario": "Tool Research", "query": "Kali tool nmap options and syntax", "needs_tool": True, "target_tool": "terminal.run"},
    {"id": "G2", "scenario": "Tool Research", "query": "Find syntax for nikto web scanner in terminal", "needs_tool": True, "target_tool": "terminal.run"},
    {"id": "G3", "scenario": "Follow-Up", "query": "Proceed with step 2", "needs_tool": True, "target_tool": "terminal.run"}
]

HISTORY_VARIATIONS = [
    [],  # Run 1: Cold start
    [    # Run 2: Varying history turn 1
        {"role": "user", "content": "Can you assist me with my workspace?"},
        {"role": "assistant", "content": "Yes, I am ready to help you with your workspace tasks."}
    ],
    [    # Run 3: Varying history turn 2
        {"role": "user", "content": "Can you assist me with my workspace?"},
        {"role": "assistant", "content": "Yes, I am ready to help you with your workspace tasks."},
        {"role": "user", "content": "Great, make sure all operations follow safety standards."},
        {"role": "assistant", "content": "Understood. I will follow safety boundaries and prompt rules strictly."}
    ]
]


def evaluate_tool_output(generated_text: str, target_tool: Optional[str]) -> Dict[str, Any]:
    if not target_tool:
        emitted = "<tool_call>" in generated_text
        return {"emitted": emitted, "valid": not emitted, "correct": not emitted}

    emitted = "<tool_call>" in generated_text
    valid = False
    correct = False

    if emitted:
        import re
        m = re.search(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", generated_text, re.DOTALL)
        if m:
            raw_json = m.group(1).strip()
            if not raw_json.endswith("}"):
                raw_json += "}"
            try:
                parsed = json.loads(raw_json)
                tool_name = parsed.get("tool") or parsed.get("name")
                if tool_name:
                    valid = True
                    target_prefix = target_tool.split(".")[0]
                    if tool_name == target_tool or tool_name.startswith(target_prefix) or target_prefix in tool_name:
                        correct = True
                    elif tool_name == "discover_additional_tool":
                        correct = True  # lazy discovery is valid
            except Exception:
                pass
    return {"emitted": emitted, "valid": valid, "correct": correct}


def run_benchmark():
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        sys.exit(1)

    print("=" * 115)
    print("      COMPREHENSIVE 31-PROMPT BENCHMARK: LEGACY MONOLITHIC vs NEW SMART PIPELINE")
    print("=" * 115)
    print(f"Loading Model on GPU: {MODEL_PATH}")
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_gpu_layers=-1,
        verbose=False
    )
    print("Model loaded successfully into VRAM.")

    pipeline = OrchestrationPipeline(engine_url="http://127.0.0.1:0")

    results = []

    print("\n" + "=" * 115)
    print(f"{'ID':<3} | {'Scenario':<18} | {'Tokens(Leg)':<11} | {'Tokens(New)':<11} | {'Reduct%':<7} | {'Cold Legacy':<11} | {'Cold New':<9} | {'Warm2 Leg':<9} | {'Warm2 New':<9} | {'Warm3 Leg':<9} | {'Warm3 New'}")
    print("=" * 115)

    all_cold_legacy = []
    all_cold_new = []
    all_warm2_legacy = []
    all_warm2_new = []
    all_warm3_legacy = []
    all_warm3_new = []
    all_tokens_legacy = []
    all_tokens_new = []

    tool_success_new = 0
    total_tool_prompts = 0
    scenario_stats = {}

    for item in BENCHMARK_PROMPTS:
        pid = item["id"]
        scenario = item["scenario"]
        query = item["query"]
        needs_tool = item["needs_tool"]
        target_tool = item["target_tool"]

        prompt_query = f"/no_think {query}" if needs_tool else query

        # 1. Measure Token Counts
        os.environ["LMMS_LEGACY_PROMPT"] = "1"
        ctx_leg, _, _, _ = pipeline.prepare_request(
            model_name="Qwen3-8B-Q4_K_M",
            user_query=prompt_query,
            conversation_history=[]
        )
        leg_tokens = len(llm.tokenize(ctx_leg.messages[0]["content"].encode("utf-8")))

        os.environ.pop("LMMS_LEGACY_PROMPT", None)
        ctx_new, _, _, _ = pipeline.prepare_request(
            model_name="Qwen3-8B-Q4_K_M",
            user_query=prompt_query,
            conversation_history=[]
        )
        new_tokens = len(llm.tokenize(ctx_new.messages[0]["content"].encode("utf-8")))
        reduct_pct = (leg_tokens - new_tokens) / leg_tokens * 100.0

        all_tokens_legacy.append(leg_tokens)
        all_tokens_new.append(new_tokens)

        # 2. Run Runs 1, 2, 3 for Legacy
        legacy_ttfts = []
        leg_tool_eval = None
        for r_idx, history in enumerate(HISTORY_VARIATIONS):
            if r_idx == 0:
                llm.reset()  # Guarantee 100% cold KV cache for Run 1
            os.environ["LMMS_LEGACY_PROMPT"] = "1"
            ctx, _, _, _ = pipeline.prepare_request(
                model_name="Qwen3-8B-Q4_K_M",
                user_query=prompt_query,
                conversation_history=history
            )
            max_tok = 60 if (r_idx == 0 and needs_tool) else 15
            stream = llm.create_chat_completion(
                messages=ctx.messages,
                max_tokens=max_tok,
                stream=True,
                temperature=0.0
            )
            stream_iter = iter(stream)
            t0 = time.perf_counter()
            first_chunk = next(stream_iter, None)
            ttft = time.perf_counter() - t0
            
            gen_text = ""
            if first_chunk and "choices" in first_chunk and len(first_chunk["choices"]) > 0:
                tok = first_chunk["choices"][0].get("delta", {}).get("content", "")
                gen_text += tok
                
            if r_idx == 0 and needs_tool:
                for chunk in stream_iter:
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        tok = chunk["choices"][0].get("delta", {}).get("content", "")
                        gen_text += tok
                leg_tool_eval = evaluate_tool_output(gen_text, target_tool)
            elif r_idx == 0 and not needs_tool:
                leg_tool_eval = evaluate_tool_output(gen_text, None)
                
            legacy_ttfts.append(ttft)

        # 3. Run Runs 1, 2, 3 for New
        new_ttfts = []
        new_tool_eval = None
        for r_idx, history in enumerate(HISTORY_VARIATIONS):
            if r_idx == 0:
                llm.reset()  # Guarantee 100% cold KV cache for Run 1
            os.environ.pop("LMMS_LEGACY_PROMPT", None)
            ctx, _, _, _ = pipeline.prepare_request(
                model_name="Qwen3-8B-Q4_K_M",
                user_query=prompt_query,
                conversation_history=history
            )
            max_tok = 60 if (r_idx == 0 and needs_tool) else 15
            stream = llm.create_chat_completion(
                messages=ctx.messages,
                max_tokens=max_tok,
                stream=True,
                temperature=0.0
            )
            stream_iter = iter(stream)
            t0 = time.perf_counter()
            first_chunk = next(stream_iter, None)
            ttft = time.perf_counter() - t0
            
            gen_text = ""
            if first_chunk and "choices" in first_chunk and len(first_chunk["choices"]) > 0:
                tok = first_chunk["choices"][0].get("delta", {}).get("content", "")
                gen_text += tok
                
            if r_idx == 0 and needs_tool:
                for chunk in stream_iter:
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        tok = chunk["choices"][0].get("delta", {}).get("content", "")
                        gen_text += tok
                new_tool_eval = evaluate_tool_output(gen_text, target_tool)
            elif r_idx == 0 and not needs_tool:
                new_tool_eval = evaluate_tool_output(gen_text, None)
                
            new_ttfts.append(ttft)

        cold_leg = legacy_ttfts[0]
        cold_new = new_ttfts[0]
        warm2_leg = legacy_ttfts[1]
        warm2_new = new_ttfts[1]
        warm3_leg = legacy_ttfts[2]
        warm3_new = new_ttfts[2]

        all_cold_legacy.append(cold_leg)
        all_cold_new.append(cold_new)
        all_warm2_legacy.append(warm2_leg)
        all_warm2_new.append(warm2_new)
        all_warm3_legacy.append(warm3_leg)
        all_warm3_new.append(warm3_new)

        if scenario not in scenario_stats:
            scenario_stats[scenario] = {
                "total": 0,
                "leg_emitted": 0, "leg_valid": 0, "leg_correct": 0,
                "new_emitted": 0, "new_valid": 0, "new_correct": 0
            }
        sc = scenario_stats[scenario]
        sc["total"] += 1
        if leg_tool_eval and leg_tool_eval["emitted"]:
            sc["leg_emitted"] += 1
        if leg_tool_eval and leg_tool_eval["valid"]:
            sc["leg_valid"] += 1
        if leg_tool_eval and leg_tool_eval["correct"]:
            sc["leg_correct"] += 1

        if new_tool_eval and new_tool_eval["emitted"]:
            sc["new_emitted"] += 1
        if new_tool_eval and new_tool_eval["valid"]:
            sc["new_valid"] += 1
        if new_tool_eval and new_tool_eval["correct"]:
            sc["new_correct"] += 1

        if needs_tool:
            total_tool_prompts += 1
            if new_tool_eval and new_tool_eval["correct"]:
                tool_success_new += 1

        print(f"{pid:<3} | {scenario:<18} | {leg_tokens:>11} | {new_tokens:>11} | {reduct_pct:>6.1f}% | {cold_leg:>10.3f}s | {cold_new:>8.3f}s | {warm2_leg:>8.3f}s | {warm2_new:>8.3f}s | {warm3_leg:>8.3f}s | {warm3_new:>8.3f}s")

    print("=" * 115)
    print("\n" + "=" * 80)
    print("                    BENCHMARK SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Scenarios Evaluated:         31 prompts")
    print(f"Total LLM Inference Runs:          186 runs (31 prompts x 3 runs x 2 configs)")
    print("-" * 80)
    print("PROMPT TOKEN REDUCTION:")
    print(f"  Legacy Mean Prompt Tokens:       {statistics.mean(all_tokens_legacy):.1f} tokens")
    print(f"  New Pipeline Mean Tokens:        {statistics.mean(all_tokens_new):.1f} tokens")
    print(f"  Mean Token Savings:              {((statistics.mean(all_tokens_legacy) - statistics.mean(all_tokens_new)) / statistics.mean(all_tokens_legacy))*100:.1f}%")
    print("-" * 80)
    print("COLD TTFT (Run 1 - Cold Start on New Scenario):")
    print(f"  Legacy Mean Cold TTFT:           {statistics.mean(all_cold_legacy):.3f} s")
    print(f"  New Pipeline Mean Cold TTFT:     {statistics.mean(all_cold_new):.3f} s")
    print(f"  Cold TTFT Speedup:               {statistics.mean(all_cold_legacy) / statistics.mean(all_cold_new):.2f}x faster")
    print("-" * 80)
    print("WARM TTFT - RUN 2 (Turn 1 Evolving History):")
    print(f"  Legacy Mean Warm TTFT:           {statistics.mean(all_warm2_legacy):.3f} s")
    print(f"  New Pipeline Mean Warm TTFT:     {statistics.mean(all_warm2_new):.3f} s")
    print("-" * 80)
    print("WARM TTFT - RUN 3 (Turn 2 Evolving History):")
    print(f"  Legacy Mean Warm TTFT:           {statistics.mean(all_warm3_legacy):.3f} s")
    print(f"  New Pipeline Mean Warm TTFT:     {statistics.mean(all_warm3_new):.3f} s")
    print("-" * 80)
    print(f"Tool Action Success Rate:          {tool_success_new}/{total_tool_prompts} ({(tool_success_new/total_tool_prompts)*100:.1f}%)")
    print("=" * 80)

    print("\n" + "=" * 95)
    print("       SCENARIO TOOL ACCURACY BREAKDOWN: LEGACY vs NEW PIPELINE (ALL 31 PROMPTS)")
    print("=" * 95)
    print(f"{'Scenario':<22} | {'Prompts':<7} | {'Legacy: Emitted / Valid / Correct':<32} | {'New: Emitted / Valid / Correct'}")
    print("-" * 95)
    for sc_name, sc in scenario_stats.items():
        leg_str = f"{sc['leg_emitted']}/{sc['total']} ({sc['leg_emitted']/sc['total']*100:.0f}%) | {sc['leg_valid']}/{sc['total']} | {sc['leg_correct']}/{sc['total']}"
        new_str = f"{sc['new_emitted']}/{sc['total']} ({sc['new_emitted']/sc['total']*100:.0f}%) | {sc['new_valid']}/{sc['total']} | {sc['new_correct']}/{sc['total']}"
        print(f"{sc_name:<22} | {sc['total']:<7} | {leg_str:<32} | {new_str}")
    print("=" * 95)

if __name__ == "__main__":
    run_benchmark()
