from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from lmms.backend.tasks.core_tasks.tasks.task import Task
from lmms.backend.tools.core_tools.base import ToolDefinition

@dataclass
class ExecutionContext:
    """
    The universal payload shared by GUI, CLI, API, Agents, and Router.
    It contains all necessary state and capabilities for an agent to execute its task.
    """
    workspace_id: Optional[str] = None
    task: Optional[Task] = None
    
    # Conversation or task memory context
    memory: List[Dict[str, str]] = field(default_factory=list)
    
    # The active/relevant files for this context
    files: List[str] = field(default_factory=list)
    
    # Relevant tool definitions that the agent has access to
    tools: List[ToolDefinition] = field(default_factory=list)
    
    # State of the git repository (e.g. current branch, uncommitted changes)
    git_state: Dict[str, Any] = field(default_factory=dict)
    
    # Currently loaded or available models to the agent
    models: List[str] = field(default_factory=list)
    
    # Active runtime profile settings
    profile: Dict[str, Any] = field(default_factory=dict)
