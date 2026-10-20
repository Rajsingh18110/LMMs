"""
Unit tests for lmms_sessions:
- SQLite session store with parent_session_id lineage
- DB schema migration safety with PRAGMA user_version
- Fork / resume round trip
- Context compaction preserving system prompt, pinned items, open tasks, recent N turns
- Compaction failure fallback (zero message loss)
- Pre-compaction history rollback / restore
"""

import os
import sqlite3
import pytest

from lmms_sessions.compactor import SessionCompactor, default_estimate_tokens
from lmms_sessions.models import Session, SessionMessage
from lmms_sessions.store import SessionStore


@pytest.fixture
def session_store(tmp_path):
    """Provides a fresh isolated SQLite session store."""
    db_file = str(tmp_path / "test_sessions.db")
    return SessionStore(db_path=db_file)


def test_db_migration_safety(tmp_path):
    """Verify PRAGMA user_version schema initialization and migration safety."""
    db_file = str(tmp_path / "migration_test.db")

    # 1. Initialize store on empty DB
    store = SessionStore(db_path=db_file)
    assert store.get_schema_version() == 1

    # 2. Verify tables and indexes exist
    with store._get_connection() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "sessions" in tables
        assert "messages" in tables
        assert "compaction_history" in tables

        indexes = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        ]
        assert "idx_messages_session" in indexes
        assert "idx_sessions_parent" in indexes

    # 3. Verify re-initializing on existing DB is safe and idempotent
    store_second = SessionStore(db_path=db_file)
    assert store_second.get_schema_version() == 1

    # 4. Verify foreign key constraints cascade
    s = store.create_session("Cascade Test")
    store.add_message(s.session_id, "user", "Message to be cascaded")
    store.save_compaction(s.session_id, 100, 50, "summary", [])

    assert len(store.get_messages(s.session_id)) == 1
    assert store.get_latest_compaction(s.session_id) is not None

    # Deleting session must cascade to messages and compaction history
    store.delete_session(s.session_id)
    assert len(store.get_messages(s.session_id)) == 0
    assert store.get_latest_compaction(s.session_id) is None


def test_fork_and_resume_round_trip(session_store):
    """Verify session creation, message persistence, forking with lineage, and resume."""
    # 1. Create parent session
    parent = session_store.create_session(title="Research Python AST")
    assert parent.parent_session_id is None

    # Add messages
    m1 = session_store.add_message(parent.session_id, "system", "You are an expert Python assistant.")
    m2 = session_store.add_message(parent.session_id, "user", "How do I parse AST in python?")
    m3 = session_store.add_message(parent.session_id, "assistant", "Use the ast.parse() standard library module.")

    parent_msgs = session_store.get_messages(parent.session_id)
    assert len(parent_msgs) == 3

    # 2. Fork session into a branch
    child = session_store.fork_session(parent.session_id, new_title="Branch: AST Transformers")
    assert child.session_id != parent.session_id
    assert child.parent_session_id == parent.session_id
    assert child.title == "Branch: AST Transformers"

    # Verify message history was duplicated into child
    child_msgs = session_store.get_messages(child.session_id)
    assert len(child_msgs) == 3
    assert [m.content for m in child_msgs] == [m.content for m in parent_msgs]
    assert [m.role for m in child_msgs] == ["system", "user", "assistant"]

    # 3. Add message to child only -> verify parent is untouched (isolation)
    session_store.add_message(child.session_id, "user", "Now show me NodeTransformer.")
    assert len(session_store.get_messages(child.session_id)) == 4
    assert len(session_store.get_messages(parent.session_id)) == 3

    # 4. Verify rename
    session_store.rename_session(parent.session_id, "Python AST Master Thread")
    updated_parent = session_store.get_session(parent.session_id)
    assert updated_parent is not None
    assert updated_parent.title == "Python AST Master Thread"

    # 5. Verify list_sessions includes parent lineage
    all_sessions = session_store.list_sessions()
    child_entry = next(s for s in all_sessions if s["session_id"] == child.session_id)
    assert child_entry["parent_session_id"] == parent.session_id
    assert child_entry["message_count"] == 4


def test_compaction_preserving_pinned_items(session_store):
    """
    Verify compaction:
    - Preserves system prompt
    - Preserves pinned messages
    - Preserves open tasks
    - Preserves last N turns
    - Summarizes intermediate dialogue
    - Shows before and after token savings
    """
    compactor = SessionCompactor(default_last_n_turns=2)
    session = session_store.create_session("Compaction Test")
    sid = session.session_id

    # Add system prompt
    session_store.add_message(sid, "system", "System: You are an autonomous software agent.")

    # Add historical dialogue turns (to be summarized)
    session_store.add_message(
        sid,
        "user",
        "Step 1: Deeply analyze the architecture of the entire repository across all modules and summarize dependencies.\n" + ("Extra background context...\n" * 10),
    )
    session_store.add_message(
        sid,
        "assistant",
        "Extensive architectural review:\n" + ("Detailed module breakdown and interface analysis...\n" * 15),
    )

    # Add pinned instruction in the middle
    session_store.add_message(
        sid,
        "user",
        "CRITICAL RULE: Always format output as JSON.",
        pinned=True,
    )

    # Add open task in the middle
    session_store.add_message(
        sid,
        "assistant",
        "Current Open Task: Implement SQLite store and test.",
        metadata={"is_task": True},
    )

    session_store.add_message(
        sid,
        "user",
        "Step 2: Read requirements file and inspect every single package constraint.\n" + ("Constraint evaluation...\n" * 10),
    )
    session_store.add_message(
        sid,
        "assistant",
        "Requirements analysis:\n" + ("Package version resolution notes...\n" * 15),
    )

    # Add recent 2 turns (4 messages) that MUST be preserved at the tail
    session_store.add_message(sid, "user", "Recent turn 1: What about bwrap?")
    session_store.add_message(sid, "assistant", "Recent answer 1: bwrap is working.")
    session_store.add_message(sid, "user", "Recent turn 2: Run pytest now.")
    session_store.add_message(sid, "assistant", "Recent answer 2: Running pytest.")


    msgs_before = session_store.get_messages(sid)
    assert len(msgs_before) == 11

    # Execute compaction
    res = compactor.compact(sid, session_store)
    assert res.success is True
    assert res.tokens_after < res.tokens_before
    assert res.messages_compacted > 0

    msgs_after = session_store.get_messages(sid)

    # 1. System prompt preserved
    assert msgs_after[0].role == "system"
    assert "autonomous software agent" in msgs_after[0].content

    # 2. Compacted summary inserted
    assert any("[Context Compaction Summary" in m.content for m in msgs_after)

    # 3. Pinned item preserved
    pinned = [m for m in msgs_after if m.pinned]
    assert len(pinned) == 1
    assert "CRITICAL RULE: Always format output as JSON" in pinned[0].content

    # 4. Open task preserved
    tasks = [m for m in msgs_after if m.metadata.get("is_task")]
    assert len(tasks) == 1
    assert "Current Open Task" in tasks[0].content

    # 5. Recent 2 turns (4 messages) preserved verbatim at tail
    tail_contents = [m.content for m in msgs_after[-4:]]
    assert "Recent turn 1: What about bwrap?" in tail_contents[0]
    assert "Recent answer 1: bwrap is working." in tail_contents[1]
    assert "Recent turn 2: Run pytest now." in tail_contents[2]
    assert "Recent answer 2: Running pytest." in tail_contents[3]


def test_compaction_failure_fallback_lossless(session_store):
    """
    CRITICAL TEST: If summarization fails (e.g. LLM error, OOM, exception),
    the compactor MUST abort and leave all original messages 100% intact.
    Zero message loss is guaranteed.
    """
    compactor = SessionCompactor(default_last_n_turns=1)
    session = session_store.create_session("Failure Fallback Test")
    sid = session.session_id

    # Create 8 dialogue turns
    for i in range(8):
        session_store.add_message(sid, "user", f"Turn {i} question")
        session_store.add_message(sid, "assistant", f"Turn {i} response")

    msgs_initial = session_store.get_messages(sid)
    assert len(msgs_initial) == 16

    # Provide a failing summarizer
    def failing_summarizer(messages):
        raise RuntimeError("Local model backend crashed or out of memory")

    res = compactor.compact(sid, session_store, summarizer=failing_summarizer)

    # Assert compaction reported failure
    assert res.success is False
    assert "Compaction aborted to prevent message loss" in str(res.error)

    # Assert message history in DB is 100% identical and unchanged
    msgs_after_fail = session_store.get_messages(sid)
    assert len(msgs_after_fail) == 16
    assert [m.content for m in msgs_after_fail] == [m.content for m in msgs_initial]


def test_compaction_restore_snapshot(session_store):
    """Verify that a compacted session can be restored to its pre-compacted state."""
    compactor = SessionCompactor(default_last_n_turns=1)
    session = session_store.create_session("Restore Test")
    sid = session.session_id

    # Create 6 turns
    for i in range(6):
        session_store.add_message(sid, "user", f"Message {i}")
        session_store.add_message(sid, "assistant", f"Reply {i}")

    original_messages = session_store.get_messages(sid)
    assert len(original_messages) == 12

    # Compact
    res = compactor.compact(sid, session_store)
    assert res.success is True
    compacted_messages = session_store.get_messages(sid)
    assert len(compacted_messages) < len(original_messages)

    # Restore from pre-compact snapshot
    ok = session_store.restore_compaction(sid)
    assert ok is True

    # Verify restored messages match original
    restored_messages = session_store.get_messages(sid)
    assert len(restored_messages) == 12
    assert [m.content for m in restored_messages] == [m.content for m in original_messages]


def test_should_auto_compact_threshold():
    """Verify auto-compaction trigger calculation at 80% default threshold."""
    compactor = SessionCompactor(auto_compact_ratio=0.8, context_window=4000)

    # Below 80% (3200 tokens) -> False
    assert compactor.should_auto_compact(current_tokens=3000) is False
    assert compactor.should_auto_compact(current_tokens=3199) is False

    # At or above 80% -> True
    assert compactor.should_auto_compact(current_tokens=3200) is True
    assert compactor.should_auto_compact(current_tokens=3500) is True
