class TaskMemory:
    """Implements Task -> Task Events -> Summarizer -> Task Memory -> Vector Database."""
    def __init__(self, db):
        self.db = db

    def summarize_and_store(self, task_id: str):
        # Fetch events
        events = self.db.fetchall("SELECT event_data FROM task_events WHERE task_id = ?", (task_id,))
        if not events:
            return
        # Mock summarize
        summary = "Summarized task actions: " + " | ".join([e['event_data'] for e in events])
        # Insert to task_memory
        import uuid
        mem_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO task_memory (id, task_id, branch_id, branch_name, memory_summary) VALUES (?, ?, ?, ?, ?)",
                        (mem_id, task_id, "branch_mock", "main", summary))
        return mem_id
