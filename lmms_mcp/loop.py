"""
LMMs MCP Tool-Calling Loop
Converts MCP tools into function-calling schemas for local models, with robust
JSON-in-prompt fallback for models that lack native function-calling.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Any, Tuple, Callable, Awaitable

from lmms_mcp.manager import MCPServerManager


class MCPToolLoop:
    """Orchestrates tool schemas, prompt injection, and response parsing."""

    def __init__(self, manager: MCPServerManager):
        self.manager = manager

    @staticmethod
    def to_openai_tool_definitions(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts raw MCP tool dicts to OpenAI function-calling format."""
        openai_tools = []
        for tool in tools:
            # Prefix with server name to avoid namespace collisions
            server = tool.get("server", "mcp")
            orig_name = tool["name"]
            qualified_name = f"{server}__{orig_name}"

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": qualified_name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                    }),
                },
                "_mcp_server": server,
                "_mcp_orig_name": orig_name,
            })
        return openai_tools

    @staticmethod
    def to_prompt_system_instruction(tools: List[Dict[str, Any]]) -> str:
        """Formats MCP tools into structured system prompt instructions for fallback."""
        if not tools:
            return ""

        lines = [
            "### AVAILABLE TOOLS (Model Context Protocol)",
            "You have access to the following external tools to accomplish user requests:",
            "",
        ]

        for tool in tools:
            server = tool.get("server", "mcp")
            name = tool["name"]
            desc = tool.get("description", "No description provided.")
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            req = schema.get("required", [])

            lines.append(f"Tool: `{server}__{name}`")
            lines.append(f"Description: {desc}")
            if props:
                lines.append(f"Arguments: {json.dumps(props)}")
            if req:
                lines.append(f"Required: {req}")
            lines.append("")

        lines.extend([
            "### TOOL CALLING INSTRUCTIONS:",
            "To invoke a tool, output a single JSON block formatted exactly like this:",
            "```json",
            "{",
            '  "tool": "server__tool_name",',
            '  "arguments": {',
            '    "param1": "value1"',
            "  }",
            "}",
            "```",
            "Do not output anything else when invoking a tool. The system will run the tool and return the result.",
        ])

        return "\n".join(lines)

    @staticmethod
    def extract_tool_call(response_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extracts tool call name and arguments from markdown, XML, or raw JSON."""
        # 1. Look for ```json ... ``` blocks
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_block_match:
            try:
                data = json.loads(json_block_match.group(1))
                if "tool" in data:
                    return data["tool"], data.get("arguments", {})
            except Exception:
                pass

        # 2. Look for <tool_call>...</tool_call> tags
        xml_match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response_text, re.DOTALL)
        if xml_match:
            try:
                data = json.loads(xml_match.group(1))
                if "tool" in data:
                    return data["tool"], data.get("arguments", {})
            except Exception:
                pass

        # 3. Look for naked JSON object containing "tool": ...
        naked_match = re.search(r"\{\s*\"tool\"\s*:\s*\"([^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(\{.*?\})\s*\}", response_text, re.DOTALL)
        if naked_match:
            tool_name = naked_match.group(1)
            try:
                args = json.loads(naked_match.group(2))
                return tool_name, args
            except Exception:
                return tool_name, {}

        return None

    def parse_qualified_tool_name(self, qualified_name: str) -> Tuple[str, str]:
        """Parses 'server__tool' into (server, tool_name)."""
        if "__" in qualified_name:
            server, tool = qualified_name.split("__", 1)
            return server, tool
        return "mcp", qualified_name

    async def execute_extracted_tool_call(
        self,
        qualified_name: str,
        arguments: Dict[str, Any],
        confirm_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[bool]]] = None,
    ) -> str:
        """Executes a tool call after checking permission policy."""
        server_name, tool_name = self.parse_qualified_tool_name(qualified_name)
        server_cfg = self.manager.config.get_server(server_name)

        # Check permissions
        policy = "allow"
        if server_cfg:
            policy = server_cfg.permissions.get(tool_name, "allow")

        if policy == "deny":
            return f"Error: Execution of tool '{qualified_name}' is DENIED by policy."

        if policy == "ask" and confirm_callback:
            allowed = await confirm_callback(server_name, tool_name, arguments)
            if not allowed:
                return f"Execution of tool '{qualified_name}' was cancelled by the user."

        try:
            result = await self.manager.call_tool(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
            )
            
            # Format MCP result content
            if hasattr(result, "content") and result.content:
                parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{qualified_name}': {e}"
