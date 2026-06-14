import os
import time
import sqlite3
from lmms.backend.tools.core_tools.base import ToolResult
from lmms.backend.config.config.permissions import get_permission_level

def init_ledger_db():
    db_path = os.path.expanduser("~/.lmms/action_ledger.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS screen_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            before_img TEXT,
            after_img TEXT
        )
    """)
    conn.commit()
    return conn

def log_action(action: str, before_img: str, after_img: str):
    try:
        conn = init_ledger_db()
        conn.execute("INSERT INTO screen_actions (action, before_img, after_img) VALUES (?, ?, ?)", (action, before_img, after_img))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log action: {e}")

async def execute_take_screenshot(params: dict) -> ToolResult:
    perm = get_permission_level()
    if perm not in ("medium", "full"):
        return ToolResult(tool_name="take_screenshot", success=False, error=f"Permission denied: Requires 'medium' or 'full' permission level (current is '{perm}')", data=None)
        
    try:
        import pyautogui
        screenshots_dir = os.path.expanduser("~/.lmms/screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        img_path = os.path.join(screenshots_dir, f"screenshot_{int(time.time())}.png")
        pyautogui.screenshot(img_path)
        return ToolResult(tool_name="take_screenshot", success=True, data={"image_path": img_path})
    except Exception as e:
        return ToolResult(tool_name="take_screenshot", success=False, error=str(e), data=None)

async def execute_click_at(params: dict) -> ToolResult:
    x = params.get("x")
    y = params.get("y")
    if x is None or y is None:
        return ToolResult(tool_name="click_at", success=False, error="Missing x or y", data=None)
        
    perm = get_permission_level()
    if perm not in ("medium", "full"):
        return ToolResult(tool_name="click_at", success=False, error=f"Permission denied: Requires 'medium' or 'full' permission level (current is '{perm}')", data=None)
        
    try:
        import pyautogui
        screenshots_dir = os.path.expanduser("~/.lmms/screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        t = int(time.time())
        before = os.path.join(screenshots_dir, f"click_before_{t}.png")
        after = os.path.join(screenshots_dir, f"click_after_{t}.png")
        
        pyautogui.screenshot(before)
        pyautogui.click(int(x), int(y))
        time.sleep(0.5)
        pyautogui.screenshot(after)
        
        log_action(f"click_at({x}, {y})", before, after)
        return ToolResult(tool_name="click_at", success=True, data={"message": f"Clicked at ({x}, {y})"})
    except Exception as e:
        return ToolResult(tool_name="click_at", success=False, error=str(e), data=None)

async def execute_type_text(params: dict) -> ToolResult:
    text = params.get("text")
    if not text:
        return ToolResult(tool_name="type_text", success=False, error="Missing text", data=None)
        
    perm = get_permission_level()
    if perm not in ("medium", "full"):
        return ToolResult(tool_name="type_text", success=False, error=f"Permission denied: Requires 'medium' or 'full' permission level (current is '{perm}')", data=None)
        
    try:
        import pyautogui
        screenshots_dir = os.path.expanduser("~/.lmms/screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        t = int(time.time())
        before = os.path.join(screenshots_dir, f"type_before_{t}.png")
        after = os.path.join(screenshots_dir, f"type_after_{t}.png")
        
        pyautogui.screenshot(before)
        pyautogui.write(text, interval=0.01)
        time.sleep(0.5)
        pyautogui.screenshot(after)
        
        log_action(f"type_text('{text}')", before, after)
        return ToolResult(tool_name="type_text", success=True, data={"message": f"Typed text length {len(text)}"})
    except Exception as e:
        return ToolResult(tool_name="type_text", success=False, error=str(e), data=None)
