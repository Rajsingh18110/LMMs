import os
from typing import Dict, Any, List, Optional, AsyncGenerator

from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.agents.core_agents.agents.history import ActionHistory

class AgentManager:
    """
    Orchestrates the specialized agent execution loops.
    Evaluates contexts to select the most appropriate agent and tracks actions in the ActionHistory ledger.
    """
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.action_history = ActionHistory(workspace_dir)
        self.agents: List[BaseAgent] = []
        
        # We auto-register the default specialized agents
        self._register_default_agents()

    def _register_default_agents(self):
        try:
            from lmms.backend.agents.core_agents.agents.specialized.coding import CodingAgent
            from lmms.backend.agents.core_agents.agents.specialized.vision import VisionAgent
            from lmms.backend.agents.core_agents.agents.specialized.orchestrator import OrchestratorAgent
            from lmms.backend.agents.core_agents.agents.specialized.tester import TesterAgent
            from lmms.backend.agents.core_agents.agents.specialized.reviewer import ReviewerAgent
            
            self.register_agent(CodingAgent())
            self.register_agent(VisionAgent())
            self.register_agent(OrchestratorAgent())
            self.register_agent(TesterAgent())
            self.register_agent(ReviewerAgent())
        except ImportError as e:
            print(f"Failed to load default agents: {e}")

    def register_agent(self, agent: BaseAgent):
        """Register a new specialized agent into the framework."""
        self.agents.append(agent)

    def route_context(self, context: ExecutionContext) -> Optional[BaseAgent]:
        """
        Evaluate the context against all registered agents to find the best match.
        If no agent scores above 0.3, returns None.
        """
        best_agent = None
        highest_score = 0.0
        
        for agent in self.agents:
            score = agent.evaluate(context)
            if score > highest_score:
                highest_score = score
                best_agent = agent
                
        if highest_score > 0.3:
            return best_agent
        return None

    async def execute_task(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        """
        Main entrypoint for task execution. 
        Routes to the correct agent, retrieves plan, and executes it.
        """
        agent = self.route_context(context)
        
        if not agent:
            yield "No suitable specialized agent found for this task. Falling back to general chat.\n"
            return
            
        yield f"Routing task to {agent.name} (Confidence matched based on context)\n"
        
        # Generate Plan
        plan = agent.plan(context)
        yield f"[{agent.name} Plan]: {plan.get('strategy', 'Proceeding with default strategy')}\n"
        
        # Execute the specialized logic
        try:
            async for chunk in agent.execute(context):
                yield chunk
        except Exception as e:
            yield f"\n[Error during execution by {agent.name}]: {str(e)}\n"
            self.action_history.record_command_executed(agent.name, "execute", exit_code=1)
            raise e
            
        # Example of tracking the completion action
        task_desc = context.task.description if context.task else "Context task"
        self.action_history._record_action(agent.name, "TASK_COMPLETED", {"task": task_desc})
        
        yield f"\n{agent.name} finished execution."

if __name__ == "__main__":
    # Simple verification script
    import asyncio
    
    async def run_test():
        print("Testing Agent Framework...")
        manager = AgentManager(workspace_dir="/tmp/lmms_test_workspace")
        
        # Mock Context targeting CodingAgent
        context = ExecutionContext(
            memory=[{"role": "user", "content": "Can you write a python script to sort this array?"}],
            files=["utils.py"]
        )
        
        print("\nSubmitting context to AgentManager:")
        async for chunk in manager.execute_task(context):
            print(chunk, end="", flush=True)
            
        print("\n\nAction History ledger entries:")
        for action in manager.action_history.get_recent_actions(5):
            print(f"- {action['timestamp']} | {action['agent']} | {action['type']} | {action['details']}")
            
    asyncio.run(run_test())
