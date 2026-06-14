import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.lmms/memory.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at DATETIME,
        updated_at DATETIME,
        mode TEXT,
        model TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp DATETIME,
        tokens INTEGER,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
    )
    ''')
    conn.commit()
    conn.close()

def create_session(session_id: str, title: str, mode: str, model: str):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO sessions (id, title, created_at, updated_at, mode, model)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, title, now, now, mode, model))
    conn.commit()
    conn.close()

def add_message(session_id: str, role: str, content: str, tokens: int = 0):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO messages (session_id, role, content, timestamp, tokens)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, role, content, now, tokens))
    c.execute('UPDATE sessions SET updated_at = ? WHERE id = ?', (now, session_id))
    conn.commit()
    conn.close()

def get_sessions():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM sessions ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_messages(session_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_session(session_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()

# Initialize on import
init_db()
