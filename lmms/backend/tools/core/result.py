from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List

@dataclass
class ToolResult:
    """
    Standardized result object returned by all canonical tools.
    """
    success: bool
    tool: str
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)

class ToolError(Exception):
    """
    Base exception for all tool execution failures.
    """
    pass

class ToolPermissionError(ToolError):
    """
    Exception raised when a tool attempts to execute a blocked action.
    """
    pass
