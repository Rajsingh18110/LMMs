import requests
import json
from typing import Optional

from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.router.execution_graph import ExecutionGraph, ExecutionStep
from lmms.backend.tasks.core_tasks.tasks.task import Task

class Planner:
    """
    Decomposes a user request into an ordered Task graph using the LLM.
    Assigns subtasks to specific agents (researcher, coder, tester, reviewer).
    """
    def __init__(self, endpoint_url: str = "http://localhost:11435/v1/chat/completions", default_model: str = "default"):
        self.endpoint_url = endpoint_url
        if default_model == "default":
            try:
                import requests
                resp = requests.get("http://localhost:11435/v1/models/ps", timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    loaded = data.get("loaded_models", [])
                    if loaded:
                        default_model = loaded[0]
            except Exception:
                pass
            
            if default_model == "default":
                import os, json
                active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
                if os.path.exists(active_f):
                    try:
                        with open(active_f, "r") as f:
                            d = json.load(f)
                            if d:
                                default_model = next(iter(d.keys()))
                    except Exception:
                        pass
        self.default_model = default_model

    def plan(self, user_request: str, context: ExecutionContext) -> ExecutionGraph:
        """
        Uses the LLM to generate an ExecutionGraph based on the user request.
        """
        from lmms.backend.agents.core_agents.agents.specialized.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
        from lmms.backend.tools.core import default_registry
        
        tools = default_registry.list_tools()
        tools_desc = json.dumps([{"name": t.name, "description": t.description} for t in tools.values()] if isinstance(tools, dict) else [{"name": getattr(t, "name", "unknown"), "description": getattr(t, "description", "")} for t in tools], indent=2)

        prompt = f"""{ORCHESTRATOR_SYSTEM_PROMPT}

You are the LMMs System Planner.
Your job is to break down the user's request into a sequential execution graph.
For each subtask, assign one of these exact agent roles:
- researcher (gathers facts, reads docs)
- coder (writes or edits code)
- tester (runs tests/code)
- reviewer (reviews the coder's work)

Available System Tools:
{tools_desc}

User Request: {user_request}

Return ONLY valid JSON in this exact format, with no markdown code blocks or extra text:
{{
    "intent": "main goal summary",
    "steps": [
        {{
            "agent": "coder",
            "action": "Description of what needs to be done",
            "dependencies": []
        }}
    ]
}}
"""

        payload = {
            "model_name": self.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        try:
            resp = requests.post(self.endpoint_url, json=payload, timeout=60)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            
            # Clean up potential markdown formatting from LLM response
            import re
            json_str = content
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
            else:
                json_str = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1:
                    json_str = json_str[start:end+1]
                
            plan_json = json.loads(json_str)
            
            graph = ExecutionGraph(intent=plan_json.get("intent", "auto-generated"))
            for step_idx, step_data in enumerate(plan_json.get("steps", [])):
                graph.add_step(
                    agent_name=step_data.get("agent", "coder"),
                    action_type=step_data.get("action", "Execute task"),
                    dependencies=step_data.get("dependencies", [])
                )
            
            # Fallback if no steps generated
            if not graph.steps:
                graph.add_step(agent_name="coder", action_type=user_request)
                
            return graph
            
        except Exception as e:
            # If the LLM call fails (e.g., no model loaded or engine down), provide a deterministic fallback
            print(f"[Planner] Failed to call LLM, falling back to deterministic plan: {e}")
            graph = ExecutionGraph(intent="fallback")
            graph.add_step(agent_name="researcher", action_type="Analyze context for " + user_request)
            graph.add_step(agent_name="coder", action_type="Implement changes for " + user_request)
            graph.add_step(agent_name="tester", action_type="Run tests for " + user_request)
            graph.add_step(agent_name="reviewer", action_type="Review changes for " + user_request)
            return graph
