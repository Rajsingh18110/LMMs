from typing import Dict, Any, Optional

class ExecutionContext:
    """
    Carries global state through the entire LMMs execution lifecycle.
    Passed to API handlers, CLI runners, Agents, and Router.
    """
    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id
        self.task_id: Optional[str] = None
        self.memory_session: Optional[str] = None
        self.active_files: list[str] = []
        self.enabled_tools: list[str] = []
        self.connected_models: list[str] = []
        self.git_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "task_id": self.task_id,
            "memory_session": self.memory_session,
            "active_files": self.active_files,
            "enabled_tools": self.enabled_tools,
            "connected_models": self.connected_models,
            "git_state": self.git_state,
            "metadata": self.metadata
        }
