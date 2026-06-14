import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.lmms/coordination.db")

def get_connection(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS coordination (
        model_name TEXT PRIMARY KEY,
        status TEXT,
        last_action TEXT,
        output_summary TEXT,
        updated_at DATETIME
    )
    ''')
    conn.commit()
    conn.close()

def write_status(model_name: str, status: str, last_action: str, output_summary: str, db_path=DB_PATH):
    conn = get_connection(db_path)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO coordination (model_name, status, last_action, output_summary, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(model_name) DO UPDATE SET
            status=excluded.status,
            last_action=excluded.last_action,
            output_summary=excluded.output_summary,
            updated_at=excluded.updated_at
    ''', (model_name, status, last_action, output_summary, now))
    conn.commit()
    conn.close()

def read_status(model_name: str, db_path=DB_PATH) -> dict:
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('SELECT * FROM coordination WHERE model_name = ?', (model_name,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def list_models(db_path=DB_PATH) -> list:
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('SELECT * FROM coordination ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Initialize on import
init_db()
