# PostgreSQL + pgvector Migration Audit

## Scope

This report captures the current LMMs persistence architecture before code migration. It is intentionally limited to audit, target schema, migration mapping, file impact, risks, and verification strategy.

## Current Architecture

LMMs currently persists workspace, chat, memory, vector, task, research, agent, and orchestration data across several independent stores:

- Workspace identity is managed by `WorkspaceManager` using `~/.lmms/workspaces/registry.json` plus a per-folder `.lmms-id` file. Workspace SQLite databases live under `~/.lmms/workspaces/<workspace_id>/database.sqlite`.
- Workspace SQLite schema version 6 stores chats, messages, files, git data, chunks, sqlite-vec embeddings, tasks, task events, task memory, agent actions, orchestration runs, and orchestration steps.
- Interactive CLI chat history is stored as JSON files under `~/.lmms/chats/`.
- CLI subcommands use a separate global SQLite database at `~/.lmms/chats.db` through `ChatRouter`.
- Memory has another global SQLite database at `~/.lmms/memory.db`.
- RAG uses FAISS files at `~/.lmms/workspaces/<workspace_id>/index.faiss` plus `meta.json`.
- Research history is stored as JSON files under `~/.lmms/research/`.
- Agent action history also has a workspace-local JSONL path at `<workspace>/.lmms/action_history.jsonl`.
- The GUI keeps chat messages in memory and does not currently have a complete persistent chat save/load path.

The biggest architectural issue is not one single database bug; it is that workspace identity, chat identity, memory, vector search, and agent/task records are split across multiple formats with inconsistent workspace keys.

## Important Current Bugs And Risks Found

- `lmms/api/server.py` still calls `runtime.generate()` without passing `model_name`. Even if the GUI and agents pass the selected model, the API runtime can still fall back to the first loaded model.
- Workspace identifiers are inconsistent: UUID from `.lmms-id`, absolute path in task rows, MD5 path hash for some RAG calls, and config `workspace_dir` in tools.
- Chat storage is fragmented between workspace SQLite, global `chats.db`, JSON chat files, and GUI in-memory state.
- Tool execution is not centrally persisted as durable `tool_runs`; some legacy tool paths can bypass the newer canonical executor boundary model.
- sqlite-vec and FAISS coexist. Migrating embeddings needs a single pgvector model/dimension strategy.
- Existing user data must remain untouched during migration until export/import verification is complete.

## Proposed PostgreSQL Schema

Core tables:

- `workspaces`: stable workspace UUID, current path, display name, created/updated timestamps, metadata.
- `workspace_paths`: path history for moved workspaces.
- `chats`: workspace-scoped chat sessions with title, summary, status, created/updated timestamps, last active timestamp, metadata.
- `messages`: chat messages with role, content, thought, model name, provider/runtime, status, timestamps, attachments, and metadata.
- `message_events`: streaming deltas, reasoning deltas, tool markers, cancellation, and error events.
- `models`: known local/API models and last selected state per workspace or global scope.

Task and agent tables:

- `tasks`
- `task_dependencies`
- `task_events`
- `task_assignments`
- `task_memory`
- `agent_actions`
- `orchestration_runs`
- `orchestration_steps`
- `tool_runs`
- `file_changes`

Knowledge and vector tables:

- `sources`: files, git objects, chats, research evidence, web pages, and generated artifacts.
- `chunks`: normalized text chunks with source references, file path, line ranges, content hash, and metadata.
- `embeddings`: pgvector embedding rows with `chunk_id`, embedding model, dimension, content hash, and vector.
- `research_runs`
- `research_evidence`
- `research_citations`

Migration support tables:

- `migration_runs`
- `legacy_id_map`
- `migration_issues`

## Migration Mapping

- `~/.lmms/workspaces/registry.json` and `.lmms-id` -> `workspaces`, `workspace_paths`.
- Per-workspace SQLite `chats` and `messages` -> `chats`, `messages`.
- JSON files in `~/.lmms/chats/` -> `chats`, `messages`, preserving assistant `thought` fields.
- Global `~/.lmms/chats.db` -> `chats` plus metadata/session flags.
- Global `~/.lmms/memory.db` -> `messages` when session mapping is possible; otherwise `sources` or migration metadata.
- Workspace SQLite `files`, `git_*`, `chunks` -> `sources`, `chunks`, git metadata tables.
- sqlite-vec `vec_chunks` and FAISS `index.faiss`/`meta.json` -> pgvector `embeddings`, preferably by re-embedding source chunks rather than trusting mixed legacy dimensions.
- `tasks`, `task_dependencies`, `task_events`, `task_assignments`, `task_memory` -> same logical PostgreSQL tables.
- `agent_actions`, orchestration tables, and JSONL action history -> `agent_actions`, `tool_runs`, `orchestration_runs`, `orchestration_steps`, `file_changes`.
- Research JSON files -> `research_runs`, `research_evidence`, `research_citations`.

## Files Likely To Change

- `lmms/backend/config/config.py`
- `lmms/backend/logic/manager.py`
- `lmms/backend/db/workspace/workspace/manager.py`
- `lmms/backend/db/workspace/workspace/db.py`
- `lmms/backend/logic/chat_router.py`
- `lmms/backend/memory/providers/sqlite.py`
- `lmms/backend/memory/embeddings/faiss_provider.py`
- `lmms/backend/tools/rag.py`
- `lmms/backend/tools/core/executor.py`
- `lmms/backend/tasks/manager.py`
- `lmms/backend/router/manager.py`
- `lmms/backend/agents/manager.py`
- `lmms/backend/agents/core_agents/agents/history.py`
- `lmms/backend/research/history.py`
- `lmms/backend/main.py`
- `lmms/backend/cli/cli.py`
- `lmms/gui/pages/chat_page.py`
- `lmms/gui/core/main_window.py`
- `lmms/gui/state/chat_message.py`
- `lmms/api/server.py`
- New PostgreSQL persistence and migration modules under `lmms/backend/db/`.

## Files Expected To Remain Mostly Untouched

- Model loading internals except model-name passthrough.
- Provider download/install code.
- Most GUI widgets, except where they need persistence integration.
- Existing user project files inside workspaces.
- Legacy SQLite/JSON/FAISS files during early migration phases.

## Recommended Implementation Phases

1. Add PostgreSQL configuration and connection layer without changing callers.
2. Add SQL migrations and schema tests.
3. Add repository classes for workspaces, chats, messages, tasks, tools, research, and embeddings.
4. Add read-through/write-through adapters so current SQLite/JSON data still works.
5. Add export/import migration CLI with dry-run mode.
6. Move GUI and CLI chat persistence to the unified repository.
7. Move task, agent, orchestration, and tool run persistence.
8. Move RAG chunks and embeddings to pgvector.
9. Keep legacy stores read-only for rollback.
10. Remove legacy write paths only after migration tests pass.

## Test Plan

- Unit tests for PostgreSQL repositories using isolated test database settings.
- Migration dry-run tests for workspace registry, workspace SQLite, chat JSON, `chats.db`, `memory.db`, research JSON, and FAISS metadata.
- Parser tests to guarantee `thought` survives save/load.
- GUI tests for workspace persistence, chat reload, selected model persistence, paste/copy behavior, and no model fallback.
- Tool boundary tests verifying all file and terminal tools use the active workspace.
- RAG tests for chunk insertion, pgvector search, and embedding dimension mismatch handling.
- Rollback tests confirming legacy files are not deleted or mutated during migration.

## Recommendation

Yes, the PostgreSQL + pgvector migration is possible in this codebase, but it should not be done as a single replacement patch. The safe path is to add a PostgreSQL persistence layer first, migrate data with explicit legacy mapping, then switch GUI/CLI/backend services over one subsystem at a time.
