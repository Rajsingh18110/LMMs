from typing import Dict, Any, AsyncGenerator
import json
from lmms.backend.agents.core_agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class CodingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CodingAgent",
            description="Specialized in software development, debugging, and codebase modifications.",
            capabilities=["text", "coding", "tool_use"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and "code" in context.task.description.lower():
            score += 0.5
        if context.files and any(f.endswith(('.py', '.js', '.ts', '.cpp', '.html')) for f in context.files):
            score += 0.3
        
        # Check intent from memory if available
        if context.memory:
            last_msg = context.memory[-1].get("content", "").lower()
            code_keywords = ["write", "function", "bug", "error", "refactor", "implement"]
            if any(k in last_msg for k in code_keywords):
                score += 0.4
                
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        # In a real system, the model generates this plan using the Context Builder
        return {
            "strategy": "Analyze existing files, apply modifications via AST/Diff tools, and run verification.",
            "steps": ["Read files", "Plan edits", "Apply edits"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        yield "Starting CodingAgent execution...\n"
        yield "Analyzing context...\n"
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.5)
        
        if context.files:
            yield f"Evaluating files: {', '.join(context.files)}\n"
            
        yield "Drafting code modifications...\n"
        await asyncio.sleep(0.5)
        
        yield "Execution completed successfully."
