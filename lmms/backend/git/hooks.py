class GitContextProvider:
    """
    Hook for the future Context Builder to pull relevant Git state into agent/LLM context.
    """
    def __init__(self, git_manager):
        self.git = git_manager

    def get_relevant_commits(self, query: str = None):
        pass

    def get_branch_state(self) -> str:
        pass

    def get_recent_changes(self):
        pass
