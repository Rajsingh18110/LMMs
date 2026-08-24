from typing import Dict, Optional, List
from lmms.backend.tools.core.definitions import ToolDefinition

class ToolRegistry:
    """
    Central repository for discovering and validating available tools.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        
    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool {definition.name} is already registered.")
        self._tools[definition.name] = definition
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)
        
    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())
