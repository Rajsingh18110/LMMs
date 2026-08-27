from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable
from lmms.backend.agents.permissions import Permission

@dataclass
class ToolDefinition:
    """
    Metadata definition for a tool registered in the canonical runtime.
    """
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    permissions: List[Permission] = field(default_factory=list)
    risk_level: str = "low" # low, medium, high
    requires_network: bool = False
    requires_confirmation: bool = False
    timeout: int = 30
    
    # Optional reference to the underlying execution callback
    callback: Callable = None
