# LMMs Model Context Protocol (MCP) Integration

LMMs natively supports the open **Model Context Protocol (MCP)** specification via the official Python MCP SDK (`mcp`) and `FastMCP`.

---

## 🌟 Highlights & Capabilities
- **100% Offline & Local First**: Run local MCP servers via `stdio` (Python, Node/npx, Go, Rust/uvx) without external cloud dependencies.
- **Lazy Lifecycle Management**: Servers spin up on demand when tools are listed or invoked, reducing background memory overhead.
- **Auto-Restart & Health Tracking**: Tracks server latency, tool lists, and crash recovery automatically.
- **Dual Tool Loop**:
  - **Native Function Calling**: Formats schemas for models supporting structured tool calling.
  - **Prompt Fallback**: Formats JSON schemas into system prompt instructions and parses `<tool_call>` or ````json blocks for local models lacking native function-calling.
- **Terminal GUI Dashboard (`cligui`)**: Rich tables, status indicators (🟢 connected, 🟡 starting, 🔴 error), and live telemetry directly in your terminal.
- **Expose Built-in Tools via FastMCP**: `python -m lmms_mcp.server` exposes LMMs tools (`read_file`, `write_file`, `run_terminal`, etc.) to any external MCP client or IDE.

---

## 🚀 CLI Commands

### 1. View Dashboard & Active Servers
```bash
lmms mcp list
# or simply:
lmms mcp
```

### 2. Add an MCP Server
```bash
# Add a stdio-based server (e.g. Filesystem)
lmms mcp add filesystem "npx" --args -y @modelcontextprotocol/server-filesystem ~/Projects

# Add via curated local template:
lmms mcp add sqlite --template
```

### 3. List Curated Templates
```bash
lmms mcp templates
```
Available templates:
- `filesystem` (Workspace filesystem access)
- `git` (Git repository navigator)
- `github` (GitHub issues & PRs)
- `sqlite` (Local database inspector)
- `postgres` (PostgreSQL connector)
- `brave_search` (Web search)
- `fetch` (HTML to markdown scraper)
- `memory` (Agent knowledge graph)
- `playwright` (Browser automation)

### 4. Test Server Connection
```bash
lmms mcp test filesystem
```

### 5. Inspect Discovered Tools
```bash
# List tools across all active servers:
lmms mcp tools

# List tools from a specific server:
lmms mcp tools filesystem
```

### 6. Enable / Disable / Remove
```bash
lmms mcp disable filesystem
lmms mcp enable filesystem
lmms mcp remove filesystem
```

### 7. View Live Server Logs
```bash
lmms mcp logs filesystem
```

---

## 💬 Chat Slash Commands
Inside an interactive session (`lmms cli` or Terminal Studio):
- `/mcp`: Display MCP servers and tools dashboard.
- `/mcp tools`: List all registered tools.
- `/mcp add <name> ...`: Add a server on the fly.
- `/gui tools`: Launch Desktop Studio focused on the **MCP & Tools** page.

---

## ⚙ Configuration (`~/.lmms/mcp.json`)
The configuration follows standard MCP specification schema:
```json
{
  "mcpServers": {
    "filesystem": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/kali/Projects"],
      "env": {},
      "enabled": true,
      "sandbox": "bwrap",
      "permissions": {
        "read_file": "allow",
        "delete_file": "ask"
      }
    }
  }
}
```
