from enum import Enum
from dataclasses import dataclass, field
import datetime

class TaskStatus(Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    BLOCKED     = "blocked"
    FAILED      = "failed"

@dataclass
class Task:
    id:          str
    title:       str
    description: str
    status:      TaskStatus = TaskStatus.PENDING
    parent_id:   str | None = None
    subtasks:    list       = field(default_factory=list)
    assigned_to: str        = ""  # model_id
    tools_used:  list       = field(default_factory=list)
    created_at:  str        = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at:  str        = field(default_factory=lambda: datetime.datetime.now().isoformat())
    result:      str        = ""
