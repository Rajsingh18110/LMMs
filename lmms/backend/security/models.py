from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ToolDefinition:
    name: str
    category: str
    risk_level: str  # safe, low, medium, high, critical
    requires_network: bool = False
    requires_target_authorization: bool = False
    destructive: bool = False
    requires_confirmation: bool = False
    description: str = ""
    # E.g. what arguments map to a "target" that needs validation
    target_args_indices: List[int] = field(default_factory=list)
    target_args_flags: List[str] = field(default_factory=list)

@dataclass
class ToolRequest:
    tool_name: str
    command_line: str
    arguments: List[str]
    kwargs: Dict[str, Any]
    workspace: str
    permission_level: str

@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    risk_level: str = "safe"
    requires_confirmation: bool = False

@dataclass
class ToolResult:
    stdout: str
    stderr: str
    exit_code: int
    was_denied: bool = False
    deny_reason: str = ""
