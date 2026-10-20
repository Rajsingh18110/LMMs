# Third-Party Licenses & Dependencies (MCP Subsystem)

This document lists all third-party libraries and runtime dependencies utilized by the **LMMs MCP Subsystem** (`lmms_mcp/` and `lmms/cli/cligui/`), along with their exact versions, project URLs, and software licenses as verified directly from installed package metadata.

---

## 📦 Runtime Dependencies

### 1. `mcp` & `mcp-types`
* **Package**: `mcp` & `mcp-types`
* **Installed Version**: `2.3.0`
* **License**: **MIT License**
* **Project URL**: [https://github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
* **Author / Maintainer**: Model Context Protocol / Anthropic
* **Usage**: Provides official MCP ClientSession, StdioServerParameters, `stdio_client`, and `sse_client` stream protocols.

### 2. `fastmcp` & `fastmcp-slim`
* **Package**: `fastmcp` & `fastmcp-slim`
* **Installed Version**: `4.1.1`
* **License**: **Apache-2.0 License**
* **Project URL**: [https://github.com/PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp)
* **Author / Maintainer**: Prefect Technologies, Inc.
* **Usage**: Exposes LMMs's built-in tools (`read_file`, `write_file`, `run_terminal`, etc.) as a standard FastMCP server over stdio for external MCP clients.

### 3. `rich`
* **Package**: `rich`
* **Installed Version**: `15.0.0`
* **License**: **MIT License**
* **Project URL**: [https://github.com/Textualize/rich](https://github.com/Textualize/rich)
* **Author / Maintainer**: Will McGugan / Textualize
* **Usage**: Renders the terminal dashboard (`cligui`), colored status dots, server tables, tool lists, and summary cards.

### 4. `prompt-toolkit`
* **Package**: `prompt-toolkit`
* **Installed Version**: `3.0.53`
* **License**: **BSD-3-Clause License**
* **Project URL**: [https://github.com/prompt-toolkit/python-prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
* **Author / Maintainer**: Jonathan Slenders
* **Usage**: Interactive prompt autocompletion, session management, and dialog widgets in CLI.

### 5. `pydantic`
* **Package**: `pydantic` & `pydantic-core`
* **Installed Version**: `2.12.x`
* **License**: **MIT License**
* **Project URL**: [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)
* **Usage**: Schema validation and model serialization within FastMCP and MCP SDK.

### 6. `anyio`
* **Package**: `anyio`
* **Installed Version**: `4.12.1`
* **License**: **MIT License**
* **Project URL**: [https://github.com/agronholm/anyio](https://github.com/agronholm/anyio)
* **Usage**: Asynchronous stream abstraction used by MCP transports.

---

## 💡 Architectural & Design References (Zero Code Copied)

### 1. `mcp-cli`
* **Reference**: [https://github.com/chrishayuk/mcp-cli](https://github.com/chrishayuk/mcp-cli)
* **License**: **MIT License**
* **Role**: **Design reference only**.
* **Notice**: Zero lines of code were copied or adapted from `mcp-cli`. Only the high-level convention of CLI subcommands (`add`, `list`, `remove`, `enable`, `disable`, `test`, `tools`, `logs`) was used as a conceptual model. All CLI parsers, configurations, and managers in `lmms_mcp/` were implemented 100% independently from scratch.

### 2. OpenAI Codex CLI (`codex`)
* **Reference**: [https://github.com/openai/codex](https://github.com/openai/codex)
* **License**: **Apache-2.0 License**
* **Role**: **Functional target & architectural benchmark**.
* **Notice**: Zero code was copied. LMMs is an independent, 100% offline Python system that replicates and expands upon Codex's CLI feature set without cloud API lock-in.
