"""
lmms_sessions.models - Data structures for LMMs SQLite session storage and context compaction.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Session:
    """Represents a conversation session thread with branching lineage."""
    session_id: str
    title: str
    parent_session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionMessage:
    """Represents an individual message turn inside a session."""
    id: int
    session_id: str
    role: str
    content: str
    pinned: bool = False
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionResult:
    """Outcome of context compaction."""
    success: bool
    tokens_before: int
    tokens_after: int
    summary: str = ""
    messages_compacted: int = 0
    error: Optional[str] = None
