"""
agent.py — LMMs HexAgent (Full Rewrite)
Supports: Ollama, Cloud APIs, AirLLM, Smart Routing, Canvas, Claude Code Mode
"""

import requests

import os
import json
import difflib
from datetime import datetime
from lmms.backend.models import ModelManager
from lmms.backend.memory.core_memory import Memory
from lmms.gui.widgets.canvas import get_canvas
from lmms.backend.tools.search import web_search
from lmms.backend.tools.browser import BrowserTool
from lmms.backend.tools.files import FileTool
from lmms.backend.tools.terminal import TerminalTool
from lmms.gui.core.ui import (
    show_error, stream_response, show_info,
    show_tool_use, console, Markdown, Panel,
    show_response, get_swapping_spinner
)


# ─────────────────────────────────────────────────────────────
# SMART ROUTER
# ─────────────────────────────────────────────────────────────

INTENT_MAP = {
    "web_search": ["search", "find", "look up", "google", "latest", "news", "current", "who is", "what is"],
    "browse": ["browse", "visit", "go to", "open site", "http", ".com", ".org", ".net"],
    "code": ["code", "write", "fix", "debug", "function", "class", "script", "program", "implement", "refactor"],
    "file_op": ["read file", "write file", "create file", "open file", "save", "delete file", "edit file"],
    "graph": ["graph", "chart", "plot", "visualize", "show data", "histogram", "bar chart"],
    "terminal": ["run", "execute", "terminal", "bash", "command", "install", "pip", "apt", "sudo"],
    "vision": ["image", "picture", "photo", "screenshot", "see this", "analyze image"],
    "vscode": ["vscode", "vs code", "editor", "open in code", "improve code", "fix code"],
    "chat": [],  # fallback
}


def detect_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in INTENT_MAP.items():
        if intent == "chat":
            continue
        if any(k in text_lower for k in keywords):
            return intent
    return "chat"


def is_complex_task(text: str) -> bool:
    """Should this go to cloud API instead of local?"""
    complex_signals = ["explain", "analyze", "compare", "write a detailed", "step by step",
                       "architecture", "design pattern", "review", "critique"]
    return any(s in text.lower() for s in complex_signals) and len(text.split()) > 15


# ─────────────────────────────────────────────────────────────
# HexAgent
# ─────────────────────────────────────────────────────────────

class HexAgent:
    def __init__(self, model=None, mode="deep"):
        self.models = ModelManager()
        if model:
            self.models.set_model(model)
        self.current_mode = mode
        self.memory = Memory()
        self.undo_stack = []
        self.redo_stack = []
        self.browser_tool = BrowserTool()
        self.file_tool = FileTool()
        self.file_tool.agent = self
        self.terminal_tool = TerminalTool()
        self.terminal_tool.agent = self
        self.canvas = get_canvas()

        # Backend selection: lmms_engine | airllm | cloud:<name>
        self.backend = "lmms_engine"
        self.airllm_model = None
        self.airllm_model_name = None

        # Active cloud connector name (when backend = cloud:<name>)
        self._cloud_connector = None

        self.tools = {
            "web_search": web_search,
            "open_url": self.browser_tool.open_url,
            "browser_click": self.browser_tool.human_click,
            "browser_type": self.browser_tool.human_type,
            "read_file": self.file_tool.read,
            "write_file": self.file_tool.write,
            "edit_in_vscode": self.file_tool.edit_in_vscode,
            "run_command": self.terminal_tool.run,
        }

        self.lmms_tools = self._build_tool_specs()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.system_prompt = (
            "You are LMMs by MarkanM Team — a powerful local AI assistant. "
            "You can search the web, browse URLs, read/write files, run terminal commands, "
            "and write code. Be concise, accurate, and helpful."
        )

    # ──────────────────────────────────────────────
    # TOOL SPECS
    # ──────────────────────────────────────────────

    def _build_tool_specs(self):
        return [
            {"type": "function", "function": {
                "name": "web_search", "description": "Search the web using DuckDuckGo",
                "parameters": {"type": "object", "properties": {
                    "query": {"type": "string", "description": "Search query"}
                }, "required": ["query"]}}},
            {"type": "function", "function": {
                "name": "open_url", "description": "Open a webpage and extract content. Automatically bypasses simple CAPTCHAs.",
                "parameters": {"type": "object", "properties": {
                    "url": {"type": "string", "description": "URL to open"}
                }, "required": ["url"]}}},
            {"type": "function", "function": {
                "name": "browser_click", "description": "Click an element on the current webpage using human-like mouse movements. Use this to bypass 'Verify you are human' or to navigate.",
                "parameters": {"type": "object", "properties": {
                    "url": {"type": "string", "description": "Current URL"},
                    "selector": {"type": "string", "description": "CSS selector or text content to click"}
                }, "required": ["url", "selector"]}}},
            {"type": "function", "function": {
                "name": "browser_type", "description": "Type text into an input field on the current webpage with human-like delays. Use for login forms.",
                "parameters": {"type": "object", "properties": {
                    "url": {"type": "string", "description": "Current URL"},
                    "selector": {"type": "string", "description": "CSS selector for the input field"},
                    "text": {"type": "string", "description": "Text to type"}
                }, "required": ["url", "selector", "text"]}}},
            {"type": "function", "function": {
                "name": "read_file", "description": "Read contents of a local file",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string", "description": "Path to file"}
                }, "required": ["path"]}}},
            {"type": "function", "function": {
                "name": "write_file", "description": "Write text content to a local file",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "content": {"type": "string"}
                }, "required": ["path", "content"]}}},
            {"type": "function", "function": {
                "name": "run_command", "description": "Execute a shell command",
                "parameters": {"type": "object", "properties": {
                    "command": {"type": "string"}
                }, "required": ["command"]}}},
            {"type": "function", "function": {
                "name": "analyze_image", "description": "Analyze an image using vision model",
                "parameters": {"type": "object", "properties": {
                    "image_path": {"type": "string"}, "prompt": {"type": "string"}
                }, "required": ["image_path", "prompt"]}}},
        ]

    # ──────────────────────────────────────────────
    # FILE ATTACH
    # ──────────────────────────────────────────────
    # ENGINE API HELPER
    # ──────────────────────────────────────────────
    def _engine_chat(self, model, messages, stream=False, tools=None):
        payload = {
            "model_name": model,
            "messages": messages,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools
            
        try:
            res = requests.post("http://localhost:11435/v1/chat/completions", json=payload, stream=stream, timeout=120)
            if not stream:
                # Engine might return raw text or JSON depending on the server response logic
                try:
                    return res.json()
                except Exception:
                    return {"message": {"content": res.text}}
                    
            def _stream_gen():
                for line in res.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                yield {"message": data}
                            except Exception:
                                pass
            return _stream_gen()
        except Exception as e:
            raise RuntimeError(f"Engine connection failed: {e}")

    # ──────────────────────────────────────────────

    def attach_files(self, paths: list):
        for path in paths:
            if not os.path.exists(path):
                show_error(f"File not found: {path}")
                continue
            try:
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    desc = self._process_image_vram_safe(path)
                    self.memory.save(self.session_id, "user", f"[Image: {path}]\n{desc}", "user")
                else:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.memory.save(self.session_id, "user", f"[File: {path}]\n{content}", "user")
                show_info(f"Attached: {path}")
            except Exception as e:
                show_error(f"Could not attach {path}: {e}")

    def attach_folder(self, folderpath: str) -> int:
        import pathspec
        if not os.path.isdir(folderpath):
            show_error(f"Directory not found: {folderpath}")
            return 0
        gitignore_path = os.path.join(folderpath, ".gitignore")
        lines = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                lines = f.readlines()
        lines.extend([".git/", "__pycache__/", "*.pyc", "node_modules/", "venv/", "env/"])
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)
        count = 0
        for root, dirs, files in os.walk(folderpath):
            for file in files:
                if count >= 50:
                    show_error("Max 50 files limit reached.")
                    return count
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, folderpath)
                if spec.match_file(rel_path):
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.memory.save(self.session_id, "user", f"[File: {rel_path}]\n{content}", "user")
                    count += 1
                except Exception:
                    pass
        show_info(f"Attached {count} files from {folderpath}")
        return count

    # ──────────────────────────────────────────────
    # UNDO / REDO
    # ──────────────────────────────────────────────

    def push_action(self, action: dict):
        self.undo_stack.append(action)
        self.redo_stack.clear()

    def undo_action(self):
        if not self.undo_stack:
            show_error("Nothing to undo.")
            return
        action = self.undo_stack.pop()
        if action["type"] == "file_write":
            path, old = action["path"], action["old_content"]
            if old is None:
                if os.path.exists(path):
                    os.remove(path)
                show_info(f"↩ Undid: Deleted {path}")
            else:
                with open(path, "w") as f:
                    f.write(old)
                show_info(f"↩ Undid: Restored {path}")
            self.redo_stack.append(action)
        elif action["type"] == "terminal_command":
            show_error(f"Cannot auto-reverse: `{action['command']}` — please reverse manually.")
            self.redo_stack.append(action)

    def redo_action(self):
        if not self.redo_stack:
            show_error("Nothing to redo.")
            return
        action = self.redo_stack.pop()
        if action["type"] == "file_write":
            with open(action["path"], "w") as f:
                f.write(action["new_content"])
            show_info(f"↪ Redid: {action['path']}")
            self.undo_stack.append(action)
        elif action["type"] == "terminal_command":
            self.terminal_tool.run(action["command"], require_confirm=False)
            self.undo_stack.append(action)

    # ──────────────────────────────────────────────
    # DIFF-BASED FILE EDIT  (Claude Code style)
    # ──────────────────────────────────────────────

    def edit_file_diff(self, path: str, new_content: str) -> str:
        """Edit file using diff, only apply changed sections. Returns diff summary."""
        if not os.path.exists(path):
            # New file
            self.push_action({"type": "file_write", "path": path, "old_content": None, "new_content": new_content})
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Created new file: {path}"

        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()

        if old_content == new_content:
            return "No changes needed."

        # Store for undo
        self.push_action({"type": "file_write", "path": path, "old_content": old_content, "new_content": new_content})

        diff = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(path)}",
            tofile=f"b/{os.path.basename(path)}",
            n=3,
        ))

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        return f"✅ Edited {path}: +{added} lines, -{removed} lines"

    # ──────────────────────────────────────────────
    # VISION
    # ──────────────────────────────────────────────

    def _process_image_vram_safe(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        import base64
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            self.models.unload_model(self.models.text_model)
            with get_swapping_spinner(self.models.vision_model):
                response = self._engine_chat(
                    model=self.models.vision_model,
                    messages=[{"role": "user", "content": prompt, "images": [image_data]}],
                    stream=False
                )
            with get_swapping_spinner(self.models.text_model):
                requests.post("http://localhost:11435/v1/models/load", json={"model_name": self.models.text_model})
            return response.get("message", {}).get("content", "No content from vision model.")
        except Exception as e:
            return f"Vision error: {e}"

    # ──────────────────────────────────────────────
    # MAIN CHAT ENTRY
    # ──────────────────────────────────────────────

    def chat(self, user_input: str, image_path: str = None):
        final_prompt = user_input
        if image_path:
            desc = self._process_image_vram_safe(image_path)
            final_prompt = f"[Image: {desc}]\n{user_input}"

        self.memory.save(self.session_id, "user", final_prompt, "user")

        # Route to backend
        if self.backend == "airllm":
            self._run_airllm(final_prompt)
        elif self.backend.startswith("cloud:"):
            connector_name = self.backend[6:]
            self._run_cloud(final_prompt, connector_name)
        elif self.current_mode == "fast":
            self._run_fast(final_prompt)
        elif self.current_mode == "dual":
            self._run_dual(final_prompt)
        else:
            self._run_deep(final_prompt)

    # ──────────────────────────────────────────────
    # SMART ROUTING: auto pick cloud for complex tasks
    # ──────────────────────────────────────────────

    def smart_chat(self, user_input: str, image_path: str = None):
        """Auto-route: complex tasks → cloud if available, else local."""
        connectors = self.models.list_connectors()
        if connectors and is_complex_task(user_input):
            show_info(f"[Smart Router] Complex task → using cloud: {connectors[0]}")
            self.backend = f"cloud:{connectors[0]}"
            self.chat(user_input, image_path)
            self.backend = "lmms_engine"
        else:
            self.chat(user_input, image_path)

    # ──────────────────────────────────────────────
    # BACKENDS
    # ──────────────────────────────────────────────

    def _get_history_messages(self):
        history = self.memory.get_history(self.session_id, limit=20)
        return [{"role": "system", "content": self.system_prompt}] + history

    def _run_fast(self, prompt: str):
        messages = self._get_history_messages()
        try:
            stream = self._engine_chat(
                model=self.models.text_model, 
                messages=messages,
                stream=True,
            )
            text = stream_response(stream, model_name="FAST Mode", show_load_time=True, mode=self.current_mode)
            self.memory.save(self.session_id, "assistant", text, self.models.text_model)
        except Exception as e:
            show_error(f"Engine error: {e}")

    def _run_deep(self, prompt: str):
        """Full agentic loop with tool use."""
        messages = self._get_history_messages()
        try:
            response = self._engine_chat(
                model=self.models.text_model,
                messages=messages,
                tools=self.lmms_tools,
                stream=False
            )
            
            tool_calls = response.get("message", {}).get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    fn_args = tc["function"].get("arguments", {})
                    show_tool_use(fn_name, str(fn_args)[:80])
                    tool_fn = self.tools.get(fn_name)
                    if tool_fn:
                        result = tool_fn(**fn_args)
                    else:
                        result = f"Unknown tool: {fn_name}"
                    messages.append({"role": "tool", "content": str(result), "name": fn_name})

                # Final answer after tools
                stream = self._engine_chat(
                    model=self.models.text_model,
                    messages=messages,
                    stream=True
                )
                text = stream_response(stream, model_name="DEEP Mode", show_load_time=True, mode=self.current_mode)
            else:
                text = response.get("message", {}).get("content", "")
                if text:
                    self.canvas.render(text, title=f"LMMs [{self.models.text_model}]")

            self.memory.save(self.session_id, "assistant", text, self.models.text_model)
        except Exception as e:
            show_error(f"Engine error: {e}")
            # Fallback to fast
            self._run_fast(prompt)

    def _run_cloud(self, prompt: str, connector_name: str):
        """Call cloud API connector."""
        show_info(f"☁ Calling cloud: {connector_name}")
        messages = self._get_history_messages()
        try:
            text = self.models.cloud_chat(connector_name, messages)
            self.canvas.render(text, title=f"Cloud [{connector_name}]")
            self.memory.save(self.session_id, "assistant", text, connector_name)
        except Exception as e:
            show_error(f"Cloud API error: {e}")

    def _run_airllm(self, prompt: str):
        """Real AirLLM inference — layer-by-layer from disk."""
        try:
            from airllm import AutoModel
        except ImportError:
            show_error("airllm not installed. Run: pip install airllm")
            return

        show_info(f"⚡ AirLLM: {self.models.text_model} (layer-by-layer, low VRAM)")

        if self.airllm_model is None or self.airllm_model_name != self.models.text_model:
            show_info("Loading model from disk...")
            try:
                self.airllm_model = AutoModel.from_pretrained(self.models.text_model)
                self.airllm_model_name = self.models.text_model
            except Exception as e:
                show_error(f"AirLLM load failed: {e}")
                return

        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.models.text_model)
            history = self.memory.get_history(self.session_id, limit=10)
            full_prompt = self.system_prompt + "\n"
            for m in history:
                full_prompt += f"{m['role']}: {m['content']}\n"
            full_prompt += f"assistant:"

            input_ids = tokenizer(full_prompt, return_tensors="pt").input_ids
            output = self.airllm_model.generate(
                input_ids,
                max_new_tokens=512,
                use_cache=False,
                do_sample=False,
            )
            text = tokenizer.decode(output[0][input_ids.shape[1]:], skip_special_tokens=True)
            self.canvas.render(text, title="AirLLM")
            self.memory.save(self.session_id, "assistant", text, "airllm")
        except Exception as e:
            show_error(f"AirLLM inference error: {e}")

    def _run_dual(self, prompt: str):
        """Two-model debate: Qwen reasons, Gemma critiques."""
        import time
        from lmms.gui.core.ui import render_dual_stats

        words = prompt.split()
        if len(words) < 4 or any(w in prompt.lower() for w in ["hello", "hi", "hey", "thanks", "ok", "bye"]):
            show_info("⚡ Simple query — skipping debate")
            self._run_fast(prompt)
            return

        history = self.memory.get_history(self.session_id, limit=20)
        qwen_messages = [{"role": "system", "content": self.system_prompt}] + history

        max_rounds = 6
        current_round = 1
        qwen_response = gemma_response = ""
        qwen_time = gemma_time = 0.0

        while current_round <= max_rounds:
            show_response(f"── Round {current_round} ──")
            if current_round > 1:
                with get_swapping_spinner(self.models.text_model):
                    self.models.unload_model(self.models.vision_model)
            try:
                t = time.time()
                stream = self._engine_chat(
                    model=self.models.text_model, 
                    messages=qwen_messages,
                    stream=True
                )
                qwen_response = stream_response(stream, model_name=f"Qwen R{current_round}", mode="dual")
                qwen_time += time.time() - t
                qwen_messages.append({"role": "assistant", "content": qwen_response})
            except Exception as e:
                show_error(f"Model error: {e}")
                break

            if "i agree" in qwen_response.lower() or "agreed" in qwen_response.lower() or current_round == max_rounds:
                break

            with get_swapping_spinner(self.models.vision_model):
                self.models.unload_model(self.models.text_model)

            try:
                t = time.time()
                gemma_prompt = (
                    f"Qwen said: {qwen_response}\n"
                    "You are a strict critic. If correct → ONLY say 'agreed'.\n"
                    "If wrong → max 2-3 sentences correction. No essays."
                )
                stream = self._engine_chat(
                    model=self.models.vision_model,
                    messages=[{"role": "user", "content": gemma_prompt}],
                    stream=True
                )
                gemma_response = stream_response(stream, model_name=f"Gemma R{current_round}", mode="dual")
                gemma_time += time.time() - t
            except Exception as e:
                show_error(f"Critic error: {e}")
                break

            if "i agree" in gemma_response.lower() or "agreed" in gemma_response.lower():
                break

            qwen_messages.append({"role": "user", "content": f"Critic says:\n{gemma_response}\nRefine your answer."})
            current_round += 1

        render_dual_stats(current_round, qwen_time, gemma_time)

        with get_swapping_spinner(self.models.text_model):
            self.models.unload_model(self.models.vision_model)

        qwen_messages.append({"role": "user", "content": "Summarize the final agreed answer concisely."})
        try:
            stream = self._engine_chat(
                model=self.models.text_model, 
                messages=qwen_messages,
                stream=True
            )
            final = stream_response(stream, model_name="Final Answer", mode="dual")
            self.memory.save(self.session_id, "assistant", final, self.models.text_model)
        except Exception as e:
            show_error(f"Final answer error: {e}")

    # ──────────────────────────────────────────────
    # CLAUDE CODE MODE
    # ──────────────────────────────────────────────

    def code_mode(self, task: str, project_path: str = "."):
        """
        Claude Code-style agentic coding:
        1. Index codebase
        2. Plan changes
        3. Apply diff-based edits
        4. Run tests / lint
        5. Fix errors in loop
        """
        from rich.console import Console
        from rich.panel import Panel
        c = Console()

        c.print(Panel(f"[bold cyan]🤖 Code Mode[/bold cyan]\nTask: {task}\nProject: {project_path}", border_style="cyan"))

        # Step 1: Index codebase
        c.print("[cyan]📁 Indexing codebase...[/cyan]")
        code_context = self._index_codebase(project_path)
        c.print(f"[green]✅ Indexed {code_context['file_count']} files ({code_context['total_lines']} lines)[/green]")

        # Step 2: Plan
        c.print("[cyan]🧠 Planning changes...[/cyan]")
        plan_prompt = f"""You are an expert coding assistant (like Claude Code).

Project structure:
{code_context['tree']}

Key files content:
{code_context['content'][:6000]}

Task: {task}

Respond with a JSON plan:
{{
  "analysis": "what the code does currently",
  "changes": [
    {{"file": "path/to/file.py", "action": "edit|create|delete", "description": "what to change"}}
  ],
  "steps": ["step 1", "step 2"]
}}
ONLY JSON, no explanation."""

        plan_text = ""
        try:
            res = self._engine_chat(
                model=self.models.text_model,
                messages=[{"role": "user", "content": plan_prompt}],
                stream=False
            )
            plan_text = res.get("message", {}).get("content", "")
        except Exception as e:
            show_error(f"Plan generation failed: {e}")
            return

        # Parse plan
        try:
            import re
            json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found")
        except Exception:
            c.print("[yellow]Could not parse plan, proceeding with direct edit...[/yellow]")
            plan = {"changes": [{"file": task, "action": "edit", "description": task}], "steps": [task]}

        c.print(f"\n[bold]Plan:[/bold]")
        for step in plan.get("steps", []):
            c.print(f"  • {step}")

        confirm = input("\nProceed? (y/n/edit): ").strip().lower()
        if confirm == "n":
            c.print("[dim]Cancelled.[/dim]")
            return
        if confirm == "edit":
            task = input("Refine task: ").strip()
            self.code_mode(task, project_path)
            return

        # Step 3: Apply changes
        for change in plan.get("changes", []):
            file_path = os.path.join(project_path, change["file"])
            action = change.get("action", "edit")
            desc = change.get("description", "")

            c.print(f"\n[cyan]✏ {action.upper()}: {file_path}[/cyan]")
            c.print(f"[dim]{desc}[/dim]")

            if action == "delete":
                if os.path.exists(file_path):
                    confirm_del = input(f"Delete {file_path}? (y/n): ").strip().lower()
                    if confirm_del == "y":
                        os.remove(file_path)
                        c.print(f"[green]Deleted {file_path}[/green]")
                continue

            # Generate code for this file
            existing = ""
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    existing = f.read()

            code_prompt = f"""You are editing {file_path}.

Current content:
```
{existing[:3000]}
```

Change needed: {desc}
Overall task: {task}

Output ONLY the complete new file content. No explanation. No markdown backticks."""

            try:
                stream = self._engine_chat(
                    model=self.models.text_model,
                    messages=[{"role": "user", "content": code_prompt}],
                    stream=True
                )
                new_content = ""
                for chunk in stream:
                    new_content += chunk.get("message", {}).get("content", "")

                result = self.edit_file_diff(file_path, new_content)
                c.print(f"[green]{result}[/green]")
            except Exception as e:
                show_error(f"Code generation failed: {e}")

        # Step 4: Run & fix loop
        c.print("\n[cyan]🔍 Running error check...[/cyan]")
        self._run_and_fix_loop(project_path, max_iterations=3)

        c.print("\n[bold green]✅ Code Mode complete![/bold green]")

    def _index_codebase(self, project_path: str) -> dict:
        """Build codebase index for Claude Code mode."""
        import pathspec
        tree_lines = []
        content_parts = []
        file_count = 0
        total_lines = 0

        gitignore = os.path.join(project_path, ".gitignore")
        ignore_lines = [".git/", "__pycache__/", "*.pyc", "node_modules/", "venv/", "*.egg-info/"]
        if os.path.exists(gitignore):
            with open(gitignore) as f:
                ignore_lines += f.readlines()
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignore_lines)

        CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".sh", ".yaml", ".yml"}

        for root, dirs, files in os.walk(project_path):
            rel_root = os.path.relpath(root, project_path)
            # Filter dirs
            dirs[:] = [d for d in dirs if not spec.match_file(os.path.join(rel_root, d) + "/")]
            indent = "  " * rel_root.count(os.sep)
            tree_lines.append(f"{indent}{os.path.basename(root)}/")

            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, project_path)
                if spec.match_file(rel_path):
                    continue
                ext = os.path.splitext(file)[1].lower()
                tree_lines.append(f"{indent}  {file}")
                file_count += 1

                if ext in CODE_EXTENSIONS and file_count <= 20:
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        lines = content.count("\n")
                        total_lines += lines
                        content_parts.append(f"\n### {rel_path}\n```\n{content[:2000]}\n```")
                    except Exception:
                        pass

        return {
            "tree": "\n".join(tree_lines[:50]),
            "content": "\n".join(content_parts),
            "file_count": file_count,
            "total_lines": total_lines,
        }

    def _run_and_fix_loop(self, project_path: str, max_iterations: int = 3):
        """Run linter/tests and auto-fix errors."""
        from rich.console import Console
        c = Console()

        for i in range(max_iterations):
            # Try running Python files for syntax errors
            errors = []
            for root, _, files in os.walk(project_path):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        result = self.terminal_tool.run(f"python3 -m py_compile {filepath} 2>&1")
                        if result and "Error" in result:
                            errors.append({"file": filepath, "error": result})

            if not errors:
                c.print("[green]✅ No errors found![/green]")
                break

            c.print(f"[yellow]⚠ Found {len(errors)} error(s). Auto-fixing (iteration {i+1}/{max_iterations})...[/yellow]")

            for err in errors[:3]:  # Fix max 3 at once
                c.print(f"[red]Error in {err['file']}:[/red] {err['error'][:100]}")
                fix_prompt = f"Fix this Python error:\n{err['error']}\n\nFile: {err['file']}\nOutput ONLY the fixed complete file. No explanation."
                try:
                    res = self._engine_chat(
                        model=self.models.text_model,
                        messages=[{"role": "user", "content": fix_prompt}],
                        stream=False
                    )
                    fixed = res.get("message", {}).get("content", "")
                    result = self.edit_file_diff(err["file"], fixed)
                    c.print(f"[green]{result}[/green]")
                except Exception as e:
                    show_error(f"Auto-fix failed: {e}")
