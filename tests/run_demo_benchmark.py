import asyncio
import os
import sys
import json
import sqlite3
import subprocess
import time
from typing import Dict, Any

from lmms.backend.router.rule_router import RuleRouter
from lmms.backend.agents.specialized.coding import CodingAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.tasks.core_tasks.tasks.task import Task
from lmms.backend.context.checkpoint import get_turn_checkpoint_manager
from lmms_sessions.store import SessionStore
from lmms_worktree.manager import default_worktree_manager
from lmms.backend.events.bus import get_event_bus

WS_DIR = "/home/kali/Projects/demo_calculator_repo"
TASK_DESC = "is repo me ek chhota bug fix karo aur test chalao. math_utils.py me divide bug fix karo aur tests/test_math.py chalao"
SESSIONS_DB = os.path.expanduser("~/.lmms/sessions.db")
EVENTS_JSONL = os.path.expanduser("~/.lmms/events/live_events.jsonl")


def get_sessions_count() -> int:
    try:
        with sqlite3.connect(SESSIONS_DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM sessions")
            return cur.fetchone()[0]
    except Exception:
        return 0


def get_git_log() -> str:
    res = subprocess.run(["git", "log", "--oneline", "-n", "3"], cwd=WS_DIR, capture_output=True, text=True)
    return res.stdout.strip()


def get_worktree_list() -> str:
    res = subprocess.run(["git", "worktree", "list"], cwd=WS_DIR, capture_output=True, text=True)
    return res.stdout.strip()


def reset_repo():
    subprocess.run(["git", "reset", "--hard", "c652de1"], cwd=WS_DIR, capture_output=True, check=True)
    subprocess.run(["git", "clean", "-fd"], cwd=WS_DIR, capture_output=True, check=True)
    default_worktree_manager.clean_stale_worktrees(WS_DIR)


async def execute_single_run(run_id: int, model_name: str) -> Dict[str, Any]:
    print(f"\n{'='*25} RUN #{run_id} ({model_name}) {'='*25}")
    reset_repo()
    
    # Pre-run state
    db_count_before = get_sessions_count()
    git_log_before = get_git_log()
    wt_before = get_worktree_list()
    
    # Event bus tracking
    ev_count_start = 0
    if os.path.exists(EVENTS_JSONL):
        with open(EVENTS_JSONL, "r", encoding="utf-8") as f:
            ev_count_start = sum(1 for _ in f)

    # 1. RuleRouter Deterministic Execution Graph
    router = RuleRouter()
    graph = router.route(TASK_DESC)
    graph_steps = [{"agent": s.agent_name, "action": s.action_type} for s in graph.steps]
    print(f"[RuleRouter] Intent: {graph.intent} | Steps: {graph_steps}")

    # 2. Setup Context & Turn Checkpoint
    turn_mgr = get_turn_checkpoint_manager(WS_DIR)
    turn_id = f"e2e_run_{run_id}_{int(time.time())}"
    turn_mgr.start_turn(turn_id=turn_id, summary=f"E2E demo run {run_id}")

    ctx = ExecutionContext(workspace_id=WS_DIR)
    ctx.task = Task(id=f"task-e2e-{run_id}", title="Bug Fix", description=TASK_DESC)
    ctx.files = ["math_utils.py", "tests/test_math.py"]
    ctx.selected_model = model_name

    # 3. Execute CodingAgent
    agent_output_chunks = []
    coder = CodingAgent()
    active_wt_path = None
    wt_list_during = None

    async for chunk in coder.execute(ctx):
        agent_output_chunks.append(chunk)
        print(chunk, end="")
        if "[Worktree] Isolated ephemeral workspace active:" in chunk:
            active_wt_path = chunk.split("active:")[1].strip()
            wt_list_during = get_worktree_list()

    full_agent_output = "".join(agent_output_chunks)
    turn_mgr.end_turn()

    # 4. Check Test Execution on Main Workspace
    test_res = subprocess.run(["python3", "-m", "unittest", "tests/test_math.py"], cwd=WS_DIR, capture_output=True, text=True)
    test_exit_code = test_res.returncode
    run_passed = (test_exit_code == 0)

    # 5. Record to sessions.db
    store = SessionStore()
    sess_id = f"sess_e2e_{run_id}_{int(time.time())}"
    store.create_session(session_id=sess_id, title=f"E2E Demo Run #{run_id}", metadata={"model": model_name})
    store.add_message(sess_id, role="user", content=TASK_DESC)
    store.add_message(sess_id, role="assistant", content=full_agent_output[:2000])

    # Post-run state
    db_count_after = get_sessions_count()
    git_log_after = get_git_log()
    wt_after = get_worktree_list()

    # Extract new event bus lines
    new_events = []
    if os.path.exists(EVENTS_JSONL):
        with open(EVENTS_JSONL, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= ev_count_start:
                    try:
                        new_events.append(json.loads(line.strip()))
                    except Exception:
                        pass

    # 6. Test /undo verification
    print(f"\n[Undo Check] Invoking /undo on turn #{turn_id}...")
    undo_ok, undo_msg = turn_mgr.undo(force=True)
    print(f"[Undo Result] ok={undo_ok}: {undo_msg}")

    # Verify repo state after /undo
    test_after_undo = subprocess.run(["python3", "-m", "unittest", "tests/test_math.py"], cwd=WS_DIR, capture_output=True, text=True)
    print(f"[Post-Undo Test] exit code = {test_after_undo.returncode} (expected 1 for restored bug)")

    result_data = {
        "run_id": run_id,
        "model_name": model_name,
        "passed": run_passed,
        "test_exit_code": test_exit_code,
        "rule_router_steps": graph_steps,
        "active_wt_path": active_wt_path,
        "wt_list_during": wt_list_during,
        "db_count_before": db_count_before,
        "db_count_after": db_count_after,
        "git_log_before": git_log_before,
        "git_log_after": git_log_after,
        "undo_ok": undo_ok,
        "undo_msg": undo_msg,
        "undo_verified": (test_after_undo.returncode != 0),
        "events_count": len(new_events),
        "agent_output": full_agent_output,
    }
    return result_data


async def main():
    model_1_5b = "qwen2.5-1.5b-instruct-q5_k_m"
    results = []
    
    print(f"Starting 5-Run Benchmark for {model_1_5b}...")
    for i in range(1, 6):
        res = await execute_single_run(i, model_1_5b)
        results.append(res)
        time.sleep(1)

    print("\n" + "="*60)
    print("BENCHMARK SUMMARY (1.5B):")
    passed_count = sum(1 for r in results if r["passed"])
    print(f"Total Runs: {len(results)} | Passed: {passed_count} | Failed: {len(results) - passed_count}")
    print(f"Success Rate: {passed_count / len(results) * 100:.1f}%")
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        print(f" Run #{r['run_id']}: {status_str} (exit code: {r['test_exit_code']}, undo: {r['undo_ok']}, db: {r['db_count_before']}->{r['db_count_after']})")

    # Save summary report
    out_file = "/home/kali/Projects/LMMs/demo_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Full benchmark details saved to: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
