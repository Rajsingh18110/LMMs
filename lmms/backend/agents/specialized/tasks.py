from lmms.backend.agents.core_agents.agents.base import BaseAgent

class TaskAgent(BaseAgent):
    """Placeholder for specialized task agent."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = "You are an expert Task Agent."

class TaskPlanner(BaseAgent):
    """Placeholder for task planner agent."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = "You are an expert Task Planner."

class TaskExecutor(BaseAgent):
    """Placeholder for task executor agent."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = "You are an expert Task Executor."
