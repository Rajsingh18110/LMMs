from typing import Dict, Optional, List
from lmms.backend.tools.core.definitions import ToolDefinition

class ToolRegistry:
    """
    Central repository for discovering and validating available tools in core tools.
    Bridges seamlessly with the orchestration and security registries.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._aliases: Dict[str, str] = {
            "files.read": "file.read",
            "view_file": "file.read",
            "files.write": "file.write",
            "write_to_file": "file.write",
            "run_command": "terminal.run",
            "bash": "terminal.run",
        }
        
    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        if not name:
            return None
        if name in self._tools:
            return self._tools[name]
        if name in self._aliases and self._aliases[name] in self._tools:
            return self._tools[self._aliases[name]]
        norm_dot = name.replace("_", ".")
        if norm_dot in self._tools:
            return self._tools[norm_dot]
        norm_under = name.replace(".", "_")
        if norm_under in self._tools:
            return self._tools[norm_under]
        return None
        
    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())
