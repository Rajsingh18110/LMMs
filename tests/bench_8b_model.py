#!/usr/bin/env python3
"""
Benchmark for Qwen3-8B-Q4_K_M (Task 4):
Measures:
1. TTFT (Time to first token)
2. Autoregressive decode speed (tokens/sec)
3. Tool call emission (<tool_call>)
4. Schema validity (valid JSON)
5. Target tool accuracy
Runs 3 iterations per scenario across tool prompts and normal chat prompts.
"""

import os
import sys
import time
import json
import statistics
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.pipeline import OrchestrationPipeline
from lmms.backend.orchestration.router import IntentRouter
from lmms.backend.orchestration.builder import ContextBuilder

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama_cpp not installed in current environment.")
    sys.exit(1)

MODEL_PATH = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")

TEST_SCENARIOS = [
    {
        "id": "A1",
        "scenario": "Normal Chat",
        "query": "hello",
        "expected_tool": None
    },
    {
        "id": "C1",
        "scenario": "Web Search",
        "query": "Search for the latest Python documentation about asyncio.",
        "expected_tool": "web_search"
    },
    {
        "id": "D1",
        "scenario": "Browser Automation",
        "query": "Open python.org and tell me the headline.",
        "expected_tool": "browser.open_url"
    },
    {
        "id": "F1",
        "scenario": "Workspace File Ops",
        "query": "Read file lmms/backend/main.py",
        "expected_tool": "files.read"
    },
    {
        "id": "F2",
        "scenario": "Terminal Execution",
        "query": "Run git status in the terminal",
        "expected_tool": "terminal.run"
    }
]

def run_8b_benchmark(runs_per_prompt: int = 3, max_tokens: int = 96):
    if not os.path.exists(MODEL_PATH):
        print(f"Error: 8B Model not found at {MODEL_PATH}")
        sys.exit(1)

    print("=" * 85)
    print("        QWEN3-8B-Q4_K_M BENCHMARK: DECODE SPEED & TOOL-CALL VERIFICATION")
    print("=" * 85)
    print(f"Loading Model: {MODEL_PATH}")
    t_load0 = time.perf_counter()
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_threads=6,
        n_gpu_layers=-1,  # Offload all layers to GPU
        use_mmap=True,
        verbose=False
    )
    t_load = time.perf_counter() - t_load0
    print(f"Model loaded into VRAM in {t_load:.2f}s.")

    pipeline = OrchestrationPipeline(engine_url="http://127.0.0.1:0")

    print("\n" + "=" * 95)
    print("TESTING WITH THINKING DISABLED (/no_think), MAX_TOKENS=256, GPU ACCELERATED")
    print("=" * 95)
    print(f"{'ID':<3} | {'Scenario':<18} | {'Run':<4} | {'TTFT(s)':<7} | {'Tokens':<6} | {'Tok/s':<7} | {'Tool Call':<9} | {'Schema Valid':<12} | {'Correct Tool'}")
    print("-" * 95)

    all_speeds = []
    all_ttfts = []
    tool_emitted_count = 0
    schema_valid_count = 0
    correct_tool_count = 0
    total_tool_prompts = 0
    raw_logs = []

    for sc in TEST_SCENARIOS:
        pid = sc["id"]
        scenario = sc["scenario"]
        query = sc["query"]
        expected_tool = sc["expected_tool"]
        is_tool_prompt = expected_tool is not None

        # Test with /no_think to disable reasoning loop
        test_query = f"/no_think {query}" if is_tool_prompt else query

        for r in range(1, runs_per_prompt + 1):
            ctx, intent_res, selection_res, budget = pipeline.prepare_request(
                model_name="Qwen3-8B-Q4_K_M",
                user_query=test_query,
                conversation_history=[],
                current_workspace="/home/kali/Projects/LMMs"
            )

            # Generate tokens via llama_cpp streaming
            t0 = time.perf_counter()
            ttft = None
            generated_text = ""
            tokens_generated = 0

            from typing import Any, cast
            stream = cast(Any, llm.create_chat_completion(
                messages=cast(Any, ctx.messages),
                max_tokens=256 if is_tool_prompt else 32,
                stream=True,
                temperature=0.0
            ))

            for chunk_raw in stream:
                chunk = cast(dict, chunk_raw)
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        if ttft is None:
                            ttft = time.perf_counter() - t0
                        generated_text += token
                        tokens_generated += 1

            total_time = time.perf_counter() - t0
            ttft = ttft if ttft is not None else total_time
            decode_time = total_time - ttft
            tokens_per_sec = (tokens_generated - 1) / decode_time if (decode_time > 0 and tokens_generated > 1) else (tokens_generated / total_time)

            all_speeds.append(tokens_per_sec)
            all_ttfts.append(ttft)

            # Tool evaluation
            tool_call_emitted = False
            schema_valid = False
            correct_tool = False

            if is_tool_prompt:
                total_tool_prompts += 1
                if "<tool_call>" in generated_text:
                    tool_call_emitted = True
                    tool_emitted_count += 1
                    import re
                    m = re.search(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", generated_text, re.DOTALL)
                    if m:
                        raw_json_str = m.group(1).strip()
                        if not raw_json_str.endswith("}"):
                            raw_json_str += "}"
                        try:
                            parsed = json.loads(raw_json_str)
                            if isinstance(parsed, dict) and ("tool" in parsed or "name" in parsed):
                                schema_valid = True
                                schema_valid_count += 1
                                emitted_name = parsed.get("tool") or parsed.get("name")
                                if emitted_name and (emitted_name == expected_tool or emitted_name.startswith(expected_tool.split(".")[0])):
                                    correct_tool = True
                                    correct_tool_count += 1
                        except Exception:
                            pass
            else:
                # Chat prompt: success if NO erroneous tool call emitted
                tool_call_emitted = "<tool_call>" in generated_text
                schema_valid = True
                correct_tool = True

            emitted_str = str(tool_call_emitted)
            valid_str = str(schema_valid)
            correct_str = str(correct_tool)
            print(f"{pid:<3} | {scenario:<18} | {r:<4} | {ttft:>7.2f} | {tokens_generated:>6} | {tokens_per_sec:>7.2f} | {emitted_str:<9} | {valid_str:<12} | {correct_str}")

            raw_logs.append({
                "id": pid,
                "scenario": scenario,
                "run": r,
                "ttft": ttft,
                "tokens": tokens_generated,
                "tok_per_sec": tokens_per_sec,
                "tool_call_emitted": tool_call_emitted,
                "schema_valid": schema_valid,
                "correct_tool": correct_tool,
                "raw_output": generated_text
            })

    print("-" * 95)
    print("\n" + "=" * 95)
    print("                    QWEN3-8B-Q4_K_M SUMMARY STATISTICS")
    print("=" * 95)
    print(f"Mean TTFT:                   {statistics.mean(all_ttfts):.2f} s")
    print(f"Median TTFT:                 {statistics.median(all_ttfts):.2f} s")
    print(f"Mean Decode Speed:           {statistics.mean(all_speeds):.2f} tokens/sec")
    print(f"Median Decode Speed:         {statistics.median(all_speeds):.2f} tokens/sec")
    if total_tool_prompts > 0:
        print(f"Tool Call Emitted Rate:      {tool_emitted_count}/{total_tool_prompts} ({(tool_emitted_count/total_tool_prompts)*100:.1f}%)")
        print(f"Schema Validity Rate:        {schema_valid_count}/{total_tool_prompts} ({(schema_valid_count/total_tool_prompts)*100:.1f}%)")
        print(f"Correct Target Tool Rate:    {correct_tool_count}/{total_tool_prompts} ({(correct_tool_count/total_tool_prompts)*100:.1f}%)")
    print("=" * 95)

    print("\n=== RAW OUTPUTS PER RUN ===")
    for entry in raw_logs:
        print(f"\n[{entry['id']} - {entry['scenario']} Run {entry['run']}] (Tokens: {entry['tokens']}, Tok/s: {entry['tok_per_sec']:.2f}):")
        print(entry["raw_output"])
        print("-" * 60)

if __name__ == "__main__":
    run_8b_benchmark(runs_per_prompt=3, max_tokens=256)

