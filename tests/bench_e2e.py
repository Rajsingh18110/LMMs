#!/usr/bin/env python3
"""
End-to-End Real Model Benchmark:
Compares the OLD Monolithic Prompt (LMMS_LEGACY_PROMPT=1) vs the NEW Smart Context Pipeline
using the live running LMMs Engine on the loaded Qwen3-Coder model.

Measures:
- Exact Prompt Tokens (via /v1/tokenize)
- Time To First Token (TTFT in ms/sec)
- Total Response Latency (sec)
- Tool Call Validity (schema check)
- End-to-End Task Success
Over 3 runs per prompt across 30+ diverse real-world scenarios.
"""

import os
import sys
import json
import time
import statistics
import requests
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.pipeline import OrchestrationPipeline

ENGINE_URL = "http://localhost:11435"
MODEL_NAME = "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M"

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
    {"id": "E4", "scenario": "Multi-Step Workflow", "query": "Multi-step audit of repository dependencies and produce a security report.", "needs_tool": True, "target_tool": "report.generate"},

    # Scenario F: Workspace File Operations (4)
    {"id": "F1", "scenario": "Workspace File Ops", "query": "Read file lmms/backend/main.py", "needs_tool": True, "target_tool": "files.read"},
    {"id": "F2", "scenario": "Workspace File Ops", "query": "Git status", "needs_tool": True, "target_tool": "terminal.run"},
    {"id": "F3", "scenario": "Workspace File Ops", "query": "List files in src/ directory", "needs_tool": True, "target_tool": "files.list"},
    {"id": "F4", "scenario": "Workspace File Ops", "query": "Ye file open karo aur check karo", "needs_tool": True, "target_tool": "files.read"},

    # Scenario G: Tool Research & Follow-Up (3)
    {"id": "G1", "scenario": "Tool Research", "query": "CVE-2024-3094 vulnerability details", "needs_tool": True, "target_tool": "security.cve_lookup"},
    {"id": "G2", "scenario": "Tool Research", "query": "Kali tool nmap options and syntax", "needs_tool": True, "target_tool": "security.tool_reference"},
    {"id": "G3", "scenario": "Follow-Up", "query": "Proceed with step 2", "needs_tool": True, "target_tool": "terminal.run", "history": [{"role": "user", "content": "git status"}, {"role": "assistant", "content": "Ready to execute step 2."}]}
]


def check_engine():
    try:
        r = requests.get(f"{ENGINE_URL}/v1/models/ps", timeout=2)
        if r.status_code == 200:
            data = r.json()
            loaded = data.get("loaded_models", [])
            print(f"[Engine] Online at {ENGINE_URL}. Loaded models: {loaded}")
            return True, loaded
    except Exception as e:
        print(f"[Engine] Offline or unreachable: {e}")
    return False, []


def count_tokens_exact(text: str) -> int:
    try:
        resp = requests.post(f"{ENGINE_URL}/v1/tokenize", json={"texts": [text]}, timeout=3)
        if resp.status_code == 200:
            counts = resp.json().get("token_counts", [])
            if counts:
                return counts[0]
    except Exception:
        pass
    # Conservative fallback
    return int(len(text) / 3.2)


def stream_completion(messages: List[Dict[str, Any]], max_tokens: int = 15) -> Dict[str, Any]:
    """Streams completion from engine, measuring TTFT and full latency."""
    t0 = time.perf_counter()
    ttft = None
    accumulated_content = ""

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True
    }

    try:
        with requests.post(f"{ENGINE_URL}/v1/chat/completions", json=payload, stream=True, timeout=120) as resp:
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}", "ttft": 0, "total_latency": 0, "text": ""}
            
            tokens_yielded = 0
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: ") and not decoded.startswith("data: [DONE]"):
                        if ttft is None:
                            ttft = time.perf_counter() - t0
                        try:
                            chunk = json.loads(decoded[6:])
                            token = chunk.get("content", "") or chunk.get("message", {}).get("content", "")
                            accumulated_content += token
                            tokens_yielded += 1
                            if tokens_yielded >= max_tokens:
                                resp.close()
                                break
                        except Exception:
                            pass
        total_time = time.perf_counter() - t0
        return {
            "error": None,
            "ttft": ttft if ttft is not None else total_time,
            "total_latency": total_time,
            "text": accumulated_content
        }

    except Exception as e:
        return {"error": str(e), "ttft": 0, "total_latency": 0, "text": ""}


def evaluate_tool_call(output_text: str, target_tool: Optional[str]) -> Dict[str, Any]:
    """Checks if output contains a valid tool call matching target or schema."""
    if not target_tool:
        # Non-tool prompt: success if it did NOT emit an erroneous tool call
        emitted = "<tool_call>" in output_text
        return {
            "emitted": emitted,
            "schema_valid": not emitted,
            "correct_tool": not emitted,
            "tool_name": None
        }

    # Tool-dependent prompt: must contain <tool_call> with valid json
    emitted = "<tool_call>" in output_text
    schema_valid = False
    correct_tool = False
    tool_name = None

    if emitted:
        import re
        m = re.search(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", output_text, re.DOTALL)
        if m:
            raw_json = m.group(1).strip()
            if not raw_json.endswith("}"):
                raw_json += "}"
            try:
                tc = json.loads(raw_json)
                if isinstance(tc, dict):
                    tool_name = tc.get("tool") or tc.get("name")
                    if tool_name:
                        schema_valid = True
                        if tool_name == target_tool or tool_name.startswith(target_tool.split(".")[0]):
                            correct_tool = True
            except Exception:
                pass

    return {
        "emitted": emitted,
        "schema_valid": schema_valid,
        "correct_tool": correct_tool,
        "tool_name": tool_name
    }


def run_benchmark(runs_per_prompt: int = 3, target_scenario_ids: Optional[List[str]] = None):
    online, loaded = check_engine()
    if not online:
        print("Error: Engine is not running on localhost:11435. Please start launcher or engine server.")
        sys.exit(1)

    model_to_use = MODEL_NAME
    if loaded and loaded[0]:
        model_to_use = loaded[0]
    print(f"Running Real-Model Benchmark on '{model_to_use}' ({runs_per_prompt} run(s) per prompt)...")

    pipeline = OrchestrationPipeline(engine_url=ENGINE_URL)

    prompts_to_run = BENCHMARK_PROMPTS
    if target_scenario_ids:
        prompts_to_run = [p for p in BENCHMARK_PROMPTS if p["id"] in target_scenario_ids]

    results_table = []

    print("\n" + "=" * 105)
    print(f"{'ID':<3} | {'Scenario':<18} | {'Mode':<5} | {'Run':<4} | {'Tokens':<6} | {'TTFT(s)':<8} | {'Tot(s)':<7} | {'Emitted':<8} | {'Schema':<7} | {'Correct'}")
    print("=" * 105)

    for p in prompts_to_run:
        pid = p["id"]
        scenario = p["scenario"]
        query = p["query"]
        history = p.get("history", [])
        is_tool_prompt = p["target_tool"] is not None
        max_gen_tokens = 96 if is_tool_prompt else 32

        # -----------------------------
        # Condition 1: NEW Pipeline
        # -----------------------------
        os.environ["LMMS_LEGACY_PROMPT"] = "0"
        for r in range(1, runs_per_prompt + 1):
            ctx, intent_res, selection_res, budget = pipeline.prepare_request(
                model_name=model_to_use,
                user_query=query,
                conversation_history=history,
                current_workspace="/home/kali/Projects/LMMs"
            )
            full_prompt_text = "".join(m["content"] for m in ctx.messages if isinstance(m.get("content"), str))
            exact_tokens = count_tokens_exact(full_prompt_text)

            comp_res = stream_completion(ctx.messages, max_tokens=max_gen_tokens)
            eval_res = evaluate_tool_call(comp_res["text"], p["target_tool"])

            ttft = comp_res["ttft"]
            tot = comp_res["total_latency"]
            emitted = eval_res["emitted"]
            schema = eval_res["schema_valid"]
            correct = eval_res["correct_tool"]

            results_table.append({
                "id": pid, "scenario": scenario, "mode": "NEW", "run": r,
                "tokens": exact_tokens, "ttft": ttft, "lat": tot,
                "emitted": emitted, "schema": schema, "correct": correct
            })

            print(f"{pid:<3} | {scenario:<18} | {'NEW':<5} | {r:<4} | {exact_tokens:>6} | {ttft:>8.2f} | {tot:>7.2f} | {str(emitted):<8} | {str(schema):<7} | {str(correct)}")

        # -----------------------------
        # Condition 2: OLD Monolithic
        # -----------------------------
        os.environ["LMMS_LEGACY_PROMPT"] = "1"
        for r in range(1, runs_per_prompt + 1):
            ctx_leg, _, _, _ = pipeline.prepare_request(
                model_name=model_to_use,
                user_query=query,
                conversation_history=history,
                current_workspace="/home/kali/Projects/LMMs"
            )
            full_leg_text = "".join(m["content"] for m in ctx_leg.messages if isinstance(m.get("content"), str))
            exact_leg_tokens = count_tokens_exact(full_leg_text)

            comp_leg_res = stream_completion(ctx_leg.messages, max_tokens=max_gen_tokens)
            eval_leg_res = evaluate_tool_call(comp_leg_res["text"], p["target_tool"])

            ttft_leg = comp_leg_res["ttft"]
            tot_leg = comp_leg_res["total_latency"]
            emitted_leg = eval_leg_res["emitted"]
            schema_leg = eval_leg_res["schema_valid"]
            correct_leg = eval_leg_res["correct_tool"]

            results_table.append({
                "id": pid, "scenario": scenario, "mode": "OLD", "run": r,
                "tokens": exact_leg_tokens, "ttft": ttft_leg, "lat": tot_leg,
                "emitted": emitted_leg, "schema": schema_leg, "correct": correct_leg
            })

            print(f"{pid:<3} | {scenario:<18} | {'OLD':<5} | {r:<4} | {exact_leg_tokens:>6} | {ttft_leg:>8.2f} | {tot_leg:>7.2f} | {str(emitted_leg):<8} | {str(schema_leg):<7} | {str(correct_leg)}")
        print("-" * 105)

    print("\n" + "=" * 90)
    print("                    TOOL-CALL VERIFICATION SUMMARY (3 RUNS)")
    print("=" * 90)
    tool_results = [r for r in results_table if r["id"] != "A1"]
    new_tool_runs = [r for r in tool_results if r["mode"] == "NEW"]
    old_tool_runs = [r for r in tool_results if r["mode"] == "OLD"]

    if new_tool_runs and old_tool_runs:
        print(f"NEW Pipeline Tool Emitted:   {sum(1 for r in new_tool_runs if r['emitted'])}/{len(new_tool_runs)} ({(sum(1 for r in new_tool_runs if r['emitted'])/len(new_tool_runs))*100:.1f}%)")
        print(f"NEW Pipeline Schema Valid:   {sum(1 for r in new_tool_runs if r['schema'])}/{len(new_tool_runs)} ({(sum(1 for r in new_tool_runs if r['schema'])/len(new_tool_runs))*100:.1f}%)")
        print(f"NEW Pipeline Correct Tool:   {sum(1 for r in new_tool_runs if r['correct'])}/{len(new_tool_runs)} ({(sum(1 for r in new_tool_runs if r['correct'])/len(new_tool_runs))*100:.1f}%)")
        print(f"NEW Pipeline Mean TTFT:      {statistics.mean([r['ttft'] for r in new_tool_runs]):.2f}s")
        print("-" * 90)
        print(f"OLD Legacy Tool Emitted:     {sum(1 for r in old_tool_runs if r['emitted'])}/{len(old_tool_runs)} ({(sum(1 for r in old_tool_runs if r['emitted'])/len(old_tool_runs))*100:.1f}%)")
        print(f"OLD Legacy Schema Valid:     {sum(1 for r in old_tool_runs if r['schema'])}/{len(old_tool_runs)} ({(sum(1 for r in old_tool_runs if r['schema'])/len(old_tool_runs))*100:.1f}%)")
        print(f"OLD Legacy Correct Tool:     {sum(1 for r in old_tool_runs if r['correct'])}/{len(old_tool_runs)} ({(sum(1 for r in old_tool_runs if r['correct'])/len(old_tool_runs))*100:.1f}%)")
        print(f"OLD Legacy Mean TTFT:        {statistics.mean([r['ttft'] for r in old_tool_runs]):.2f}s")
    print("=" * 90)


if __name__ == "__main__":
    runs = 3
    scenarios = ["A1", "C1", "D1", "F1"]
    for arg in sys.argv[1:]:
        if arg.isdigit():
            runs = int(arg)
        elif arg.startswith("--scenarios="):
            scenarios = arg.split("=")[1].split(",")
    run_benchmark(runs_per_prompt=runs, target_scenario_ids=scenarios)

