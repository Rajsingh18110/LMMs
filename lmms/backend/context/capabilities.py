from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class IntentContext:
    name: str
    confidence: float
    required_capabilities: List[str]
    required_tools: List[str]

@dataclass
class TokenBudget:
    max_tokens: int = 4096
    system_tokens: int = 500
    workspace_tokens: int = 1000
    task_tokens: int = 500
    git_tokens: int = 500
    memory_tokens: int = 500
    file_tokens: int = 1000
    tool_tokens: int = 500

@dataclass
class ExecutionContext:
    request_id: str
    timestamp: str
    raw_prompt: str
    intent: Optional[IntentContext] = None
    
    # Retrieved Payload
    workspace_data: Dict[str, Any] = field(default_factory=dict)
    task_data: Dict[str, Any] = field(default_factory=dict)
    git_data: Dict[str, Any] = field(default_factory=dict)
    memory_data: List[Dict[str, Any]] = field(default_factory=list)
    file_data: List[Dict[str, Any]] = field(default_factory=list)
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Discovered Tools
    tools: List[Dict[str, Any]] = field(default_factory=list)
    
    # State
    runtime_profile: str = "default_4k"
    token_budget: Optional[TokenBudget] = None
    
    # Final package
    assembled_prompt: str = ""
