from typing import Optional, Dict, Any
from lmms.backend.agents.registry import AgentRegistry

class RuleBasedRouter:
    """
    Phase I deterministic router.
    Matches Intent Context to Agent Manifests.
    """
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def route(self, intent_name: str) -> Optional[str]:
        best_agent = None
        best_priority = -1

        for agent in self.registry.list_agents():
            if intent_name in agent.get("supported_intents", []):
                if agent.get("priority", 0) > best_priority:
                    best_priority = agent.get("priority", 0)
                    best_agent = agent["name"]
        
        return best_agent
