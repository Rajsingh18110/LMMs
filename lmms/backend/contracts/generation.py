from typing import List, Dict, Any, Optional, Union, Literal
from dataclasses import dataclass, field

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str # JSON string

@dataclass
class Message:
    role: str # "user", "assistant", "system", "tool"
    content: Union[str, List[Dict[str, Any]]] = ""
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None # If role is "tool"

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    total_tokens: int = 0
    cost: Optional[float] = None

@dataclass
class GenerationRequest:
    model_id: str
    messages: List[Message]
    modality: str = "text"
    execution_mode: Literal["FAST", "BALANCED", "DEEP"] = "BALANCED"
    tools: Optional[List[Dict[str, Any]]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None

@dataclass
class GenerationEvent:
    type: Literal[
        "generation_started",
        "thinking_delta",
        "content_delta",
        "tool_call_started",
        "tool_call_delta",
        "tool_call_finished",
        "usage_update",
        "generation_completed",
        "generation_failed",
        "generation_cancelled"
    ]
    content: str = ""
    reasoning: str = ""
    tool_call: Optional[ToolCall] = None
    usage: Optional[Usage] = None
    error: Optional[str] = None
