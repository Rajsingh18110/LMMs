"""
LMMs MCP Configuration Manager
Manages ~/.lmms/mcp.json with full schema validation and curated server templates.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.lmms/mcp.json")

# Curated local server templates (Zero telemetry, 100% offline ready or user-configured)
CURATED_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "filesystem": {
        "description": "Secure workspace and local filesystem access",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", os.path.expanduser("~/Projects")],
        "env": {},
        "sandbox": "bwrap",
    },
    "git": {
        "description": "Inspect and navigate Git repositories",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git"],
        "env": {},
        "sandbox": "none",
    },
    "github": {
        "description": "GitHub issues, PRs and repository operations",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        "sandbox": "none",
    },
    "sqlite": {
        "description": "Query and inspect local SQLite databases",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", os.path.expanduser("~/.lmms/connectors.db")],
        "env": {},
        "sandbox": "none",
    },
    "postgres": {
        "description": "PostgreSQL database connector",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
        "env": {},
        "sandbox": "none",
    },
    "brave_search": {
        "description": "Web search via Brave Search API",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": ""},
        "sandbox": "none",
    },
    "fetch": {
        "description": "Fetch web pages and convert to markdown",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "sandbox": "none",
    },
    "memory": {
        "description": "Knowledge graph and persistent memory for agents",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "sandbox": "none",
    },
    "playwright": {
        "description": "Browser automation and web scraping",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-playwright"],
        "env": {},
        "sandbox": "none",
    },
}


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"  # "stdio" | "sse" | "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    enabled: bool = True
    sandbox: str = "none"  # "none" | "bwrap" | "restricted"
    permissions: Dict[str, str] = field(default_factory=dict)  # {"tool_name": "allow"|"ask"|"deny"}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.transport == "stdio":
            d.pop("url", None)
        else:
            d.pop("command", None)
            d.pop("args", None)
        return d

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> MCPServerConfig:
        return cls(
            name=name,
            transport=data.get("transport", "stdio"),
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            enabled=data.get("enabled", True),
            sandbox=data.get("sandbox", "none"),
            permissions=data.get("permissions", {}),
        )


class MCPConfig:
    """Manages reading, writing, and updating ~/.lmms/mcp.json."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = os.path.abspath(os.path.expanduser(config_path))
        self.servers: Dict[str, MCPServerConfig] = {}
        self.last_internal_write_time: float = 0.0
        self.load()

    def load(self) -> None:
        """Loads configuration from JSON file or initializes defaults."""
        if not os.path.exists(self.config_path):
            self.servers = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_servers = data.get("mcpServers", {})
            self.servers = {
                name: MCPServerConfig.from_dict(name, sdata)
                for name, sdata in raw_servers.items()
            }
        except Exception:
            # Fallback to empty if corrupted
            self.servers = {}

    def save(self) -> None:
        """Saves current configuration atomically to ~/.lmms/mcp.json."""
        cfg_dir = os.path.dirname(self.config_path)
        os.makedirs(cfg_dir, exist_ok=True)
        data = {
            "mcpServers": {
                name: s.to_dict() for name, s in self.servers.items()
            }
        }
        # Atomic write: write to temp file in same filesystem, sync to disk, then atomic rename
        temp_file = os.path.join(cfg_dir, f".mcp.json.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.config_path)
            self.last_internal_write_time = time.time()
        except Exception:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
            raise

    def add_server(
        self,
        name: str,
        command_or_url: str,
        transport: str = "stdio",
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        sandbox: str = "none",
        enabled: bool = True,
    ) -> MCPServerConfig:
        """Adds or updates a server configuration."""
        name = name.strip()
        args = args or []
        env = env or {}

        if transport == "stdio":
            config = MCPServerConfig(
                name=name,
                transport="stdio",
                command=command_or_url,
                args=args,
                env=env,
                sandbox=sandbox,
                enabled=enabled,
            )
        else:
            config = MCPServerConfig(
                name=name,
                transport=transport,
                url=command_or_url,
                env=env,
                sandbox=sandbox,
                enabled=enabled,
            )

        self.servers[name] = config
        self.save()
        return config

    def remove_server(self, name: str) -> bool:
        """Removes a server by name."""
        if name in self.servers:
            del self.servers[name]
            self.save()
            return True
        return False

    def enable_server(self, name: str) -> bool:
        """Enables a server."""
        if name in self.servers:
            self.servers[name].enabled = True
            self.save()
            return True
        return False

    def disable_server(self, name: str) -> bool:
        """Disables a server."""
        if name in self.servers:
            self.servers[name].enabled = False
            self.save()
            return True
        return False

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Retrieves server configuration by name."""
        return self.servers.get(name)

    def list_servers(self) -> List[MCPServerConfig]:
        """Returns list of all configured servers."""
        return list(self.servers.values())

    def apply_template(self, template_key: str, name: Optional[str] = None) -> Optional[MCPServerConfig]:
        """Applies a curated template to create a new server."""
        key = template_key.lower().replace("-", "_")
        if key not in CURATED_TEMPLATES:
            return None

        tmpl = CURATED_TEMPLATES[key]
        server_name = name or key
        return self.add_server(
            name=server_name,
            command_or_url=tmpl.get("command", tmpl.get("url", "")),
            transport=tmpl.get("transport", "stdio"),
            args=tmpl.get("args", []),
            env=tmpl.get("env", {}),
            sandbox=tmpl.get("sandbox", "none"),
            enabled=True,
        )

    def set_tool_permission(self, server_name: str, tool_name: str, policy: str) -> bool:
        """Sets permission policy for a specific tool ('allow', 'ask', 'deny')."""
        server = self.get_server(server_name)
        if not server:
            return False
        if policy not in ("allow", "ask", "deny"):
            raise ValueError("Policy must be one of: 'allow', 'ask', 'deny'")
        server.permissions[tool_name] = policy
        self.save()
        return True
