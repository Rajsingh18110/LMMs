from typing import Dict, Any, AsyncGenerator
import json
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ReviewerAgent",
            description="Reviews code changes and test results against requirements to determine PASS or REJECT.",
            capabilities=["review", "analysis", "text"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and "review" in context.task.description.lower():
            score += 0.8
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Analyze the changed files, diffs, and test results against the original goal, and emit PASS or REJECT.",
            "steps": ["Review diff", "Review test results", "Determine PASS/REJECT"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        import requests
        
        yield "Starting ReviewerAgent execution...\n"
        
        task_desc = context.task.description if context.task else "Review the changes"
        files_str = "\n".join(context.files) if context.files else "None"
        
        # In a fully wired system, we would also inject the actual diffs and test results
        # from the ExecutionContext's memory/results dictionary.
        # For now, we supply the context available.
        prompt = f"""You are the ReviewerAgent.
Your task: {task_desc}
Context files: {files_str}

Evaluate if the proposed changes appear to satisfy the requirements.
Output ONLY a JSON block like this:
{{
    "thoughts": "The code changes address the requirement by...",
    "status": "PASS" // or "REJECT"
}}
"""
        try:
            # Dynamically check active model
            try:
                resp = requests.get("http://localhost:11435/v1/models/ps", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    loaded = data.get("loaded_models", [])
                    if loaded:
                        active_model = loaded[0]
                    else:
                        active_model = "default"
                else:
                    active_model = "default"
            except Exception:
                active_model = "default"

            response = requests.post(
                "http://localhost:11435/v1/chat/completions",
                json={
                    "model_name": active_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            llm_text = data.get("message", {}).get("content", "")
            
            # Extract JSON block
            if llm_text.startswith("```json"):
                llm_text = llm_text[7:]
            if llm_text.startswith("```"):
                llm_text = llm_text[3:]
            if llm_text.endswith("```"):
                llm_text = llm_text[:-3]
                
            json_str = llm_text.strip()
                
            response_json = json.loads(json_str)
            yield f"Thoughts: {response_json.get('thoughts', 'No thoughts')}\n"
            
            status = response_json.get("status", "REJECT")
            yield f"Review Status: {status}\n"
            
            if status == "PASS":
                yield "Execution completed successfully.\n"
            else:
                yield "Execution completed with validation errors.\n"
                
        except Exception as e:
            yield f"ReviewerAgent LLM call failed: {e}\n"
            yield "Execution completed with validation errors.\n"
