"""
chat_event.py

Structured event model for the LMMs chat pipeline.

Architecture:
    Agent Runtime
         │
    ChatService (parses raw chunks → ChatEvents)
         │
    pyqtSignal[ChatEvent]
         │
    ChatPage (routes events → message state → UI update)

Event types:
    reasoning_delta  — model <think>...</think> content increment
    assistant_delta  — main response text increment
    tool_started     — tool execution began
    tool_finished    — tool execution completed
    task_started     — agent task began
    task_step        — task plan step status update
    task_completed   — agent task finished
    system_log       — internal routing / debug info (UI drops silently)
    completed        — generation pipeline finished successfully
    error            — generation pipeline failed
    no_response      — pipeline finished with zero visible content
"""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ChatEvent:
    type: str               # see module docstring for valid values
    message_id: str         # the assistant ChatMessage this event belongs to

    # Payload fields — populated depending on type
    content: str = ""       # delta text (reasoning_delta / assistant_delta)
    tool_name: str = ""     # tool_started / tool_finished
    tool_args: Dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
    step_index: int = -1    # task_step
    step_title: str = ""    # task_step
    step_status: str = ""   # pending | active | done | failed
    error_msg: str = ""     # error
    metadata: Dict[str, Any] = field(default_factory=dict)
