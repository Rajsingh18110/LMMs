class GitMemory:
    """
    Prepares isolated memory spaces per branch and tracks vector embeddings for commits.
    """
    def __init__(self, db_manager):
        self.db = db_manager
