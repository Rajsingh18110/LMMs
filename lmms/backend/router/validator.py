from typing import List
from lmms.backend.router.execution_graph import ExecutionGraph

class RouteValidator:
    def __init__(self, backend_manager):
        self.backend = backend_manager
        
    def validate(self, graph: ExecutionGraph) -> bool:
        """
        Validates the route against capabilities and models.
        """
        if not graph or not graph.steps:
            return False
            
        loaded_agents = self.backend.agents.list_loaded_agents()
        
        for step in graph.steps:
            if step.agent_name not in loaded_agents:
                # E.g. Hallucinated agent name
                return False
                
        return True
