from typing import Dict, Any, AsyncGenerator
import json
from lmms.backend.agents.core_agents.agents.base import BaseAgent
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
        import json
        import requests
        import os
        import asyncio
        import difflib
        import re
        from lmms.backend.tools.files import FileTool
        from lmms.backend.tools.terminal import TerminalTool

        yield "Starting CodingAgent execution...\n"
        
        file_tool = FileTool()
        term_tool = TerminalTool()
        
        files_to_read = set(context.files if context.files else [])
        if context.task:
            mentioned_files = re.findall(r'[\w/.-]+\.py', context.task.description)
            for f in mentioned_files:
                files_to_read.add(f)
                
        file_contents = {}
        if files_to_read:
            yield f"Reading files: {', '.join(files_to_read)}\n"
            for f in files_to_read:
                try:
                    content = file_tool.read(f)
                    file_contents[f] = content
                except Exception as e:
                    file_contents[f] = f"Error reading: {e}"
        else:
            yield "No specific files provided in context. Proceeding...\n"

        active_model = context.selected_model
        if not active_model or active_model == "LMMs Engine":
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
                    
        yield f"Generating edit instructions via LLM ({active_model})...\n"
        
        prompt = f"""You are an expert autonomous Coding Agent.
Task: {context.task.description if context.task else 'Complete the coding task'}

Context files:
"""
        for filepath, content in file_contents.items():
            prompt += f"\n--- {filepath} ---\n{content}\n"
            
        prompt += """
Please plan the implementation, modify the files, and run a validation command.
Return ONLY valid JSON in this exact format, with no markdown code blocks around it. Use exact text from the file for 'search'.
{
    "thoughts": "explain your plan",
    "edits": [
        {
            "path": "file/path.py",
            "search": "exact old lines to replace",
            "replace": "new lines to insert"
        }
    ],
    "command": "python3 -m py_compile file/path.py"
}
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
            
            if llm_text.startswith("```json"):
                llm_text = llm_text[7:]
            if llm_text.startswith("```"):
                llm_text = llm_text[3:]
            if llm_text.endswith("```"):
                llm_text = llm_text[:-3]
                
            response_json = json.loads(llm_text.strip())
            
            yield f"Thoughts: {response_json.get('thoughts', 'No thoughts provided')}\n"
            
            edits = response_json.get("edits", [])
            edits_successful = True
            backups = {}
            
            for edit in edits:
                path = edit.get("path")
                search = edit.get("search")
                replace = edit.get("replace")
                
                if path and search is not None and replace is not None:
                    old_content = file_contents.get(path, "")
                    if not old_content and os.path.exists(path):
                        try:
                            old_content = file_tool.read(path)
                        except Exception:
                            old_content = ""
                            
                    if search in old_content:
                        new_content = old_content.replace(search, replace, 1)
                        
                        diff = list(difflib.unified_diff(
                            old_content.splitlines(keepends=True),
                            new_content.splitlines(keepends=True),
                            fromfile=f"a/{path}",
                            tofile=f"b/{path}"
                        ))
                        diff_str = "".join(diff)
                        if diff_str:
                            yield f"\n[Diff for {path}]:\n{diff_str}\n"
                        else:
                            yield f"\n[Diff for {path}]: No changes detected.\n"
                            
                        yield f"Writing to file: {path}...\n"
                        backups[path] = old_content
                        res = file_tool.write(path, new_content)
                        yield f"  Result: {res}\n"
                    else:
                        yield f"Search block not found in {path}. Edit skipped.\n"
                        edits_successful = False
                else:
                    edits_successful = False
                    
            cmd = response_json.get("command")
            validation_successful = True
            if cmd:
                yield f"Running validation command: `{cmd}`...\n"
                try:
                    exit_code, out = term_tool.run(cmd, require_confirm=False, return_exit_code=True)
                    yield f"  Terminal Output:\n{out}\n"
                    if exit_code != 0:
                        validation_successful = False
                except Exception as e:
                    yield f"  Terminal Error: {e}\n"
                    validation_successful = False
                    
            if edits_successful and validation_successful:
                yield "Execution completed successfully.\n"
            else:
                yield "Execution completed with validation errors. Rolling back changes...\n"
                for p, old_val in backups.items():
                    file_tool.write(p, old_val)
                    yield f"  Rolled back: {p}\n"
            
        except json.JSONDecodeError as e:
            yield f"Error: Failed to parse LLM response as JSON. {e}\nResponse was:\n{llm_text}\n"
        except Exception as e:
            yield f"Error during execution: {e}\n"
