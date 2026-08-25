from typing import Dict, Any, AsyncGenerator
import json
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TesterAgent",
            description="Executes test suites and verification commands, reporting back exact outputs and exit codes.",
            capabilities=["testing", "verification", "tool_use"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and "test" in context.task.description.lower():
            score += 0.8
        if context.files and any(f.endswith(('_test.py', 'test_.py')) for f in context.files):
            score += 0.5
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Discover and execute tests via TerminalTool, then report structured results.",
            "steps": ["Read task", "Run tests", "Report results"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        import requests
        from lmms.backend.tools.terminal import TerminalTool
        
        yield "Starting TesterAgent execution...\n"
        
        task_desc = context.task.description if context.task else "Run tests"
        files_str = "\n".join(context.files) if context.files else "None"
        
        prompt = f"""You are the TesterAgent.
Your task is: {task_desc}
Context files: {files_str}

Identify the correct test command to run. If testing a Python script directly, it might be `pytest <filename>`, `python3 -m unittest <filename>`, or `python3 <filename>`.
If it's a general directory, it might be `pytest tests/`.

Output ONLY a JSON block like this:
{{
    "thoughts": "I need to run...",
    "command": "pytest tests/test_something.py"
}}
"""
        try:
            # Dynamically check active model
            active_model = context.selected_model
            if not active_model or active_model == "LMMs Engine":
                active_model = "default"
                try:
                    resp = requests.get("http://localhost:11435/v1/models/ps", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        loaded = data.get("loaded_models", [])
                        if loaded:
                            active_model = loaded[0]
                except Exception:
                    pass

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
            
            cmd = response_json.get("command")
            if not cmd:
                yield "No test command generated. Execution completed with validation errors.\n"
                return
                
            yield f"Running test command: `{cmd}`...\n"
            term_tool = TerminalTool()
            
            try:
                exit_code, out = term_tool.run(cmd, require_confirm=False, return_exit_code=True)
                yield f"Terminal Output:\n{out}\n"
                if exit_code == 0:
                    yield "Tests PASSED.\n"
                    yield "Execution completed successfully.\n"
                else:
                    yield "Tests FAILED.\n"
                    yield "Execution completed with validation errors.\n"
            except Exception as e:
                yield f"Terminal Error: {e}\n"
                yield "Execution completed with validation errors.\n"
                
        except Exception as e:
            yield f"TesterAgent LLM call failed: {e}\n"
            yield "Execution completed with validation errors.\n"
