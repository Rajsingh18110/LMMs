import os
import sqlite3
from lmms.backend.tools.core_tools.tools.base import ToolResult

DB_PATH = os.path.expanduser("~/.lmms/connectors.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_name TEXT UNIQUE,
            config_json TEXT
        )
    """)
    conn.commit()
    return conn

def get_telegram_config():
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_json FROM connectors WHERE connector_name = 'telegram'")
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return json.loads(row[0])
    return None

def set_telegram_config(api_id: str, api_hash: str, phone: str):
    import json
    config = json.dumps({"api_id": api_id, "api_hash": api_hash, "phone": phone})
    conn = init_db()
    conn.execute("INSERT OR REPLACE INTO connectors (connector_name, config_json) VALUES ('telegram', ?)", (config,))
    conn.commit()
    conn.close()

async def execute_telegram_search_channels(params: dict) -> ToolResult:
    config = get_telegram_config()
    if not config:
        return ToolResult(tool_name="telegram_search_channels", success=False, error="Please run `/connector telegram setup` first.", data=None)
    
    return ToolResult(tool_name="telegram_search_channels", success=True, data={"message": "Telegram search channels logic would run here using telethon."})

async def execute_telegram_read_channel(params: dict) -> ToolResult:
    config = get_telegram_config()
    if not config:
        return ToolResult(tool_name="telegram_read_channel", success=False, error="Please run `/connector telegram setup` first.", data=None)
    
    return ToolResult(tool_name="telegram_read_channel", success=True, data={"message": "Telegram read channel logic would run here using telethon."})

async def execute_telegram_search_messages(params: dict) -> ToolResult:
    config = get_telegram_config()
    if not config:
        return ToolResult(tool_name="telegram_search_messages", success=False, error="Please run `/connector telegram setup` first.", data=None)
    
    return ToolResult(tool_name="telegram_search_messages", success=True, data={"message": "Telegram search messages logic would run here using telethon."})
