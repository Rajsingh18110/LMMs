import uuid
from typing import Any
from lmms.backend.router.fallback import FallbackManager

class OrchestrationManager:
    """
    The Orchestrator Hub. Controls the flow, ensuring no peer-to-peer agent delegation.
    """
    def __init__(self, backend_manager, db):
        self.backend = backend_manager
        self.db = db
        self.events = backend_manager.events
        self.fallback = FallbackManager(backend_manager)

    def handle_task(self, intent_name: str, task_id: str, context: Any):
        """
        Main orchestration loop.
        """
        run_id = str(uuid.uuid4())
        workspace_id = self.backend.workspace.get_active_workspace()
        
        self.events.publish("OrchestrationStarted", {"run_id": run_id, "task": task_id})
        
        # 1. Routing & Fallback
        graph = self.fallback.route_with_fallback(intent_name, str(context))
        
        # Log to DB
        self.db.execute(
            "INSERT INTO orchestration_runs (id, task_id, route, status) VALUES (?, ?, ?, ?)",
            (run_id, task_id, str(graph.to_dict()), "Running")
        )
        
        # 2. Execution Loop (Hub always regains control)
        for step in graph.steps:
            step_id = str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO orchestration_steps (id, run_id, agent, status) VALUES (?, ?, ?, ?)",
                (step_id, run_id, step.agent_name, "Started")
            )
            
            try:
                # Orchestrator invokes Agent
                # We mock the context payload
                self.backend.agents.execute_agent(
                    intent_name=intent_name, # Usually we'd pass the specific intent/action here
                    workspace_id=workspace_id,
                    task_id=task_id
                )
                
                self.db.execute(
                    "UPDATE orchestration_steps SET status = ?, result = ? WHERE id = ?",
                    ("Finished", "Success", step_id)
                )
            except Exception as e:
                self.db.execute(
                    "UPDATE orchestration_steps SET status = ?, result = ? WHERE id = ?",
                    ("Failed", str(e), step_id)
                )
                self.events.publish("OrchestrationFailed", {"run_id": run_id, "failed_step": step.agent_name})
                self.db.execute("UPDATE orchestration_runs SET status = 'Failed', finished_at = CURRENT_TIMESTAMP WHERE id = ?", (run_id,))
                return
                
        # 3. Finalize
        self.db.execute("UPDATE orchestration_runs SET status = 'Completed', finished_at = CURRENT_TIMESTAMP WHERE id = ?", (run_id,))
        self.events.publish("OrchestrationFinished", {"run_id": run_id})
