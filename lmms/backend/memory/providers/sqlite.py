import sqlite3
import os
from datetime import datetime


class Memory:
    def __init__(self, db_path="~/.lmms/memory.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME,
                model_used TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save(self, session_id, role, content, model="system"):
        # Save every message permanently
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp, model_used) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat(), model),
        )
        conn.commit()
        conn.close()

    def get_history(self, session_id, limit=20):
        # Get last N messages for context
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        # Return in chronological order
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def search(self, query):
        # Search past conversations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT session_id, role, content, timestamp FROM conversations WHERE content LIKE ? ORDER BY timestamp DESC",
            (f"%{query}%",),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def clear_session(self, session_id):
        # Clear specific session
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
