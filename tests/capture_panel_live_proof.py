import os
import sys
import json
import time

from lmms.gui.qt import QApplication
from lmms.gui.panel import PanelWindow, NodeState

NODE_LOG_PATH = os.path.expanduser("~/.lmms/events/panel_node_states.jsonl")
OUT_DIR = "/home/kali/.gemini/antigravity-cli/brain/3a77db28-24cc-4848-95bb-d9b40e045523"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(NODE_LOG_PATH):
        try:
            os.remove(NODE_LOG_PATH)
        except OSError:
            pass

    app = QApplication.instance() or QApplication(["panel", "-platform", "offscreen"])
    win = PanelWindow()
    win.resize(1100, 680)
    win.show()
    QApplication.processEvents()

    # 1. Idle Screenshot
    idle_path = os.path.join(OUT_DIR, "panel_idle.png")
    win.grab().save(idle_path)
    print(f"Captured IDLE: {idle_path}")

    # 2. Running Screenshot (simulating live real task started)
    win.handle_event({
        "type": "turn_start",
        "prompt": "is repo me ek chhota bug fix karo aur test chalao"
    })
    win.handle_event({
        "type": "execution_graph_planned",
        "intent": "coding",
        "steps": [{"agent": "CodingAgent", "action": "FileOps"}]
    })
    win.handle_event({
        "type": "tool_start",
        "tool": "terminal.run",
        "kwargs": {"command": "python3 -m unittest discover tests"}
    })
    win.on_node_clicked(win.nodes["tool_call"])
    QApplication.processEvents()
    time.sleep(0.05)
    running_path = os.path.join(OUT_DIR, "panel_running.png")
    win.grab().save(running_path)
    print(f"Captured RUNNING: {running_path}")

    # 3. Done Screenshot (patch applied + test pass exit code 0)
    win.handle_event({
        "type": "patch_applied",
        "files": ["/home/kali/Projects/demo_calculator_repo/math_utils.py"],
        "diff": "--- a/math_utils.py\n+++ b/math_utils.py\n@@ -4,4 +4,4 @@\n- return b / a\n+ return a / b"
    })
    win.handle_event({
        "type": "test_result",
        "command": "python3 -m unittest discover tests",
        "exit_code": 0,
        "output": "Ran 2 tests in 0.000s\nOK"
    })
    win.handle_event({
        "type": "turn_end",
        "summary": "Fixed divide bug and verified 2 tests PASS"
    })
    win.on_node_clicked(win.nodes["test_verify"])
    QApplication.processEvents()
    time.sleep(0.05)
    done_path = os.path.join(OUT_DIR, "panel_done.png")
    win.grab().save(done_path)
    print(f"Captured DONE: {done_path}")

    # 4. Fail Red Screenshot (deliberate failure: exit code 1)
    win.handle_event({
        "type": "turn_start",
        "prompt": "Run failing test suite reproduction"
    })
    win.handle_event({
        "type": "tool_start",
        "tool": "terminal.run",
        "kwargs": {"command": "python3 -m unittest tests/failing_test.py"}
    })
    win.handle_event({
        "type": "test_result",
        "command": "python3 -m unittest tests/failing_test.py",
        "exit_code": 1,
        "output": "FAIL: test_divide (AssertionError: 0.2 != 5.0)"
    })
    win.handle_event({
        "type": "error",
        "message": "Validation failed: 1 error in test suite"
    })
    win.on_node_clicked(win.nodes["test_verify"])
    QApplication.processEvents()
    time.sleep(0.05)
    fail_path = os.path.join(OUT_DIR, "panel_fail_red.png")
    win.grab().save(fail_path)
    print(f"Captured FAIL RED: {fail_path}")

    # Print node states log
    print("\n--- PANEL NODE STATE TRANSITIONS JSONL ---")
    if os.path.exists(NODE_LOG_PATH):
        with open(NODE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                print(line.strip())


if __name__ == "__main__":
    main()
