import os
import sqlite3
import uuid

CHATS_DB = os.path.expanduser("~/.lmms/chats.db")

class ChatRouter:
    def __init__(self):
        self.db_path = CHATS_DB
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # Create table exactly as requested
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                workspace_path TEXT,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # We also need a flag to track if the context line was injected
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_session_flags (
                chat_id TEXT PRIMARY KEY,
                context_injected BOOLEAN DEFAULT 0,
                FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()

    def get_active_chat(self, workspace_path=None):
        """
        Scenario B/C: If workspace_path is provided, query WHERE workspace_path = ?
        Scenario A: If None, query WHERE workspace_path IS NULL
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if workspace_path is None:
            cursor.execute("SELECT * FROM chats WHERE workspace_path IS NULL ORDER BY last_active DESC LIMIT 1")
        else:
            cursor.execute("SELECT * FROM chats WHERE workspace_path = ? ORDER BY last_active DESC LIMIT 1", (workspace_path,))
            
        row = cursor.fetchone()

        if row:
            chat_id = row['chat_id']
            # update last active
            cursor.execute("UPDATE chats SET last_active = CURRENT_TIMESTAMP WHERE chat_id = ?", (chat_id,))
        else:
            # Create new row
            chat_id = str(uuid.uuid4())
            if workspace_path is None:
                title = "AI Chat"
                cursor.execute("INSERT INTO chats (chat_id, workspace_path, title) VALUES (?, NULL, ?)", (chat_id, title))
            else:
                title = f"{os.path.basename(workspace_path)} Chat"
                cursor.execute("INSERT INTO chats (chat_id, workspace_path, title) VALUES (?, ?, ?)", (chat_id, workspace_path, title))
            
            # Init flag
            cursor.execute("INSERT INTO chat_session_flags (chat_id, context_injected) VALUES (?, 0)", (chat_id,))
            
        conn.commit()
        
        # Check if we need to inject context
        cursor.execute("SELECT context_injected FROM chat_session_flags WHERE chat_id = ?", (chat_id,))
        flag_row = cursor.fetchone()
        injected = flag_row['context_injected'] if flag_row else 1
        
        needs_context = False
        if workspace_path and not injected:
            needs_context = True
            cursor.execute("UPDATE chat_session_flags SET context_injected = 1 WHERE chat_id = ?", (chat_id,))
            conn.commit()

        conn.close()
        
        return {
            "chat_id": chat_id,
            "workspace_path": workspace_path,
            "needs_context": needs_context
        }

    def list_chats(self, workspace_path=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if workspace_path is None:
            cursor.execute("SELECT * FROM chats WHERE workspace_path IS NULL ORDER BY last_active DESC")
        else:
            cursor.execute("SELECT * FROM chats WHERE workspace_path = ? ORDER BY last_active DESC", (workspace_path,))
            
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_new_chat(self, workspace_path=None, title=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        chat_id = str(uuid.uuid4())
        
        if workspace_path is None:
            t = title or "AI Chat"
            cursor.execute("INSERT INTO chats (chat_id, workspace_path, title) VALUES (?, NULL, ?)", (chat_id, t))
        else:
            t = title or f"{os.path.basename(workspace_path)} Chat"
            cursor.execute("INSERT INTO chats (chat_id, workspace_path, title) VALUES (?, ?, ?)", (chat_id, workspace_path, t))
            
        cursor.execute("INSERT INTO chat_session_flags (chat_id, context_injected) VALUES (?, 0)", (chat_id,))
        conn.commit()
        conn.close()
        return chat_id
