"""
lmms_sessions.store - SQLite-backed session store with branching lineage (parent_session_id)
and schema migration safety using standard library sqlite3.
"""

import contextlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from lmms_sessions.models import Session, SessionMessage

CURRENT_SCHEMA_VERSION = 1


class SessionStore:
    """Manages sessions, messages, and compaction history in SQLite."""

    def __init__(self, db_path: Optional[str] = None, max_snapshots_per_session: int = 5):
        self.max_snapshots_per_session = max_snapshots_per_session
        if db_path is None:
            home = Path.home()
            lmms_dir = home / ".lmms"
            lmms_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(str(lmms_dir), 0o700)
            except OSError:
                pass
            self.db_path = str(lmms_dir / "sessions.db")
        else:
            self.db_path = db_path
            parent = os.path.dirname(os.path.abspath(self.db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
                try:
                    os.chmod(parent, 0o700)
                except OSError:
                    pass

        # Secure file permissions 0600 on creation
        if not os.path.exists(self.db_path):
            try:
                fd = os.open(self.db_path, os.O_WRONLY | os.O_CREAT, 0o600)
                os.close(fd)
            except OSError:
                pass
        else:
            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                pass

        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()


    def _init_db(self) -> None:
        """Applies schema migrations based on PRAGMA user_version."""
        with self._get_connection() as conn:
            cur = conn.execute("PRAGMA user_version;")
            row = cur.fetchone()
            current_version = int(row[0]) if row else 0

            if current_version < 1:
                # Version 1 schema: sessions with parent_session_id, messages, compaction_history
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        parent_session_id TEXT,
                        title TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        metadata TEXT DEFAULT '{}',
                        FOREIGN KEY(parent_session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        pinned INTEGER DEFAULT 0,
                        token_count INTEGER DEFAULT 0,
                        created_at REAL NOT NULL,
                        metadata TEXT DEFAULT '{}',
                        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS compaction_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        compacted_at REAL NOT NULL,
                        tokens_before INTEGER NOT NULL,
                        tokens_after INTEGER NOT NULL,
                        summary TEXT NOT NULL,
                        pre_compact_messages TEXT NOT NULL,
                        FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
                    PRAGMA user_version = 1;
                """)

    def get_schema_version(self) -> int:
        """Returns the current PRAGMA user_version of the database."""
        with self._get_connection() as conn:
            cur = conn.execute("PRAGMA user_version;")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def create_session(
        self,
        title: str = "New Session",
        parent_session_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Creates a new session in SQLite."""
        sid = session_id or uuid.uuid4().hex[:8]
        now = time.time()
        meta_json = json.dumps(metadata or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, parent_session_id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sid, parent_session_id, title, now, now, meta_json),
            )

        return Session(
            session_id=sid,
            parent_session_id=parent_session_id,
            title=title,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieves session metadata by ID."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT session_id, parent_session_id, title, created_at, updated_at, metadata FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            try:
                meta = json.loads(row["metadata"])
            except Exception:
                meta = {}

            return Session(
                session_id=row["session_id"],
                parent_session_id=row["parent_session_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=meta,
            )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all sessions with message counts and parent lineage."""
        query = """
            SELECT 
                s.session_id,
                s.parent_session_id,
                s.title,
                s.created_at,
                s.updated_at,
                s.metadata,
                COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.session_id = m.session_id
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC;
        """
        results: List[Dict[str, Any]] = []
        with self._get_connection() as conn:
            for row in conn.execute(query):
                try:
                    meta = json.loads(row["metadata"])
                except Exception:
                    meta = {}
                results.append({
                    "session_id": row["session_id"],
                    "parent_session_id": row["parent_session_id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": int(row["message_count"]),
                    "metadata": meta,
                })
        return results

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Renames a session."""
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                (new_title, now, session_id),
            )
            return cur.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and cascades to its messages."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0

    def fork_session(self, source_session_id: str, new_title: Optional[str] = None) -> Session:
        """
        Forks an existing session: creates a child session with parent_session_id
        pointing to source_session_id, and copies the message history.
        """
        source = self.get_session(source_session_id)
        if not source:
            raise ValueError(f"Source session '{source_session_id}' not found.")

        title = new_title or f"Fork of {source.title}"
        forked = self.create_session(title=title, parent_session_id=source_session_id)

        # Copy messages from source to forked session
        messages = self.get_messages(source_session_id)
        with self._get_connection() as conn:
            for msg in messages:
                conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, pinned, token_count, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        forked.session_id,
                        msg.role,
                        msg.content,
                        1 if msg.pinned else 0,
                        msg.token_count,
                        msg.created_at,
                        json.dumps(msg.metadata),
                    ),
                )

        return forked

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        pinned: bool = False,
        token_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionMessage:
        """Adds a message to a session and updates the session's updated_at timestamp."""
        now = time.time()
        meta_json = json.dumps(metadata or {})
        tok = token_count or max(1, len(content) // 4)

        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, pinned, token_count, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, 1 if pinned else 0, tok, now, meta_json),
            )
            msg_id = int(cur.lastrowid or 0)
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )

        return SessionMessage(
            id=msg_id,
            session_id=session_id,
            role=role,
            content=content,
            pinned=pinned,
            token_count=tok,
            created_at=now,
            metadata=metadata or {},
        )

    def replace_messages(self, session_id: str, new_messages: List[Dict[str, Any]]) -> None:
        """Atomically clears and replaces all messages for a session within a single transaction."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            for m in new_messages:
                tok = m.get("token_count", 0) or max(1, len(m.get("content", "")) // 4)
                created_ts = m.get("created_at") or now
                conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, pinned, token_count, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        m["role"],
                        m["content"],
                        1 if m.get("pinned", False) else 0,
                        tok,
                        created_ts,
                        json.dumps(m.get("metadata", {})),
                    ),
                )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))


    def get_messages(self, session_id: str) -> List[SessionMessage]:

        """Retrieves all messages for a session in chronological order."""
        messages: List[SessionMessage] = []
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT id, session_id, role, content, pinned, token_count, created_at, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            for row in cur:
                try:
                    meta = json.loads(row["metadata"])
                except Exception:
                    meta = {}

                messages.append(SessionMessage(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    pinned=bool(row["pinned"]),
                    token_count=row["token_count"],
                    created_at=row["created_at"],
                    metadata=meta,
                ))
        return messages

    def set_pinned(self, message_id: int, pinned: bool) -> bool:
        """Pins or unpins a message."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE messages SET pinned = ? WHERE id = ?",
                (1 if pinned else 0, message_id),
            )
            return cur.rowcount > 0

    def save_compaction(
        self,
        session_id: str,
        tokens_before: int,
        tokens_after: int,
        summary: str,
        pre_compact_messages: Union[List[SessionMessage], List[Dict[str, Any]]],
    ) -> int:
        """Stores pre-compact message snapshot in compaction_history."""
        now = time.time()
        serialized = json.dumps([
            {
                "id": getattr(m, "id", None) if not isinstance(m, dict) else m.get("id"),
                "role": getattr(m, "role", "user") if not isinstance(m, dict) else m.get("role", "user"),
                "content": getattr(m, "content", "") if not isinstance(m, dict) else m.get("content", ""),
                "pinned": getattr(m, "pinned", False) if not isinstance(m, dict) else m.get("pinned", False),
                "token_count": getattr(m, "token_count", 0) if not isinstance(m, dict) else m.get("token_count", 0),
                "created_at": getattr(m, "created_at", now) if not isinstance(m, dict) else m.get("created_at", now),
                "metadata": getattr(m, "metadata", {}) if not isinstance(m, dict) else m.get("metadata", {}),
            }
            for m in pre_compact_messages
        ])

        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO compaction_history (session_id, compacted_at, tokens_before, tokens_after, summary, pre_compact_messages)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, now, tokens_before, tokens_after, summary, serialized),
            )
            new_id = int(cur.lastrowid or 0)

            # Enforce snapshot retention limit per session
            if self.max_snapshots_per_session > 0:
                cur_old = conn.execute(
                    """
                    SELECT id FROM compaction_history
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT -1 OFFSET ?
                    """,
                    (session_id, self.max_snapshots_per_session),
                )
                old_ids = [r[0] for r in cur_old.fetchall()]
                if old_ids:
                    placeholders = ",".join("?" for _ in old_ids)
                    conn.execute(
                        f"DELETE FROM compaction_history WHERE id IN ({placeholders})",
                        old_ids,
                    )

            return new_id



    def get_latest_compaction(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent compaction snapshot for the session."""
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, session_id, compacted_at, tokens_before, tokens_after, summary, pre_compact_messages
                FROM compaction_history
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            try:
                pre_msgs = json.loads(row["pre_compact_messages"])
            except Exception:
                pre_msgs = []

            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "compacted_at": row["compacted_at"],
                "tokens_before": row["tokens_before"],
                "tokens_after": row["tokens_after"],
                "summary": row["summary"],
                "pre_compact_messages": pre_msgs,
            }

    def restore_compaction(self, session_id: str) -> bool:
        """
        Restores the pre-compact message history from the latest snapshot,
        ensuring zero message loss rollback.
        """
        latest = self.get_latest_compaction(session_id)
        if not latest or not latest["pre_compact_messages"]:
            return False

        pre_messages = latest["pre_compact_messages"]
        compaction_id = latest["id"]

        with self._get_connection() as conn:
            # 1. Clear current compacted messages
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

            # 2. Re-insert original pre-compact messages
            for m in pre_messages:
                conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, pinned, token_count, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        m["role"],
                        m["content"],
                        1 if m.get("pinned", False) else 0,
                        m.get("token_count", 0),
                        m.get("created_at") or time.time(),
                        json.dumps(m.get("metadata", {})),

                    ),
                )

            # 3. Remove the used compaction snapshot
            conn.execute("DELETE FROM compaction_history WHERE id = ?", (compaction_id,))
            conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (time.time(), session_id))

        return True
