import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class ChatMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # user, assistant, system
    model_name: str = ""
    content: str = ""
    status: str = "pending"  # pending, generating, done, error, cancelled
    thought: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    tool_events: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    # UI specific state
    thought_expanded: bool = False
    
    def append_content(self, text: str):
        self.content += text

    def set_status(self, new_status: str):
        self.status = new_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "model_name": self.model_name,
            "content": self.content,
            "status": self.status,
            "thought": self.thought,
            "thought_expanded": self.thought_expanded,
            "metrics": self.metrics,
            "tool_events": self.tool_events,
            "attachments": self.attachments,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        created_at_str = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "user"),
            model_name=data.get("model_name", ""),
            content=data.get("content", ""),
            status=data.get("status", "done"),
            thought=data.get("thought", ""),
            metrics=data.get("metrics", {}),
            tool_events=data.get("tool_events", []),
            attachments=data.get("attachments", []),
            created_at=created_at,
            thought_expanded=data.get("thought_expanded", False)
        )
