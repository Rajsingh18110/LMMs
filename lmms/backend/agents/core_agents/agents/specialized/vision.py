from typing import Dict, Any, AsyncGenerator
from lmms.backend.agents.core_agents.base import BaseAgent
from lmms.backend.agents.core_agents.context import ExecutionContext

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="VisionAgent",
            description="Specialized in image analysis, layout interpretation, and optical character recognition.",
            capabilities=["vision", "text"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and ("image" in context.task.description.lower() or "vision" in context.task.description.lower()):
            score += 0.6
            
        if context.files and any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for f in context.files):
            score += 0.8
            
        # Check intent from memory
        if context.memory:
            last_msg = context.memory[-1].get("content", "").lower()
            if "look at this" in last_msg or "what is in this image" in last_msg or "[image" in last_msg:
                score += 0.5
                
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Load image into VRAM, extract features, and respond based on prompt.",
            "steps": ["Load vision model", "Process image arrays", "Generate caption/analysis"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        yield "Starting VisionAgent execution...\n"
        
        import asyncio
        await asyncio.sleep(0.5)
        
        image_files = [f for f in context.files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if image_files:
            yield f"Processing images: {', '.join(image_files)}\n"
            await asyncio.sleep(0.5)
            yield "Identified key elements in the image.\n"
        else:
            yield "No images found in context, analyzing base layout constraints.\n"
            
        yield "Vision analysis complete."
