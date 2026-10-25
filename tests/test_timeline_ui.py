"""
Comprehensive test suite for Gemini-style thinking and tool execution timeline in LMMs Terminal CLI.

Tests cover:
- Domain pill extraction, normalization, deduplication, and verification against source text
- Continuous vertical timeline tree connections
- Exactly-once rendering for generic tool observations (duplicate print bug regression test)
- Consecutive duplicate event detection
- Multiple search queries with associated domain pills
- Long-timeline memory bounding and rolling buffer eviction
- Visual states: thinking completion, failure, cancellation
- Real terminal rendering with Console recording harness
"""

import io
import re
import pytest
from rich.console import Console
from lmms.backend.cli.timeline import (
    TimelineRenderer,
    extract_domain_pills,
    get_timeline_renderer,
    render_tool_execution_panel,
    render_tool_observation_panel,
)


def strip_ansi(text: str) -> str:
    """Helper to remove ANSI escape sequences for text assertions."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


def test_domain_pill_extraction_verified():
    """Verify domains are extracted, normalized, deduplicated, and never hallucinated."""
    text = """
    Found 4 results:
    1. Documentation: https://docs.ollama.com/api/tool-calls
    2. Benchmark Report: https://benchlm.ai/evals/ollama-agents
    3. Duplicate link to docs: https://docs.ollama.com/overview
    4. WWW link: https://www.github.com/ollama/ollama
    5. Source citation: site: hermes-agent.ai/docs
    """
    pills = extract_domain_pills(text)

    # Must contain verified domains, stripped of www. and paths
    assert "docs.ollama.com" in pills
    assert "benchlm.ai" in pills
    assert "github.com" in pills
    assert "hermes-agent.ai" in pills

    # Must be deduplicated (docs.ollama.com only appears once)
    assert pills.count("docs.ollama.com") == 1

    # Must not contain junk or unverified domains
    for d in pills:
        assert "/" not in d
        assert not d.startswith("www.")
        assert "." in d


def test_domain_pill_extraction_empty_or_invalid():
    """Verify empty, malformed, or fake inputs produce empty domain lists."""
    assert extract_domain_pills("") == []
    assert extract_domain_pills("Hello world without any links") == []
    assert extract_domain_pills("Invalid url http://.com or http://bad_domain") == []
    assert extract_domain_pills(None) == []


def test_timeline_vertical_tree_search_and_pills():
    """Verify search events produce vertical trunks and horizontal domain pills."""
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)
    renderer = TimelineRenderer(console=test_console)

    renderer.start_turn(prompt="search for ollama tools", model_name="nemotron-3.5-super")

    # Tool call: search
    renderer.emit_tool_call("web_search", {"query": "ollama tool calling capabilities"})

    # Tool observation: includes links
    obs = "Search results:\n- https://docs.ollama.com/tools\n- https://benchlm.ai/evals"
    renderer.emit_observation("web_search", obs)

    # Thinking complete
    renderer.finish_thinking(elapsed_s=12, model_name="nemotron-3.5-super")

    clean = strip_ansi(string_io.getvalue())

    # Continuous vertical tree
    assert "│" in clean
    assert "Searching" in clean
    assert 'Searching "ollama tool calling capabilities"' in clean

    # Domain pills
    assert "docs.ollama.com" in clean
    assert "benchlm.ai" in clean

    # Header
    assert "::: Thought for 12s" in clean
    assert "Model : nemotron-3.5-super" in clean


def test_generic_tool_observation_no_duplicate_print():
    """
    Regression test for the diagnosed duplicate print bug:
    Generic tool observations previously printed lines twice (line 398 and line 400).
    Verify that generic tool observation renders exactly once.
    """
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)
    renderer = TimelineRenderer(console=test_console)

    renderer.emit_tool_call("custom_unregistered_tool", {"action": "sync"})
    renderer.emit_observation("custom_unregistered_tool", "Database sync completed with 42 rows updated.")

    clean = strip_ansi(string_io.getvalue())
    lines = [line.strip() for line in clean.splitlines() if line.strip()]

    # Count occurrences of the observation text
    obs_matches = [line for line in lines if "Database sync completed with 42 rows updated." in line]
    assert len(obs_matches) == 1, f"Expected exactly 1 observation line, found {len(obs_matches)}: {lines}"


def test_consecutive_duplicate_event_detection():
    """Verify that repeated consecutive tool calls receive a repeat badge to prevent confusing output."""
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)
    renderer = TimelineRenderer(console=test_console)

    renderer.emit_tool_call("terminal.run", {"command": "cargo test"})
    renderer.emit_tool_call("terminal.run", {"command": "cargo test"})

    clean = strip_ansi(string_io.getvalue())
    assert "(repeated)" in clean


def test_multiple_search_queries_connected_trunk():
    """Verify multiple sequential search queries remain connected along the vertical trunk."""
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)
    renderer = TimelineRenderer(console=test_console)

    renderer.start_turn(prompt="deep search", model_name="nemotron-120b")

    renderer.emit_tool_call("web_search", {"query": "query 1"})
    renderer.emit_observation("web_search", "Results: https://site-a.com/article")

    renderer.emit_tool_call("web_search", {"query": "query 2"})
    renderer.emit_observation("web_search", "Results: https://site-b.org/paper")

    renderer.emit_tool_call("web_search", {"query": "query 3"})
    renderer.emit_observation("web_search", "Results: https://site-c.net/repo")

    renderer.finish_thinking(elapsed_s=31, model_name="nemotron-120b")

    clean = strip_ansi(string_io.getvalue())

    assert 'Searching "query 1"' in clean
    assert 'Searching "query 2"' in clean
    assert 'Searching "query 3"' in clean
    assert "site-a.com" in clean
    assert "site-b.org" in clean
    assert "site-c.net" in clean
    assert "::: Thought for 31s" in clean


def test_long_timeline_memory_bounded():
    """Verify that very long multi-step execution sessions cap memory in a rolling buffer."""
    test_console = Console(file=io.StringIO(), force_terminal=False)
    renderer = TimelineRenderer(console=test_console, max_history_events=100)

    # Emit 250 tool calls and observations
    for i in range(250):
        renderer.emit_tool_call("files.read", {"path": f"file_{i}.py"}, step=i)
        renderer.emit_observation("files.read", f"Loaded {i} lines", step=i)

    history = renderer.get_event_history()
    # Memory must be bounded around max_history_events (not 500)
    assert len(history) <= 100
    assert len(history) > 50


def test_failure_and_cancellation_states():
    """Verify distinct error and cancellation visual nodes on the timeline."""
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)
    renderer = TimelineRenderer(console=test_console)

    renderer.emit_tool_call("terminal.run", {"command": "invalid_command"})
    renderer.emit_failure("Command failed with exit code 127: invalid_command not found")
    renderer.emit_cancellation("Operation stopped by user")

    clean = strip_ansi(string_io.getvalue())
    assert "Failed:" in clean
    assert "invalid_command not found" in clean
    assert "Cancelled:" in clean
    assert "Operation stopped by user" in clean


def test_backwards_compatible_delegates():
    """Verify that module-level functions render_tool_execution_panel & render_tool_observation_panel work."""
    string_io = io.StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard", width=120)

    # Re-initialize singleton with test console
    renderer = get_timeline_renderer(console=test_console)
    renderer.reset()

    out_exec = render_tool_execution_panel("files.read", {"path": "pubspec.yaml"}, step=1, max_steps=24)
    out_obs = render_tool_observation_panel("files.read", "name: my_app\nversion: 1.0.0\n", step=1, max_steps=24)

    clean = strip_ansi(string_io.getvalue())
    assert "Reading" in clean
    assert "pubspec.yaml" in clean
    assert "2 lines loaded" in clean
    assert "Step 1/24" not in clean  # Confirm removal of display-only cap
