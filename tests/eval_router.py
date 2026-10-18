#!/usr/bin/env python3
"""
Router Evaluation Script: Measures IntentRouter accuracy, per-intent precision/recall,
confusion matrix, and dangerous error rate (action requests that got zero tools).
"""

import os
import json
import sys
from collections import defaultdict
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lmms.backend.orchestration.router import IntentRouter, IntentType


def run_evaluation(data_path: str = "tests/data/router_eval.jsonl", verbose_errors: bool = True):
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}")
        sys.exit(1)

    router = IntentRouter()
    
    total = 0
    correct_intent = 0
    correct_tools_flag = 0
    dangerous_errors: List[Dict[str, Any]] = []
    misrouted_queries: List[Dict[str, Any]] = []
    
    # Metrics tracking
    # Intent -> TP, FP, FN
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    support = defaultdict(int)
    
    # Confusion matrix: [expected][predicted] -> count
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            total += 1
            
            query = item["query"]
            expected_intent = item["expected_intent"]
            expected_tools = item["expected_tools"]
            history = item.get("history")
            workspace = item.get("workspace")
            
            res = router.route(
                query=query,
                conversation_history=history,
                current_workspace=workspace
            )
            
            pred_intent = res.intent.value
            pred_tools = res.requires_tools
            
            support[expected_intent] += 1
            confusion_matrix[expected_intent][pred_intent] += 1
            
            # Check intent match
            if pred_intent == expected_intent:
                correct_intent += 1
                tp[expected_intent] += 1
            else:
                fp[pred_intent] += 1
                fn[expected_intent] += 1
                misrouted_queries.append({
                    "line": line_num,
                    "query": query,
                    "expected_intent": expected_intent,
                    "predicted_intent": pred_intent,
                    "confidence": res.confidence,
                    "expected_tools": expected_tools,
                    "predicted_tools": pred_tools,
                    "reason": res.reason
                })
                
            # Check dangerous error (Action requested tools, but router gave zero tools)
            if expected_tools and not pred_tools:
                dangerous_errors.append({
                    "line": line_num,
                    "query": query,
                    "expected_intent": expected_intent,
                    "predicted_intent": pred_intent,
                    "confidence": res.confidence,
                    "reason": res.reason
                })
                
            if pred_tools == expected_tools:
                correct_tools_flag += 1

    overall_accuracy = (correct_intent / total) * 100.0 if total > 0 else 0.0
    tool_flag_accuracy = (correct_tools_flag / total) * 100.0 if total > 0 else 0.0
    dangerous_error_rate = (len(dangerous_errors) / total) * 100.0 if total > 0 else 0.0

    print("=" * 80)
    print("                INTENT ROUTER EVALUATION REPORT")
    print("=" * 80)
    print(f"Total Test Cases:           {total}")
    print(f"Intent Classification Acc:  {correct_intent}/{total} ({overall_accuracy:.2f}%)")
    print(f"Tool Need Detection Acc:    {correct_tools_flag}/{total} ({tool_flag_accuracy:.2f}%)")
    print(f"Dangerous Errors (Zero-Tool Actions): {len(dangerous_errors)} ({dangerous_error_rate:.2f}%)")
    print("-" * 80)
    
    # Per-intent precision / recall table
    all_intents = sorted(list(set(list(support.keys()) + list(tp.keys()) + list(fp.keys()))))
    print(f"{'Intent':<25} | {'Prec':<7} | {'Recall':<7} | {'F1-Score':<8} | {'Support':<7}")
    print("-" * 65)
    for intent in all_intents:
        p = tp[intent] / (tp[intent] + fp[intent]) if (tp[intent] + fp[intent]) > 0 else 0.0
        r = tp[intent] / (tp[intent] + fn[intent]) if (tp[intent] + fn[intent]) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        s = support[intent]
        print(f"{intent:<25} | {p*100:>6.1f}% | {r*100:>6.1f}% | {f1*100:>7.1f}%  | {s:>7}")
    print("-" * 65)

    # Confusion matrix
    print("\nConfusion Matrix (Row = Expected, Col = Predicted):")
    header = f"{'Expected':<22} | " + " ".join(f"{it[:4]:>4}" for it in all_intents)
    print(header)
    print("-" * len(header))
    for exp in all_intents:
        row_str = f"{exp:<22} | "
        for pred in all_intents:
            count = confusion_matrix[exp][pred]
            row_str += f"{count:>4} "
        print(row_str)

    # Dangerous errors
    if dangerous_errors:
        print("\n" + "!" * 80)
        print(f"DANGEROUS ERRORS ({len(dangerous_errors)} queries where actions received ZERO tools):")
        print("!" * 80)
        for err in dangerous_errors:
            print(f"  Line {err['line']:<3}: \"{err['query']}\"")
            print(f"           Expected: {err['expected_intent']} (Tools=True) -> Got: {err['predicted_intent']} (Tools=False, conf={err['confidence']:.2f})")
            print(f"           Reason: {err['reason']}")
    else:
        print("\n[SUCCESS] Zero dangerous errors! All action requests received tools.")

    if verbose_errors and misrouted_queries:
        print("\n" + "-" * 80)
        print(f"OTHER MISROUTED QUERIES ({len(misrouted_queries)}):")
        print("-" * 80)
        for mis in misrouted_queries:
            if mis in dangerous_errors:
                continue
            print(f"  Line {mis['line']:<3}: \"{mis['query']}\"")
            print(f"           Expected: {mis['expected_intent']} -> Got: {mis['predicted_intent']} (conf={mis['confidence']:.2f})")
            print(f"           Reason: {mis['reason']}")
    print("=" * 80)

    return {
        "total": total,
        "accuracy": overall_accuracy,
        "tool_flag_accuracy": tool_flag_accuracy,
        "dangerous_errors_count": len(dangerous_errors),
        "dangerous_error_rate": dangerous_error_rate,
        "misrouted_count": len(misrouted_queries)
    }


if __name__ == "__main__":
    run_evaluation()
