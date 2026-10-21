# LMMS vs OpenAI Codex: Deep Forensic Audit Report
**Role**: Principal Engineer & Hostile Auditor  
**Date**: October 21, 2026  
**Target Codebases**:
- OpenAI Codex: `/home/kali/Projects/codex/codex-rs`
- LMMs: `/home/kali/Projects/LMMs`

---

## Executive Summary & Honest Parity Score

> [!CAUTION]
> **Hostile Auditor Assessment**:  
> Previous claims of *"100% operational across all phases"* were **significantly overclaimed**. Multiple components were only verified in isolated unit tests while remaining **completely disconnected** or **stubbed** in the primary user entrypoint (`lmms/backend/main.py`).

### Parity Score Formula
Each of the 24 foundational capability dimensions is evaluated on a strict operational rubric:
- **YES (1.0)**: Fully functional in live CLI user flow with raw execution proof.
- **PARTIAL (0.5)**: Implemented but constrained, partially wired, or missing critical Codex edge-case handling.
- **DISCONNECTED (0.25)**: Code exists in repository, may pass unit tests, but is NOT called or wired in the real runtime execution flow.
- **NO (0.0)**: Completely missing or empty stub (0 bytes).

$$\text{Score} = \frac{\sum \text{Points}}{\text{Total Features}} \times 100 = \frac{4 \times 1.0 + 12 \times 0.5 + 5 \times 0.25 + 3 \times 0.0}{24} = \frac{11.25}{24} \times 100 = \mathbf{46.88\%}$$

---

## Master Comparison Matrix (Codex vs LMMS)

| # | Codex Feature | Codex Source (File:Line) | LMMS Status | LMMS Source (File:Line) | Identified Gap | Priority | Evidence / Command Verification |
|---|---|---|---|---|---|---|---|
| 1 | **apply-patch Engine** | `apply-patch/src/lib.rs:35` | **PARTIAL** | `lmms/backend/tools/patch.py:90` | Supports `*** Begin Patch` and unified diff with `seek_sequence`, but `main.py` prompt does not instruct model to produce this format by default. | **P0** | `python3 tests/test_codex_parity.py` -> `test_02_codex_begin_patch_format` PASS |
| 2 | **Sandbox / bwrap Containment** | `bwrap/src/main.rs:1` | **PARTIAL** | `lmms_sandbox/bwrap.py:18` | Bubblewrap wrapper exists, but `main.py` defaults to `permission_level=medium` which bypasses sandbox (`sandboxed=False`). | **P0** | `grep -n "sandboxed" lmms/backend/tools/terminal.py` -> conditional bypass on lines 45-50 |
| 3 | **MCP Client Bridge** | `rmcp-client/src/lib.rs:1` | **PARTIAL** | `lmms_mcp/manager.py:38` | Dynamic bridge exists in `registry.py`, but MCP tools from `~/.lmms/mcp.json` are not pre-warmed in initial prompt context. | **P1** | `python3 tests/test_codex_parity.py` -> `test_05_dynamic_mcp_tool_bridging` PASS |
| 4 | **MCP Server Provider** | `codex-mcp/src/lib.rs:1` | **PARTIAL** | `lmms_mcp/server.py:15` | FastMCP server exists for basic tools, but has no auto-registration hook for IDE clients (VS Code/Cursor). | **P2** | `cat lmms_mcp/server.py` -> FastMCP server declaration |
| 5 | **Subprocess Execution (Exec)** | `exec/src/lib.rs:1` | **YES** | `lmms/backend/tools/terminal.py:27` | Full boundary checks, dangerous command filter, interactive conversion (`top`, `sudo`). | **P1** | `terminal.py:30` -> BLOCKED_COMMANDS verified |
| 6 | **Exec Policy & Approvals** | `execpolicy/src/policy.rs:1` | **PARTIAL** | `lmms_sandbox/policy.py:25` | `execpolicy.toml` parser exists, but runs disconnected from `permission_manager.py` in `main.py`. | **P0** | `grep -rn "execpolicy" lmms/backend/main.py` -> 0 matches |
| 7 | **Git Worktree Isolation** | `worktree/src/lib.rs:1` | **DISCONNECTED** | `lmms_worktree/manager.py:30` | `default_worktree_manager` exists, but CLI chat edits files directly on active branch instead of an ephemeral worktree. | **P0** | `grep -n "create_worktree" lmms/backend/main.py` -> only in CLI flags, never in chat loop |
| 8 | **Session Rollout & Lineage** | `rollout/src/lib.rs:1` | **PARTIAL** | `lmms_sessions/store.py:20` | SQLite store records turns, but in-chat session branching (`parent_session_id`) cannot be triggered without exiting to `/sessions`. | **P1** | `lmms/backend/main.py:2820` -> writes to `SessionStore` verified |
| 9 | **Context Compactor** | `core/src/compactor.rs` | **DISCONNECTED** | `lmms/backend/orchestration/compactor.py:1` | `compactor.py` was claimed operational, but `main.py` NEVER imports it! Uses ad-hoc inline observation truncation instead. | **P0** | `grep -rn "compactor" lmms/backend/main.py` -> NOT FOUND |
| 10 | **Reviewer Agent** | `collaboration-mode-templates/` | **DISCONNECTED** | `lmms/backend/agents/specialized/reviewer.py:1` | `ReviewerAgent` exists (100+ lines), but is dead code—no trigger in `main.py` or slash command exists. | **P1** | `grep -rn "ReviewerAgent" lmms/backend/main.py` -> NOT FOUND |
| 11 | **ReAct Loop & Tool Calling** | `shell-command/src/lib.rs` | **YES** | `lmms/backend/main.py:2550` | Dual parser (`<tool_call>` & raw JSON), ReAct loop, observation retention, loop protection. | **P0** | `test_backend_verification.py` -> Phase 3 PASS |
| 12 | **SSE Streaming & Audio Sync** | `app-server/src/lib.rs` | **YES** | `lmms/backend/main.py:2360` | Live chunk streaming, token overflow backpressure retry, clause-buffered voice synthesis. | **P1** | `main.py:2365` -> `chunks_iterator` verified |
| 13 | **Auth & Keyring Vault** | `login/src/lib.rs`, `keyring-store/` | **NO** | *None in backend* | Zero backend auth, no API key vault or keyring store. | **P2** | `ls lmms/backend/security/` -> No auth module |
| 14 | **Telemetry & Metrics** | `analytics/src/lib.rs` | **DISCONNECTED** | `lmms/backend/telemetry/metrics.py:1` | `metrics.py` is **0 bytes (empty file)**! `TraceLogger` writes to memory only without persistent replay. | **P1** | `ls -la lmms/backend/telemetry/metrics.py` -> 0 bytes |
| 15 | **Hierarchical AGENTS.md** | `models-manager/models.json:17` | **PARTIAL** | `lmms/backend/context/workspace_rules.py:1` | Loads `.lmmsrules`, but completely ignores standard `AGENTS.md` directory trees. | **P1** | `grep -rn "AGENTS.md" lmms/backend/` -> NOT FOUND |
| 16 | **Slash Commands System** | `tui/src/slash_command.rs` | **PARTIAL** | `lmms/backend/main.py:1840` | Supports `/newchat`, `/chat`, `/sessions`. Lacks `/panel`, `/review`, `/diff`, `/checkpoint`. | **P0** | `main.py:1845` -> slash command routing |
| 17 | **Undo & Turn Rollback** | `core/src/thread_rollout_truncation.rs:56` | **PARTIAL** | `lmms/backend/main.py:2125` | `/undo` requires explicit `-f <file>` and calls `git checkout HEAD~1`, which destroys uncommitted changes. No turn checkpoint rollback. | **P0** | `main.py:2135` -> `git checkout HEAD~1` confirmed |
| 18 | **Resume / Fork Session** | `core/src/session/` | **PARTIAL** | `lmms_sessions/store.py:65` | DB store supports it, but cannot be invoked in-stream from the active conversation turn. | **P1** | `lmms_sessions/store.py:65` -> `fork_session` exists |
| 19 | **Multimodal Vision / Image** | `attachment-store/src/lib.rs` | **YES** | `lmms/backend/main.py:2210` | Auto-extracts image paths from prompts, validates extensions, encodes base64 data URLs. | **P2** | `main.py:2215` -> base64 extraction verified |
| 20 | **Web Search & Crawling** | `tools/src/web_search.rs` | **YES** | `lmms/backend/tools/search.py:1` | Real web search scraping, Playwright DOM parsing, and Crawl4AI markdown extraction. | **P1** | `tools/search.py:20` -> `canonical_search_callback` verified |
| 21 | **System Notifications** | `app-server-protocol/src/notifications.rs` | **PARTIAL** | `lmms_server/dispatcher.py` | JSON-RPC notifications exist, but no desktop OS notifications fire when tasks complete. | **P2** | `lmms_server/dispatcher.py` -> JSON-RPC notifications |
| 22 | **TUI Interface** | `tui/src/lib.rs` | **PARTIAL** | `lmms/tui/main.py:1` | Textual TUI exists, but does not synchronize with CLI session state. | **P2** | `lmms/tui/main.py` -> Textual TUI entry |
| 23 | **RuleRouter / Agent Graph** | `core/src/tools/spec_plan.rs` | **DISCONNECTED** | `lmms/backend/router/rule_router.py:1` | `RuleRouter` builds an `ExecutionGraph`, but `main.py` NEVER executes it! Coding prompts bypass it completely. | **P0** | `grep -rn "RuleRouter" lmms/backend/main.py` -> NOT FOUND |
| 24 | **/panel Workflow GUI** | *N/A (Codex uses VS Code ext)* | **NO** | *None* | No PyQt6 node-canvas GUI with real-time event bus synchronization exists for the CLI. | **P0** | Search for `/panel` in `main.py` -> NOT FOUND |

---

## Detailed Section Breakdown

### Section A: Features That Truly Work in Live Flow (With Evidence)
1. **ReAct Tool-Calling Loop (`main.py:2550`)**:
   - Parses `<tool_call>` tags, JSON code blocks, and function dictionaries.
   - Enforces loop protection (stops after 3 identical calls) and runs iterative multi-turn execution.
   - *Evidence*: `python3 test_backend_verification.py` -> `test_phase_3_react_loop_and_dual_parser` passes cleanly.
2. **Subprocess Execution & Safety Boundaries (`tools/terminal.py:27`)**:
   - Filters `BLOCKED_COMMANDS` (`rm -rf /`, `mkfs`, fork bombs), converts interactive `top` to batch `top -b -n 1`, and enforces `is_within_workspace`.
   - *Evidence*: `terminal.py:30` BLOCKED_COMMANDS verified.
3. **Multimodal Vision Ingestion (`main.py:2210`)**:
   - Detects image file paths in prompts, verifies existence, base64 encodes, and streams OpenAI vision payloads.
4. **SSE Token Streaming & Audio Synthesis (`main.py:2360`)**:
   - Handles delta tokens from llama_cpp engine with backpressure recovery and live clause-buffered voice generation.

---

### Section B: Features in Code But Disconnected From Live CLI Flow
1. **Context Compactor (`lmms/backend/orchestration/compactor.py`)**:
   - Code exists with budget preservation and turn compaction, but `main.py` uses raw string slicing (`content[:head] + ...`). `compactor.py` is never imported.
2. **RuleRouter & Execution Graph (`lmms/backend/router/rule_router.py`)**:
   - `RuleRouter.route()` builds an `ExecutionGraph` with `OrchestratorAgent -> CodingAgent -> TesterAgent`, but `main.py` never calls or executes this graph.
3. **ReviewerAgent (`lmms/backend/agents/specialized/reviewer.py`)**:
   - 100+ lines of code review logic that is completely unreachable by any CLI command.
4. **Git Worktree Isolation (`lmms_worktree/manager.py`)**:
   - `WorktreeManager` exists with PID tracking and lease locks, but coding actions in CLI mutate files directly on the host repo.
5. **Telemetry Trace Logging (`lmms/backend/telemetry/metrics.py`)**:
   - `metrics.py` is 0 bytes. `observability.py` exists but does not write persistent replay logs.

---

### Section C: Features Completely Missing
1. **`/panel` Workflow Canvas GUI**: No PyQt6 node-canvas window with live event-bus animations exists.
2. **`AGENTS.md` Hierarchical Evaluation**: No scanner exists to parse and inherit nested `AGENTS.md` files up the directory tree.
3. **Security Auth & Keyring**: No unified credential vault or secure storage for API keys.
4. **Single-Command `/undo` Rollback**: No checkpoint-based state rewind exists to roll back dirty/uncommitted turns.

---

### Section D: False Claims & Overclaims in Previous Work
1. **Claim**: *"Fixed Context Double-Truncation Bug... In compactor.py, increased recent_turns_to_preserve from 3 to 8 turns"*.
   - **Auditor Fact**: `compactor.py` was modified, but `compactor.py` **is never even imported or called in `main.py`**. The CLI chat loop was using a hardcoded string truncation algorithm!
2. **Claim**: *"Coding and file operation requests are now deterministically dispatched to the OrchestratorAgent -> CodingAgent -> TesterAgent execution graph"*.
   - **Auditor Fact**: `rule_router.py` was created and tested in isolation, but `main.py` **never invokes `RuleRouter` or `ExecutionGraph`**. All prompts fell through directly to the raw chat loop!
3. **Claim**: *"All 5 Phases verified 100% operational"*.
   - **Auditor Fact**: Tests verified unit-level function returns, not end-to-end integration through the user-facing CLI.

---

### Section E: Mutation Check (Proving Test Veracity)
To satisfy Rule 4, we perform a mutation check on `ApplyPatchEngine`:
- **Mutation 1 (Search Sequence Mismatch)**:
  Target: `def add(a, b): return a + b`  
  Patch Search: `def subtract(a, b): return a - b`  
  *Result*: Rejected with `"Target sequence not found"`.
- **Mutation 2 (AST Syntax Corruption)**:
  Patch Replacement: `def broken_syntax(`  
  *Result*: Rejected with `AST SyntaxError`. Zero bytes written to disk. File integrity preserved.

---

## Action Plan: Priority Ordering for Phase 2

1. **P0-1: Wire `RuleRouter` & `ExecutionGraph` into `main.py`**:
   - Ensure coding prompts deterministically execute through `OrchestratorAgent -> CodingAgent -> TesterAgent`.
2. **P0-2: Wire Real Ephemeral Worktrees into `CodingAgent`**:
   - Execute all code edits and test runs inside an isolated git worktree via `default_worktree_manager`.
3. **P0-3: Wire `compactor.py` into `main.py` Context Pipeline**:
   - Replace primitive string slicing with the production `SessionCompactor`.
4. **P0-4: Implement Intelligent Single-Command `/undo`**:
   - Implement turn-level file snapshotting so `/undo` reverts the exact file modifications from the previous turn without manual flags.
5. **P0-5: Hierarchical `AGENTS.md` Engine**:
   - Scan from current file directory up to git root, load `AGENTS.md`, and inject scoped instructions.
6. **P0-6: Build `/panel` PyQt6 Node-Canvas Workflow Window**:
   - Build a standalone PyQt6 process connecting via IPC event bus with live pulse/glow animations and side-panel inspection.
