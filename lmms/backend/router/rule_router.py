from lmms.backend.router.execution_graph import ExecutionGraph
from lmms.backend.orchestration.router import IntentRouter, IntentType

class RuleRouter:
    """
    Deterministic rule-based execution graph router.
    Powered by the unified IntentRouter engine to route coding, file ops,
    and debugging accurately to CodingAgent and OrchestratorAgent.
    """
    def __init__(self):
        self.intent_router = IntentRouter()

    def route(self, intent_name: str) -> ExecutionGraph:
        graph = ExecutionGraph(intent=intent_name)
        
        # Check if intent_name is a raw prompt or a formal intent keyword
        detected_intent = None
        try:
            res = self.intent_router.route(intent_name)
            detected_intent = res.intent
        except Exception:
            pass

        norm = (intent_name or "").strip().lower()
        
        if detected_intent == IntentType.CODING or norm in ("coding", "code", "fix", "debug", "refactor"):
            graph.add_step(agent_name="OrchestratorAgent", action_type="PlanTask")
            graph.add_step(agent_name="CodingAgent", action_type="WriteCode", dependencies=["OrchestratorAgent"])
            graph.add_step(agent_name="TesterAgent", action_type="VerifyCode", dependencies=["CodingAgent"])
        elif detected_intent == IntentType.WORKSPACE_FILE_OPS or norm in ("file_ops", "files", "workspace"):
            graph.add_step(agent_name="CodingAgent", action_type="FileOps")
        elif detected_intent == IntentType.TERMINAL or norm in ("terminal", "bash", "command"):
            graph.add_step(agent_name="CodingAgent", action_type="TerminalRun")
        elif detected_intent in (IntentType.WEB_SEARCH, IntentType.TOOL_RESEARCH) or norm in ("search", "research"):
            graph.add_step(agent_name="ResearchAgent", action_type="DeepResearch")
        elif norm in ("gitoperation", "git"):
            graph.add_step(agent_name="GitAgent", action_type="CommitChanges")
        else:
            graph.add_step(agent_name="ChatAgent", action_type="GeneralChat")
            
        return graph
