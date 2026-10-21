from typing import Dict, Any, Optional, List, AsyncGenerator
import json
import os
import re
import difflib
import requests
import asyncio
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class CodingAgent(BaseAgent):
    """
    Production-grade Autonomous Coding Agent for LMMs.
    Specialized in codebase inspection, AST analysis, surgical diff edits,
    and automatic execution/test validation.
    """
    def __init__(self, manifest: Optional[Dict[str, Any]] = None):
        if manifest and isinstance(manifest, dict):
            name = manifest.get("name", "CodingAgent")
            description = manifest.get("description", "Specialized in software development, debugging, and codebase modifications.")
            capabilities = manifest.get("capabilities", ["text", "coding", "tool_use"])
            super().__init__(name=name, description=description, capabilities=capabilities)
            self.manifest = manifest
        else:
            super().__init__(
                name="CodingAgent",
                description="Specialized in software development, debugging, and codebase modifications.",
                capabilities=["text", "coding", "tool_use"]
            )
            self.manifest = {}

    def evaluate(self, context: ExecutionContext) -> float:
        score = 0.0
        if context.task and any(k in context.task.description.lower() for k in ["code", "fix", "bug", "implement", "refactor"]):
            score += 0.5
        if context.files and any(f.endswith(('.py', '.js', '.ts', '.cpp', '.html', '.dart', '.rs', '.go')) for f in context.files):
            score += 0.3
        
        if context.memory:
            last_msg = context.memory[-1].get("content", "").lower()
            code_keywords = ["write", "function", "bug", "error", "refactor", "implement", "class", "script"]
            if any(k in last_msg for k in code_keywords):
                score += 0.4
                
        return min(1.0, score)

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Analyze existing files, apply modifications via surgical diff tools, and run verification.",
            "steps": ["Read files", "Plan edits", "Apply edits", "Run verification test"]
        }

    def validate(self, context: Any) -> bool:
        return True

    def cleanup(self) -> None:
        pass

    def execute_sync(self, context: Any) -> str:
        """Synchronous wrapper for execution."""
        from lmms.backend.agents.core_agents.agents.context import ExecutionContext as EC
        from lmms.backend.tasks.core_tasks.tasks.task import Task
        if isinstance(context, dict):
            task_desc = context.get("task", "")
            ec = EC(workspace_id=context.get("workspace", "default"), task=Task(id="task-1", title="Coding Task", description=str(task_desc)))
        else:
            ec = context

        output_chunks = []
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def _run():
            async for chunk in self.execute(ec):
                output_chunks.append(chunk)

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_run())).result()
        else:
            loop.run_until_complete(_run())

        return "".join(output_chunks)

    async def execute(self, context: Any) -> AsyncGenerator[str, None]:
        if isinstance(context, dict):
            # Adapt dict to ExecutionContext
            from lmms.backend.tasks.core_tasks.tasks.task import Task
            from lmms.backend.agents.core_agents.agents.context import ExecutionContext as EC
            task_desc = context.get("task", "")
            ws_id = context.get("workspace", "default")
            context = EC(workspace_id=ws_id, task=Task(id="t-1", title="Coding Task", description=str(task_desc)))

        from lmms.backend.tools.core import default_executor
        
        files_to_read = set(context.files if context.files else [])
        if context.task:
            mentioned_files = re.findall(r'[\w/.-]+\.(?:py|js|ts|html|css|json|yaml|dart|go|rs)', context.task.description)
            for f in mentioned_files:
                files_to_read.add(f)
                
        file_contents = {}
        if files_to_read:
            yield f"Reading files: {', '.join(files_to_read)}\n"
            for f in files_to_read:
                res = default_executor.execute("file.read", {"path": f})
                if res.success:
                    file_contents[f] = res.data.get("content", "")
                else:
                    file_contents[f] = f"Error reading: {res.error}"
        else:
            yield "No specific files provided in context. Proceeding...\n"

        active_model = getattr(context, "selected_model", None)
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
        
        llm_text = ""
        try:
            resp = requests.post("http://localhost:11435/v1/chat/completions", json=payload, timeout=120)
            resp.raise_for_status()
            llm_text = resp.json().get("message", {}).get("content", "")
            
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
                            r = default_executor.execute("file.read", {"path": path})
                            old_content = r.data.get("content", "") if r.success else ""
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
                        r = default_executor.execute("file.write", {"path": path, "content": new_content})
                        yield f"  Result: {'OK' if r.success else r.error}\n"
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
                    r = default_executor.execute("terminal.run", {"command": cmd, "cwd": os.getcwd()})
                    out = r.data.get("output", "") if r.success else r.error
                    exit_code = r.data.get("exit_code", 1) if r.success else 1
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
                    default_executor.execute("file.write", {"path": p, "content": old_val})
                    yield f"  Rolled back: {p}\n"
            
        except json.JSONDecodeError as e:
            yield f"Error: Failed to parse LLM response as JSON. {e}\nResponse was:\n{llm_text}\n"
        except Exception as e:
            yield f"Error during execution: {e}\n"
