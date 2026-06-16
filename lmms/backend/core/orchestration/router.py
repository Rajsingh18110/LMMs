from typing import Optional, List, Dict, Any, AsyncGenerator

from lmms.backend.core.orchestration.graph import ExecutionGraph, GraphNode
from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.agents.core_agents.agents.manager import AgentManager
from lmms.backend.tasks.core_tasks.task import Task

class Router:
    """
    The master orchestration node. Evaluates complex intents and decomposes them 
    into an ExecutionGraph of sub-tasks.
    """
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager

    def decompose_intent(self, intent: str, context: ExecutionContext) -> ExecutionGraph:
        """
        In a real system, an LLM would take the intent and generate a JSON DAG.
        Here we use heuristic logic to decompose common multi-modal tasks.
        """
        graph = ExecutionGraph(name=f"Graph for: {intent[:20]}...")
        
        # Heuristic: If we have images in context AND code keywords in intent,
        # it's a Vision -> Coding sequence.
        has_images = any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in context.files)
        needs_code = any(k in intent.lower() for k in ['code', 'react', 'html', 'python', 'script'])
        
        if has_images and needs_code:
            # Node 1: Vision extraction
            v_ctx = ExecutionContext(
                workspace_id=context.workspace_id,
                task=Task(id="sub-1", title="Vision Extraction", description="Extract UI elements and layout from image"),
                memory=[{"role": "user", "content": "Analyze this layout for code generation."}],
                files=context.files
            )
            v_node = GraphNode(id="vision_node", description="Vision extraction", context=v_ctx)
            
            # Node 2: Code generation
            c_ctx = ExecutionContext(
                workspace_id=context.workspace_id,
                task=Task(id="sub-2", title="Code Generation", description=intent),
                memory=[{"role": "user", "content": f"Generate code based on vision analysis: {intent}"}]
            )
            c_node = GraphNode(id="coding_node", description="Code generation", context=c_ctx, dependencies=["vision_node"])
            
            graph.add_node(v_node)
            graph.add_node(c_node)
            
        else:
            # Fallback: Single node execution graph
            node = GraphNode(
                id="main_node",
                description="Standard Execution",
                context=context
            )
            graph.add_node(node)
            
        return graph

    async def execute_graph(self, graph: ExecutionGraph) -> AsyncGenerator[str, None]:
        """
        Topological execution of the ExecutionGraph using the AgentManager.
        """
        yield f"Starting Orchestration Graph: {graph.name}\n"
        
        while not graph.is_complete():
            ready_nodes = graph.get_ready_nodes()
            if not ready_nodes:
                yield "Deadlock detected in execution graph or graph failed.\n"
                break
                
            for node in ready_nodes:
                yield f"\n--- Executing Node: {node.id} ({node.description}) ---\n"
                node.status = "in_progress"
                
                output = ""
                try:
                    async for chunk in self.agent_manager.execute_task(node.context):
                        yield chunk
                        output += chunk
                        
                    graph.mark_completed(node.id, output)
                except Exception as e:
                    yield f"Node {node.id} failed: {e}\n"
                    graph.mark_failed(node.id)
                    break
        
        yield "\nOrchestration Graph Execution Complete.\n"
