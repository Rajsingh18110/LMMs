from lmms.backend.router.execution_graph import ExecutionGraph

class RuleRouter:
    """
    Deterministic basic router. Used primarily as a fallback.
    """
    def route(self, intent_name: str) -> ExecutionGraph:
        graph = ExecutionGraph(intent=intent_name)
        
        if intent_name == "Coding":
            # Simple rule mapping
            graph.add_step(agent_name="ResearchAgent", action_type="GatherContext")
            graph.add_step(agent_name="CodingAgent", action_type="WriteCode", dependencies=["ResearchAgent"])
        elif intent_name == "GitOperation":
            graph.add_step(agent_name="GitAgent", action_type="CommitChanges")
        else:
            graph.add_step(agent_name="ResearchAgent", action_type="GeneralChat")
            
        return graph
