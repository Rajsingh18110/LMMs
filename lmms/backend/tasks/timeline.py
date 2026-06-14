class TaskTimeline:
    """Integrates Task events into the unified Workspace Timeline."""
    def __init__(self, db, events):
        self.db = db
        self.events = events
        self.events.on("TaskCreated", self.record_event)
        self.events.on("TaskUpdated", self.record_event)
        self.events.on("TaskCompleted", self.record_event)
        self.events.on("TaskBlocked", self.record_event)

    def record_event(self, event):
        import uuid
        task_id = event.data.get("task_id")
        if task_id:
            event_id = str(uuid.uuid4())
            self.db.execute("INSERT INTO task_events (id, task_id, event_type, event_data) VALUES (?, ?, ?, ?)",
                            (event_id, task_id, event.name, str(event.data)))

    def get_timeline(self, task_id: str):
        return self.db.fetchall("SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp ASC", (task_id,))
