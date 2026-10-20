"""
LMMs FastMCP Server
Exposes LMMs's built-in tools (files, terminal, kali_knowledge) as a standard MCP server
using FastMCP so external MCP clients or IDEs can interact with LMMs tools.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp_server = FastMCP(
    name="lmms-tools",
)


@mcp_server.tool()
def read_file(path: str) -> str:
    """Read the contents of a file inside the allowed workspace."""
    from lmms.backend.tools.files import canonical_file_read
    res = canonical_file_read(path)
    return res.get("content", "")


@mcp_server.tool()
def write_file(path: str, content: str) -> str:
    """Write or overwrite text content to a file inside the allowed workspace."""
    from lmms.backend.tools.files import canonical_file_write
    res = canonical_file_write(path, content)
    return f"File successfully written to {res.get('path', path)}"


@mcp_server.tool()
def run_terminal(command: str, cwd: str = "") -> str:
    """Execute a shell command safely within the current workspace."""
    from lmms.backend.tools.terminal import canonical_terminal_callback
    target_cwd: Optional[str] = cwd if cwd else None
    res = canonical_terminal_callback(command=command, cwd=target_cwd)
    return res.get("output", "")


@mcp_server.tool()
def search_workspace(pattern: str, root_dir: str = ".") -> List[str]:
    """Search for files matching a pattern inside the workspace."""
    from glob import glob
    matches = glob(os.path.join(root_dir, "**", pattern), recursive=True)
    return matches[:50]


@mcp_server.tool()
def get_system_status() -> Dict[str, Any]:
    """Get LMMs workstation hardware, memory, and runtime engine status."""
    from lmms.engine.hardware import HardwareProfiler
    return HardwareProfiler().profile()


def run_standalone():
    """Runs the FastMCP server over stdio for external MCP consumers."""
    mcp_server.run()


if __name__ == "__main__":
    run_standalone()
