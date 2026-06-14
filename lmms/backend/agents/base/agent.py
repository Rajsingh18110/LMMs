from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAgent(ABC):
    """
    Abstract Base Class enforcing the Agent interface.
    """
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.name = manifest.get("name", "UnknownAgent")
        self.capabilities = manifest.get("capabilities", [])
        self.permissions = manifest.get("permissions", [])
        self.required_tools = manifest.get("required_tools", [])
        self.supported_intents = manifest.get("supported_intents", [])
        self.priority = manifest.get("priority", 0)

    @abstractmethod
    def execute(self, context: Any) -> Any:
        """Runs the main execution loop for the agent."""
        pass

    @abstractmethod
    def validate(self, context: Any) -> bool:
        """Validates if the agent can run given the context and tools."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Performs cleanup after agent completion or failure."""
        pass
