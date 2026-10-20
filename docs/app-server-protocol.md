# LMMs App-Server Protocol Specification (JSON-RPC 2.0)

The LMMs App-Server exposes a high-performance, asynchronous JSON-RPC 2.0 interface designed for IDE extensions (VS Code, Cursor, JetBrains), desktop GUIs, and external orchestrators.

## 1. Transports & Security

### 1.1 Unix Domain Socket (Default & Recommended)
- **Default Socket Path:**
  - If `$XDG_RUNTIME_DIR` exists: `$XDG_RUNTIME_DIR/lmms/lmms.sock`
  - Fallback: `~/.lmms/lmms.sock`
- **Security:**
  - Socket directory created with mode `0700` (user-only).
  - Socket file created with mode `0600` (user-only read/write).
  - No network exposure. Stale socket files are automatically cleaned up on shutdown.

### 1.2 Stdio Mode
- Started via `lmms app-server --stdio`.
- Directly attaches to standard input (stdin) and standard output (stdout).
- Ideal for IDE language servers and child process integrations.

### 1.3 Optional Localhost TCP
- Enabled explicitly via `--tcp <port>` (e.g. `lmms app-server --tcp 8765`).
- Strictly binds to `127.0.0.1` (localhost only).
- **Mandatory Authentication:** Requires `--auth-token <token>` or generates a cryptographically random 32-byte hexadecimal token printed to stderr.
- Clients must include `"auth_token": "<token>"` in the request `params`.

---

## 2. Framing & Message Format

All messages are JSON-RPC 2.0 objects formatted as single-line JSON followed by a newline (`\n`):

### 2.1 Request Format
```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"client_name": "vscode-lmms", "client_version": "1.0.0"}}
```

### 2.2 Response Format
```json
{"jsonrpc": "2.0", "id": 1, "result": {"server_name": "lmms-app-server", "server_version": "1.0.0"}}
```

### 2.3 Error Format
```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
```

### 2.4 Notification Format (Server to Client)
Notifications do not contain an `id` field and indicate streaming events:
```json
{"jsonrpc": "2.0", "method": "message.token", "params": {"session_id": "s1", "request_id": 1, "token": "Hello"}}
```

---

## 3. Protocol Methods

| Method | Parameters | Return Value | Description |
|---|---|---|---|
| `initialize` | `client_name?: str, client_version?: str` | Server info & capabilities object | Handshake declaring protocol support and version. |
| `status` | none | System health & status object | Reports engine readiness, active sessions, sandbox info, and MCP tool counts. |
| `session.create` | `title?: str, metadata?: object` | Session metadata object | Creates a fresh SQLite-backed conversation session. |
| `session.list` | none | Array of session objects | Lists all sessions with message counts, timestamps, and lineage. |
| `session.resume` | `session_id: str` | Session object with full message history | Retrieves session details and past messages in chronological order. |
| `session.fork` | `session_id: str, title?: str` | New forked session object | Clones session dialogue up to current point with `parent_session_id`. |
| `session.rename` | `session_id: str, title: str` | `{"success": true, ...}` | Renames a session. |
| `message.send` | `session_id?: str, content: str, stream?: bool, permission_tier?: str` | Assistant response message object | Dispatches prompt to model. Streams tokens and tool calls as notifications. |
| `message.cancel` | `request_id: str \| int` | `{"cancelled": bool}` | Aborts an active ongoing message generation. |
| `tool.approve` | `prompt_id: str` | `{"approved": true}` | Approves a pending tool permission request. |
| `tool.deny` | `prompt_id: str, reason?: str` | `{"denied": true}` | Rejects a pending tool permission request. |
| `mcp.list` | none | Array of MCP servers & tools | Enumerates tools exposed by active MCP servers. |
| `mcp.call` | `server_name: str, tool_name: str, arguments: object` | MCP tool result object | Invokes tool via configured sandbox. |
| `worktree.status` | `repo_path?: str` | Worktree status object | Returns active branch, dirty state, and worktree isolation state. |
| `worktree.diff` | `repo_path?: str` | `{"diff": str}` | Returns unified git diff of worktree modifications. |
| `worktree.apply` | `repo_path?: str` | `{"applied": bool}` | Merges worktree commits/edits back to base workspace. |
| `worktree.discard` | `repo_path?: str` | `{"discarded": bool}` | Discards isolated worktree and cleans temporary git worktree. |
| `compact` | `session_id: str, restore?: bool` | Compaction summary or restore status | Executes context compaction or rolls back to pre-compact snapshot. |

---

## 4. Server Notifications (Streaming Events)

During `message.send`, the server emits notifications back to the client:

### 4.1 `message.token`
Emitted as model tokens are generated:
```json
{
  "jsonrpc": "2.0",
  "method": "message.token",
  "params": {
    "session_id": "c1f8a2",
    "request_id": 42,
    "token": "def calculate_sum"
  }
}
```

### 4.2 `message.tool_call`
Emitted when model outputs a structured tool invocation:
```json
{
  "jsonrpc": "2.0",
  "method": "message.tool_call",
  "params": {
    "session_id": "c1f8a2",
    "tool_name": "run_command",
    "call_id": "tc_98a1",
    "arguments": {"cmd": "pytest tests/"}
  }
}
```

### 4.3 `tool.permission_request`
Emitted when an execution requires user authorization:
```json
{
  "jsonrpc": "2.0",
  "method": "tool.permission_request",
  "params": {
    "prompt_id": "p_44a2",
    "tool_name": "run_command",
    "arguments": {"cmd": "pytest tests/"},
    "tier": "medium"
  }
}
```
*Client responds by calling `tool.approve` or `tool.deny` with `prompt_id`.*

### 4.4 `session.compacted`
Emitted when context reaches the auto-compaction ratio and was successfully summarized:
```json
{
  "jsonrpc": "2.0",
  "method": "session.compacted",
  "params": {
    "session_id": "c1f8a2",
    "tokens_before": 3400,
    "tokens_after": 1150
  }
}
```

---

## 5. Error Codes

| Code | Constant | Meaning |
|---|---|---|
| `-32700` | `PARSE_ERROR` | Invalid JSON received by the server. |
| `-32600` | `INVALID_REQUEST` | The JSON sent is not a valid JSON-RPC 2.0 object. |
| `-32601` | `METHOD_NOT_FOUND` | The method does not exist / is not available. |
| `-32602` | `INVALID_PARAMS` | Invalid method parameter(s). |
| `-32603` | `INTERNAL_ERROR` | Internal JSON-RPC error. |
| `-32001` | `REQUEST_CANCELLED` | Active request was aborted via `message.cancel`. |
| `-32002` | `UNAUTHORIZED` | TCP auth token was missing or invalid. |
| `-32003` | `SESSION_NOT_FOUND` | Specified `session_id` does not exist in SQLite store. |
| `-32004` | `PERMISSION_DENIED` | Sandbox or security policy blocked the action. |
| `-32005` | `TOOL_ERROR` | Tool execution failure inside sandbox. |
| `-32006` | `BACKPRESSURE_OVERFLOW` | Client socket write buffer exceeded limits. |
