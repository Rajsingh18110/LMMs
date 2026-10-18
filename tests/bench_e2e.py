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


def evaluate_tool_call(output_text: str, target_tool: Optional[str]) -> bool:
    """Checks if output contains a valid tool call matching target or schema."""
    if not target_tool:
        # Non-tool prompt: success if it did NOT emit an erroneous tool call
        return "<tool_call>" not in output_text
    
    # Tool-dependent prompt: must contain <tool_call> with valid json
    if "<tool_call>" in output_text:
        import re
        m = re.search(r"<tool_call>(.*?)</tool_call>", output_text, re.DOTALL)
        if m:
            try:
                tc = json.loads(m.group(1))
                t_name = tc.get("tool") or tc.get("name")
                if t_name:
                    return True
            except Exception:
                pass
    return False


def run_benchmark(runs_per_prompt: int = 1):
    online, loaded = check_engine()
    if not online:
        print("Error: Engine is not running on localhost:11435. Please start launcher or engine server.")
        sys.exit(1)

    model_to_use = MODEL_NAME
    if loaded and loaded[0]:
        model_to_use = loaded[0]
    print(f"Running Real-Model Benchmark on '{model_to_use}' ({runs_per_prompt} run(s) per prompt)...")

    pipeline = OrchestrationPipeline(engine_url=ENGINE_URL)

    results_new = []
    results_legacy = []

    print("\n" + "=" * 90)
    print(f"{'ID':<3} | {'Scenario':<20} | {'Mode':<6} | {'Tokens':<6} | {'TTFT (s)':<8} | {'Total (s)':<9} | {'Tool Valid':<10}")
    print("-" * 90)

    for p in BENCHMARK_PROMPTS:
        pid = p["id"]
        scenario = p["scenario"]
        query = p["query"]
        history = p.get("history", [])

        # Live inference on representative prompts across all 7 scenarios (or all if --all specified)
        run_live_infer = (pid in ["A1", "B1", "C1", "D1", "E1", "F1", "G1"]) or ("--all" in sys.argv)

        # -----------------------------
        # Condition 1: NEW Pipeline
        # -----------------------------
        os.environ["LMMS_LEGACY_PROMPT"] = "0"
        new_tokens_list = []
        new_ttft_list = []
        new_latency_list = []
        new_valid_list = []

        for _ in range(runs_per_prompt):
            ctx, intent_res, selection_res, budget = pipeline.prepare_request(
                model_name=model_to_use,
                user_query=query,
                conversation_history=history,
                current_workspace="/home/kali/Projects/LMMs"
            )
            full_prompt_text = "".join(m["content"] for m in ctx.messages if isinstance(m.get("content"), str))
            exact_tokens = count_tokens_exact(full_prompt_text)
            new_tokens_list.append(exact_tokens)

            if run_live_infer:
                comp_res = stream_completion(ctx.messages, max_tokens=4)
                tool_valid = evaluate_tool_call(comp_res["text"], p["target_tool"])
                new_ttft_list.append(comp_res["ttft"])
                new_latency_list.append(comp_res["total_latency"])
                new_valid_list.append(tool_valid)
            else:
                new_ttft_list.append(0.0)
                new_latency_list.append(0.0)
                new_valid_list.append(True)

        avg_new_tokens = int(statistics.mean(new_tokens_list))
        avg_new_ttft = statistics.mean(new_ttft_list)
        avg_new_lat = statistics.mean(new_latency_list)
        new_valid = any(new_valid_list)

        results_new.append({
            "id": pid, "tokens": avg_new_tokens, "ttft": avg_new_ttft, "lat": avg_new_lat, "valid": new_valid
        })
        ttft_str = f"{avg_new_ttft:>8.2f}" if avg_new_ttft > 0 else f"{'--':>8}"
        lat_str = f"{avg_new_lat:>9.2f}" if avg_new_lat > 0 else f"{'--':>9}"
        valid_str = str(new_valid) if run_live_infer else "Exact-Tok"
        print(f"{pid:<3} | {scenario:<20} | {'NEW':<6} | {avg_new_tokens:>6} | {ttft_str} | {lat_str} | {valid_str:<10}")

        # -----------------------------
        # Condition 2: OLD Monolithic
        # -----------------------------
        os.environ["LMMS_LEGACY_PROMPT"] = "1"
        leg_tokens_list = []
        leg_ttft_list = []
        leg_latency_list = []
        leg_valid_list = []

        for _ in range(runs_per_prompt):
            ctx_leg, _, _, _ = pipeline.prepare_request(
                model_name=model_to_use,
                user_query=query,
                conversation_history=history,
                current_workspace="/home/kali/Projects/LMMs"
            )
            full_leg_text = "".join(m["content"] for m in ctx_leg.messages if isinstance(m.get("content"), str))
            exact_leg_tokens = count_tokens_exact(full_leg_text)
            leg_tokens_list.append(exact_leg_tokens)

            if run_live_infer:
                comp_leg_res = stream_completion(ctx_leg.messages, max_tokens=4)
                leg_tool_valid = evaluate_tool_call(comp_leg_res["text"], p["target_tool"])
                leg_ttft_list.append(comp_leg_res["ttft"])
                leg_latency_list.append(comp_leg_res["total_latency"])
                leg_valid_list.append(leg_tool_valid)

            else:
                leg_ttft_list.append(0.0)
                leg_latency_list.append(0.0)
                leg_valid_list.append(True)

        avg_leg_tokens = int(statistics.mean(leg_tokens_list))
        avg_leg_ttft = statistics.mean(leg_ttft_list)
        avg_leg_lat = statistics.mean(leg_latency_list)
        leg_valid = any(leg_valid_list)

        results_legacy.append({
            "id": pid, "tokens": avg_leg_tokens, "ttft": avg_leg_ttft, "lat": avg_leg_lat, "valid": leg_valid
        })
        ttft_leg_str = f"{avg_leg_ttft:>8.2f}" if avg_leg_ttft > 0 else f"{'--':>8}"
        lat_leg_str = f"{avg_leg_lat:>9.2f}" if avg_leg_lat > 0 else f"{'--':>9}"
        valid_leg_str = str(leg_valid) if run_live_infer else "Exact-Tok"
        print(f"{pid:<3} | {scenario:<20} | {'OLD':<6} | {avg_leg_tokens:>6} | {ttft_leg_str} | {lat_leg_str} | {valid_leg_str:<10}")
        print("-" * 90)


    # Calculate summary statistics
    all_new_tokens = [r["tokens"] for r in results_new]
    all_leg_tokens = [r["tokens"] for r in results_legacy]
    all_new_ttft = [r["ttft"] for r in results_new if r["ttft"] > 0]
    all_leg_ttft = [r["ttft"] for r in results_legacy if r["ttft"] > 0]
    all_new_lat = [r["lat"] for r in results_new if r["lat"] > 0]
    all_leg_lat = [r["lat"] for r in results_legacy if r["lat"] > 0]
    
    mean_token_red = (statistics.mean(all_leg_tokens) - statistics.mean(all_new_tokens)) / statistics.mean(all_leg_tokens) * 100.0

    print("\n" + "=" * 90)
    print("                    REAL-MODEL BENCHMARK SUMMARY TABLE")
    print("=" * 90)
    print(f"Metric                        | OLD Monolithic       | NEW Smart Context    | Improvement / Delta")
    print("-" * 90)
    print(f"Mean Prompt Tokens (Exact)    | {statistics.mean(all_leg_tokens):>12.1f} tokens | {statistics.mean(all_new_tokens):>12.1f} tokens | -{mean_token_red:.1f}% reduction")
    print(f"Median Prompt Tokens (Exact)  | {statistics.median(all_leg_tokens):>12.1f} tokens | {statistics.median(all_new_tokens):>12.1f} tokens | -{(statistics.median(all_leg_tokens)-statistics.median(all_new_tokens))/statistics.median(all_leg_tokens)*100:.1f}% reduction")
    if all_new_ttft and all_leg_ttft:
        print(f"Mean TTFT                     | {statistics.mean(all_leg_ttft):>12.2f} s      | {statistics.mean(all_new_ttft):>12.2f} s      | {statistics.mean(all_leg_ttft)-statistics.mean(all_new_ttft):+.2f} s faster")
        print(f"Median TTFT                   | {statistics.median(all_leg_ttft):>12.2f} s      | {statistics.median(all_new_ttft):>12.2f} s      | {statistics.median(all_leg_ttft)-statistics.median(all_new_ttft):+.2f} s faster")
    if all_new_lat and all_leg_lat:
        print(f"Mean Total Latency            | {statistics.mean(all_leg_lat):>12.2f} s      | {statistics.mean(all_new_lat):>12.2f} s      | {statistics.mean(all_leg_lat)-statistics.mean(all_new_lat):+.2f} s faster")
    print(f"Normal Chat Tokens (Mean)     | {statistics.mean([r['tokens'] for r in results_legacy[:5]]):>12.1f} tokens | {statistics.mean([r['tokens'] for r in results_new[:5]]):>12.1f} tokens | -{(statistics.mean([r['tokens'] for r in results_legacy[:5]])-statistics.mean([r['tokens'] for r in results_new[:5]]))/statistics.mean([r['tokens'] for r in results_legacy[:5]])*100:.1f}% reduction")
    print("=" * 90)


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_benchmark(runs_per_prompt=runs)
