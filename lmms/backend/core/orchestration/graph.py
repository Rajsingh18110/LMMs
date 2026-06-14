from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from lmms.backend.agents.core_agents.context import ExecutionContext

@dataclass
class GraphNode:
    """
    A single node in the execution graph, representing a distinct sub-task
    to be executed by a specific capability or agent.
    """
    id: str
    description: str
    context: ExecutionContext
    dependencies: List[str] = field(default_factory=list)
    output: Optional[str] = None
    status: str = "pending" # pending, in_progress, completed, failed

class ExecutionGraph:
    """
    A directed acyclic graph (DAG) representing a multi-step orchestration plan.
    """
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}
        
    def add_node(self, node: GraphNode):
        self.nodes[node.id] = node
        
    def get_ready_nodes(self) -> List[GraphNode]:
        """Returns all nodes that have their dependencies completed and are still pending."""
        ready = []
        for node in self.nodes.values():
            if node.status == "pending":
                deps_completed = all(
                    self.nodes[dep].status == "completed" 
                    for dep in node.dependencies if dep in self.nodes
                )
                if deps_completed:
                    ready.append(node)
        return ready

    def mark_completed(self, node_id: str, output: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "completed"
            self.nodes[node_id].output = output
            
            # Pass this output as memory/context to dependent nodes
            for node in self.nodes.values():
                if node_id in node.dependencies:
                    node.context.memory.append({
                        "role": "user",
                        "content": f"[Output from {node_id}]:\n{output}"
                    })

    def mark_failed(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "failed"
            
    def is_complete(self) -> bool:
        return all(n.status == "completed" for n in self.nodes.values())
