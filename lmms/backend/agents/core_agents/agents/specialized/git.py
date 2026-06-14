from lmms.backend.agents.core_agents.base import BaseAgent

class GitAgent(BaseAgent):
    """
    Specialized agent for Git operations.
    Capabilities: Commit Analysis, Branch Analysis, Diff Summaries, Merge Suggestions, Conflict Detection.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = "You are an expert Git operations agent."
