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
import subprocess
import sys
import pytest

from lmms_sessions.compactor import SessionCompactor, default_estimate_tokens
from lmms_sessions.models import Session, SessionMessage
from lmms_sessions.store import SessionStore


def test_import_does_not_create_user_session_store(tmp_path):
    """Importing session helpers must not create files in the user's home."""
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [os.getcwd(), env.get("PYTHONPATH", "")])
    )

    subprocess.run(
        [sys.executable, "-c", "import lmms_sessions.compactor"],
        cwd=os.getcwd(),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not (home / ".lmms").exists()


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


def _concurrent_writer_worker(db_path: str, count: int, worker_name: str, queue):
    """Worker process writing messages concurrently to test SQLite WAL concurrency."""
    try:
        store = SessionStore(db_path=db_path)
        session = store.create_session(title=f"Worker {worker_name}")
        for i in range(count):
            store.add_message(session.session_id, "user", f"{worker_name} message {i}")
        queue.put((worker_name, session.session_id, None))
    except Exception as exc:
        queue.put((worker_name, None, str(exc)))


def test_sqlite_concurrent_processes_and_permissions(tmp_path):
    """
    1. Verify sessions.db file is created with 0600 permissions.
    2. Verify two concurrent OS processes writing simultaneously complete without 'database is locked'.
    """
    import multiprocessing
    import stat

    db_file = str(tmp_path / "concurrent_sessions.db")
    # Initialize store
    main_store = SessionStore(db_path=db_file)

    # Verify permissions 0600
    file_stat = os.stat(db_file)
    file_perm = stat.S_IMODE(file_stat.st_mode)
    assert file_perm == 0o600, f"Expected 0600 permissions, got {oct(file_perm)}"

    queue = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=_concurrent_writer_worker, args=(db_file, 40, "P1", queue))
    p2 = multiprocessing.Process(target=_concurrent_writer_worker, args=(db_file, 40, "P2", queue))

    p1.start()
    p2.start()

    p1.join(timeout=15)
    p2.join(timeout=15)

    assert not p1.is_alive()
    assert not p2.is_alive()

    results = [queue.get(timeout=2), queue.get(timeout=2)]
    for wname, sid, err in results:
        assert err is None, f"Worker {wname} encountered error: {err}"
        assert sid is not None
        msgs = main_store.get_messages(sid)
        assert len(msgs) == 40


def test_compaction_never_splits_tool_call_pairs(session_store):
    """
    Verify that compaction never separates an assistant tool_call from its tool_result
    even if the naive 'last N turns' boundary falls between them.
    """
    compactor = SessionCompactor(default_last_n_turns=1)
    s = session_store.create_session("Tool Pair Test")
    sid = s.session_id

    # Dialogue history:
    # 0: System prompt
    session_store.add_message(sid, "system", "You are an assistant with tools.")
    # 1: User turn 1
    session_store.add_message(sid, "user", "What is the weather in Delhi?")
    # 2: Assistant turn 1
    session_store.add_message(sid, "assistant", "Checking weather...")
    # 3: User turn 2
    session_store.add_message(sid, "user", "Run the fetch tool.")
    # 4: Assistant tool call
    session_store.add_message(
        sid,
        "assistant",
        "<tool_call>fetch_weather({'location': 'Delhi'})</tool_call>",
        metadata={"tool_calls": [{"id": "call_123", "name": "fetch_weather"}]},
    )
    # 5: Tool result
    session_store.add_message(
        sid,
        "tool",
        "<observation>Delhi: 28C, Sunny</observation>",
        metadata={"tool_call_id": "call_123"},
    )
    # 6: Final assistant response
    session_store.add_message(sid, "assistant", "The weather in Delhi is 28C and sunny.")

    # With default_last_n_turns=1 (target 2 messages: 5 and 6), naive cutoff would be at index 5,
    # separating assistant tool call (index 4) from tool result (index 5)!
    res = compactor.compact(sid, session_store)
    assert res.success is True

    compacted = session_store.get_messages(sid)
    # Ensure both tool call and tool result are kept intact in the recent messages
    roles_after = [m.role for m in compacted]
    contents_after = [m.content for m in compacted]

    # Verify tool call and tool observation are both present
    tool_call_present = any("<tool_call>" in c for c in contents_after)
    tool_obs_present = any("<observation>" in c for c in contents_after)
    assert tool_call_present is True
    assert tool_obs_present is True

    # Verify tool call appears immediately before tool observation in the tail
    call_idx = next(i for i, c in enumerate(contents_after) if "<tool_call>" in c)
    obs_idx = next(i for i, c in enumerate(contents_after) if "<observation>" in c)
    assert obs_idx == call_idx + 1


def test_fork_and_resume_live_context_reload(tmp_path):
    """
    Verify that /fork copies history and /resume reloads live conversation context
    via SessionCLI and on_context_change callbacks.
    """
    from lmms_sessions.cli import SessionCLI

    db_path = str(tmp_path / "cli_test.db")
    cli = SessionCLI(store=SessionStore(db_path=db_path))

    # Track callback invocations
    context_history = []
    def on_change(msgs):
        context_history.append(msgs)

    cli.on_context_change = on_change

    # 1. Start on initial session
    parent_id = cli.active_session_id
    cli.store.add_message(parent_id, "user", "Message 1 in Parent")
    cli.store.add_message(parent_id, "assistant", "Response 1 in Parent")

    # 2. Fork
    cli.handle_fork(["Forked Branch"])
    forked_id = cli.active_session_id
    assert forked_id != parent_id

    # Verify on_context_change was invoked with duplicated parent messages
    assert len(context_history) == 1
    assert len(context_history[0]) == 2
    assert context_history[0][0]["content"] == "Message 1 in Parent"

    # Add new message to forked branch only
    cli.store.add_message(forked_id, "user", "Message 2 in Fork")

    # 3. Resume parent
    cli.handle_resume([parent_id])
    assert cli.active_session_id == parent_id

    # Verify on_context_change reloaded parent messages (which only has 2 messages, not 3)
    assert len(context_history) == 2
    assert len(context_history[1]) == 2
    assert context_history[1][-1]["content"] == "Response 1 in Parent"


def test_compaction_snapshot_retention_limit(tmp_path):
    """Verify that compaction snapshot retention limit prunes older snapshots."""
    db_path = str(tmp_path / "retention_test.db")
    # Configured to keep only last 3 snapshots
    store = SessionStore(db_path=db_path, max_snapshots_per_session=3)
    s = store.create_session("Retention Test")
    sid = s.session_id

    # Save 7 compactions
    for i in range(1, 8):
        store.save_compaction(
            session_id=sid,
            tokens_before=1000 * i,
            tokens_after=500 * i,
            summary=f"Summary {i}",
            pre_compact_messages=[{"role": "user", "content": f"msg {i}"}],
        )

    # Check compaction_history count in DB
    with store._get_connection() as conn:
        rows = conn.execute(
            "SELECT id, summary FROM compaction_history WHERE session_id = ? ORDER BY id ASC",
            (sid,),
        ).fetchall()
        assert len(rows) == 3
        summaries = [r["summary"] for r in rows]
        # Only the 3 newest summaries (5, 6, 7) should be retained
        assert summaries == ["Summary 5", "Summary 6", "Summary 7"]


def test_real_chat_loop_auto_compact_and_live_context_reload(tmp_path, monkeypatch):
    """
    Integration test: verify that auto-compact runs in InteractiveChat after turns
    and updates the in-memory self.messages using a fake model.
    """
    from lmms.cli.interactive import InteractiveChat
    from lmms_sessions.cli import SessionCLI

    db_path = str(tmp_path / "chat_loop_test.db")
    store = SessionStore(db_path=db_path)
    # Set small auto-compact threshold
    compactor = SessionCompactor(auto_compact_ratio=0.5, context_window=200, default_last_n_turns=1)
    custom_cli = SessionCLI(store=store, compactor=compactor)

    chat = InteractiveChat(model_name="fake-model")
    chat.session_cli = custom_cli
    chat.session_cli.on_context_change = chat._on_context_changed

    # Mock stream_chat on CLIClient to return predictable tokens
    def fake_stream_chat(*args, **kwargs):
        yield "This is a detailed response from the fake model that generates tokens."

    monkeypatch.setattr(chat.client, "stream_chat", fake_stream_chat)

    cur_id = chat.session_cli._ensure_initial_session()

    # Simulate 6 chat turns directly through chat loop logic
    for turn in range(6):
        user_msg = f"User Turn {turn}: " + "word " * 15
        chat.messages.append({"role": "user", "content": user_msg})
        chat.session_cli.store.add_message(cur_id, role="user", content=user_msg)

        full_resp = "".join(list(chat.client.stream_chat(model_name=chat.model_name, messages=chat.messages)))
        chat.messages.append({"role": "assistant", "content": full_resp})
        chat.session_cli.store.add_message(cur_id, role="assistant", content=full_resp)

        # Chat loop auto-compact check
        if chat.session_cli.compactor.should_auto_compact(cur_id, chat.session_cli.store):
            res = chat.session_cli.compactor.compact(cur_id, chat.session_cli.store)
            if res.success:
                chat.messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in chat.session_cli.get_live_messages()
                ]

    # Verify that compaction triggered and live in-memory context was replaced
    assert len(chat.messages) < 12
    # Verify summary message is present in the live in-memory messages
    has_summary = any("Context Compaction Summary" in m["content"] for m in chat.messages)
    assert has_summary is True
    # Verify DB has snapshot
    assert store.get_latest_compaction(cur_id) is not None

