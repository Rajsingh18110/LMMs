from typing import Dict, Any, AsyncGenerator
import json
import requests
import os
import asyncio
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ResearchAgent",
            description="Specialized in autonomous web browsing, information gathering, and data synthesis.",
            capabilities=["web_browsing", "search", "synthesis"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and any(w in context.task.description.lower() for w in ["research", "search", "find", "scrape", "browse"]):
            score += 0.8
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "INSPECT target, GATHER data using BrowserTool, SYNTHESIZE findings.",
            "steps": ["Inspect target URL/query", "Gather information via browser", "Synthesize results"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        from lmms.backend.tools.browser import BrowserTool
        from lmms.backend.tools.search import SearchTool
        
        yield "Starting ResearchAgent execution (INSPECT -> GATHER -> SYNTHESIZE)...\n"
        
        browser = BrowserTool()
        search = SearchTool()
        
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
            
        if active_model == "default":
            active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
            if os.path.exists(active_f):
                try:
                    with open(active_f, "r") as f:
                        d = json.load(f)
                        if d:
                            active_model = next(iter(d.keys()))
                except Exception:
                    pass

        task_desc = context.task.description if context.task else 'Research the given topic'
        history = []
        
        for step in range(5): # Max 5 steps
            yield f"\n[Step {step+1}] Generating research action via LLM ({active_model})...\n"
            
            prompt = f"""You are an expert autonomous Research Agent.
Task: {task_desc}

History of actions and results:
{json.dumps(history, indent=2)}

You can take one of the following actions:
1. "search": Search the web. Requires "query".
2. "open_url": Navigate to a URL. Requires "url".
3. "click": Click an element. Requires "url" and "selector".
4. "synthesize": You have enough information and want to finalize. Requires "content" containing your final synthesized research.

Return ONLY valid JSON in this exact format, with no markdown code blocks around it:
{{
    "thoughts": "explain your plan for this step",
    "action": "open_url",
    "url": "https://example.com"
}}
"""
            payload = {
                "model_name": active_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            
            try:
                resp = requests.post("http://localhost:11435/v1/chat/completions", json=payload, timeout=120)
                resp.raise_for_status()
                llm_text = resp.json().get("message", {}).get("content", "")
                
                import re
                json_str = llm_text
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', llm_text, re.DOTALL | re.IGNORECASE)
                if match:
                    json_str = match.group(1).strip()
                else:
                    json_str = re.sub(r'<think>.*?</think>', '', llm_text, flags=re.DOTALL).strip()
                    start = json_str.find('{')
                    end = json_str.rfind('}')
                    if start != -1 and end != -1:
                        json_str = json_str[start:end+1]
                
                response_json = json.loads(json_str)
                action = response_json.get("action")
                
                yield f"Thoughts: {response_json.get('thoughts', '')}\n"
                yield f"Action: {action}\n"
                
                result = ""
                if action == "search":
                    query = response_json.get("query", "")
                    yield f"Searching for: {query}...\n"
                    result = search.search(query)
                elif action == "open_url":
                    url = response_json.get("url", "")
                    yield f"Opening URL: {url}...\n"
                    result = browser.open_url(url)
                elif action == "click":
                    url = response_json.get("url", "")
                    sel = response_json.get("selector", "")
                    yield f"Clicking '{sel}' on {url}...\n"
                    result = browser.click_element(url, sel)
                elif action == "synthesize":
                    yield f"Synthesizing final results...\n"
                    content = response_json.get("content", "")
                    yield f"\n[FINAL RESEARCH]\n{content}\n"
                    break
                else:
                    result = f"Unknown action: {action}"
                    
                yield f"Action Result length: {len(result)} characters\n"
                history.append({"action": response_json, "result": result[:1000] + ("..." if len(result)>1000 else "")})
                
            except json.JSONDecodeError as e:
                yield f"Error parsing JSON: {e}\nResponse:\n{llm_text}\n"
                break
            except Exception as e:
                yield f"Error during execution: {e}\n"
                break
                
        yield "\nResearchAgent execution completed.\n"
