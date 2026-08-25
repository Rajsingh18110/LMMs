from typing import Dict, Any, AsyncGenerator
import json
import requests
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class PlainChatAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="PlainChatAgent",
            description="Handles general conversation and simple questions that do not require specialized workflows.",
            capabilities=["chat", "text"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        # Fixed baseline score. If no specialized agent scores above 0.35, this agent will take over.
        return 0.35

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Respond directly to the user's message using the base LLM without executing complex sub-agent tools.",
            "steps": ["Stream LLM response"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        # Determine the active model
        active_model = "default"
        try:
            resp = requests.get("http://localhost:11435/v1/models/ps", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                loaded = data.get("loaded_models", [])
                if loaded:
                    active_model = loaded[0]
        except Exception:
            pass

        # Build prompt using task description
        user_prompt = context.task.description if context.task else ""
        messages = [{"role": "user", "content": user_prompt}]
        if context.memory:
            # We can also append recent memory if needed, but for simplicity, we pass user_prompt
            pass

        payload = {
            "model_name": active_model,
            "messages": messages,
            "stream": True
        }

        try:
            response = requests.post("http://localhost:11435/v1/chat/completions", json=payload, stream=True, timeout=120)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "error" in chunk:
                                yield f"\n[Error]: {chunk['error']}\n"
                                break
                            
                            content = chunk.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
                            
            yield "\n"
        except Exception as e:
            yield f"\n[Error connecting to engine]: {e}\n"
