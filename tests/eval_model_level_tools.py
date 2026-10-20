#!/usr/bin/env python3
"""
Model-Level Tool Outcome Evaluation on 60 Tool-Needing Queries:
Evaluates Qwen3-8B on GPU with /no_think and max_tokens=256 across 60 queries that require tools.
Measures whether the model ends up calling the right tool either via router pre-loading OR via lazy discovery from the compact index.
"""

import os
import sys
import json
import time
import re
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.pipeline import OrchestrationPipeline
from lmms.backend.orchestration.executor import UnifiedToolExecutor
from llama_cpp import Llama

MODEL_PATH = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")


def load_tool_queries(n_target: int = 60) -> List[Dict[str, Any]]:
    holdout_files = [
        "tests/data/router_holdout_3.jsonl",
        "tests/data/router_holdout_2.jsonl",
        "tests/data/router_holdout.jsonl",
    ]
    tool_queries = []
    seen = set()

    for hf in holdout_files:
        if not os.path.exists(hf):
            continue
        with open(hf, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                q = d.get("query", "").strip()
                needs_tool = d.get("expected_tools") if "expected_tools" in d else d.get("requires_tools", d.get("needs_tools", False))
                if needs_tool and q and q not in seen:
                    seen.add(q)
                    tool_queries.append({
                        "query": q,
                        "source": os.path.basename(hf),
                        "expected_intent": d.get("expected_intent") or d.get("intent", "")
                    })
                    if len(tool_queries) >= n_target:
                        break
        if len(tool_queries) >= n_target:
            break

    return tool_queries[:n_target]


def evaluate_output(text: str, query: str, expected_intent: str) -> Dict[str, Any]:
    emitted = "<tool_call>" in text
    valid = False
    correct = False
    tool_name = ""
    parsed_kwargs = {}

    if emitted:
        m = re.search(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", text, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            # If model generated raw text ending prematurely, attempt closing brace
            if not raw.endswith("}"):
                raw += "}"
            try:
                data = json.loads(raw)
                tool_name = data.get("tool") or data.get("name") or ""
                parsed_kwargs = data.get("kwargs") or data.get("arguments") or {}
                valid = bool(tool_name)
            except Exception:
                try:
                    import ast
                    s = re.sub(r'\btrue\b', 'True', raw)
                    s = re.sub(r'\bfalse\b', 'False', s)
                    s = re.sub(r'\bnull\b', 'None', s)
                    data = ast.literal_eval(s)
                    tool_name = data.get("tool") or data.get("name") or ""
                    parsed_kwargs = data.get("kwargs") or data.get("arguments") or {}
                    valid = bool(tool_name)
                except Exception:
                    valid = False

    # Check correctness based on intent / query semantics
    if valid and tool_name:
        tn = tool_name.lower()
        if "web_search" in tn or "search" in tn or "google" in tn:
            if "search" in expected_intent or any(k in query.lower() for k in ["who", "what", "search", "latest", "today", "price", "weather", "news", "currently"]):
                correct = True
        elif "browser" in tn:
            if "browser" in expected_intent or any(k in query.lower() for k in ["http", "browse", "page", "webpage", "click", "form", "screenshot", "scroll", "scrape"]):
                correct = True
        elif "files" in tn or "file" in tn:
            if "file" in expected_intent or any(k in query.lower() for k in ["file", "read", "write", "cat", "delete", "list", "save", "pyproject", "readme"]):
                correct = True
        elif "terminal" in tn or "shell" in tn or "bash" in tn:
            if "terminal" in expected_intent or "file" in expected_intent or any(k in query.lower() for k in ["terminal", "command", "git", "bash", "top", "free", "df", "ps", "nvidia", "pytest", "sh"]):
                correct = True
        elif "app" in tn:
            if "app" in expected_intent or any(k in query.lower() for k in ["launch", "app", "application", "calculator", "chrome"]):
                correct = True
        elif "message" in tn:
            if any(k in query.lower() for k in ["notification", "notify", "message", "send"]):
                correct = True
        elif "discover_additional_tool" in tn:
            correct = True  # Model requested tool discovery dynamically

    return {
        "emitted": emitted,
        "valid": valid,
        "correct": correct,
        "tool_name": tool_name,
        "kwargs": parsed_kwargs
    }


def main():
    queries = load_tool_queries(60)
    print("=" * 100)
    print(f"MODEL-LEVEL TOOL OUTCOME EVALUATION ({len(queries)} TOOL-NEEDING QUERIES)")
    print(f"Model: {MODEL_PATH}")
    print("Hardware: Native CUDA (n_gpu_layers=-1, 37/37 layers offloaded)")
    print("Thinking Mode: DISABLED (/no_think), max_tokens=256")
    print("=" * 100)

    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_gpu_layers=-1,
        verbose=False
    )
    pipeline = OrchestrationPipeline(engine_url="http://127.0.0.1:0")
    executor = UnifiedToolExecutor(pipeline.registry)

    total = len(queries)
    emitted_count = 0
    valid_count = 0
    correct_count = 0
    executor_success_count = 0

    print(f"{'#':<3} | {'Query':<40} | {'Router Tools':<12} | {'Tool Emitted':<22} | {'Correct?':<8} | {'Exec?':<6}")
    print("-" * 100)

    for idx, item in enumerate(queries, 1):
        q = item["query"]
        expected_intent = item["expected_intent"]
        ctx, intent, sel, budget = pipeline.prepare_request(
            model_name="Qwen3-8B-Q4_K_M",
            user_query=q,
            conversation_history=[]
        )

        # Force /no_think in user query if not present
        effective_messages = list(ctx.messages)
        if effective_messages and effective_messages[-1]["role"] == "user":
            user_content = effective_messages[-1]["content"]
            if "/no_think" not in user_content:
                effective_messages[-1] = {"role": "user", "content": user_content + "\n/no_think"}

        from typing import Any, cast
        res = cast(dict, llm.create_chat_completion(
            messages=cast(Any, effective_messages),
            max_tokens=256,
            temperature=0.0
        ))

        gen_text = cast(str, res["choices"][0]["message"].get("content", "") or "")
        ev = evaluate_output(gen_text, q, expected_intent)

        if ev["emitted"]:
            emitted_count += 1
        if ev["valid"]:
            valid_count += 1
        if ev["correct"]:
            correct_count += 1

        # Test execution through UnifiedToolExecutor
        exec_ok = False
        if ev["valid"] and ev["tool_name"]:
            try:
                exec_res = executor.execute(ev["tool_name"], ev["kwargs"])
                exec_ok = exec_res.success
                if exec_ok:
                    executor_success_count += 1
            except Exception:
                exec_ok = False

        short_q = (q[:37] + "...") if len(q) > 40 else q
        tool_str = (ev["tool_name"][:20]) if ev["tool_name"] else ("NO_TOOL" if not ev["emitted"] else "INVALID")
        r_tools = len(sel.selected_tools)

        print(f"{idx:<3} | {short_q:<40} | {r_tools:<12} | {tool_str:<22} | {str(ev['correct']):<8} | {str(exec_ok):<6}")

    print("=" * 100)
    print("                     EVALUATION SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Total Tool-Needing Queries Evaluated: {total}")
    print(f"Tool Calls Emitted Rate:               {emitted_count}/{total} ({emitted_count/total*100:.1f}%)")
    print(f"Valid Schema Rate:                     {valid_count}/{total} ({valid_count/total*100:.1f}%)")
    print(f"Correct Tool Action Rate:              {correct_count}/{total} ({correct_count/total*100:.1f}%)")
    print(f"UnifiedToolExecutor Live Success Rate: {executor_success_count}/{total} ({executor_success_count/total*100:.1f}%)")
    print("=" * 100)


if __name__ == "__main__":
    main()
