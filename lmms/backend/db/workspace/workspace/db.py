import sqlite3
import os

SCHEMA_VERSION = 6

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    status TEXT DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT,
    role TEXT,
    content TEXT,
    tokens INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    path TEXT,
    size INTEGER,
    mtime REAL,
    language TEXT,
    indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS git_commits (
    hash TEXT PRIMARY KEY,
    author TEXT,
    message TEXT,
    date DATETIME,
    indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT,  -- 'file', 'chat', 'git_commit'
    source_id TEXT,
    content TEXT,
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Note: vec0 requires rowid as INTEGER
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    embedding FLOAT[384]
);
"""

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS git_repositories (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    path TEXT,
    default_branch TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS git_worktrees (
    id TEXT PRIMARY KEY,
    repository_id TEXT,
    path TEXT,
    branch TEXT,
    is_locked BOOLEAN DEFAULT 0,
    FOREIGN KEY(repository_id) REFERENCES git_repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS git_branches (
    id TEXT PRIMARY KEY,
    repository_id TEXT,
    name TEXT,
    is_active BOOLEAN DEFAULT 0,
    last_commit TEXT,
    FOREIGN KEY(repository_id) REFERENCES git_repositories(id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS git_commits;
CREATE TABLE IF NOT EXISTS git_commits (
    id TEXT PRIMARY KEY,
    repository_id TEXT,
    hash TEXT,
    author TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(repository_id) REFERENCES git_repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS git_files (
    id TEXT PRIMARY KEY,
    commit_id TEXT,
    file_path TEXT,
    change_type TEXT,
    FOREIGN KEY(commit_id) REFERENCES git_commits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workspace_snapshots (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    branch_id TEXT,
    commit_hash TEXT,
    summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE chunks ADD COLUMN branch_id TEXT;
ALTER TABLE chunks ADD COLUMN branch_name TEXT;
"""

SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    branch_id TEXT,
    branch_name TEXT,
    parent_task_id TEXT,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'Pending',
    priority TEXT DEFAULT 'Medium',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT,
    depends_on_task_id TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS task_events (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    event_type TEXT,
    event_data TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS task_assignments (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    assigned_agent TEXT,
    assigned_model TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS task_memory (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    branch_id TEXT,
    branch_name TEXT,
    memory_summary TEXT,
    embedding_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
"""

SCHEMA_V4 = """
CREATE TABLE IF NOT EXISTS agent_actions (
    id TEXT PRIMARY KEY,
    agent_name TEXT,
    workspace_id TEXT,
    task_id TEXT,
    action_type TEXT,
    tool_used TEXT,
    result TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_V5 = """
CREATE TABLE IF NOT EXISTS orchestration_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    route TEXT,
    status TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME
);

CREATE TABLE IF NOT EXISTS orchestration_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    agent TEXT,
    status TEXT,
    result TEXT,
    FOREIGN KEY(run_id) REFERENCES orchestration_runs(id) ON DELETE CASCADE
);
"""

SCHEMA_V6 = """
ALTER TABLE chats ADD COLUMN workspace_path TEXT DEFAULT NULL;
ALTER TABLE chats ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP;
"""

class DatabaseManager:
    """
    Manages the SQLite database for a workspace, including vector extensions.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_dir()
        self.conn = self._get_connection()
        self._migrate()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            conn.enable_load_extension(True)
            import sqlite_vec
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception as e:
            # Silently ignore sqlite_vec load failure for non-vector testing
            pass
        
        # Configure PRAGMAs for high performance concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate(self):
        """Schema migration system."""
        current_version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        
        if current_version < 1:
            try:
                self.conn.executescript(SCHEMA_V1)
            except sqlite3.OperationalError as e:
                # If vec0 is missing, run it line by line ignoring vec_chunks
                for stmt in SCHEMA_V1.split(';'):
                    stmt = stmt.strip()
                    if stmt and "vec0" not in stmt:
                        self.conn.execute(stmt)
            
        if current_version < 2:
            self.conn.executescript(SCHEMA_V2)
            
        if current_version < 3:
            self.conn.executescript(SCHEMA_V3)
            
        if current_version < 4:
            self.conn.executescript(SCHEMA_V4)
            
        if current_version < 5:
            self.conn.executescript(SCHEMA_V5)
            
        if current_version < 6:
            self.conn.executescript(SCHEMA_V6)
            
        self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.conn.commit()

    def execute(self, query: str, params: tuple = ()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetchall(self, query: str, params: tuple = ()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
        
    def fetchone(self, query: str, params: tuple = ()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def close(self):
        self.conn.close()
