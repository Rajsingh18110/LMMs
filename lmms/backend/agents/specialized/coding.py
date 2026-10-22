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
        
        # Enable ephemeral worktree isolation if git workspace is present
        ws = getattr(context, "workspace_id", None) or os.getcwd()
        wt_session = None
        try:
            from lmms_worktree.manager import default_worktree_manager
            if default_worktree_manager.is_git_repo(ws):
                wt_session = default_worktree_manager.enable(ws)
                yield f"[Worktree] Isolated ephemeral workspace active: {wt_session.worktree_path}\n"
        except Exception as wt_err:
            wt_session = None

        effective_ws = wt_session.worktree_dir if wt_session else ws
        from lmms.backend.tools.files import config as files_config
        orig_files_ws = files_config.get("workspace_dir")
        files_config.set("workspace_dir", effective_ws)

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
Return ONLY valid JSON in this exact format. You can specify code changes using a Codex-grade "patch" string (using '*** Begin Patch' / '*** Update File: <path>' or Unified Diff) OR search/replace "edits":
{
    "thoughts": "explain your plan",
    "patch": "*** Begin Patch\\n*** Update File: file/path.py\\n@@ ...\\n-exact old lines\\n+new lines\\n*** End Patch",
    "edits": [
        {
            "path": "file/path.py",
            "search": "exact old lines to replace",
            "replace": "new lines to insert"
        }
    ],
    "command": "python3 -m unittest discover tests"
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
            
            response_json = {}
            json_str = llm_text
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', llm_text, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
            else:
                cleaned = re.sub(r'<think>.*?</think>', '', llm_text, flags=re.DOTALL).strip()
                start = cleaned.find('{')
                end = cleaned.rfind('}')
                if start != -1 and end != -1:
                    json_str = cleaned[start:end+1]
                else:
                    json_str = cleaned
                
            try:
                response_json = json.loads(json_str)
            except Exception:
                # Fallback: model emitted raw patch or text without JSON wrapper
                raw_patch_match = re.search(r'(\*\*\* Begin Patch.*?\*\*\* End Patch)', llm_text, re.DOTALL)
                if not raw_patch_match:
                    raw_patch_match = re.search(r'(diff --git.*)', llm_text, re.DOTALL)
                if raw_patch_match:
                    response_json = {
                        "thoughts": "Extracted raw patch from model completion",
                        "patch": raw_patch_match.group(1).strip(),
                        "command": "python3 -m unittest"
                    }
                else:
                    response_json = {"thoughts": llm_text, "edits": []}

            yield f"Thoughts: {response_json.get('thoughts', 'No thoughts provided')}\n"
            
            edits = response_json.get("edits", [])
            patch_str = response_json.get("patch")
            edits_successful = True
            backups = {}

            patch_applied_successfully = False
            # 1. Apply Codex-grade Patch if provided
            if patch_str:
                yield f"Applying Codex-grade patch...\n"
                from lmms.backend.tools.patch import default_patch_engine
                default_patch_engine.workspace_root = effective_ws
                patch_res = default_patch_engine.apply_patch(patch_str)
                if patch_res.get("success"):
                    files_mod = patch_res.get('files_modified', [])
                    yield f"Patch applied successfully to: {', '.join(files_mod)}\n"
                    if patch_res.get("diff"):
                        yield f"\n[Patch Diff]:\n{patch_res['diff']}\n"
                    patch_applied_successfully = True
                    edits_successful = True
                    try:
                        from lmms.backend.events.bus import get_event_bus
                        get_event_bus().publish("patch_applied", {"files": files_mod, "diff": patch_res.get("diff", "")})
                    except Exception:
                        pass
                else:
                    yield f"Patch application failed: {patch_res.get('error')}\n"
                    edits_successful = False
            
            # 2. Apply surgical edits with AST Compile Guard only if patch was not applied
            if not patch_applied_successfully and edits:
                for edit in edits:
                path = edit.get("path")
                search = edit.get("search")
                replace = edit.get("replace")
                
                if path and search is not None and replace is not None:
                    # Backup original content for safe rollback
                    if os.path.exists(path) and path not in backups:
                        try:
                            with open(path, "r", encoding="utf-8") as bf:
                                backups[path] = bf.read()
                        except Exception:
                            pass

                    from lmms.backend.tools.files import FileTool
                    ft = FileTool()
                    res_msg = ft.replace_in_file(path, search, replace)
                    if "Successfully modified" in res_msg:
                        yield f"Applied surgical edit to: {path} (AST validated)\n"
                        # Extract diff lines if returned
                        diff_part = res_msg.partition("Diff:")[2]
                        if diff_part:
                            yield f"[Diff for {path}]:{diff_part}\n"
                    else:
                        yield f"Edit in {path} failed: {res_msg}\n"
                        edits_successful = False
                else:
                    edits_successful = False
                    
            cmd = response_json.get("command")
            if cmd and cmd.strip() == "python3 -m unittest" and os.path.isdir(os.path.join(effective_ws, "tests")):
                cmd = "python3 -m unittest discover tests"
            validation_successful = True
            if cmd:
                yield f"Running validation command in sandbox: `{cmd}`...\n"
                try:
                    from lmms.backend.tools.terminal import canonical_terminal_callback
                    t_res = canonical_terminal_callback(command=cmd, cwd=effective_ws, sandboxed=True)
                    out = t_res.get("output", "")
                    exit_code = t_res.get("exit_code", 0)
                    yield f"  Sandbox Terminal Output (exit code {exit_code}):\n{out}\n"
                    try:
                        from lmms.backend.events.bus import get_event_bus
                        get_event_bus().publish("test_result", {"command": cmd, "exit_code": exit_code, "output": out})
                    except Exception:
                        pass
                    if exit_code != 0:
                        validation_successful = False
                except Exception as e:
                    yield f"  Sandbox Terminal Error: {e}\n"
                    try:
                        from lmms.backend.events.bus import get_event_bus
                        get_event_bus().publish("error", {"command": cmd, "error": str(e)})
                    except Exception:
                        pass
                    validation_successful = False
                    
            if edits_successful and validation_successful:
                if wt_session:
                    try:
                        from lmms_worktree.manager import default_worktree_manager
                        applied, app_msg = default_worktree_manager.apply(ws)
                        if applied:
                            yield f"[Worktree] Verified edits merged cleanly back to {ws}\n"
                        else:
                            yield f"[Worktree] Merge warning: {app_msg}\n"
                    except Exception as e:
                        yield f"[Worktree] Apply error: {e}\n"
                yield "Execution completed successfully.\n"
            else:
                if wt_session:
                    try:
                        from lmms_worktree.manager import default_worktree_manager
                        default_worktree_manager.discard(ws)
                        yield f"[Worktree] Edits failed validation. Worktree cleanly discarded without modifying {ws}.\n"
                    except Exception:
                        pass
                yield "Execution completed with validation errors. Rolling back changes...\n"
                for p, old_val in backups.items():
                    try:
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(old_val)
                        yield f"  Rolled back: {p}\n"
                    except Exception as rb_err:
                        yield f"  Rollback failed for {p}: {rb_err}\n"
            
        except json.JSONDecodeError as e:
            yield f"Error: Failed to parse LLM response as JSON. {e}\nResponse was:\n{llm_text}\n"
        except Exception as e:
            yield f"Error during execution: {e}\n"
        finally:
            try:
                files_config.set("workspace_dir", orig_files_ws)
            except Exception:
                pass

    def write_code(self, task_description: str, files: Optional[List[str]] = None) -> str:
        """Convenience method to run coding agent synchronously on a task."""
        from lmms.backend.tasks.core_tasks.tasks.task import Task
        from lmms.backend.agents.core_agents.agents.context import ExecutionContext as EC
        ec = EC(workspace_id="default", task=Task(id="task-1", title="Coding Task", description=task_description), files=files or [])
        return self.execute_sync(ec)

    def generate_patch(self, original: str, modified: str, filepath: str = "file.py") -> str:
        """Generates unified diff patch between original and modified code."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(orig_lines, mod_lines, fromfile=f"a/{filepath}", tofile=f"b/{filepath}")
        return "".join(diff)

    def execute_tool_step(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """Executes a single tool step using the default executor."""
        from lmms.backend.tools.core import default_executor
        return default_executor.execute(tool_name, kwargs)


