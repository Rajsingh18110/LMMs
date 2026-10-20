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
- **Mandatory Authentication:** Requires `--auth-token <token>` or generates a cryptographically random 32-byte hexadecimal token.
- **Timing-Attack Resilient:** Validated using `hmac.compare_digest` before any method is processed.
- **Privacy:** The auth token is strictly confidential and is never logged in server logs or error payloads.
- Clients must include `"auth_token": "<token>"` in the request `params`.

---

## 2. Framing & Message Format

All messages are JSON-RPC 2.0 objects formatted as single-line JSON terminated by a newline (`\n`).

### 2.1 Message Size Limit & Framing Rules
- **Framing:** Strict single-line JSON followed by ASCII newline (`\n`). Clients must not break a JSON object across multiple lines.
- **Max Message Size:** Default limit is **4 MB (4,194,304 bytes)** per line.
- **Oversized Message Handling:** If an incoming message exceeds 4 MB before the newline delimiter, the server immediately drops the payload and emits a standard JSON-RPC parse error:
  ```json
  {"jsonrpc": "2.0", "id": null, "error": {"code": -32700, "message": "Message exceeds maximum allowed size (4194304 bytes)"}}
  ```
  The connection is closed to protect host memory.

### 2.2 Request Format
```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"client_name": "vscode-lmms", "client_version": "1.0.0"}}
```

### 2.3 Response Format
```json
{"jsonrpc": "2.0", "id": 1, "result": {"server_name": "lmms-app-server", "server_version": "1.0.0"}}
```

### 2.4 Error Format
```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
```

### 2.5 Notification Format (Server to Client)
Notifications do not contain an `id` field and represent real-time asynchronous events:
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
| `message.send` | `session_id?: str, content: str, stream?: bool, permission_tier?: str` | Assistant response message object | Serialized per session. Dispatches prompt to model/engine. Streams tokens and tool calls. |
| `message.cancel` | `request_id: str \| int` | `{"cancelled": bool}` | Aborts an active ongoing message generation. |
| `tool.approve` | `prompt_id: str` | `{"approved": true}` | Approves a pending tool permission request. |
| `tool.deny` | `prompt_id: str, reason?: str` | `{"denied": true}` | Rejects a pending tool permission request. |
| `mcp.list` | none | Array of MCP tools | Enumerates tools exposed by active MCP servers. |
| `mcp.call` | `server_name: str, tool_name: str, arguments: object` | MCP tool result object | Invokes tool with path validation and ExecPolicy sandboxing; records audit trail. |
| `mcp.add` | `name: str, command?: str, url?: str, transport?: str, args?: list, env?: dict, sandbox?: str, enabled?: bool` | Configured server object | Adds or updates an MCP server configuration. |
| `mcp.remove` | `name: str` | `{"success": true, "name": str}` | Stops and removes an MCP server configuration. |
| `mcp.update` | `name: str, ...updates...` | Updated server object | Modifies attributes of an existing MCP server. |
| `mcp.enable` | `name: str` | `{"name": str, "enabled": true}` | Enables a configured MCP server. |
| `mcp.disable` | `name: str` | `{"name": str, "enabled": false}` | Disables and stops an MCP server. |
| `mcp.restart` | `name: str` | `{"name": str, "status": str}` | Restarts an active MCP server session. |
| `mcp.test` | `name: str` | `{"connected": bool, "tools": list}` | Tests connection and tool discovery for an MCP server. |
| `mcp.tools` | `server?: str` | Array of tool descriptors | Returns discovered tools, optionally filtered by server name. |
| `mcp.logs` | `name: str, limit?: int` | Array of log strings | Returns timestamped logs for a given server. |
| `mcp.templates` | none | Dictionary of template presets | Returns template gallery (Filesystem, Git, GitHub, SQLite, etc.). |
| `permissions.get` | `server?: str` | Object mapping tool names to policy | Returns permission policies ('allow', 'ask', 'deny'). |
| `permissions.set` | `server: str, tool: str, policy: str` | `{"server": str, "tool": str, "policy": str}` | Updates permission policy ('allow', 'ask', 'deny'). |
| `sandbox.status` | none | Sandbox backends status | Reports bubblewrap, Landlock ABI, and network status. |
| `sandbox.policy.get` | none | ExecPolicy rules object | Returns denied patterns, auto-allowed commands, and restricted paths. |
| `sandbox.policy.set` | `denied_patterns?: list, ...` | Updated ExecPolicy object | Updates ExecPolicy security rules. |
| `worktree.status` | `repo_path?: str` | Worktree status object | Validates workspace path; returns active branch and worktree state. |
| `worktree.diff` | `repo_path?: str` | `{"diff": str}` | Validates workspace path; returns git diff of worktree modifications. |
| `worktree.apply` | `repo_path?: str` | `{"applied": bool}` | Validates workspace path; merges worktree edits back to base repository. |
| `worktree.discard` | `repo_path?: str` | `{"discarded": bool}` | Validates workspace path; discards isolated worktree and cleans directory. |
| `compact` | `session_id: str, restore?: bool` | Compaction summary or restore status | Executes context compaction or rolls back to pre-compact snapshot. |

---

## 4. Server Notifications (Streaming Events)

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
    "tool_name": "run_terminal",
    "call_id": "tc_01",
    "arguments": {"command": "git status"}
  }
}
```

### 4.3 `tool.permission_request`
Emitted when model requests to invoke a tool requiring user confirmation:
```json
{
  "jsonrpc": "2.0",
  "method": "tool.permission_request",
  "params": {
    "prompt_id": "pr_88",
    "tool_name": "delete_directory",
    "arguments": {"path": "./temp"},
    "tier": "medium"
  }
}
```

### 4.4 `mcp.status_changed`
Emitted when an MCP server starts, connects, encounters an error, or changes configuration:
```json
{
  "jsonrpc": "2.0",
  "method": "mcp.status_changed",
  "params": {
    "server": "github",
    "status": "connected"
  }
}
```

### 4.5 `mcp.tool_call`
Emitted when an MCP tool invocation executes:
```json
{
  "jsonrpc": "2.0",
  "method": "mcp.tool_call",
  "params": {
    "server": "sqlite",
    "tool": "read_query",
    "arguments": {"query": "SELECT * FROM users"},
    "duration_ms": 14.2,
    "status": "success",
    "result_summary": "Returned 3 rows"
  }
}
```

---

## 5. Audit Trail & Cryptographic Verification

All MCP tool invocations are logged into `~/.lmms/audit.jsonl` (mode `0600`):
- **Secret Redaction:** High-entropy API tokens, passwords, and authorization headers are scrubbed before writing.
- **Hash Chaining:** Each record includes `prev_hash` and `hash = SHA256(prev_hash : canonical_entry_json)`.
- **Integrity Commands:**
  - View audit records: `lmms audit view [--limit N] [--server S] [--json]`
  - Verify chain: `lmms audit verify`
