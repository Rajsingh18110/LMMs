from enum import Enum

class AgentState(Enum):
    IDLE = "Idle"
    QUEUED = "Queued"
    RUNNING = "Running"
    WAITING = "Waiting"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
