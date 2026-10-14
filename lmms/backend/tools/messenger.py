import os
import json
import sqlite3
import subprocess
import requests
from typing import Optional, Dict, Any

DB_PATH = os.path.expanduser("~/.lmms/connectors.db")

class MessengerTool:
    """
    Unified messaging and notification tool for LMMs.
    Allows the agent to send messages via Telegram, Discord, Slack, custom Webhooks,
    or native Desktop Notifications (notify-send).
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
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
        conn.close()

    def get_config(self, connector_name: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM connectors WHERE connector_name = ?", (connector_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

    def set_config(self, connector_name: str, config: Dict[str, Any]):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO connectors (connector_name, config_json) VALUES (?, ?)",
            (connector_name, json.dumps(config))
        )
        conn.commit()
        conn.close()

    def send_telegram(self, message: str, chat_id: Optional[str] = None, bot_token: Optional[str] = None) -> str:
        """Send a message via Telegram Bot API."""
        cfg = self.get_config("telegram") or {}
        token = bot_token or cfg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        target_chat = chat_id or cfg.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")

        if not token:
            return (
                "Error: Telegram Bot Token not configured. "
                "Please configure it via `/connector telegram setup` or pass `bot_token` in tool kwargs."
            )
        if not target_chat:
            return "Error: Telegram `chat_id` not specified. Provide the recipient chat ID."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if data.get("ok"):
                return f"[SUCCESS] Telegram message sent to chat_id {target_chat}."
            else:
                return f"Telegram API Error: {data.get('description', 'Unknown error')}"
        except Exception as e:
            return f"Failed to send Telegram message: {str(e)}"

    def send_webhook(self, webhook_url: str, message: str, username: str = "LMMs Agent") -> str:
        """Send a message to a Discord, Slack, or generic JSON webhook."""
        if not webhook_url:
            return "Error: No webhook URL provided."

        # Detect platform format
        if "discord.com" in webhook_url or "discordapp.com" in webhook_url:
            payload = {"content": message, "username": username}
        elif "slack.com" in webhook_url:
            payload = {"text": message, "username": username}
        else:
            payload = {"text": message, "message": message, "sender": username}

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                return f"[SUCCESS] Webhook message delivered successfully ({resp.status_code})."
            else:
                return f"Webhook responded with HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as e:
            return f"Failed to deliver webhook: {str(e)}"

    def send_desktop_notification(self, title: str, message: str) -> str:
        """Send a native Linux desktop notification via notify-send."""
        try:
            subprocess.run(["notify-send", title, message], check=False)
            return f"[SUCCESS] Desktop notification displayed: '{title}: {message}'."
        except Exception as e:
            return f"Failed to show desktop notification: {str(e)}"

    def send(self, platform: str, message: str, recipient: Optional[str] = None, **kwargs) -> str:
        """
        Unified dispatch:
        platform: 'telegram', 'discord', 'slack', 'webhook', or 'desktop'
        recipient: chat_id for telegram, webhook_url for discord/slack/webhook
        """
        p = platform.lower().strip()
        if p == "telegram":
            return self.send_telegram(message, chat_id=recipient, bot_token=kwargs.get("bot_token"))
        elif p in ("discord", "slack", "webhook"):
            url = recipient or kwargs.get("webhook_url")
            return self.send_webhook(url, message)
        elif p in ("desktop", "notify", "notification"):
            title = recipient or kwargs.get("title") or "LMMs Alert"
            return self.send_desktop_notification(title, message)
        else:
            return f"Error: Unsupported messaging platform '{platform}'. Supported: telegram, discord, slack, webhook, desktop."
