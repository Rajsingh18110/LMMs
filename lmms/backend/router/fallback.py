from lmms.backend.router.llm_router import LLMRouter
from lmms.backend.router.rule_router import RuleRouter
from lmms.backend.router.validator import RouteValidator
from lmms.backend.router.execution_graph import ExecutionGraph

class FallbackManager:
    """
    Manages strict fallback logic: LLMRouter -> Validator -> Fallback -> RuleRouter.
    No endless retry loops.
    """
    def __init__(self, backend_manager):
        self.backend = backend_manager
        self.events = backend_manager.events
        self.llm_router = LLMRouter()
        self.rule_router = RuleRouter()
        self.validator = RouteValidator(backend_manager)

    def route_with_fallback(self, intent_name: str, context: str) -> ExecutionGraph:
        # 1. Try LLM Router
        self.events.publish("RouteCreated", {"source": "LLMRouter", "intent": intent_name})
        graph = self.llm_router.route(intent_name, context)
        
        # 2. Validation
        if self.validator.validate(graph):
            self.events.publish("RouteValidated", {"source": "LLMRouter"})
            return graph
            
        # 3. Fallback Triggered
        self.events.publish("RouteRejected", {"reason": "Validation Failed or Empty Graph"})
        self.events.publish("FallbackTriggered", {"fallback_to": "RuleRouter"})
        
        # 4. Use deterministic fallback
        return self.rule_router.route(intent_name)
