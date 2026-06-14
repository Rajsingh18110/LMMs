from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

from lmms.backend.agents.core_agents.context import ExecutionContext

class BaseAgent(ABC):
    """
    Abstract base class for all specialized AI Agents in the LMMs OS.
    """
    
    def __init__(self, name: str, description: str, capabilities: list[str]):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        
    @abstractmethod
    def evaluate(self, context: ExecutionContext) -> float:
        """
        Evaluate how well this agent is suited to handle the current context/task.
        Returns a confidence score between 0.0 and 1.0.
        """
        pass
        
    @abstractmethod
    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Create an execution plan based on the task and context.
        Returns a structured plan (can be a dict containing steps, reasoning, etc).
        """
        pass

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        """
        Execute the task based on the context and the plan.
        Yields status updates or final text response asynchronously.
        """
        pass
        
    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"
