import uuid
from datetime import datetime
from lmms.backend.agents.registry import AgentRegistry
from lmms.backend.agents.router_hooks.rule_based import RuleBasedRouter
from lmms.backend.agents.permissions import PermissionValidator, PermissionError
from lmms.backend.agents.states import AgentState
from lmms.backend.agents.specialized.coding import CodingAgent
from lmms.backend.agents.specialized.research import ResearchAgent

class AgentManager:
    def __init__(self, backend_manager, db):
        self.backend = backend_manager
        self.db = db
        self.events = backend_manager.events
        
        # Initialize Registry
        manifests_path = os.path.expanduser("~/.lmms/manifests")
        if not os.path.exists(manifests_path):
            os.makedirs(manifests_path, exist_ok=True)
        
        self.registry = AgentRegistry(manifests_path)
        
        # Initialize Router
        self.router = RuleBasedRouter(self.registry)
        
        # Initialize Validator
        self.validator = PermissionValidator()
        
        # Map class types
        self.agent_classes = {
            "CodingAgent": CodingAgent,
            "ResearchAgent": ResearchAgent
        }

    def execute_agent(self, intent_name: str, workspace_id: str, task_id: str):
        """
        Full lifecycle orchestrator.
        """
        # 1. Route to agent
        agent_name = self.router.route(intent_name)
        if not agent_name:
            self.events.publish("AgentFailed", {"reason": "No agent found for intent"})
            return
            
        # 2. Instantiate
        manifest = self.registry.get_manifest(agent_name)
        AgentClass = self.agent_classes.get(agent_name)
        if not AgentClass:
            return
            
        agent = AgentClass(manifest)
        
        # 3. State Tracking -> Running
        self.events.publish("AgentStarted", {"agent": agent_name})
        
        # 4. Mock Tool Execution & Validation Loop
        try:
            # Let's say intent requires write_to_file
            tool_to_use = "write_to_file"
            
            # Validation Step
            self.validator.validate(tool_to_use, agent.permissions)
            
            # Action Ledger tracking
            action_id = str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO agent_actions (id, agent_name, workspace_id, task_id, action_type, tool_used, result) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (action_id, agent_name, workspace_id, task_id, "ToolExecution", tool_to_use, "Success")
            )
            
            # Agent Execution
            agent.execute(None)
            
            self.events.publish("AgentFinished", {"agent": agent_name, "state": AgentState.COMPLETED.value})
            
        except PermissionError as e:
            # Action Ledger Failure tracking
            action_id = str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO agent_actions (id, agent_name, workspace_id, task_id, action_type, tool_used, result) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (action_id, agent_name, workspace_id, task_id, "ToolExecution", tool_to_use, f"Failed: {str(e)}")
            )
            
            self.events.publish("AgentFailed", {"agent": agent_name, "reason": str(e), "state": AgentState.FAILED.value})

    def list_loaded_agents(self):
        return [m["name"] for m in self.registry.list_agents()]
