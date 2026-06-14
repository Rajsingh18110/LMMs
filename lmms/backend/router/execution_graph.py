from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ExecutionStep:
    agent_name: str
    action_type: str
    dependencies: List[str] = field(default_factory=list)

@dataclass
class ExecutionGraph:
    """
    A Directed Acyclic Graph (DAG) of the orchestration plan.
    Instead of single-agent routing, we route to a plan.
    """
    intent: str
    steps: List[ExecutionStep] = field(default_factory=list)

    def add_step(self, agent_name: str, action_type: str, dependencies: List[str] = None):
        step = ExecutionStep(
            agent_name=agent_name,
            action_type=action_type,
            dependencies=dependencies or []
        )
        self.steps.append(step)

    def to_dict(self):
        return {
            "intent": self.intent,
            "steps": [{"agent": s.agent_name, "action": s.action_type, "dependencies": s.dependencies} for s in self.steps]
        }
