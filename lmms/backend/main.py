import os
import sys
import threading
import time
import requests
import secrets
import subprocess
import asyncio
import websockets
import json
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from lmms.backend.memory.persona import get_persona, auto_extract_persona
from lmms.backend.tools.search import web_search
from lmms.backend.tools.browser import BrowserTool
from lmms.backend.tools.files import FileTool
from lmms.backend.tools.terminal import TerminalTool
from lmms.backend.tools.app_launcher import AppLauncherTool
from lmms.backend.tools.messenger import MessengerTool
from lmms.backend.config.config import ConfigManager
from lmms.backend.context.workspace_rules import load_workspace_rules
from lmms.backend.cli.diagnostics import collect_doctor_report, collect_status, render_doctor, render_status
from lmms.backend.cli.review import git_review, is_read_only_command, preview_file_change
from lmms.backend.tools.boundaries import is_within_workspace
from lmms.backend.cli.checkpoints import create_checkpoint, list_checkpoints, rollback_checkpoint
from lmms.backend.orchestration import OrchestrationPipeline, RequestTrace, IntentType

from lmms.backend.cli.scope_cli import cmd_scope_init, cmd_scope_status, cmd_scope_validate, cmd_scope_activate, cmd_scope_complete, cmd_scope_export, cmd_scope_reset
from lmms.backend.security.report import generate_report
from lmms.backend.security.models import ToolRequest, ToolResult, PermissionResult
from lmms.backend.security.permission_manager import permission_manager
from lmms.backend.security.executor import executor
from lmms.backend.security.evidence import record_tool_evidence
from lmms.backend.cli.tools_cli import cmd_tools_status
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.formatted_text import HTML, ANSI
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import Completer, Completion


def _patched_ask(message, choices=None, default=None, **kwargs):
    import io
    sio = io.StringIO()
    c = Console(file=sio, force_terminal=True, color_system="standard")
    msg = message
    if choices:
        msg += f" \\[{'/'.join(choices)}]"
    if default:
        msg += f" (default: {default})"
    msg += ": "
    c.print(msg, end="")
    ansi_str = sio.getvalue()
    
    while True:
        ans = prompt(ANSI(ansi_str)).strip()
        if not ans and default is not None:
            return default
        if not choices or ans in choices:
            return ans
Prompt.ask = staticmethod(_patched_ask)  # type: ignore


try:
    from lmms.common.discovery import get_engine_url
    ENGINE_URL = get_engine_url(interactive=False)
except Exception:
    ENGINE_URL = os.environ.get("LMMS_ENGINE_URL", "http://localhost:11435")


def extract_active_model_from_stats(stats: dict) -> str | None:
    """Return the first active model from either the engine's legacy or current payload format."""
    if not isinstance(stats, dict):
        return None

    if isinstance(stats.get("models"), dict) and stats["models"]:
        return next(iter(stats["models"].keys()))

    loaded = stats.get("loaded_models")
    if isinstance(loaded, list) and loaded:
        return str(loaded[0])

    if isinstance(loaded, dict) and loaded:
        return str(next(iter(loaded.keys())))

    return None


def should_force_tool_mode(prompt: str) -> bool:
    """Return True only when the user is explicitly asking for a tool-driven agent action.

    Normal chat like 'hello', 'hi', or general Q&A should stay in direct-answer mode.
    """
    if not isinstance(prompt, str):
        return False

    cleaned = prompt.strip()
    if not cleaned:
        return False

    lowered = cleaned.lower()
    if lowered.startswith(("/", "@")):
        return False

    explicit_tool_signals = [
        "use browser.open_url",
        "browser.open_url",
        "browser.crawl_url",
        "crawl4ai",
        "browser.click_element",
        "browser.fill_form",
        "browser.scrape",
        "browser.scrape_live",
        "browser.type",
        "browser.press_key",
        "browser.get_interactive_dom",
        "browser.screenshot",
        "browser.scroll",
        "browser.open_authenticated",
        "app.launch",
        "app.list",
        "app.close",
        "os.launch_app",
        "message.send",
        "telegram.send_message",
        "send message",
        "send telegram",
        "desktop notification",
        "notify me",
        "launch app",
        "open app",
        "open browser",
        "fill form",
        "interactive dom",
        "web_search",
        "search the web",
        "use tool",
        "use tools",
        "read /",
        "write /",
        "[attached files]",
        "open url",
        "crawl_url",
        "crawl this",
        "inspect the site",
        "summarize file",
        "debug this project",
        "read the file",
        "search for",
        "find file",
        "run command",
        "terminal.run",
        "files.read",
        "files.write",
        "vector_db.search",
        "analyze this repo",
        "scan",
        "run it",
        "run the",
        "start the server",
        "start server",
        "localhost",
        "local host",
        "setup project",
        "set up project",
        "install deps",
        "install dependencies",
        "docker",
        "npm install",
        "pip install",
    ]
    if any(sig in lowered for sig in explicit_tool_signals):
        return True

    if len(cleaned.split()) <= 8 and any(word in lowered for word in [
        "hello", "hi", "hey", "thanks", "good morning", "good evening",
        "what is", "who are you", "how are you", "can you help", "who are",
    ]):
        return False

    # Tool-driven commands are typically imperative and task-like rather than casual chat.
    if any(keyword in lowered for keyword in ["read ", "write ", "search ", "open ", "run ", "debug ", "inspect ", "summarize ", "launch ", "notify ", "scrape ", "click ", "login "]):
        return True

    return False


_cli_session_auto_started = False


def check_engine_health() -> bool:
    clean_url = ENGINE_URL.rstrip("/")
    candidates = [f"{clean_url}/ping", f"{clean_url}/v1/health", f"{clean_url}/webhook"]
    if "127.0.0.1" not in clean_url and "localhost" not in clean_url:
        candidates.extend(["http://127.0.0.1:11435/ping", "http://127.0.0.1:11435/webhook"])

    for ep in candidates:
        try:
            resp = requests.get(ep, timeout=2.5)
            if resp.status_code == 200:
                return True
        except Exception:
            continue
    return False


def auto_start_engine() -> bool:
    global _cli_session_auto_started
    if check_engine_health():
        return True

    from lmms.api.service import wait_for_server_healthy, start_server_daemon, is_server_running

    # Check if daemon is already starting up and wait briefly
    if wait_for_server_healthy(timeout=2.0):
        return True

    if not is_server_running():
        try:
            start_server_daemon(port=11435, host="0.0.0.0", engine_tier=3, forever=False, initiator="cli")
            _cli_session_auto_started = True
        except Exception:
            pass

    # Wait up to 8 seconds for engine to complete init
    if wait_for_server_healthy(timeout=8.0):
        return True

    return check_engine_health()

def stop_local_engine():
    """Stops the local inference engine daemon to free 100% RAM & GPU VRAM."""
    try:
        requests.post("http://127.0.0.1:11435/v1/internal/shutdown", timeout=1.5)
    except Exception:
        pass
    try:
        import subprocess
        subprocess.run(["pkill", "-f", "llama-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "lmms-engine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def get_clean_model_display_name(model_key_or_name: str) -> str:
    """Returns a readable model name (e.g. 'nvidia/nemotron-3.5-super-vl-120b-a12b') instead of internal registry key."""
    if not model_key_or_name or model_key_or_name == "None":
        return "None"
    try:
        from lmms.backend.core.registry.online_models import OnlineModelRegistry
        m = OnlineModelRegistry.get_model(model_key_or_name)
        if m:
            return m.get("id") or m.get("name") or model_key_or_name
    except Exception:
        pass
    return model_key_or_name


async def ipc_handshake():
    token = os.environ.get("LMMS_INTERNAL_TOKEN")
    if not token:
        return False
        
    try:
        uri = "ws://localhost:11435/v1/internal/ws"
        async with websockets.connect(uri) as websocket:
            await websocket.send(token)
            response = await websocket.recv()
            if response == "HANDSHAKE_SUCCESS":
                print("[IPC] Successfully merged with Engine!")
                return True
            else:
                print(f"[IPC] Handshake failed: {response}")
                return False
    except Exception as e:
        # Engine might not have the WS endpoint up yet or at all
        pass
    return False

def start_api():
    print("Starting Backend OS API on port 11436...")
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI(title="LMMs Backend OS")
    
    @app.get("/v1/health")
    def health_check():
        return {"status": "Backend OS is running", "engine_connected": check_engine_health()}
        
    uvicorn.run(app, host="0.0.0.0", port=11436, log_level="warning")




import uuid
import re

class ObservationProcessor:
    @staticmethod
    def extract_state(raw_output: str, command_hint: str) -> dict:
        state = {}
        # Ports
        ports = re.findall(r'(?:port|listening on|http://[^:]+:)(\d{2,5})', raw_output, re.IGNORECASE)
        if ports: state['Runtime Ports'] = f"Active on {', '.join(list(set(ports)))}"
        
        # Errors
        error_lines = []
        for line in raw_output.splitlines():
            if re.search(r'(error|exception|traceback|failed|fatal|permission denied|command not found)', line, re.IGNORECASE):
                error_lines.append(line.strip())
        if error_lines: state['Last Error'] = error_lines[-1] # keep the last most relevant error
        
        # Files created/modified from pip
        if "pip install" in command_hint:
            state['Dependencies'] = "pip install completed/attempted"
            
        return state

    @staticmethod
    def process(raw_output: str, command_hint: str, exit_code: int = 0) -> tuple:
        """Returns (compact_output, obs_id)"""
        obs_id = f"obs_{str(uuid.uuid4())[:8]}"
        
        # Generous retention limit: code files, diffs, and AST maps must not be truncated
        MAX_RAW = 12000
        if len(raw_output) <= MAX_RAW:
            compact = f"[Level 0: Raw] [ID: {obs_id}]\n{raw_output}"
            final_obs = {
                "command": command_hint,
                "exit_code": exit_code,
                "stdout": compact
            }
            import json
            return json.dumps(final_obs, indent=2), obs_id

        # Only if output exceeds 12,000 chars, do intelligent compression
        lines = raw_output.splitlines()
        error_keywords = ['error', 'exception', 'traceback', 'failed', 'fatal', 'syntaxerror', 'indentationerror', 'permission denied']
        important_lines = []
        compressed_lines = []
        repetitive_counts = {}
        last_pattern = None
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            is_important = any(kw in stripped.lower() for kw in error_keywords)
            if is_important:
                important_lines.append(stripped)
                compressed_lines.append(stripped)
                last_pattern = None
                continue
                
            req_match = re.match(r'^(Requirement already satisfied:)(.*)', stripped)
            if req_match:
                pat = req_match.group(1)
                repetitive_counts[pat] = repetitive_counts.get(pat, 0) + 1
                if last_pattern != pat:
                    compressed_lines.append(f"...[{pat} <count_placeholder>]...")
                last_pattern = pat
                continue
                
            compressed_lines.append(stripped)
            last_pattern = None

        final_lines = []
        for line in compressed_lines:
            if '<count_placeholder>' in line:
                pat = line.split('<')[0].replace('...', '').strip()
                count = repetitive_counts.get(pat, 0)
                final_lines.append(f"[compressed] {count} x {pat}")
            else:
                final_lines.append(line)
                
        output_str = "\n".join(final_lines)
        
        if len(output_str) > 20000:
            head = "\n".join(final_lines[:150])
            tail = "\n".join(final_lines[-150:])
            seen_errs = set()
            dedup_errs = []
            for e in important_lines:
                if e not in seen_errs:
                    seen_errs.add(e)
                    dedup_errs.append(e)
            
            errs = "\n".join(dedup_errs[:50])
            output_str = f"[Level 3: Preserved Key Sections] [ID: {obs_id}]\n{head}\n\n...[Large Output Compacted: {len(lines)} lines total]...\n\n[Preserved Errors/Tracebacks]\n{errs}\n\n[Tail Content]\n{tail}"
        else:
            output_str = f"[Level 1: Output] [ID: {obs_id}]\n{output_str}"

        final_obs = {
            "command": command_hint,
            "exit_code": exit_code,
            "stdout": output_str
        }
        import json
        return json.dumps(final_obs, indent=2), obs_id


class ContextManager:
    def __init__(self, context_limit=8192, reserve=700, safety=200):
        self.context_limit = context_limit
        self.reserve = reserve
        self.safety = safety
        self.usable_context = context_limit - reserve - safety
        self.working_memory = {}

    def update_working_memory(self, state: dict):
        for key, val in state.items():
            self.working_memory[key] = val

    def get_working_memory_str(self) -> str:
        if not self.working_memory: return ""
        res = "## Working Memory (Current State)\n"
        for k, v in self.working_memory.items():
            res += f"- {k}: {v}\n"
        return res
        
    def check_and_prune(self, current_tokens: int, messages: list, count_tokens_fn, current_model: str, max_allowed: Optional[int] = None) -> list:
        limit = max_allowed if max_allowed is not None and max_allowed > 0 else self.usable_context
        # Dynamic check
        if current_tokens <= limit:
            return messages
            
        print(f"\n[dim]Context limit nearing (Tokens: {current_tokens}/{limit}), pruning observations and conversation history...[/dim]")
        
        # Pass 1: Prune intermediate tool observations
        while current_tokens > limit:
            obs_idx = -1
            for i, m in enumerate(messages):
                if m.get("role") == "user" and "<observation>" in str(m.get("content", "")):
                    obs_idx = i
                    break
                    
            if obs_idx != -1:
                content = str(messages[obs_idx].get("content", ""))
                state = ObservationProcessor.extract_state(content, "")
                self.update_working_memory(state)
                
                # Truncate aggressively to essential snippet first
                if len(content) > 300:
                    messages[obs_idx]["content"] = "<observation>\n...[Earlier tool observation summarized to save context window]...\n</observation>"
                else:
                    if obs_idx > 0 and messages[obs_idx-1].get("role") == "assistant":
                        messages.pop(obs_idx)
                        messages.pop(obs_idx-1)
                    else:
                        messages.pop(obs_idx)
                
                # Recompute tokens
                current_tokens = sum(count_tokens_fn(m["content"] if isinstance(m["content"], str) else str(m["content"]), current_model) for m in messages)
            else:
                break

        # Pass 2: If still overflowing, prune earliest non-system conversation turns
        while current_tokens > limit and len(messages) > 2:
            # Keep system prompt at [0] and latest user prompt at [-1]
            prune_idx = 1
            if messages[prune_idx].get("role") != "system":
                messages.pop(prune_idx)
                current_tokens = sum(count_tokens_fn(m["content"] if isinstance(m["content"], str) else str(m["content"]), current_model) for m in messages)
            else:
                break

        return messages


class CapabilityManager:
    def __init__(self):
        self.active_capabilities = {"core", "terminal", "files", "web", "apps", "messaging"}
        self.available_capabilities = {"web", "apps", "messaging"}
        
    def activate(self, cap: str):
        if cap in self.available_capabilities:
            self.active_capabilities.add(cap)
            return True
        return False
            
    def get_system_prompt_additions(self) -> str:
        prompt = ""
        if "web" in self.active_capabilities:
            prompt += (
                "## Browsing Private Sites & Authentication\n"
                "If the user asks you to fetch data from a private or authenticated website, DO NOT immediately ask for credentials.\n"
                "ALWAYS try to use `browser.open_url` or `browser.scrape_live` FIRST to navigate to the page and inspect the interactive DOM.\n"
                "If login is required, inspect interactive elements via `browser.get_interactive_dom`, fill credentials with `browser.fill_form`, and click the login button via `browser.click_element`.\n"
                "If a CAPTCHA or SSO authentication is needed, use `browser.open_authenticated` with `headless: false`.\n\n"
            )
        if "apps" in self.active_capabilities:
            prompt += (
                "## Desktop Application Launching\n"
                "You can launch desktop applications (Chrome, VLC, Calculator, VS Code, Spotify) or open files/URLs using `app.launch`.\n"
                "Apps run in detached background mode and will not freeze the terminal.\n\n"
            )
        if "messaging" in self.active_capabilities:
            prompt += (
                "## Notifications & Messaging\n"
                "You can send native desktop notifications or messages to Telegram/Discord/Slack webhooks using `message.send`.\n\n"
            )
        return prompt
        
    def filter_tools(self, tools_list: str) -> str:
        filtered = []
        for line in tools_list.splitlines():
            if not line.strip(): continue
            if "browser." in line or "web_search" in line:
                if "web" in self.active_capabilities:
                    filtered.append(line)
            elif "app." in line:
                if "apps" in self.active_capabilities:
                    filtered.append(line)
            elif "message." in line or "telegram." in line:
                if "messaging" in self.active_capabilities:
                    filtered.append(line)
            else:
                filtered.append(line)
        return "\n".join(filtered)



def robust_parse_tool_call(raw_tc: str) -> dict:
    """Robust universal parser that handles XML function tags, OpenAI function calling, raw JSON, and truncated syntax."""
    import re
    import json
    import ast

    if not raw_tc:
        return {}

    raw_tc = raw_tc.strip()

    # 1. XML-style function calling (Nemotron / Hermes / Qwen / Command-R)
    # Examples:
    # <function=files.list><kwargs>{"path":"..."}</parameter></function>
    # <function=terminal.run><parameter=command>ls -la</parameter></function>
    fn_match = re.search(r'<function(?:=|\s+name=[\"\']?)([^>\s\"\']+)[\"\']?>', raw_tc, re.IGNORECASE)
    if not fn_match:
        fn_match = re.search(r'<function>([^<]+)</function>', raw_tc, re.IGNORECASE)

    if fn_match:
        tool_name = fn_match.group(1).strip()
        kwargs = {}

        # Look for JSON payload in <kwargs> or <arguments>
        kw_json = re.search(r'<(?:kwargs|arguments)>(.*?)(?:</(?:kwargs|arguments)>|</parameter>|</function>|$)', raw_tc, re.DOTALL | re.IGNORECASE)
        if kw_json:
            j_str = kw_json.group(1).strip()
            j_obj = re.search(r'(\{.*\})', j_str, re.DOTALL)
            if j_obj:
                try:
                    kwargs = json.loads(j_obj.group(1), strict=False)
                except Exception:
                    pass

        # Look for <parameter=key>value</parameter>
        for p_m in re.finditer(r'<parameter(?:=|\s+name=[\"\']?)([^>\s\"\']+)[\"\']?>(.*?)(?:</parameter>|$)', raw_tc, re.DOTALL | re.IGNORECASE):
            k = p_m.group(1).strip()
            v = p_m.group(2).strip()
            if (v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']')):
                try:
                    v = json.loads(v, strict=False)
                except Exception:
                    pass
            kwargs[k] = v

        # Look for <parameter>\nkey\nvalue\n</parameter>
        if not kwargs:
            for p_m in re.finditer(r'<parameter>\s*([a-zA-Z_0-9]+)\s*\n\s*(.*?)\s*(?:</parameter>|$)', raw_tc, re.DOTALL | re.IGNORECASE):
                k = p_m.group(1).strip()
                v = p_m.group(2).strip()
                kwargs[k] = v

        if tool_name and tool_name not in ('<tool_name>', 'tool_name'):
            return {'tool': tool_name, 'kwargs': kwargs}

    # 2. Strip tags & markdown fences if present
    if '<tool_call>' in raw_tc:
        tc_m = re.search(r'<tool_call>\s*(.*?)\s*(?:</tool_call>|$)', raw_tc, re.DOTALL)
        if tc_m:
            raw_tc = tc_m.group(1).strip()
    if raw_tc.startswith('```json'):
        raw_tc = raw_tc[7:].strip()
    elif raw_tc.startswith('```'):
        raw_tc = raw_tc[3:].strip()
    if raw_tc.endswith('```'):
        raw_tc = raw_tc[:-3].strip()

    def normalize_payload(data: dict) -> dict:
        if not isinstance(data, dict):
            return {}
        # Format A: {"tool": "name", "kwargs": {...}}
        if "tool" in data:
            return {
                "tool": data["tool"],
                "kwargs": data.get("kwargs", {}) if isinstance(data.get("kwargs"), dict) else {}
            }
        # Format B: {"name": "...", "arguments": {...}} (OpenAI Function Calling)
        if "name" in data and ("arguments" in data or "parameters" in data):
            args = data.get("arguments", data.get("parameters", {}))
            if isinstance(args, str):
                try:
                    args = json.loads(args, strict=False)
                except Exception:
                    args = {"raw_arguments": args}
            return {
                "tool": data["name"],
                "kwargs": args if isinstance(args, dict) else {}
            }
        # Format C: {"function": {"name": "...", "arguments": {...}}}
        if "function" in data and isinstance(data["function"], dict):
            fn = data["function"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args, strict=False)
                except Exception:
                    pass
            return {
                "tool": fn.get("name", ""),
                "kwargs": args if isinstance(args, dict) else {}
            }
        # Format D: Direct function name as top-level key: {"files.read": {"path": "..."}}
        for k, v in data.items():
            if isinstance(v, dict) and any(sep in k for sep in [".", "_"]):
                return {"tool": k, "kwargs": v}
        return data

    # 3. Standard JSON parsing
    try:
        parsed = json.loads(raw_tc, strict=False)
        norm = normalize_payload(parsed)
        if norm.get("tool") and norm["tool"] not in ("<tool_name>", "tool_name"):
            return norm
    except Exception:
        pass

    # 4. JSON substring match
    j_sub = re.search(r'(\{.*\})', raw_tc, re.DOTALL)
    if j_sub:
        try:
            parsed = json.loads(j_sub.group(1), strict=False)
            norm = normalize_payload(parsed)
            if norm.get("tool") and norm["tool"] not in ("<tool_name>", "tool_name"):
                return norm
        except Exception:
            pass

    # 5. ast.literal_eval fallback with JS booleans
    try:
        s = re.sub(r'\btrue\b', 'True', raw_tc)
        s = re.sub(r'\bfalse\b', 'False', s)
        s = re.sub(r'\bnull\b', 'None', s)
        parsed = ast.literal_eval(s)
        norm = normalize_payload(parsed)
        if norm.get("tool") and norm["tool"] not in ("<tool_name>", "tool_name"):
            return norm
    except Exception:
        pass

    # 6. Regex fallback for tool/kwargs
    tool_match = re.search(r'"(?:tool|name)"\s*:\s*"([^"]+)"', raw_tc)
    if tool_match:
        t_name = tool_match.group(1).strip()
        if t_name not in ("<tool_name>", "tool_name"):
            kwargs = {}
            for param in ("path", "command", "query", "url", "content"):
                pm = re.search(rf'"{param}"\s*:\s*"([^"]*)"', raw_tc)
                if pm:
                    kwargs[param] = pm.group(1)
            return {"tool": t_name, "kwargs": kwargs}

    # 7. Repair trailing syntax
    trimmed = raw_tc.rstrip()
    for fix in ['"}}', '"}', '}}', '}']:
        try:
            parsed = json.loads(trimmed + fix, strict=False)
            norm = normalize_payload(parsed)
            if norm.get("tool") and norm["tool"] not in ("<tool_name>", "tool_name"):
                return norm
        except Exception:
            pass

    raise ValueError("Could not parse tool call as valid JSON.")


def run_cli():
    import nest_asyncio
    nest_asyncio.apply()
    console = Console()
    console.clear()

    def cli_heartbeat():
        import requests
        import time
        while True:
            try:
                requests.post("http://127.0.0.1:11435/v1/internal/ping", timeout=2)
            except Exception:
                pass
            time.sleep(5)
            

    from lmms.backend.core.registry.online_models import OnlineModelRegistry
    is_online_active = (OnlineModelRegistry.get_active_type() == "online" and OnlineModelRegistry.get_active_model() is not None)

    if is_online_active:
        active_online = OnlineModelRegistry.get_active_model()
        current_model = active_online.get("key")
        status = "[bold cyan]ONLINE (CLOUD)[/bold cyan]"
        stop_local_engine()
    else:
        engine_started = auto_start_engine()
        if engine_started and os.environ.get("LMMS_INTERNAL_TOKEN"):
            asyncio.run(ipc_handshake())
        status = "[bold green]ONLINE[/bold green]" if check_engine_health() else "[bold red]OFFLINE[/bold red]"
        if check_engine_health():
            t = threading.Thread(target=cli_heartbeat, daemon=True)
            t.start()

    
    # State tracking
    current_workspace = "None"
    last_ws_file = os.path.expanduser("~/.lmms/config/last_workspace.txt")
    if os.path.exists(last_ws_file):
        try:
            with open(last_ws_file, "r") as f:
                saved_ws = f.read().strip()
                if os.path.exists(saved_ws):
                    current_workspace = saved_ws
        except: pass

    if current_workspace != "None":
        ConfigManager().set("workspace_dir", current_workspace)
        
    current_model = "None"
    
    # Auto-detect current model
    if check_engine_health():
        try:
            config_path = os.path.expanduser("~/.lmms/config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r") as f:
                        cfg = json.load(f)
                        saved_model = cfg.get("chat_selected_model") or cfg.get("default_model")
                except:
                    saved_model = None

                r = requests.get(f"{ENGINE_URL}/v1/models/ps", timeout=2)
                stats = r.json()
                detected_model = extract_active_model_from_stats(stats)
                
                if saved_model:
                    current_model = saved_model
                    if detected_model != saved_model:
                        def _autoload_saved():
                            try:
                                requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": saved_model}, timeout=60)
                            except Exception:
                                pass
                        threading.Thread(target=_autoload_saved, daemon=True, name="CLI-ModelAutoLoader").start()
                elif detected_model:
                    current_model = detected_model
        except Exception:
            pass

    try:
        from lmms.backend.core.registry.online_models import OnlineModelRegistry
        if OnlineModelRegistry.get_active_type() == "online":
            active_online = OnlineModelRegistry.get_active_model()
            if active_online:
                current_model = active_online.get("key")
    except Exception:
        pass

    current_pair = "None"
    current_mode = "/fast"
    current_permission_level = "medium"
    show_thoughts = False
    planning_mode = False
    checkpoint_created_this_session = False

    def visible_cli_reply(text: str) -> str:
        display = text or ""
        if not show_thoughts:
            display = re.sub(r'<think>.*?(</think>|$)', '', display, flags=re.DOTALL).strip()
            display = re.sub(r'<thought>.*?(</thought>|$)', '', display, flags=re.DOTALL).strip()
            display = re.sub(r'<reasoning>.*?(</reasoning>|$)', '', display, flags=re.DOTALL).strip()
            if "</think>" in display:
                display = display.split("</think>", 1)[1].strip()
            if "</thought>" in display:
                display = display.split("</thought>", 1)[1].strip()
            if "</reasoning>" in display:
                display = display.split("</reasoning>", 1)[1].strip()
        display = re.sub(r'<tool_call>.*?(</tool_call>|$)', '', display, flags=re.DOTALL).strip()
        display = re.sub(r'<function[=>\s].*?(?:</function>|$)', '', display, flags=re.DOTALL | re.IGNORECASE).strip()
        return display
    
    # Init config files
    CONFIG_DIR = os.path.expanduser("~/.lmms/config")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    WORKSPACES_FILE = os.path.join(CONFIG_DIR, "workspaces.json")
    PAIRS_FILE = os.path.join(CONFIG_DIR, "pairs.json")
    if not os.path.exists(WORKSPACES_FILE):
        with open(WORKSPACES_FILE, "w") as f: json.dump({}, f)
    if not os.path.exists(PAIRS_FILE):
        with open(PAIRS_FILE, "w") as f: json.dump({}, f)
        
    # Tools Initialization
    browser_tool = BrowserTool()
    file_tool = FileTool()
    terminal_tool = TerminalTool()
    app_launcher = AppLauncherTool()
    messenger_tool = MessengerTool()
    
    # Smart Context & Dynamic Tool Orchestration Pipeline
    orchestration_pipeline = OrchestrationPipeline(engine_url=ENGINE_URL)
    orchestration_pipeline.executor.register_handler(
        "web_search",
        lambda **kwargs: web_search(kwargs.get("query", ""), kwargs.get("max_results", 24))
    )
    orchestration_pipeline.executor.register_handler(
        "browser.open_url",
        lambda **kwargs: browser_tool.open_url(kwargs.get("url", ""), headless=kwargs.get("headless", False))
    )
    orchestration_pipeline.executor.register_handler(
        "browser.get_interactive_dom",
        lambda **kwargs: browser_tool.get_interactive_dom(str(kwargs.get("url") or ""))
    )
    orchestration_pipeline.executor.register_handler(
        "browser.click_element",
        lambda **kwargs: browser_tool.click_element(
            selector=str(kwargs.get("selector") or kwargs.get("id") or ""),
            url=str(kwargs.get("url") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.fill_form",
        lambda **kwargs: browser_tool.fill_form(
            fields=kwargs.get("fields", {}),
            url=str(kwargs.get("url") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.type",
        lambda **kwargs: browser_tool.type_text(
            selector=str(kwargs.get("selector") or kwargs.get("id") or ""),
            text=str(kwargs.get("text") or ""),
            press_enter=bool(kwargs.get("press_enter", False)),
            url=str(kwargs.get("url") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.type_text",
        lambda **kwargs: browser_tool.type_text(
            selector=str(kwargs.get("selector") or kwargs.get("id") or ""),
            text=str(kwargs.get("text") or ""),
            press_enter=bool(kwargs.get("press_enter", False)),
            url=str(kwargs.get("url") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.press_key",
        lambda **kwargs: browser_tool.press_key(str(kwargs.get("key", "Enter")))
    )
    orchestration_pipeline.executor.register_handler(
        "browser.scrape_live",
        lambda **kwargs: browser_tool.scrape_live(
            url=str(kwargs.get("url") or ""),
            selector=str(kwargs.get("selector") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.scrape",
        lambda **kwargs: browser_tool.scrape_live(
            url=str(kwargs.get("url") or ""),
            selector=str(kwargs.get("selector") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.screenshot",
        lambda **kwargs: browser_tool.screenshot(
            save_path=str(kwargs.get("save_path", "/tmp/lmms_browser.png")),
            url=str(kwargs.get("url") or "")
        )
    )
    orchestration_pipeline.executor.register_handler(
        "browser.scroll",
        lambda **kwargs: browser_tool.scroll(kwargs.get("url", ""), kwargs.get("direction", "down"), kwargs.get("amount", 1000))
    )
    orchestration_pipeline.executor.register_handler(
        "files.read",
        lambda **kwargs: file_tool.read(kwargs.get("path", ""))
    )
    orchestration_pipeline.executor.register_handler(
        "files.write",
        lambda **kwargs: file_tool.write(kwargs.get("path", ""), kwargs.get("content", ""))
    )
    orchestration_pipeline.executor.register_handler(
        "app.launch",
        lambda **kwargs: app_launcher.launch(kwargs.get("app_name_or_target") or kwargs.get("app_name") or kwargs.get("target", ""), kwargs.get("args") or [])
    )
    orchestration_pipeline.executor.register_handler(
        "app.list",
        lambda **kwargs: app_launcher.list_apps(kwargs.get("filter_query", ""))
    )
    orchestration_pipeline.executor.register_handler(
        "app.close",
        lambda **kwargs: app_launcher.close_app(kwargs.get("app_name", ""))
    )
    orchestration_pipeline.executor.register_handler(
        "message.send",
        lambda **kwargs: messenger_tool.send(
            platform=kwargs.get("platform", "desktop"),
            message=kwargs.get("message", ""),
            recipient=kwargs.get("recipient")
        )
    )



    def check_permission(tool_name: str, kwargs: dict, current_workspace: str, current_perm_level: str) -> bool:
        nonlocal checkpoint_created_this_session
        
        # Backward compatibility for planning mode
        if planning_mode and tool_name in [
            "files.write", "browser.click_element", "browser.fill_form",
            "browser.type", "browser.type_text", "browser.press_key",
            "app.launch", "os.launch_app", "app.close", "message.send", "telegram.send_message"
        ]:
            console.print("[yellow]Planning mode is read-only. Use /apply before making changes.[/yellow]")
            return False

        if planning_mode and tool_name == "terminal.run" and not is_read_only_command(kwargs.get("command", "")):
            console.print("[yellow]Planning mode only permits read-only terminal commands. Use /apply before running this command.[/yellow]")
            return False
            
        req = ToolRequest(
            tool_name=tool_name,
            command_line=kwargs.get("command", ""),
            arguments=[],
            kwargs=kwargs,
            workspace=current_workspace,
            permission_level=current_perm_level
        )
        
        perm = permission_manager.check_permission(req)
        
        if not perm.allowed:
            console.print(f"[bold red]Tool Execution Denied:[/bold red] {perm.reason}")
            # Evidence recording handled in execution loop or executor
            return False
            
        if perm.requires_confirmation:
            console.print(f"[bold yellow]Tool Policy Requires Confirmation: {perm.reason}[/bold yellow]")
            approved = Prompt.ask(f"[bold yellow]Allow {tool_name} with args {kwargs}? (y/n)[/bold yellow]").lower() == "y"
            if not approved:
                return False

        # Workspace boundary check for files.write
        if tool_name == "files.write":
            path = kwargs.get("path", "")
            content = kwargs.get("content", "")
            eff_ws = current_workspace if current_workspace != "None" else os.getcwd()
            if not is_within_workspace(path, eff_ws):
                return Prompt.ask(f"[bold red]AI wants to write outside the active workspace: {path}. Allow? (y/n)[/bold red]").lower() == "y"

            diff = preview_file_change(path, content)
            console.print(Panel(diff, title=f"Proposed change: {path}", border_style="yellow"))
            approved = Prompt.ask("[bold yellow]Apply this file change? (y/n)[/bold yellow]").lower() == "y"
            if approved and not checkpoint_created_this_session:
                create_checkpoint(current_workspace, "Auto Checkpoint before write")
                checkpoint_created_this_session = True
            return approved
            
        return True

    import uuid
    import base64
    import re
    from rich._spinners import SPINNERS
    SPINNERS["lmms_wave"] = {
        "interval": 120,
        "frames": [
            ".  ", "·  ", "'  ", "·  ", ".  ",
            " . ", " · ", " ' ", " · ", " . ",
            "  .", "  ·", "  '", "  ·", "  .",
            " ◜ ", " ◝ ", " ◞ ", " ◟ ", " ◯ ",
            "  .", "  ·", "  '", "  ·", "  .",
            " . ", " · ", " ' ", " · ", " . ",
            ".  ", "·  ", "'  ", "·  ", ".  "
        ]
    }
    
    CHATS_DIR = os.path.expanduser("~/.lmms/chats")
    os.makedirs(CHATS_DIR, exist_ok=True)
    
    current_chat_id = str(uuid.uuid4())
    current_chat_name = "Untitled"
    chat_history = []
    
    def print_banner():
        console.print("[bold cyan]LMMS v1.0[/bold cyan] [dim]· powered by markanm[/dim]")
        console.print("[dim]Type 'exit' to quit. Type '/cl' for the full command list.[/dim]\n")

    _token_cache = {}
    
    def count_tokens_batch(texts: list[str], model_name: str) -> list[int]:
        uncached_indices = []
        uncached_texts = []
        results = [0] * len(texts)
        
        for i, text in enumerate(texts):
            h = hash(text)
            if (model_name, h) in _token_cache:
                results[i] = _token_cache[(model_name, h)]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                
        if uncached_texts:
            try:
                r = requests.post(f"{ENGINE_URL}/v1/tokenize", json={"model_name": model_name, "texts": uncached_texts}, timeout=2)
                if r.status_code == 200:
                    counts = r.json().get("token_counts", [len(t) // 3 for t in uncached_texts])
                    for idx, c in zip(uncached_indices, counts):
                        results[idx] = c
                        _token_cache[(model_name, hash(texts[idx]))] = c
                    return results
            except: pass
            
            # Fallback
            for idx, text in zip(uncached_indices, uncached_texts):
                c = len(text) // 3
                results[idx] = c
                _token_cache[(model_name, hash(text))] = c
                
        return results

    def count_tokens(text: str, model_name: str) -> int:
        return count_tokens_batch([text], model_name)[0]

    _context_budget_cache = {}

    def get_context_budget(model_name: str):
        if model_name in _context_budget_cache:
            return _context_budget_cache[model_name]
        try:
            r = requests.get(f"{ENGINE_URL}/v1/model/context", params={"model_name": model_name}, timeout=1)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    n_ctx = data.get("context_length", 8192)
                    if n_ctx <= 0:
                        n_ctx = 8192
                    reserve = int(n_ctx * 0.18)
                    res = (n_ctx, reserve, n_ctx - reserve)
                    _context_budget_cache[model_name] = res
                    return res
        except: pass
        res = (8192, int(8192 * 0.18), int(8192 * 0.82))
        _context_budget_cache[model_name] = res
        return res

    print_banner()

    # --- CLI Auto-Complete & Session Setup ---
    command_dict = {
        "/fast": "Fast and concise AI mode",
        "/deep": "Deep reasoning AI mode",
        "/code": "Code generation mode",
        "/research": "Research and analysis mode",
        "/ml": "Switch active model",
        "/folder": "Open workspace folder",
        "/read": "Read file to context",
        "/chat": "Manage chats",
        "/pair": "Manage agent pairs",
        "/cl": "Show command list",
        "/stop": "Stop the engine",
        "/scope": "Manage authorized security scopes",
        "/tools": "View security tool status and permissions",
        "/report": "Generate security engagement report",
        "/plan": "Switch to Planning mode",
        "/apply": "Apply planned changes",
        "/review": "Review git diff for current workspace",
        "/status": "Show engine and workspace status",
        "/doctor": "Run diagnostics on engine",
        "/checkpoint": "Create a workspace checkpoint",
        "/checkpoints": "List workspace checkpoints",
        "/rollback": "Rollback workspace to a checkpoint",
        "/undo": "Undo the last action",
        "/redo": "Redo the last undone action",
        "/workspace": "Manage workspaces",
        "/reboot": "Restart the CLI and Engine",
        "/perm": "Set or view permission tiers: sandboxed, low, medium, or full",
        "/worktree": "Git worktree isolation (/worktree on|off|status|diff|apply|discard)",
        "/mcp": "Model Context Protocol tools, servers, and live dashboard",
        "/voice": "Full interactive voice mode with wave animation [F4]",
        "/mic": "Record audio directly from microphone",
        "exit": "Quit CLI",
        "clear": "Clear screen"
    }

    class CommandCompleter(Completer):
        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor()
            text = document.text
            
            if text.startswith("lmms pull ") or text.startswith("pull ") or text.startswith("/pull "):
                search_term = text.split("pull ", 1)[1]
                if len(search_term) >= 2:
                    try:
                        from huggingface_hub import HfApi
                        api = HfApi()
                        
                        # Apply mapping for common tags
                        mapped_term = search_term.replace(":", "-").lower()
                        KNOWN_MODELS = {
                            "qwen3-8b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                            "qwen3": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                            "gemma": "bartowski/gemma-2-9b-it-GGUF",
                            "llama3": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
                            "llama3-8b": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF"
                        }
                        
                        # If exact match in known models, return just that
                        if mapped_term in KNOWN_MODELS:
                            yield Completion(KNOWN_MODELS[mapped_term], start_position=-len(search_term), display_meta="Known Model")
                        else:
                            models = list(api.list_models(search=mapped_term, filter="gguf", limit=10, sort="downloads"))
                            for m in models:
                                yield Completion(m.id, start_position=-len(search_term), display_meta=f"{m.downloads} DLs")
                    except Exception:
                        pass
                return

            if word.startswith("/") or document.text.startswith("/"):
                for cmd, desc in command_dict.items():
                    if cmd.startswith(word):
                        # Truncate desc if needed
                        yield Completion(cmd, start_position=-len(word), display_meta=desc[:60])

    from prompt_toolkit.completion import ThreadedCompleter
    from prompt_toolkit.key_binding import KeyBindings
    kb = KeyBindings()

    @kb.add('f4')
    def _(event):
        event.app.current_buffer.text = '/voice'
        event.app.current_buffer.validate_and_handle()

    @kb.add('c-a')
    def _(event):
        # Select all text
        b = event.app.current_buffer
        b.cursor_position = 0
        b.start_selection()
        b.cursor_position = len(b.text)

    @kb.add('c-z')
    def _(event):
        # Undo last action
        event.app.current_buffer.undo()

    _cached_engine_health = [check_engine_health()]

    def get_bottom_toolbar():
        from lmms.backend.core.registry.online_models import OnlineModelRegistry
        is_cloud_active = (OnlineModelRegistry.get_active_type() == "online")
        if is_cloud_active:
            status_color = "ansicyan"
            status_text = "ONLINE (CLOUD)"
        else:
            is_online = _cached_engine_health[0]
            status_color = "ansigreen" if is_online else "ansired"
            status_text = "ONLINE" if is_online else "OFFLINE"
        
        display_m = get_clean_model_display_name(current_model)
        return HTML(
            f' <ansigray>Engine:</ansigray> <{status_color}>{status_text}</{status_color}> │ '
            f'<ansigray>Model:</ansigray> <ansigreen>{display_m}</ansigreen> │ '
            f'<ansigray>Mode:</ansigray> <ansicyan>{current_mode}</ansicyan> │ '
            f'<ansigray>Workspace:</ansigray> <ansigreen>{current_workspace}</ansigreen> │ '
            f'<ansigray>Perms:</ansigray> <ansicyan>{current_permission_level}</ansicyan> │ '
            f'<ansiyellow>[F4]</ansiyellow> <ansigray>🎙️ Voice</ansigray> '
        )

    session = PromptSession(
        completer=ThreadedCompleter(CommandCompleter()),
        complete_while_typing=True,
        bottom_toolbar=get_bottom_toolbar,
        key_bindings=kb,
        reserve_space_for_menu=8
    )

    def _health_poller():
        import time
        while True:
            time.sleep(2)
            try:
                from lmms.backend.core.registry.online_models import OnlineModelRegistry
                if OnlineModelRegistry.get_active_type() == "online":
                    continue
            except Exception:
                pass
            new_health = check_engine_health()
            if new_health != _cached_engine_health[0]:
                _cached_engine_health[0] = new_health
                try:
                    if hasattr(session, "app") and session.app and hasattr(session.app, "loop") and session.app.loop:
                        session.app.loop.call_soon_threadsafe(session.app.invalidate)
                except Exception:
                    pass

    threading.Thread(target=_health_poller, daemon=True, name="CLI-Health-Poller").start()
    # ----------------------------------------
    
    context_manager = ContextManager()
    cap_manager = CapabilityManager()
    vsession = None

    while True:
        voice_mode_active = False
        vsession = None
        try:
            with patch_stdout():
                cmd = session.prompt(HTML('<ansicyan>❯</ansicyan> ')).strip()

            # --- Audio & Mic Logic ---
            if not cmd:
                continue

            cmd_raw = cmd.lower()
            if cmd_raw in ["/mic", "/voice"]:
                import platform
                if platform.system() == "Windows":
                    console.print("[yellow]Microphone/Voice recording natively on Windows is not yet supported. Please use text input.[/yellow]")
                    continue
                    
                import speech_recognition as sr
                import select
                import termios
                import tty
                from lmms.backend.voice import VoiceSession
                
                vsession = VoiceSession()
                voice_mode_active = True
                vsession.start_animation("Listening... (Press ENTER to stop, Ctrl+C to cancel)")
                
                p = subprocess.Popen(["arecord", "-f", "cd", "-t", "wav", "-q", "/tmp/lmms_mic.wav"])
                
                interrupted = False
                old_settings = None
                try:
                    old_settings = termios.tcgetattr(sys.stdin)
                    tty.setcbreak(sys.stdin.fileno())
                    while True:
                        if select.select([sys.stdin], [], [], 0.05)[0]:
                            c = sys.stdin.read(1)
                            if c in ('\n', '\r'):
                                break
                            elif c == '\x03':  # Ctrl+C pressed
                                interrupted = True
                                break
                except (KeyboardInterrupt, Exception):
                    interrupted = True
                finally:
                    if old_settings is not None:
                        try:
                            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        except Exception:
                            pass
                    try:
                        p.terminate()
                        p.wait(timeout=1)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
                    
                if interrupted:
                    vsession.stop_animation()
                    voice_mode_active = False
                    console.print("\n[yellow]Voice mode cancelled.[/yellow]")
                    continue
                
                vsession.update_status("Transcribing voice...")
                
                r = sr.Recognizer()
                try:
                    with sr.AudioFile("/tmp/lmms_mic.wav") as source:
                        audio_data = r.record(source)
                    transcribed = r.recognize_google(audio_data)  # type: ignore
                except Exception as e:
                    vsession.stop_animation()
                    voice_mode_active = False
                    console.print(f"[red]Could not understand audio: {e}[/red]")
                    continue
                    
                cmd = transcribed
                if cmd_raw == "/mic":
                    vsession.stop_animation()
                    console.print(f"[bold cyan]Transcribed:[/bold cyan] {cmd}")
                    voice_mode_active = False
                else:
                    vsession.set_heard(cmd)   # Show what user said inside the User Box
                    vsession.update_status("Thinking...")
                    voice_mode_active = True
            elif cmd.strip("'\"").endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a")):
                file_path = cmd.strip("'\"")
                import speech_recognition as sr
                if os.path.exists(file_path):
                    console.print(f"[dim]Transcribing audio file: {file_path}...[/dim]")
                    r = sr.Recognizer()
                    try:
                        with sr.AudioFile(file_path) as source:
                            audio_data = r.record(source)
                        cmd = r.recognize_google(audio_data)  # type: ignore
                        console.print(f"[bold cyan]Transcribed:[/bold cyan] {cmd}")
                    except Exception as e:
                        console.print(f"[red]Could not transcribe audio (ensure it's a valid WAV/FLAC/AIFF): {e}[/red]")
                        continue
            # --------------------------

            if not cmd:
                continue
                
            if cmd.startswith("lmms "):
                cmd = cmd[5:].strip()

            parts = cmd.split()
            base_cmd = parts[0]

            if cmd in ["exit", "quit", "clear", "/reboot", "reboot"]:
                if cmd == "clear":
                    console.clear()
                    print_banner()
                    continue
                if cmd in ["/reboot", "reboot"]:
                    console.print("[yellow]Initiating system reboot...[/yellow]")
                    try:
                        requests.post("http://127.0.0.1:11435/v1/internal/shutdown", timeout=2)
                    except:
                        pass
                    sys.exit(42)

                break
                
            elif base_cmd == "/thinking":
                show_thoughts = not show_thoughts
                state_str = "ENABLED" if show_thoughts else "DISABLED"
                console.print(f"[bold green]Thought process visibility is now {state_str}.[/bold green]")

            elif base_cmd == "/plan":
                planning_mode = True
                current_mode = "/plan"
                console.print("[bold cyan]Planning mode enabled. LMMs can inspect, but cannot edit or run mutating commands. Use /apply when you approve the plan.[/bold cyan]")

            elif base_cmd == "/apply":
                planning_mode = False
                current_mode = "/code"
                checkpoint_created_this_session = False
                console.print("[bold green]Apply mode enabled. LMMs will show a diff and ask before each file change.[/bold green]")

            elif base_cmd == "/review":
                review = git_review(current_workspace)
                if not review["available"]:
                    console.print(f"[yellow]{review['message']}[/yellow]")
                else:
                    console.print(Panel(review["stat"], title="Git Diff Summary", border_style="cyan"))
                    color = "green" if review["clean"] else "red"
                    console.print(f"[{color}]Diff check: {review['check']}[/{color}]")

            elif base_cmd == "/cl":
                console.print("\n[bold yellow]=== LMMs Complete Command List ===[/bold yellow]")
                console.print("""
[bold cyan]╭──────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                    [bold white]LMMs AI Operating System[/bold white]                  [bold cyan]│[/bold cyan]
[bold cyan]╰──────────────────────────────────────────────────────────────╯[/bold cyan]

[bold magenta]🧠 Core AI & Interaction[/bold magenta]
  [green]/fast, /deep, /code[/green]      Switch reasoning modes
  [green]/vision, /mic, /voice[/green]     Use vision OCR, microphone, and interactive voice [F4]
  [green]/addmodel[/green]                  Open PyQt6 GUI to add online models & webhooks
  [green]/ml[/green]                        Swap between offline and online models
  [green]/chat, /newchat[/green]          Manage conversation threads

[bold magenta]💻 Autonomous Coding Workflow[/bold magenta]
  [green]/plan, /apply, /review[/green]   Plan and execute code changes
  [green]/checkpoint, /rollback[/green]   Save states and rollback mistakes
  [green]/undo, /redo[/green]             Instantly revert AI file edits
  [green]/status, /doctor[/green]         System and project health checks

[bold magenta]🛡️  Workspace & Security[/bold magenta]
  [green]/scope init|status[/green]       Manage strict workspace boundaries
  [green]/tools list[/green]              View allowed system/terminal tools
  [green]/report[/green]                  Generate security audit of AI actions
  [green]/workspace, /folder[/green]      Manage and open projects

[bold magenta]⚙️  Engine & Local Models[/bold magenta]
  [green]lmms pull <model>[/green]          Download a model from HuggingFace
  [green]lmms run <model>[/green]           Start a model directly
  [green]lmms ps, stop, rm[/green]        View active, stop, or delete models
  [green]lmms set --cli[/green]            Change default launch mode

[dim]For full help, type any command followed by --help[/dim]
""")
                console.print("[bold yellow]==================================[/bold yellow]\n")

            # -------------------------------------
            # COMMAND ROUTING
            # -------------------------------------
            elif base_cmd in ["/stop", "--stop", "stop engine"]:
                console.print("[dim]Stopping engine...[/dim]")
                subprocess.run("pkill -f 'lmms.lmmsengine.main server'", shell=True)
                console.print("[bold green]Engine stopped![/bold green]")
                
            elif base_cmd == "/read" and len(parts) > 1:
                file_path = parts[1]
                if current_workspace != "None":
                    file_path = os.path.join(current_workspace, file_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read(5000)
                    console.print(f"[green]Successfully read {parts[1]}. Content added to AI context.[/green]")
                    chat_history.append({"role": "user", "content": f"Here is the content of {parts[1]}:\\n```\\n{content}\\n```\\nPlease analyze this."})
                    chat_history.append({"role": "assistant", "content": f"I have read {parts[1]}. What would you like to know about it?"})
                except Exception as e:
                    console.print(f"[red]Failed to read file: {e}[/red]")
                    
            elif base_cmd == "/workspace" or base_cmd == "/folder":
                try:
                    with open(WORKSPACES_FILE, "r") as f: workspaces = json.load(f)
                except: workspaces = {}
                
                if base_cmd == "/folder":
                    folder_path = ""
                    if len(parts) > 1:
                        folder_path = parts[1]
                    else:
                        try:
                            console.print("[dim]Opening native file manager...[/dim]")
                            result = subprocess.run(["zenity", "--file-selection", "--directory", "--title=Select Workspace Folder"], capture_output=True, text=True)
                            if result.returncode == 0 and result.stdout.strip():
                                folder_path = result.stdout.strip()
                            else:
                                console.print("[yellow]Folder selection cancelled.[/yellow]")
                        except Exception as e:
                            console.print(f"[red]Could not open native file manager (Zenity): {e}[/red]")
                            folder_path = Prompt.ask("Enter folder path manually").strip()

                    if folder_path and os.path.exists(folder_path):
                        current_workspace = os.path.abspath(folder_path)
                        ConfigManager().set("workspace_dir", current_workspace)
                        ws_id = str(uuid.uuid4())[:8]
                        workspaces[ws_id] = {"path": current_workspace, "created_at": str(datetime.now())}
                        with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        with open(os.path.expanduser("~/.lmms/config/last_workspace.txt"), "w") as f: f.write(current_workspace)
                        console.print(f"[green]Workspace Opened:[/green] {current_workspace}")
                        
                        # Initialize Git for undo/redo
                        if not os.path.exists(os.path.join(current_workspace, ".git")):
                            subprocess.run(["git", "init"], cwd=current_workspace, capture_output=True)
                    elif folder_path:
                        console.print(f"[red]Folder does not exist: {folder_path}[/red]")
                        
                elif len(parts) > 1:
                    sub_cmd = parts[1]
                    if sub_cmd == "create" and len(parts) > 2:
                        path = parts[2]
                        os.makedirs(path, exist_ok=True)
                        ws_id = str(uuid.uuid4())[:8]
                        workspaces[ws_id] = {"path": path, "created_at": str(datetime.now())}
                        with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        console.print(f"[green]Workspace created and registered: {path}[/green]")
                    elif sub_cmd == "list":
                        console.print("[bold cyan]Registered Workspaces:[/bold cyan]")
                        for wid, info in workspaces.items():
                            console.print(f"[{wid}] {info['path']}")
                    elif sub_cmd == "open" and len(parts) > 2:
                        target = parts[2]
                        # check if it's an ID
                        if target in workspaces:
                            current_workspace = workspaces[target]["path"]
                        else:
                            current_workspace = target
                            ws_id = str(uuid.uuid4())[:8]
                            workspaces[ws_id] = {"path": target, "created_at": str(datetime.now())}
                            with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                        ConfigManager().set("workspace_dir", current_workspace)
                        console.print(f"[green]Workspace Opened:[/green] {current_workspace}")
                        if not os.path.exists(os.path.join(current_workspace, ".git")):
                            subprocess.run(["git", "init"], cwd=current_workspace, capture_output=True)
                    elif sub_cmd == "close":
                        current_workspace = "None"
                        console.print("[green]Workspace closed.[/green]")
                    elif sub_cmd == "delete" and len(parts) > 2:
                        wid = parts[2]
                        if wid in workspaces:
                            del workspaces[wid]
                            with open(WORKSPACES_FILE, "w") as f: json.dump(workspaces, f)
                            console.print(f"[green]Workspace {wid} deleted from registry.[/green]")
                        else:
                            console.print(f"[red]Workspace ID {wid} not found.[/red]")
                    elif sub_cmd == "restore" and len(parts) > 2:
                        # Restore logic using Git
                        console.print(f"[dim]Executing git checkout {parts[2]} in {current_workspace}[/dim]")
                        if current_workspace != "None":
                            res = subprocess.run(["git", "checkout", parts[2]], cwd=current_workspace, capture_output=True, text=True)
                            if res.returncode == 0:
                                console.print("[green]Workspace restored successfully.[/green]")
                            else:
                                console.print(f"[red]Failed to restore: {res.stderr}[/red]")
                        else:
                            console.print("[red]No active workspace to restore.[/red]")
                else:
                    console.print("[red]Usage: lmms workspace create|list|open|close|delete|restore[/red]")

            elif base_cmd == "/task":
                if current_workspace == "None":
                    console.print("[red]No active workspace to manage tasks.[/red]")
                    continue
                tasks_file = os.path.join(current_workspace, ".lmms_tasks.json")
                try:
                    with open(tasks_file, "r") as f: tasks = json.load(f)
                except: tasks = {}
                
                if len(parts) > 1:
                    sub_cmd = parts[1]
                    if sub_cmd == "create" and len(parts) > 2:
                        desc = " ".join(parts[2:])
                        tid = str(uuid.uuid4())[:6]
                        tasks[tid] = {"desc": desc, "status": "pending", "created": str(datetime.now())}
                        with open(tasks_file, "w") as f: json.dump(tasks, f)
                        console.print(f"[green]Task {tid} created.[/green]")
                    elif sub_cmd == "list":
                        console.print("[bold cyan]Active Tasks:[/bold cyan]")
                        for tid, t in tasks.items():
                            status_color = "green" if t["status"] == "complete" else "yellow" if t["status"] == "pending" else "red"
                            console.print(f"[{tid}] [{status_color}]{t['status']}[/{status_color}] {t['desc']}")
                    elif sub_cmd == "complete" and len(parts) > 2:
                        tid = parts[2]
                        if tid in tasks:
                            tasks[tid]["status"] = "complete"
                            with open(tasks_file, "w") as f: json.dump(tasks, f)
                            console.print(f"[green]Task {tid} marked complete.[/green]")
                    elif sub_cmd == "block" and len(parts) > 2:
                        tid = parts[2]
                        if tid in tasks:
                            tasks[tid]["status"] = "blocked"
                            with open(tasks_file, "w") as f: json.dump(tasks, f)
                            console.print(f"[red]Task {tid} marked blocked.[/red]")
                else:
                    console.print("[red]Usage: lmms task create|list|show|complete|block|timeline[/red]")

            elif base_cmd == "/git":
                if current_workspace == "None":
                    console.print("[red]No active workspace.[/red]")
                    continue
                if not os.path.exists(os.path.join(current_workspace, ".git")):
                    console.print("[red]Not a git repository.[/red]")
                    continue
                
                if len(parts) > 1:
                    sub_cmd = parts[1]
                    git_cmds = {
                        "status": ["git", "status", "-s"],
                        "commits": ["git", "log", "--oneline", "-n", "10"],
                        "branch": ["git", "branch"],
                    }
                    if sub_cmd in git_cmds:
                        res = subprocess.run(git_cmds[sub_cmd], cwd=current_workspace, capture_output=True, text=True)
                        console.print(res.stdout if res.stdout else res.stderr)
                    else:
                        console.print(f"[dim]Advanced git AI query: {sub_cmd}[/dim]")
                else:
                    console.print("[red]Usage: lmms git status|commits|branch|timeline|memory|summarize|explain[/red]")

            elif base_cmd == "/scope":
                if len(parts) > 1:
                    subcmd = parts[1]
                    if subcmd == "init":
                        cmd_scope_init(current_workspace)
                    elif subcmd == "status":
                        cmd_scope_status(current_workspace)
                    elif subcmd == "validate":
                        cmd_scope_validate(current_workspace)
                    elif subcmd == "activate":
                        cmd_scope_activate(current_workspace)
                    elif subcmd == "complete":
                        cmd_scope_complete(current_workspace)
                    elif subcmd == "reset":
                        cmd_scope_reset(current_workspace)
                    elif subcmd == "export":
                        cmd_scope_export(current_workspace, parts[2] if len(parts) > 2 else "scope_export.json")
                    else:
                        console.print("[red]Usage: /scope init|status|validate|activate|complete|reset|export[/red]")
                else:
                    cmd_scope_status(current_workspace)

            elif base_cmd == "/tools":
                if len(parts) > 1 and parts[1] in ["status", "list", "permissions"]:
                    cmd_tools_status()
                else:
                    cmd_tools_status()

            elif base_cmd == "/mcp":
                from lmms_mcp.cli import handle_mcp_cli
                handle_mcp_cli(parts[1:])

            elif base_cmd == "/report":
                console.print("[cyan]Triggering AI to generate a security report...[/cyan]")
                cmd = "Please generate a comprehensive security report summarizing our findings, the assets we discovered, and the timeline of actions. Use the security.generate_report tool."

            elif base_cmd == "/checkpoint":
                c_name = " ".join(parts[1:]) if len(parts) > 1 else "Manual Checkpoint"
                create_checkpoint(current_workspace, c_name)

            elif base_cmd == "/checkpoints":
                list_checkpoints(current_workspace)

            elif base_cmd == "/rollback":
                if len(parts) > 1:
                    rollback_checkpoint(current_workspace, parts[1])
                else:
                    console.print("[red]Usage: /rollback <id>[/red]")

            elif base_cmd == "/status":
                render_status(console, collect_status(current_workspace, ENGINE_URL))

            elif base_cmd == "/doctor":
                render_doctor(console, collect_doctor_report(current_workspace, ENGINE_URL))

            elif base_cmd in ["/pull", "/run", "/stop", "/ps", "/rm", "/list", "/info", "/search"] or base_cmd in ["-e", "-air", "--air"]:
                if base_cmd in ["-e", "-air", "--air"]:
                    engine_cmd = parts[1] if len(parts) > 1 else "status"
                elif base_cmd.startswith("/"):
                    engine_cmd = base_cmd[1:]
                else:
                    engine_cmd = base_cmd
                    
                console.print(f"[dim][EngineBridge] Forwarding command to Engine: {engine_cmd}[/dim]")
                if engine_cmd == "ps":
                    try:
                        r = requests.get(f"{ENGINE_URL}/v1/models/ps")
                        console.print(r.json())
                    except Exception as e:
                        console.print(f"[red]Failed to reach engine: {e}[/red]")
                elif engine_cmd == "list":
                    try:
                        r = requests.get(f"{ENGINE_URL}/v1/models/list")
                        console.print(r.json())
                    except Exception as e:
                        console.print(f"[red]Failed to reach engine: {e}[/red]")
                elif engine_cmd == "pull" and len(parts) > 1:
                    target = parts[2] if base_cmd == "-e" else parts[1]
                    console.print(f"[dim]Fetching available formats for {target}...[/dim]")
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", category=FutureWarning)
                            from huggingface_hub import HfApi
                        api = HfApi()
                        
                        if "/" in target:
                            repo_id = target
                        else:
                            search_term = target.replace(":", "-").lower()
                            models = list(api.list_models(search=search_term, filter="gguf", limit=10, sort="downloads"))
                            if not models:
                                console.print(f"[red]Could not find any GGUF repo matching {target}[/red]")
                                continue
                            repo_id = models[0].id
                            
                        repo_info = api.model_info(repo_id, files_metadata=True)
                        siblings = repo_info.siblings or []
                        gguf_files = [f for f in siblings if f.rfilename.endswith(".gguf")]
                        
                        if not gguf_files:
                            console.print(f"[red]No GGUF file found in {repo_id}[/red]")
                            continue
                            
                        gguf_files.sort(key=lambda x: x.size if x.size else 0)
                        
                        from prompt_toolkit.shortcuts import radiolist_dialog
                        values = []
                        for i, f in enumerate(gguf_files):
                            size_mb = (f.size / (1024 * 1024)) if f.size else 0
                            size_str = f"{size_mb/1024:.2f} GB" if size_mb > 1024 else f"{size_mb:.2f} MB"
                            values.append((f.rfilename, f"{f.rfilename} ({size_str})"))
                            
                        result = radiolist_dialog(
                            title=f"Pull {repo_id}",
                            text="Select a quantization format (Use UP/DOWN, press SPACE to select *, then TAB to Ok and ENTER):",
                            values=values
                        ).run()
                        
                        if result:
                            console.print(f"[dim]Requesting download for {result}...[/dim]")
                            r = requests.post(f"{ENGINE_URL}/v1/models/pull", json={"model_name": repo_id, "file_name": result})
                            if r.status_code == 200:
                                downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
                                with Progress(
                                    SpinnerColumn(),
                                    TextColumn("[progress.description]{task.description}"),
                                    BarColumn(bar_width=40),
                                    TaskProgressColumn(),
                                    TextColumn("{task.fields[status_info]}"),
                                    transient=True
                                ) as progress:
                                    task_id = progress.add_task(f"Downloading [cyan]{result}[/cyan]", total=100, status_info="...")
                                    try:
                                        while True:
                                            time.sleep(0.5)
                                            try:
                                                with open(downloads_file, "r") as f:
                                                    state = json.load(f)
                                                
                                                if repo_id in state:
                                                    status = state[repo_id].get("status", "")
                                                    pct = 0
                                                    status_info = status
                                                    if "%" in status:
                                                        try:
                                                            pct_str = status.split("%")[0].strip()
                                                            pct = int(pct_str)
                                                            status_info = status.split("%", 1)[1].strip()
                                                        except:
                                                            pass
                                                            
                                                    progress.update(task_id, completed=pct, status_info=status_info)
                                                    
                                                    if "100%" in status:
                                                        progress.update(task_id, completed=100)
                                                        console.print(f"[bold green]✓ Download complete: {repo_id}/{result}[/bold green]")
                                                        break
                                                    elif "failed" in status:
                                                        console.print(f"[red]Failed: {status}[/red]")
                                                        break
                                            except Exception:
                                                pass
                                    except KeyboardInterrupt:
                                        console.print("\n[yellow]Cancelling download...[/yellow]")
                                        try:
                                            with open(downloads_file, "r") as f: state = json.load(f)
                                            if repo_id in state:
                                                state[repo_id]["cancel"] = True
                                                state[repo_id]["status"] = "failed (cancelled by user)"
                                            with open(downloads_file, "w") as f: json.dump(state, f)
                                        except Exception:
                                            pass
                            else:
                                console.print(r.json())
                        else:
                            console.print("[yellow]Pull cancelled.[/yellow]")
                    except Exception as e:
                        console.print(f"[red]Failed to pull model: {e}[/red]")
                else:
                    console.print("[dim]Executing generic Engine bridge hook...[/dim]")

            elif base_cmd in ["/fast", "/deep", "/code", "/research", "/vision", "/image"]:
                current_mode = base_cmd
                console.print(f"[bold green]AI Mode switched to: {current_mode}[/bold green]")
                
            elif base_cmd in ["/explain", "/summarize", "/benchmark", "/memory", "/router"]:
                console.print(f"[dim][AI] Executing special command: {base_cmd}[/dim]")

            elif base_cmd == "/newchat":
                current_chat_id = str(uuid.uuid4())
                current_chat_name = "Untitled"
                chat_history.clear()
                try:
                    from lmms_sessions.cli import default_session_cli
                    new_s = default_session_cli.store.create_session(
                        session_id=current_chat_id,
                        title=current_chat_name,
                        metadata={"workspace": current_workspace}
                    )
                    default_session_cli.active_session_id = new_s.session_id
                except Exception:
                    pass
                console.print("[bold green]Started a new chat session![/bold green]")
                
            elif base_cmd == "/chat":
                if len(parts) == 1 or (len(parts) == 2 and parts[1] == "-l"):
                    console.print("[bold cyan]Saved Chats for this Workspace:[/bold cyan]")
                    chats = []
                    for f_name in os.listdir(CHATS_DIR):
                        if f_name.endswith(".json"):
                            try:
                                with open(os.path.join(CHATS_DIR, f_name), "r") as f:
                                    data = json.load(f)
                                    if data.get("workspace", "None") == current_workspace:
                                        chats.append((data.get("id"), data.get("name", "Untitled")))
                            except:
                                pass
                    if not chats:
                        console.print("[dim]No saved chats found.[/dim]")
                    else:
                        for i, (cid, cname) in enumerate(chats, 1):
                            console.print(f"{i}. [bold]{cname}[/bold] (ID: {cid[:8]})")
                            
                        if len(parts) == 2 and parts[1] == "-l":
                            choices = [str(i) for i in range(1, len(chats) + 1)] + ["cancel"]
                            choice = Prompt.ask("Select chat number to load", choices=choices, default="cancel")
                            if choice != "cancel":
                                idx = int(choice) - 1
                                target_id = chats[idx][0]
                                parts = ["/chat", target_id]  # Re-assign parts to trigger loading block
                            else:
                                console.print("[dim]Cancelled.[/dim]")
                                
                if len(parts) == 2 and parts[1] != "-l":
                    target_id = parts[1]
                    found = False
                    for f_name in os.listdir(CHATS_DIR):
                        if f_name.startswith(target_id) and f_name.endswith(".json"):
                            try:
                                with open(os.path.join(CHATS_DIR, f_name), "r") as f:
                                    data = json.load(f)
                                if data.get("workspace", "None") != current_workspace:
                                    console.print("[red]Chat belongs to a different workspace.[/red]")
                                    found = True
                                    break
                                current_chat_id = data.get("id")
                                current_chat_name = data.get("name", "Untitled")
                                chat_history.clear()
                                chat_history.extend(data.get("messages", []))
                                console.print(f"[bold green]Loaded chat: {current_chat_name}[/bold green]")
                                found = True
                                break
                            except:
                                pass
                    if not found:
                        console.print(f"[red]Chat not found with ID: {target_id}[/red]")

            elif base_cmd == "/addmodel":
                has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
                if has_display:
                    console.print("\n[bold cyan]🧠 Launching AI Models & Custom Webhook Hub (PyQt6 Desktop GUI)...[/bold cyan]")
                    try:
                        subprocess.Popen(
                            [sys.executable, "-m", "lmms.gui.dialogs.model_manager_dialog"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        console.print("[bold green]✓ Native GUI window opened![/bold green] [dim]Configure your API keys, Indian AI providers, or custom webhooks.[/dim]")
                        console.print("[dim]Use [/dim][bold cyan]/ml[/bold cyan][dim] anytime to view and switch between offline & online models.[/dim]\n")
                    except Exception as e:
                        console.print(f"[red]Failed to launch GUI: {e}[/red]")
                else:
                    console.print("\n[yellow]No graphical display detected ($DISPLAY / $WAYLAND_DISPLAY).[/yellow]")
                    console.print("[dim]You can configure models directly in [/dim][cyan]~/.lmms/config/online_models.json[/cyan]\n")

            elif base_cmd == "/ml":
                from lmms.backend.core.registry.online_models import OnlineModelRegistry
                online_models = OnlineModelRegistry.list_models(safe=True)
                active_online = OnlineModelRegistry.get_active_model()
                active_type = OnlineModelRegistry.get_active_type()

                # Get offline models
                offline_models = []
                try:
                    r = requests.get(f"{ENGINE_URL}/v1/models/list", timeout=3)
                    offline_models = [m['name'] for m in r.json().get("models", [])]
                except Exception:
                    models_dir = os.path.expanduser("~/.lmms/models")
                    if os.path.exists(models_dir):
                        offline_models = [f[:-5] for f in os.listdir(models_dir) if f.endswith(".gguf")]

                if len(parts) > 1:
                    if parts[1] == "-l":
                        console.print("\n[bold cyan]=== Configured AI Models ===[/bold cyan]")
                        console.print(f"[bold yellow]📁 Offline Models (Local GGUF / AirEngine):[/bold yellow]")
                        if offline_models:
                            for m in offline_models:
                                is_act = (m == current_model and active_type == "offline")
                                act_tag = " [bold green][ACTIVE][/bold green]" if is_act else ""
                                console.print(f"  • {m}{act_tag}")
                        else:
                            console.print("  [dim]No downloaded models. Use `lmms pull <model>`[/dim]")

                        console.print(f"\n[bold yellow]🌐 Online Models & Custom Webhooks:[/bold yellow]")
                        if online_models:
                            for om in online_models:
                                is_act = (om.get("key") == (active_online.get("key") if active_online else None)) and active_type == "online"
                                act_tag = " [bold green][ACTIVE][/bold green]" if is_act else ""
                                console.print(f"  • {om.get('name')} ({om.get('provider_name')}){act_tag} [dim]Endpoint: {om.get('base_url')}[/dim]")
                        else:
                            console.print("  [dim]No online models configured. Type `/addmodel` to add Anthropic, OpenAI, Sarvam AI, or Custom Webhooks.[/dim]\n")
                        continue

                    elif parts[1] == "-s" and len(parts) > 2:
                        requested = parts[2].lower()
                        # Check online models first
                        found_online = None
                        for om in online_models:
                            if requested in om.get("name", "").lower() or requested in om.get("id", "").lower() or requested in om.get("key", "").lower():
                                found_online = om
                                break

                        if found_online:
                            OnlineModelRegistry.set_active_model(found_online.get("key"), "online")
                            current_model = found_online.get("key")
                            console.print(f"[bold green]✓ Active model switched to: [Online] {found_online.get('name')}[/bold green]")
                            print_banner()
                            continue

                        # Check offline models
                        match = next((m for m in offline_models if requested in m.lower()), requested)
                        try:
                            r = requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": match}, timeout=180)
                            if r.status_code == 200:
                                current_model = match
                                OnlineModelRegistry.set_active_model(None, "offline")
                                console.print(f"[bold green]✓ Active model switched to: [Offline] {current_model}[/bold green]")
                            else:
                                console.print(f"[red]Failed to load offline model: {r.json()}[/red]")
                        except Exception as e:
                            console.print(f"[red]Error loading model: {e}[/red]")
                        print_banner()
                        continue

                # Interactive Category Selector:
                console.print("\n[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]")
                console.print("[bold cyan]│[/bold cyan]                 [bold white]LMMs Model Switcher (/ml)[/bold white]                   [bold cyan]│[/bold cyan]")
                console.print("[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]")
                curr_desc = f"[Online] {active_online.get('name')}" if (active_type == 'online' and active_online) else f"[Offline] {current_model}"
                console.print(f"[bold magenta]Current Active Model:[/bold magenta] [bold green]{curr_desc}[/bold green]\n")

                console.print(f"[1] 📁 Offline Models (Local GGUF / AirEngine) [dim]({len(offline_models)} available)[/dim]")
                console.print(f"[2] 🌐 Online Models (Anthropic, OpenAI, Sarvam AI, Webhooks) [dim]({len(online_models)} configured)[/dim]")
                console.print(f"[3] ➕ Add Online Model / Webhook (Launch /addmodel GUI)")
                console.print(f"[4] Cancel\n")

                cat_choice = Prompt.ask("Select category", choices=["1", "2", "3", "4"], default="1")
                if cat_choice == "1":
                    if not offline_models:
                        console.print("[yellow]No local models downloaded yet. Use `lmms pull <model>` (e.g. `lmms pull qwen3:8b`)[/yellow]")
                        continue
                    console.print("\n[bold cyan]Available Offline Models:[/bold cyan]")
                    for idx, m in enumerate(offline_models):
                        is_act = (m == current_model and active_type == "offline")
                        tag = " [bold green][ACTIVE][/bold green]" if is_act else ""
                        console.print(f"  [{idx+1}] {m}{tag}")
                    sel = Prompt.ask("Select offline model number", choices=[str(i+1) for i in range(len(offline_models))])
                    if sel:
                        selected_offline = offline_models[int(sel)-1]
                        try:
                            if not check_engine_health():
                                console.print("[dim cyan]⚡ Starting local offline engine daemon...[/dim cyan]")
                                auto_start_engine()
                            with console.status(f"[bold cyan]Loading {selected_offline}... (Press Ctrl+C to cancel)[/bold cyan]", spinner="dots"):
                                r = requests.post(f"{ENGINE_URL}/v1/models/load", json={"model_name": selected_offline}, timeout=180)
                            if r.status_code == 200:
                                current_model = selected_offline
                                OnlineModelRegistry.set_active_model(None, "offline")
                                console.print(f"[bold green]✓ Active model switched to: [Offline] {current_model}[/bold green]")
                            else:
                                console.print(f"[red]Failed to load: {r.json()}[/red]")
                        except Exception as e:
                            console.print(f"[red]Error loading model: {e}[/red]")

                elif cat_choice == "2":
                    if not online_models:
                        console.print("\n[yellow]No online models configured yet![/yellow]")
                        console.print("[dim]Type [/dim][bold cyan]/addmodel[/bold cyan][dim] to launch the GUI and configure Anthropic, OpenAI, Sarvam AI, or Custom Webhooks.[/dim]\n")
                        continue
                    console.print("\n[bold cyan]Configured Online Models & Webhooks:[/bold cyan]")
                    for idx, om in enumerate(online_models):
                        is_act = (om.get("key") == (active_online.get("key") if active_online else None)) and active_type == "online"
                        tag = " [bold green][ACTIVE][/bold green]" if is_act else ""
                        console.print(f"  [{idx+1}] {om.get('name')} [dim]({om.get('provider_name')})[/dim]{tag}")
                    sel = Prompt.ask("Select online model number", choices=[str(i+1) for i in range(len(online_models))])
                    if sel:
                        chosen_online = online_models[int(sel)-1]
                        OnlineModelRegistry.set_active_model(chosen_online.get("key"), "online")
                        current_model = chosen_online.get("key")
                        console.print(f"[bold green]✓ Active model switched to: [Online] {chosen_online.get('name')}[/bold green]")
                        stop_local_engine()
                        console.print("[dim green]⚡ Local offline engine stopped to free 100% RAM & GPU VRAM.[/dim green]")

                elif cat_choice == "3":
                    if bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                        subprocess.Popen([sys.executable, "-m", "lmms.gui.dialogs.model_manager_dialog"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                        console.print("[bold green]✓ Launched /addmodel GUI window![/bold green]")
                    else:
                        console.print("[yellow]No graphical display found. Configure in ~/.lmms/config/online_models.json[/yellow]")

            elif base_cmd == "/pair":
                try:
                    with open(PAIRS_FILE, "r") as f: pairs = json.load(f)
                except: pairs = {}
                
                if len(parts) > 1:
                    if parts[1] == "-n" and len(parts) > 3:
                        pair_id = parts[2]
                        if len(pairs) >= 4 and pair_id not in pairs:
                            console.print("[red]Max 4 pair presets allowed. Delete one first.[/red]")
                            continue
                        config = {}
                        for p in parts[3:]:
                            if ":" in p:
                                mod_type, mod_name = p.split(":", 1)
                                config[mod_type] = mod_name
                        pairs[pair_id] = config
                        with open(PAIRS_FILE, "w") as f: json.dump(pairs, f)
                        console.print(f"[green]Pair {pair_id} configured: {config}[/green]")
                    elif parts[1] == "-l":
                        console.print("[bold cyan]Active Pair Presets:[/bold cyan]")
                        for pid, cfg in pairs.items():
                            console.print(f"[{pid}] {cfg}")
                    elif parts[1] == "-d" and len(parts) > 2:
                        pid = parts[2]
                        if pid in pairs:
                            del pairs[pid]
                            with open(PAIRS_FILE, "w") as f: json.dump(pairs, f)
                            console.print(f"[green]Pair {pid} deleted.[/green]")
                            if current_pair == pid: current_pair = "None"
                        else:
                            console.print(f"[red]Pair {pid} not found.[/red]")
                    else:
                        pair_id = parts[1]
                        if pair_id in pairs:
                            current_pair = pair_id
                            console.print(f"[bold green]✓ Paired with {pair_id}![/bold green]")
                        else:
                            console.print(f"[red]Pair ID {pair_id} not found.[/red]")
                else:
                    console.print("Usage: /pair <id> | /pair -n <id> <config> | /pair -l | /pair -d <id>")

            elif base_cmd == "/perm":
                if len(parts) > 1:
                    level = parts[1].lower()
                    if level == "sandboxed":
                        from lmms_sandbox.runner import default_runner
                        s_status = default_runner.get_status()
                        if s_status["isolation_status"] == "NOT isolated":
                            console.print("[bold red]Cannot enable sandboxed mode: Neither Bubblewrap nor Landlock is available on this system.[/bold red]")
                            console.print("[yellow]To enable containment, install bubblewrap: sudo apt install bubblewrap[/yellow]")
                        else:
                            current_permission_level = "sandboxed"
                            console.print(f"[green]Permission level set to: sandboxed ({s_status['isolation_status']})[/green]")
                    elif level in ["low", "medium", "full"]:
                        current_permission_level = level
                        console.print(f"[green]Permission level set to: {current_permission_level}[/green]")
                    else:
                        console.print("[red]Invalid permission level. Use: sandboxed, low, medium, or full.[/red]")
                else:
                    console.print(f"[bold cyan]Current Permission Level:[/bold cyan] {current_permission_level}")
                    console.print("Available tiers:")
                    console.print("  • [yellow]sandboxed[/yellow]: Unprivileged bwrap/Landlock containment (isolated /home, masked secrets, workspace read-write only)")
                    console.print("  • [cyan]low[/cyan]: Read-only inspection; all mutating actions require confirmation")
                    console.print("  • [green]medium[/green]: Standard developer freedom inside workspace")
                    console.print("  • [magenta]full[/magenta]: Unrestricted system commands")

            elif base_cmd == "/worktree":
                from lmms_worktree.cli import handle_worktree_cli
                handle_worktree_cli(parts[1:], current_workspace)

            elif base_cmd == "/sessions":
                from lmms_sessions.cli import default_session_cli
                default_session_cli.handle_sessions(parts[1:])

            elif base_cmd == "/fork":
                from lmms_sessions.cli import default_session_cli
                default_session_cli.handle_fork(parts[1:])
                if default_session_cli.active_session_id and default_session_cli.active_session_id != current_chat_id:
                    current_chat_id = default_session_cli.active_session_id
                    chat_history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in default_session_cli.get_live_messages()
                    ]
                    sess_obj = default_session_cli.store.get_session(current_chat_id)
                    current_chat_name = sess_obj.title if sess_obj else "Forked Session"

            elif base_cmd == "/resume":
                from lmms_sessions.cli import default_session_cli
                default_session_cli.handle_resume(parts[1:])
                if default_session_cli.active_session_id and default_session_cli.active_session_id != current_chat_id:
                    current_chat_id = default_session_cli.active_session_id
                    chat_history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in default_session_cli.get_live_messages()
                    ]
                    sess_obj = default_session_cli.store.get_session(current_chat_id)
                    current_chat_name = sess_obj.title if sess_obj else "Resumed Session"

            elif base_cmd == "/rename":
                from lmms_sessions.cli import default_session_cli
                default_session_cli.handle_rename(parts[1:])
                sess_obj = default_session_cli.store.get_session(default_session_cli.active_session_id)
                if sess_obj:
                    current_chat_name = sess_obj.title

            elif base_cmd == "/compact":
                from lmms_sessions.cli import default_session_cli
                default_session_cli.handle_compact(parts[1:])

            elif base_cmd == "/mcp":
                from lmms_mcp.config import default_config_manager
                cfg = default_config_manager.load_config()
                sub = parts[1] if len(parts) > 1 else "list"
                if sub in ["list", "ls"]:
                    console.print("\n[bold cyan]=== Configured MCP Servers (~/.lmms/mcp.json) ===[/bold cyan]")
                    for sname, sinfo in cfg.mcp_servers.items():
                        status_str = "[green]ENABLED[/green]" if sinfo.enabled else "[dim]disabled[/dim]"
                        console.print(f" • [bold]{sname}[/bold] ({sinfo.transport}): {status_str} — {sinfo.command}")
                elif sub == "enable" and len(parts) > 2:
                    default_config_manager.set_server_enabled(parts[2], True)
                    console.print(f"[green]✓ Enabled MCP server '{parts[2]}'[/green]")
                elif sub == "disable" and len(parts) > 2:
                    default_config_manager.set_server_enabled(parts[2], False)
                    console.print(f"[yellow]✓ Disabled MCP server '{parts[2]}'[/yellow]")
                else:
                    console.print("Usage: /mcp list | /mcp enable <name> | /mcp disable <name>")

            elif base_cmd == "/metrics":
                from lmms.backend.telemetry.metrics import default_metrics
                summary = default_metrics.get_summary()
                console.print(Panel(json.dumps(summary, indent=2), title="LMMs OS Execution Metrics", border_style="green"))

            elif base_cmd == "/diff":
                ws = current_workspace if current_workspace != "None" else os.getcwd()
                res = subprocess.run(["git", "diff"], cwd=ws, capture_output=True, text=True)
                diff_out = res.stdout.strip()
                if not diff_out:
                    res_staged = subprocess.run(["git", "diff", "--cached"], cwd=ws, capture_output=True, text=True)
                    diff_out = res_staged.stdout.strip()
                if diff_out:
                    console.print(Panel(diff_out[:6000], title="Working Tree Diff", border_style="cyan"))
                else:
                    console.print("[dim]No uncommitted git diff in current workspace.[/dim]")

            elif base_cmd == "/checkpoint":
                from lmms.backend.cli.checkpoints import create_checkpoint, list_checkpoints, rollback_checkpoint
                ws = current_workspace if current_workspace != "None" else os.getcwd()
                sub = parts[1] if len(parts) > 1 else "create"
                if sub in ["list", "ls"]:
                    list_checkpoints(ws)
                elif sub in ["rollback", "restore"] and len(parts) > 2:
                    rollback_checkpoint(ws, parts[2])
                else:
                    cname = " ".join(parts[2:]) if len(parts) > 2 else (" ".join(parts[1:]) if len(parts) > 1 and parts[1] != "create" else "Manual Checkpoint")
                    create_checkpoint(ws, cname)

            elif base_cmd == "/review":
                from lmms.backend.agents.specialized.reviewer import ReviewerAgent
                from lmms.backend.agents.core_agents.agents.context import ExecutionContext
                from lmms.backend.tasks.core_tasks.tasks.task import Task, TaskStatus

                ws = current_workspace if current_workspace != "None" else os.getcwd()
                diff_cmd = ["git", "diff", "HEAD"]
                diff_res = subprocess.run(diff_cmd, cwd=ws, capture_output=True, text=True)
                diff_text = diff_res.stdout.strip()
                if not diff_text:
                    diff_res2 = subprocess.run(["git", "diff", "--cached"], cwd=ws, capture_output=True, text=True)
                    diff_text = diff_res2.stdout.strip()

                task_desc = " ".join(parts[1:]) if len(parts) > 1 else f"Review current uncommitted diff in {ws}"
                if diff_text:
                    task_desc += f"\n\nUncommitted Diff:\n{diff_text[:4000]}"

                async def run_review():
                    ctx = ExecutionContext(workspace_id=ws)
                    ctx.task = Task(id="review-1", title="Code Review", description=task_desc, status=TaskStatus.IN_PROGRESS)
                    ctx.selected_model = current_model
                    rev = ReviewerAgent()
                    console.print(f"[bold cyan]Running ReviewerAgent on workspace:[/bold cyan] {ws}")
                    async for chunk in rev.execute(ctx):
                        console.print(chunk, end="")

                asyncio.run(run_review())

                    
            elif base_cmd == "/agent":
                if len(parts) > 1:
                    sub_cmd = parts[1]
                    if sub_cmd == "list":
                        console.print("Not implemented yet.")
                    elif sub_cmd == "run" and len(parts) > 2:
                        task_name = " ".join(parts[2:])
                        from lmms.backend.agents.core_agents.agents.specialized.orchestrator import OrchestratorAgent
                        from lmms.backend.agents.core_agents.agents.context import ExecutionContext
                        from lmms.backend.tasks.core_tasks.tasks.task import Task, TaskStatus
                        
                        async def run_agent():
                            context = ExecutionContext()
                            context.task = Task(id="cli", title=task_name, description=task_name, status=TaskStatus.IN_PROGRESS)
                            orchestrator = OrchestratorAgent()
                            console.print(f"[bold cyan]Running Orchestrator for task:[/bold cyan] {task_name}")
                            try:
                                async for chunk in orchestrator.execute(context):
                                    console.print(chunk, end="")
                            except Exception as e:
                                console.print(f"\n[bold red]Error executing orchestrator:[/bold red] {e}")
                        
                        asyncio.run(run_agent())
                    else:
                        console.print(f"[cyan]Routing agent command '{sub_cmd}' to Backend...[/cyan]")
                else:
                    console.print("[red]Usage: lmms agent list|run|enable|disable[/red]")

            elif base_cmd == "/orchestrate":
                if len(parts) > 1:
                    task_name = " ".join(parts[1:])
                    from lmms.backend.agents.core_agents.agents.specialized.orchestrator import OrchestratorAgent
                    from lmms.backend.agents.core_agents.agents.context import ExecutionContext
                    from lmms.backend.tasks.core_tasks.tasks.task import Task, TaskStatus
                    
                    async def run_orchestrator():
                        context = ExecutionContext()
                        context.task = Task(id="cli", title=task_name, description=task_name, status=TaskStatus.IN_PROGRESS)
                        orchestrator = OrchestratorAgent()
                        console.print(f"[bold cyan]Orchestrating task:[/bold cyan] {task_name}")
                        try:
                            async for chunk in orchestrator.execute(context):
                                console.print(chunk, end="")
                        except Exception as e:
                            console.print(f"\n[bold red]Error orchestrating:[/bold red] {e}")
                    
                    asyncio.run(run_orchestrator())
                else:
                    console.print("[red]Usage: lmms orchestrate <task>[/red]")
                
            elif base_cmd in ["/undo", "/redo"]:
                from lmms.backend.context.checkpoint import get_turn_checkpoint_manager
                ws_root = current_workspace if current_workspace != "None" else os.getcwd()
                turn_mgr = get_turn_checkpoint_manager(ws_root)
                target_file = None
                force_undo = "--force" in parts or "-force" in parts
                clean_parts = [p for p in parts[1:] if p not in ["--force", "-force"]]
                if len(clean_parts) > 1 and clean_parts[0] in ["-f", "--file"]:
                    target_file = clean_parts[1]
                elif clean_parts and not clean_parts[0].startswith("-"):
                    target_file = clean_parts[0]

                if base_cmd == "/undo":
                    ok, msg = turn_mgr.undo(target_file=target_file, force=force_undo)
                    if ok:
                        console.print(f"[bold green]✓ {msg}[/bold green]")
                    else:
                        console.print(f"[yellow]{msg}[/yellow]")
                else:
                    ok, msg = turn_mgr.redo(target_file=target_file)
                    if ok:
                        console.print(f"[bold green]✓ {msg}[/bold green]")
                    else:
                        console.print(f"[yellow]{msg}[/yellow]")

            elif base_cmd.startswith("/"):
                if "/" in base_cmd[1:] or os.path.exists(cmd.strip("'\" ")):
                    pass # Let absolute file paths fall through to chat logic
                else:
                    console.print(f"[red]Unknown command: {base_cmd}. Type /cl for list.[/red]")
                    continue

            # Chat Prompt Fallback
            else:
                if cmd.startswith("@problem"):
                    console.print("[dim][Autonomous] @problem macro activated. Commencing automated debugging...[/dim]")
                    cmd = (
                        "I am encountering a problem in my codebase. "
                        "Please immediately use terminal.run to check `git status`, `git log -n 3`, "
                        "and use `grep` or view files to find any recent syntax errors, tracebacks, or bugs. "
                        "Once you find the issue, fix it autonomously using files.write or files.read, and test it. "
                        "After fixing, use git to commit the changes. "
                        f"User's extra context: {cmd.replace('@problem', '').strip()}"
                    )

                from lmms.backend.core.registry.online_models import OnlineModelRegistry
                is_online = OnlineModelRegistry.is_online_model(current_model) or (OnlineModelRegistry.get_active_type() == "online" and OnlineModelRegistry.get_active_model() is not None)

                if not is_online and not check_engine_health():
                    console.print("[red]Engine is offline. Cannot generate response.[/red]")
                    continue
                    
                if current_model == "None":
                    if is_online:
                        act_m = OnlineModelRegistry.get_active_model()
                        if act_m:
                            current_model = act_m.get("key")
                    if current_model == "None":
                        console.print("[yellow]No model is currently selected! Use '/ml' to select an offline or online model, or '/addmodel' to add one.[/yellow]")
                        continue
                    
                    
                # Trigger background persona extraction
                auto_extract_persona(cmd, current_model)

                # Smart Context & Dynamic Tool Orchestration Pipeline
                try:
                    req_t0 = time.time()
                    assembled_ctx, intent_res, selection_res, budget = orchestration_pipeline.prepare_request(
                        model_name=current_model,
                        user_query=cmd,
                        conversation_history=chat_history[-10:],
                        current_workspace=current_workspace,
                        permission_level=current_permission_level,
                        active_mode=current_mode
                    )

                    n_ctx = budget.context_limit
                    reserve = budget.output_reserve
                    available_for_input = budget.usable_context
                    messages = list(assembled_ctx.messages)

                    turn_start_time = time.time()
                    # RuleRouter Deterministic Execution Graph & Event Bus
                    try:
                        from lmms.backend.router.rule_router import RuleRouter
                        from lmms.backend.events.bus import get_event_bus
                        eb = get_event_bus()
                        rule_router = RuleRouter()
                        exec_graph = rule_router.route(cmd)
                        graph_summary = rule_router.execute_graph(exec_graph, context={"task": cmd, "workspace": current_workspace, "model": current_model})
                        eb.emit("execution_graph_planned", {
                            "intent": intent_res.intent.value,
                            "steps": [{"agent": s.agent_name, "action": s.action_type} for s in exec_graph.steps],
                            "execution_summary": graph_summary,
                        })
                        if graph_summary:
                            graph_block = "## Execution Graph\n" + "\n".join(f"- {line}" for line in graph_summary)
                            if messages and messages[0].get("role") == "system":
                                messages[0]["content"] += "\n\n" + graph_block
                            else:
                                messages.insert(0, {"role": "system", "content": graph_block})
                    except Exception:
                        pass

                    # Multimodal parsing
                    valid_img_paths = []
                    potential_path = cmd.strip("'\" ")
                    if os.path.exists(potential_path) and potential_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        valid_img_paths.append(potential_path)
                    else:
                        img_paths = re.findall(r"'(/[a-zA-Z0-9_./\-\s]+(?:\.[pP][nN][gG]|\.[jJ][pP][gG]|\.[jJ][pP][eE][gG]|\.[wW][eE][bB][pP]))'", cmd)
                        if not img_paths:
                            img_paths = re.findall(r"(/[a-zA-Z0-9_./\-\s]+(?:\.[pP][nN][gG]|\.[jJ][pP][gG]|\.[jJ][pP][eE][gG]|\.[wW][eE][bB][pP]))", cmd)
                        for p in img_paths:
                            if os.path.exists(p.strip()):
                                valid_img_paths.append(p.strip())

                    user_content = cmd
                    if valid_img_paths:
                        user_content = [{"type": "text", "text": cmd}]
                        for p in valid_img_paths:
                            try:
                                with open(p, "rb") as img_file:
                                    b64 = base64.b64encode(img_file.read()).decode("utf-8")
                                    user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
                            except Exception:
                                pass

                    if valid_img_paths and messages and messages[-1]["role"] == "user":
                        messages[-1]["content"] = user_content

                    # Calculate iteration limits based on verified token budget
                    avg_iter_cost = 600
                    max_possible = max(1, budget.remaining_tokens // avg_iter_cost)
                    MIN_ITERATIONS = 24
                    if current_mode == "/fast":
                        MAX_ITERATIONS = max(MIN_ITERATIONS, min(max_possible, 24))
                    else:
                        MAX_ITERATIONS = max(MIN_ITERATIONS, min(max_possible, 40))

                    iter_count = 0
                except Exception as e:
                    console.print(f"[red]Error preparing messages: {e}[/red]")
                    continue
                    
                # Track turn snapshot for atomic, non-destructive undo/redo
                try:
                    from lmms.backend.context.checkpoint import get_turn_checkpoint_manager
                    ws_root = current_workspace if current_workspace != "None" else os.getcwd()
                    turn_mgr = get_turn_checkpoint_manager(ws_root)
                    turn_mgr.start_turn(turn_id=str(uuid.uuid4())[:8], summary=cmd[:60])
                except Exception:
                    turn_mgr = None

                # Automatic ephemeral worktree isolation for coding turns in Git repositories
                is_auto_worktree = False
                try:
                    from lmms_worktree.manager import default_worktree_manager
                    if intent_res.intent == IntentType.CODING and current_workspace and current_workspace != "None":
                        if default_worktree_manager.is_git_repo(current_workspace) and not default_worktree_manager.get_session(current_workspace):
                            wt_session = default_worktree_manager.enable(current_workspace)
                            wt_session.is_auto_ephemeral = True
                            is_auto_worktree = True
                            console.print(f"[dim cyan]🔒 [Worktree] Ephemeral workspace active: {wt_session.worktree_dir}[/dim cyan]")
                except Exception:
                    is_auto_worktree = False

                reply = ""
                full_reply = ""
                executed_tool_calls = []
                search_tool_count = 0
                model_header_printed = False
                while iter_count < MAX_ITERATIONS:
                    iter_count += 1
                    
                    if True:
                        try:
                            # Context compaction & prompt budget enforcement across multi-turn tool observations
                            tok_count = sum(orchestration_pipeline.budget_manager.count_tokens(m["content"] if isinstance(m["content"], str) else str(m["content"]), current_model) for m in messages)
                            if tok_count > available_for_input:
                                compacted_msgs, _ = orchestration_pipeline.compactor.compact(
                                    messages=messages,
                                    usable_budget=available_for_input,
                                    current_prompt_tokens=tok_count,
                                    model_name=current_model
                                )
                                messages = list(compacted_msgs)
                            clean_messages = messages

                            # Apply AI Mode settings
                            req_temp = 0.5
                            req_top_p = 0.9
                            if current_mode == "/fast":
                                req_temp = 0.3
                                req_top_p = 0.8
                            elif current_mode == "/deep":
                                req_temp = 0.8
                                req_top_p = 0.95
                                if messages and messages[0]["role"] == "system" and "Think deeply" not in messages[0]["content"]:
                                    messages[0]["content"] += "\nThink deeply and step-by-step before answering."
                            elif current_mode == "/code":
                                req_temp = 0.2

                            # Inject warning if hitting iteration cap
                            if iter_count == MAX_ITERATIONS - 1:
                                messages.append({"role": "user", "content": "System Note: You are about to reach the maximum number of tool iterations (8/8). If you have not solved the problem, please output a final summary of what you tried and the current errors without calling more tools."})

                            # In voice mode: zero thinking, direct conversational answers
                            req_messages = clean_messages
                            req_think = show_thoughts
                            req_mode = current_mode.strip("/")
                            if voice_mode_active:
                                req_think = False
                                req_mode = "fast"
                                voice_instruction = "You are LMMs Voice Assistant. Speak directly, concisely, and conversationally in the user's language. STRICT: NEVER use <think> tags. NEVER output internal reasoning, analysis, or monologue. Begin immediately with your spoken answer in 1-2 short sentences."
                                voice_msg_copy = [dict(m) for m in clean_messages]
                                if voice_msg_copy and voice_msg_copy[0].get("role") == "system":
                                    voice_msg_copy[0]["content"] += f"\n\n{voice_instruction}"
                                else:
                                    voice_msg_copy.insert(0, {"role": "system", "content": voice_instruction})
                                req_messages = voice_msg_copy

                            from lmms.backend.core.registry.online_models import OnlineModelRegistry
                            is_online_call = OnlineModelRegistry.is_online_model(current_model) or (OnlineModelRegistry.get_active_type() == "online" and OnlineModelRegistry.get_active_model() is not None)

                            if is_online_call:
                                from lmms.backend.providers.online_client import OnlineModelClient
                                chunks_iterator = OnlineModelClient.stream_chat(
                                    model_name=current_model,
                                    messages=req_messages,
                                    temperature=req_temp,
                                    top_p=req_top_p,
                                    max_tokens=max(reserve, 4096),
                                    mode=req_mode,
                                    think=req_think
                                )
                                resp = None
                            else:
                                resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                                    "model_name": current_model,
                                    "messages": req_messages,
                                    "stream": True,
                                    "temperature": req_temp,
                                    "top_p": req_top_p,
                                    "repetition_penalty": 1.15,
                                    "mode": req_mode,
                                    "think": req_think,
                                    "max_tokens": max(reserve, 2048) if intent_res.intent == IntentType.CODING else reserve
                                }, stream=True, timeout=(10, 3600))
                                resp.raise_for_status()
                                chunks_iterator = resp.iter_lines()
                        except requests.exceptions.ReadTimeout:
                            console.print(f"\n[bold red]❌ Engine Error: Model took too long to load or server died unexpectedly.[/bold red]")
                            break
                        except requests.exceptions.HTTPError as e:
                            error_detail = str(e)
                            if e.response is not None:
                                try:
                                    error_detail = e.response.json().get("detail", str(e))
                                except Exception:
                                    pass
                            if "context length" in error_detail.lower() or "too large" in error_detail.lower() or "exceeded" in error_detail.lower():
                                console.print(f"\n[bold yellow]⚠️ Context Overflow detected! Auto-compacting with ContextCompactor...[/bold yellow]")
                                try:
                                    from lmms.backend.orchestration.compactor import ContextCompactor
                                    compactor = ContextCompactor(token_count_fn=count_tokens)
                                    messages, report = compactor.compact(
                                        messages,
                                        usable_budget=int(available_for_input * 0.75),
                                        current_prompt_tokens=int(available_for_input * 1.1),
                                        model_name=current_model
                                    )
                                    console.print(f"[dim yellow]⚡ Context compacted: saved ~{report.tokens_saved_estimate} tokens (observations pruned: {report.observations_pruned}).[/dim yellow]")
                                except Exception:
                                    for idx, m in enumerate(messages):
                                        if isinstance(m["content"], str) and "<observation>" in m["content"]:
                                            messages[idx]["content"] = m["content"][:1000] + "\n...[Force Truncated]\n</observation>"
                                iter_count -= 1
                                continue
                            console.print(f"\n[bold red]❌ Engine Error: {error_detail}[/bold red]")
                            break
                        except requests.exceptions.RequestException as e:
                            console.print(f"\n[bold red]❌ Error communicating with AI: {str(e)}[/bold red]")
                            break
                        except Exception as e:
                            console.print(f"\n[red]Error communicating with AI: {e}[/red]")
                            break
                            
                    full_reply = ""
                    try:
                        first_token = False
                        live_view = None
                        try:
                            last_refresh = time.time()
                            final_display = ""
                            leak_check_done = False

                            with console.status(f"[bold blue]{current_model}:[/bold blue]", spinner="lmms_wave") as spin_status:
                                for line_bytes in chunks_iterator:
                                    if not line_bytes:
                                        continue
                                        
                                    line_str = line_bytes.decode("utf-8")
                                    if line_str.startswith("data: "):
                                        data_str = line_str[6:]
                                        if data_str == "[DONE]": 
                                            break
                                        try:
                                            chunk = json.loads(data_str)
                                            if "error" in chunk:
                                                err_text = str(chunk["error"])
                                                if "context" in err_text.lower() or "exceed" in err_text.lower():
                                                    console.print(f"\n[bold yellow]⚠️ Context window exceeded during streaming! Auto-truncating earlier turns and retrying...[/bold yellow]")
                                                    # Prune aggressively and retry
                                                    messages = context_manager.check_and_prune(tok_count, messages, count_tokens, current_model, max_allowed=int(available_for_input * 0.75))
                                                    iter_count -= 1
                                                    full_reply = ""
                                                    break
                                                full_reply += f"\n\n❌ **Engine Error:** {err_text}"
                                                if live_view:
                                                    live_view.update(Panel(Markdown(full_reply), title=f"❌ {current_model} Error", border_style="red", padding=(1, 2), expand=False), refresh=True)
                                                else:
                                                    console.print(Panel(Markdown(full_reply), title=f"❌ {current_model} Error", border_style="red", padding=(1, 2), expand=False))
                                                break
                                                
                                            chunk_text = chunk.get("content", "")
                                            if not chunk_text and "choices" in chunk and chunk["choices"]:
                                                delta = chunk["choices"][0].get("delta", {})
                                                chunk_text = delta.get("content") or ""
                                            full_reply += chunk_text
                                            
                                            if voice_mode_active and vsession is not None:
                                                from lmms.backend.voice import extract_thoughts_and_response, stream_audio
                                                cur_thoughts, cur_spoken = extract_thoughts_and_response(full_reply)
                                                
                                                vsession.update_thoughts(cur_thoughts)
                                                vsession.update_ai_response(cur_spoken)
                                                
                                                if cur_spoken:
                                                    if not hasattr(vsession, "sentence_buffer"):
                                                        vsession.sentence_buffer = ""
                                                        vsession.update_status("Speaking...")
                                                    if not hasattr(vsession, "last_spoken_len"):
                                                        vsession.last_spoken_len = 0
                                                    if not hasattr(vsession, "first_chunk_sent"):
                                                        vsession.first_chunk_sent = False
                                                        
                                                    new_spoken = cur_spoken[vsession.last_spoken_len:]
                                                    vsession.last_spoken_len = len(cur_spoken)
                                                    
                                                    vsession.sentence_buffer += new_spoken
                                                    buf = vsession.sentence_buffer
                                                    
                                                    # Ultra-low latency voice start:
                                                    # Dispatch first 3-4 words or any punctuation break immediately
                                                    if not vsession.first_chunk_sent:
                                                        import re
                                                        clause_match = re.search(r'([,!?:;\n।])', buf)
                                                        words = buf.split()
                                                        if clause_match:
                                                            end_pos = clause_match.end()
                                                            completed = buf[:end_pos].strip()
                                                            if completed:
                                                                stream_audio(completed, voice="female")
                                                                vsession.sentence_buffer = buf[end_pos:].lstrip()
                                                                vsession.first_chunk_sent = True
                                                        elif len(words) >= 4:
                                                            completed = " ".join(words[:4])
                                                            stream_audio(completed, voice="female")
                                                            vsession.sentence_buffer = " ".join(words[4:]).lstrip()
                                                            vsession.first_chunk_sent = True
                                                    else:
                                                        # Subsequent sentences and clauses
                                                        if any(p in new_spoken for p in [".", "?", "!", "\n", "।", ","]):
                                                            import re
                                                            parts = re.split(r'([.?!।]\s+|\n|,\s+)', vsession.sentence_buffer)
                                                            if len(parts) > 1:
                                                                completed = "".join(parts[:-1]).strip()
                                                                if completed and len(completed) >= 3:
                                                                    stream_audio(completed, voice="female")
                                                                vsession.sentence_buffer = parts[-1].lstrip()
                                                elif cur_thoughts:
                                                    vsession.update_status("Thinking...")

                                            
                                            if not leak_check_done:
                                                if len(full_reply) < 80:
                                                    pass  # Buffer it, but STILL render it
                                                else:
                                                    cleaned = re.sub(r'^(?:The user says|According to identity rules|I\'ll output|We need to answer|Provide concise|You are a|Use internal knowledge)[\s\S]*?(?:No tool needed\.|Answer:|\n\n|Hello!)', '', full_reply, flags=re.IGNORECASE).strip()
                                                    if cleaned:
                                                        full_reply = cleaned
                                                    leak_check_done = True
                                                    
                                            display_reply = visible_cli_reply(full_reply)
                                            final_display = display_reply
                                            
                                            if display_reply and not first_token:
                                                first_token = True
                                                if not voice_mode_active:
                                                    spin_status.stop()
                                                    if not model_header_printed:
                                                        console.print(f"\n[bold cyan]Model : {get_clean_model_display_name(current_model)}[/bold cyan]")
                                                        model_header_printed = True
                                                    live_view = Live(Markdown(display_reply), console=console, refresh_per_second=15, auto_refresh=True)
                                                    live_view.start()
                                                
                                            if live_view and display_reply and not voice_mode_active:
                                                now = time.time()
                                                if now - last_refresh > 0.05:
                                                    live_view.update(Markdown(display_reply), refresh=True)
                                                    last_refresh = now
                                                else:
                                                    live_view.update(Markdown(display_reply), refresh=False)
                                        except Exception: 
                                            pass
                                
                                # Apply leak cleanup to fully completed full_reply if not done
                                if not leak_check_done:
                                    cleaned_reply = re.sub(r'^(?:The user says|According to identity rules|I\'ll output|We need to answer|Provide concise|You are a|Use internal knowledge)[\s\S]*?(?:No tool needed\.|Answer:|\n\n|Hello!)', '', full_reply, flags=re.IGNORECASE).strip()
                                    if cleaned_reply:
                                        full_reply = cleaned_reply
                                        
                                final_display = visible_cli_reply(full_reply)
                                    
                                # Force a final render
                                if final_display and live_view:
                                    live_view.update(Markdown(final_display), refresh=True)
                                elif full_reply and not first_token:
                                    spin_status.stop()
                                    pass  # Model thinking only — tool call will execute next
                        finally:
                            if live_view:
                                live_view.stop()
                            try:
                                if resp is not None:
                                    resp.close()
                            except:
                                pass

                    except KeyboardInterrupt:
                        if not check_engine_health():
                            msg = "\n\n[bold red]-- Engine process died unexpectedly during generation --[/bold red]"
                            full_reply += msg
                            console.print(Markdown(msg))
                        else:
                            full_reply += "\n\n[dim]-- Generation Interrupted by User --[/dim]"
                            console.print(Markdown("\n[dim]-- Generation Interrupted by User --[/dim]"))
                        reply = full_reply
                        # We break out of the tool iteration loop so it goes back to the user prompt
                        break
                                        
                    if not full_reply:
                        _tok_start = time.time()
                        msg_texts = [m.get("content", "") for m in messages if isinstance(m.get("content"), str)]
                        total_msg_cost = sum(count_tokens_batch(msg_texts, current_model))
                        _tok_end = time.time()

                        
                        if iter_count < MAX_ITERATIONS and total_msg_cost > available_for_input * 0.8:
                            console.print(f"\n[bold yellow]⚠️ Silent generation failure (context pressure). Auto-compacting with ContextCompactor...[/bold yellow]")
                            try:
                                from lmms.backend.orchestration.compactor import ContextCompactor
                                compactor = ContextCompactor(token_count_fn=count_tokens)
                                messages, report = compactor.compact(
                                    messages,
                                    usable_budget=int(available_for_input * 0.75),
                                    current_prompt_tokens=total_msg_cost,
                                    model_name=current_model
                                )
                                console.print(f"[dim yellow]⚡ Context compacted: saved ~{report.tokens_saved_estimate} tokens.[/dim yellow]")
                            except Exception:
                                for idx, m in enumerate(messages):
                                    if isinstance(m["content"], str) and "<observation>" in m["content"]:
                                        messages[idx]["content"] = m["content"][:500] + "\n...[Force Truncated]\n</observation>"
                            iter_count -= 1
                            continue

                        full_reply = "No response from AI."
                        clean_disp_name = get_clean_model_display_name(current_model)
                        console.print(f"\n[bold yellow]⚠️ {clean_disp_name}[/bold yellow]")
                        console.print(Markdown(full_reply))
                        reply = full_reply
                        break

                    # Check for tool call
                    force_tool_mode = should_force_tool_mode(cmd)
                    tool_call_match = re.search(r"<tool_call>\s*(.*?)\s*(</tool_call>|$)", full_reply, re.DOTALL)
                    
                    if not tool_call_match:
                        # Fallback 1: XML-style function call <function=...>...</function>
                        xml_fn_match = re.search(r'(<function[=>\s].*?(?:</function>|$))', full_reply, re.DOTALL | re.IGNORECASE)
                        if xml_fn_match:
                            tool_call_match = xml_fn_match

                    if not tool_call_match:
                        # Fallback 2: check if the reply contains a raw JSON tool call
                        try:
                            raw_json_match = re.search(r'(\{\s*"tool"\s*:\s*".*?"\s*,\s*"kwargs"\s*:.*?\})', full_reply, re.DOTALL)
                            if raw_json_match:
                                tool_call_match = raw_json_match
                        except Exception:
                            pass

                    # If the model emitted a tool_call but we're not in force_tool_mode,
                    # we STILL execute it — the model decided a tool is needed.
                    # We only suppress/strip tool calls when the reply is PURELY a tool call
                    # with NO other text AND the user's message is clearly conversational.
                    is_pure_tool_only = tool_call_match and not full_reply.replace(tool_call_match.group(0), "").strip()
                    is_casual_chat = not force_tool_mode and len(cmd.split()) <= 8
                    
                    if tool_call_match and is_pure_tool_only and is_casual_chat:
                        # Casual chat like "hello" that triggered a spurious tool call — strip it
                        full_reply = re.sub(r"<tool_call>.*?(</tool_call>|$)", "", full_reply, flags=re.DOTALL).strip()
                        full_reply = re.sub(r"<function[=>\s].*?(</function>|$)", "", full_reply, flags=re.DOTALL | re.IGNORECASE).strip()
                        if not full_reply:
                            full_reply = "I'm ready to help, but this looks like a normal chat request rather than a tool-driven task."
                            console.print(Markdown(full_reply))
                        reply = full_reply
                        break

                    if tool_call_match:
                        raw_tc = ""
                        try:
                            raw_tc = tool_call_match.group(1).strip() if tool_call_match.groups() else tool_call_match.group(0).strip()
                            # Only extract raw JSON if this is NOT an XML function call
                            if not re.search(r'<function[=>\s]', raw_tc, re.IGNORECASE):
                                json_match = re.search(r"(\{.*\})", raw_tc, re.DOTALL)
                                if json_match:
                                    raw_tc = json_match.group(1).strip()
                            if raw_tc.startswith("```json"):
                                raw_tc = raw_tc[7:]
                            elif raw_tc.startswith("```"):
                                raw_tc = raw_tc[3:]
                            if raw_tc.endswith("```"):
                                raw_tc = raw_tc[:-3]
                            raw_tc = raw_tc.strip()
                            
                            tc_data = robust_parse_tool_call(raw_tc)
                            t_name = tc_data.get("tool", "")
                            t_kwargs = tc_data.get("kwargs", {})
                            if not t_name or t_name in ("tool_name", "<tool_name>"):
                                raise ValueError(f"Invalid or placeholder tool name '{t_name}'.")

                            # 1. Universal Answer Delivery Guard:
                            # Terminate on substantive answer ONLY for search/information intents,
                            # NEVER for coding, workspace file operations, or multi-step execution tasks!
                            is_informational_intent = intent_res.intent in (IntentType.WEB_SEARCH, IntentType.TOOL_RESEARCH, IntentType.GENERAL_KNOWLEDGE)
                            is_action_prompt = any(act in cmd.lower() for act in ["write", "create", "make", "build", "run", "execute", "install", "test", "flutter", "game", "code", "script"])

                            clean_text_before_tool = re.sub(r"<tool_call>.*?(</tool_call>|$)", "", full_reply, flags=re.DOTALL).strip()
                            clean_text_before_tool = re.sub(r"<function[=>\s].*?(</function>|$)", "", clean_text_before_tool, flags=re.DOTALL | re.IGNORECASE).strip()
                            clean_text_before_tool = re.sub(r"<think>.*?</think>", "", clean_text_before_tool, flags=re.DOTALL).strip()
                            clean_text_before_tool = re.sub(r"<thought>.*?</thought>", "", clean_text_before_tool, flags=re.DOTALL).strip()
                            clean_text_before_tool = re.sub(r"<reasoning>.*?</reasoning>", "", clean_text_before_tool, flags=re.DOTALL).strip()
                            has_substantive_answer = (
                                len(clean_text_before_tool) >= 120 and
                                iter_count >= 2 and
                                any(marker in clean_text_before_tool for marker in ["\n", "1.", "2.", "- ", "* ", "• ", "http", "Project", "Overview", "Based on", "Here is", "Here are", "Summary", "```"])
                            )

                            # 2. Duplicate tool call guard:
                            tool_sig = f"{t_name}:{json.dumps(t_kwargs, sort_keys=True)}"
                            is_duplicate = tool_sig in executed_tool_calls

                            # 3. Search frequency guard:
                            if t_name in ("web_search", "browser.open_url"):
                                search_tool_count += 1

                            # 4. Block unauthorized actions during pure search/informational intents:
                            is_unauthorized_terminal = (
                                is_informational_intent
                                and t_name == "terminal.run"
                                and any(danger in t_kwargs.get("command", "").lower() for danger in ["git clone", "rm ", "curl -o", "wget ", "mkdir ", "chmod "])
                                and not any(explicit in cmd.lower() for explicit in ["clone", "install", "download", "run ", "execute", "setup"])
                            )

                            # Universal Substantive Answer Delivery Guard (Offline & Online):
                            # If a duplicate tool is emitted but the model ALREADY synthesized a complete response,
                            # deliver the completed answer immediately instead of looping into silent failure!
                            if is_duplicate:
                                if has_substantive_answer:
                                    console.print(f"\n[dim green]✓ Substantive response synthesized. Delivering completed answer...[/dim green]")
                                    reply = clean_text_before_tool
                                    break

                                if iter_count >= 2:
                                    console.print(f"\n[dim yellow]⚠️ Model repeated tool call: {t_name}. Providing feedback to advance reasoning...[/dim yellow]")
                                    messages.append({"role": "assistant", "content": full_reply})
                                    messages.append({
                                        "role": "user",
                                        "content": f"<observation>\n[Notice: {t_name} was already executed with identical arguments. Please evaluate previous observation and proceed to the next step, file modification, or provide final response.]\n</observation>"
                                    })
                                    continue

                            if t_name in ("web_search", "browser.open_url") and search_tool_count > 24:
                                console.print(f"\n[dim green]✓ Sufficient web information gathered. Proceeding to answer...[/dim green]")
                                final_ans = clean_text_before_tool if len(clean_text_before_tool) > 50 else full_reply
                                final_ans = re.sub(r"<tool_call>.*?(</tool_call>|$)", "", final_ans, flags=re.DOTALL).strip()
                                reply = final_ans
                                break

                            executed_tool_calls.append(tool_sig)

                            # Append assistant's partial reply
                            messages.append({"role": "assistant", "content": full_reply})
                            
                            req = ToolRequest(
                                tool_name=t_name,
                                command_line=t_kwargs.get("command", ""),
                                arguments=[],
                                kwargs=t_kwargs,
                                workspace=current_workspace,
                                permission_level=current_permission_level
                            )
                            perm = permission_manager.check_permission(req)
                            
                            if check_permission(t_name, t_kwargs, current_workspace, current_permission_level):
                                console.print(f"\n[bold magenta][Step {iter_count}/{MAX_ITERATIONS}] Running:[/bold magenta] [white]{t_name} {t_kwargs}[/white]")
                                try:
                                    from lmms.backend.events.bus import get_event_bus
                                    get_event_bus().tool_start(t_name, t_kwargs, step=iter_count)
                                except Exception:
                                    pass
                                # Dynamic capability discovery (Scenario G):
                                if t_name not in selection_res.selected_ids:
                                    selection_res = orchestration_pipeline.selector.discover_additional_tool(
                                        selection_res, missing_capability=t_name
                                    )
                                    # Update system prompt to include newly discovered tool
                                    new_schemas = orchestration_pipeline.builder.format_tool_schemas(selection_res.selected_tools)
                                    if messages and messages[0]["role"] == "system":
                                        base_p = orchestration_pipeline.builder.build_base_prompt(current_model)
                                        messages[0]["content"] = f"{base_p}\n\n{new_schemas}"

                                observation = ""
                                if t_name == "terminal.run":
                                    res = executor.execute(req, perm)
                                    observation = (res.stdout + "\n" + res.stderr).strip() or "Command completed with no output."
                                elif t_name == "browser.open_authenticated":
                                    if current_permission_level == "low":
                                        observation = "Permission denied: Requires medium or full permission for authenticated browsing."
                                    else:
                                        console.print("[bold yellow]AI requested access to your Browser Cookies (Authenticated Session).[/bold yellow]")
                                        allow = prompt(HTML('<ansiyellow>Allow? (y/n): </ansiyellow>')).strip().lower()
                                        if allow != "y":
                                            observation = "User denied access to browser profile."
                                        else:
                                            profiles = browser_tool.get_browser_profiles()
                                            if not profiles:
                                                observation = "No browser profiles found on the system."
                                            else:
                                                console.print("[bold cyan]Available Profiles:[/bold cyan]")
                                                for idx, pname in enumerate(profiles.keys()):
                                                    console.print(f"[{idx}] {pname}")
                                                sel_idx = prompt(HTML('<ansicyan>Select profile number: </ansicyan>')).strip()
                                                try:
                                                    sel_name = list(profiles.keys())[int(sel_idx)]
                                                    profile_data = profiles[sel_name]
                                                    sel_path = profile_data["base_path"]
                                                    profile_dir_name = profile_data["dir_name"]
                                                    is_headless = t_kwargs.get("headless", True)
                                                    observation = browser_tool.open_authenticated(t_kwargs.get("url", ""), sel_path, profile_dir_name, is_headless)
                                                except (ValueError, IndexError):
                                                    observation = "Invalid profile selection."
                                elif t_name == "vector_db.search":
                                    import hashlib
                                    from lmms.backend.tools.rag import RAGTool
                                    ws_id = hashlib.md5(current_workspace.encode()).hexdigest() if current_workspace != "None" else "global"
                                    max_tool_tokens = int(available_for_input * 0.3)
                                    rag_tool = RAGTool(workspace_id=ws_id)
                                    observation = rag_tool.search(t_kwargs.get("query", ""), max_tokens=max_tool_tokens)
                                elif t_name == "retrieve_archive":
                                    obs_id = t_kwargs.get("obs_id", "")
                                    log_dir = os.path.join(CONFIG_DIR, "logs", "observations")
                                    obs_file = os.path.join(log_dir, f"{obs_id}.txt")
                                    if os.path.exists(obs_file):
                                        with open(obs_file, "r") as f:
                                            observation = f.read()
                                    else:
                                        observation = f"Observation {obs_id} not found."
                                else:
                                    exec_res = orchestration_pipeline.executor.execute(
                                        tool_name=t_name,
                                        kwargs=t_kwargs,
                                        permission_level=current_permission_level,
                                        is_planning_mode=planning_mode
                                    )
                                    if exec_res.success:
                                        observation = exec_res.data if exec_res.data is not None else "[SUCCESS] Completed with no output."
                                    else:
                                        observation = exec_res.error or f"Tool '{t_name}' execution failed."

                                    
                                if t_name != "terminal.run":
                                    record_tool_evidence(req, perm, ToolResult(str(observation), "", 0))
                                    
                                # Broadcast tool completion and results to live event bus
                                try:
                                    from lmms.backend.events.bus import get_event_bus
                                    eb = get_event_bus()
                                    is_tool_ok = ("failed" not in str(observation).lower() and "error" not in str(observation).lower()[:20])
                                    eb.tool_end(t_name, success=is_tool_ok, output=str(observation))
                                    try:
                                        from lmms.backend.telemetry.metrics import get_metrics_tracker
                                        get_metrics_tracker().record_tool_call(t_name, duration_s=0.05, success=is_tool_ok)
                                    except Exception:
                                        pass
                                    if t_name in ("patch.apply", "apply_patch"):
                                        eb.patch_applied([t_kwargs.get("path", "")], [], diff=str(observation))
                                    elif t_name == "terminal.run":
                                        cmd_str = t_kwargs.get("command", "")
                                        if any(k in cmd_str for k in ["pytest", "unittest", "cargo test", "npm test", "go test"]):
                                            eb.test_result(cmd_str, exit_code, exit_code == 0, output=str(observation))
                                except Exception:
                                    pass

                                # Truncate observation for display
                                disp_obs = str(observation)
                                if len(disp_obs) > 500:
                                    disp_obs = disp_obs[:500] + "... (truncated)"
                                console.print(f"[bold cyan][Step {iter_count}/{MAX_ITERATIONS}] Observation:[/bold cyan] [dim]{disp_obs}[/dim]")
                            else:
                                record_tool_evidence(req, perm, ToolResult("", "", 1, was_denied=True, deny_reason="Denied by interactive check or policy"))
                                observation = "Tool execution denied by user or policy."
                                console.print(f"\n[bold red][Step {iter_count}/{MAX_ITERATIONS}] Denied tool execution: {t_name}[/bold red]")
                                
                            obs_cmd_hint = t_kwargs.get("command", "") if t_name == "terminal.run" else ""
                            exit_code = 0
                            
                            # Get the raw output, process it, and get the obs_id
                            truncated_obs, obs_id = ObservationProcessor.process(str(observation), obs_cmd_hint, exit_code)
                            
                            # Log raw observation to disk
                            try:
                                obs_dir = os.path.join(CONFIG_DIR, "logs", "observations")
                                os.makedirs(obs_dir, exist_ok=True)
                                with open(os.path.join(obs_dir, f"{obs_id}.txt"), "w") as f:
                                    f.write(str(observation))
                            except:
                                pass
                                
                            messages.append({"role": "user", "content": f"<observation>\n{truncated_obs}\n</observation>"})
                            
                            # Audit log
                            try:
                                log_dir = os.path.join(CONFIG_DIR, "logs")
                                os.makedirs(log_dir, exist_ok=True)
                                log_file = os.path.join(log_dir, f"session_{current_chat_id}.jsonl")
                                with open(log_file, "a", encoding="utf-8") as lf:
                                    lf.write(json.dumps({
                                        "timestamp": datetime.now().isoformat(),
                                        "step": f"{iter_count}/{MAX_ITERATIONS}",
                                        "tool": t_name,
                                        "kwargs": t_kwargs,
                                        "observation": observation
                                    }) + "\n")
                                os.chmod(log_file, 0o600)
                            except Exception as e:
                                pass

                            continue  # Loop again
                        except Exception as e:
                            with open("/tmp/ai_json_crash.txt", "a") as f:
                                f.write(f"FAILED RAW_TC:\n{raw_tc}\nEXCEPTION: {e}\nFULL_REPLY:\n{full_reply}\n------\n")
                            console.print("  [dim]↻ Self-correcting JSON format...[/dim]")
                            messages.append({"role": "assistant", "content": full_reply})
                            messages.append({"role": "user", "content": f"<observation>\nError parsing tool JSON: {e}. Ensure you use valid JSON, double quotes for keys, and escape internal quotes.\n</observation>"})

                            continue
                            
                    # If no tool call: check if the task was agentic and the model gave
                    # advice text instead of acting. If so, push back and continue.
                    if force_tool_mode and iter_count < MAX_ITERATIONS:
                        # Check if model gave advice (contains action verbs) but no tool call
                        advice_indicators = [
                            "docker-compose", "npm install", "pip install", "npm start",
                            "python app.py", "you can run", "you should run", "run the",
                            "to start", "would you like me", "here's how", "follow these",
                            "step 1", "step 2", "1.", "2."
                        ]
                        gave_advice = any(ind in full_reply.lower() for ind in advice_indicators)
                        if gave_advice:
                            messages.append({"role": "assistant", "content": full_reply})
                            messages.append({"role": "user", "content": (
                                "<observation>\n"
                                "SYSTEM: You gave text advice instead of running the commands yourself. "
                                "This is NOT acceptable. You MUST use terminal.run to execute every command. "
                                "DO NOT write instructions for the user. RUN the commands now using tool_call.\n"
                                "</observation>"
                            )})
                            continue

                    reply = full_reply
                    break
                    
                # Note: we only store text in the history so we don't blow up context limits with multiple images.
                now_str = datetime.now().isoformat()
                chat_history.append({"role": "user", "content": cmd, "timestamp": now_str})
                
                thought_content = ""
                answer_content = reply
                if "<think>" in reply and "</think>" in reply:
                    think_start = reply.find("<think>")
                    think_end = reply.find("</think>") + len("</think>")
                    thought_content = reply[think_start + len("<think>"):reply.find("</think>")].strip()
                    answer_content = (reply[:think_start] + reply[think_end:]).strip()
                elif "</think>" in reply:
                    think_end = reply.find("</think>") + len("</think>")
                    thought_content = reply[:reply.find("</think>")].strip()
                    answer_content = reply[think_end:].strip()
                
                msg_data = {"role": "assistant", "content": answer_content, "timestamp": now_str, "model": current_model}
                if thought_content:
                    msg_data["thought"] = thought_content
                chat_history.append(msg_data)
                # Save chat history
                chat_data = {
                    "id": current_chat_id,
                    "name": current_chat_name,
                    "workspace": current_workspace,
                    "messages": chat_history
                }
                with open(os.path.join(CHATS_DIR, f"{current_chat_id}.json"), "w") as f:
                    json.dump(chat_data, f)

                # Persist to unified SQLite SessionStore for App-Server and /sessions commands
                try:
                    from lmms_sessions.store import SessionStore
                    _s_store = SessionStore()
                    _db_sess = _s_store.get_session(current_chat_id)
                    if not _db_sess:
                        _s_store.create_session(
                            session_id=current_chat_id,
                            title=current_chat_name or "Untitled",
                            metadata={"workspace": current_workspace}
                        )
                    if len(chat_history) >= 2:
                        u_msg = chat_history[-2]
                        a_msg = chat_history[-1]
                        if u_msg.get("role") == "user":
                            _s_store.add_message(current_chat_id, role="user", content=u_msg.get("content", ""))
                        if a_msg.get("role") == "assistant":
                            _s_store.add_message(current_chat_id, role="assistant", content=a_msg.get("content", ""))
                except Exception:
                    pass

                # Finalize turn snapshot
                try:
                    if turn_mgr is not None:
                        turn_mgr.end_turn()
                except Exception:
                    pass

                # Live Telemetry & Metrics recording
                try:
                    from lmms.backend.telemetry.metrics import get_metrics_tracker
                    p_toks = len(str(messages)) // 4
                    c_toks = len(full_reply) // 4
                    turn_dur = round(time.time() - turn_start_time, 3)
                    get_metrics_tracker().record_tokens(p_toks, c_toks, duration_s=turn_dur)
                except Exception:
                    pass
                    
                # Review and validation gate before final completion
                try:
                    if current_workspace and current_workspace != "None":
                        from lmms_worktree.manager import default_worktree_manager
                        wt_sess = default_worktree_manager.get_session(current_workspace)
                        if wt_sess and getattr(wt_sess, "is_auto_ephemeral", False):
                            from lmms.backend.cli.review import verify_workspace_state
                            ws_verification = verify_workspace_state(wt_sess.worktree_dir)
                            if ws_verification.get("passed", True):
                                applied, app_msg = default_worktree_manager.apply(current_workspace)
                                if applied:
                                    console.print(f"[bold green]✓ [Worktree] Changes verified and merged cleanly into {current_workspace}[/bold green]")
                                else:
                                    console.print(f"[yellow]⚠️ [Worktree] Merge warning: {app_msg}[/yellow]")
                            else:
                                default_worktree_manager.discard(current_workspace)
                                err_msg = "\n".join(ws_verification.get("syntax_errors", []))
                                console.print(f"[bold red]✗ [Worktree] Verification failed: changes cleanly discarded.\n{err_msg}[/bold red]")
                        elif intent_res.intent == IntentType.CODING:
                            from lmms.backend.cli.review import verify_workspace_state
                            ws_verification = verify_workspace_state(current_workspace)
                            if not ws_verification.get("passed", True):
                                err_msg = "\n".join(ws_verification.get("syntax_errors", []))
                                console.print(f"[yellow]⚠️ Post-execution review warning: Syntax or git validation issues detected:\n{err_msg}[/yellow]")
                except Exception:
                    pass

                # Telemetry trace recording
                try:
                    import uuid
                    orchestration_pipeline.trace_logger.record_trace(RequestTrace(
                        request_id=str(uuid.uuid4()),
                        conversation_id=current_chat_id or "default",
                        timestamp=time.time(),
                        model_name=current_model,
                        backend_engine="engine_1_air_llamacpp",
                        intent=intent_res.intent.value,
                        intent_confidence=intent_res.confidence,
                        selected_tools=selection_res.selected_ids,
                        rejected_tools=selection_res.rejected_ids,
                        context_limit=budget.context_limit,
                        usable_budget=budget.usable_context,
                        output_reserve=budget.output_reserve,
                        base_prompt_tokens=budget.base_prompt_tokens,
                        tool_schemas_tokens=budget.tool_schemas_tokens,
                        history_tokens=budget.history_tokens,
                        user_query_tokens=budget.user_query_tokens,
                        total_prompt_tokens=budget.total_prompt_tokens,
                        compacted=budget.is_overflow,
                        observations_pruned=0,
                        cache_prefix_hash=assembled_ctx.prefix_hash,
                        cache_hit=False,
                        ttft_ms=0,
                        total_latency_ms=int((time.time() - req_t0) * 1000),
                        tool_calls_count=max(0, iter_count - 1)
                    ))
                except Exception:
                    pass

                # Auto-naming for first message
                # Auto-naming for first message in background thread so it never blocks the prompt loop or engine health poller
                if current_chat_name == "Untitled" and len(chat_history) == 2:
                    def _async_gen_title(chat_id, user_msg):
                        try:
                            name_resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                                "model_name": current_model,
                                "messages": [{"role": "user", "content": f"Generate a short 3-word title for this chat based on the first message: '{user_msg}'. Reply ONLY with the title."}],
                                "stream": False,
                                "temperature": 0.3
                            }, timeout=8)
                            new_name = name_resp.json().get("message", {}).get("content", "Untitled").strip().strip('"').replace('\n', ' ')
                            if new_name and len(new_name) < 50:
                                chat_file = os.path.join(CHATS_DIR, f"{chat_id}.json")
                                if os.path.exists(chat_file):
                                    with open(chat_file, "r") as f:
                                        c_data = json.load(f)
                                    c_data["name"] = new_name
                                    with open(chat_file, "w") as f:
                                        json.dump(c_data, f)
                        except Exception:
                            pass
                    threading.Thread(target=_async_gen_title, args=(current_chat_id, cmd), daemon=True, name="Async-Chat-Title").start()
                
                if voice_mode_active and vsession is not None:
                    try:
                        from lmms.backend.voice import extract_thoughts_and_response, stream_audio, wait_for_tts
                        _, final_spoken = extract_thoughts_and_response(full_reply)
                        final_text_to_print = final_spoken.strip() if final_spoken.strip() else answer_content
                        
                        if hasattr(vsession, "sentence_buffer") and vsession.sentence_buffer.strip():
                            stream_audio(vsession.sentence_buffer.strip(), voice="female")
                            
                        # Wait for TTS queue to drain before stopping animation
                        wait_for_tts()
                        vsession.stop_animation()
                        
                        # Print the final reply natively so the user can read it (clean, no think tags)
                        console.print(f"\n[bold cyan]Model : {get_clean_model_display_name(current_model)}[/bold cyan]")
                        console.print(Markdown(final_text_to_print))
                    except Exception:
                        pass
                    voice_mode_active = False

        except KeyboardInterrupt:
            try:
                from lmms_worktree.manager import default_worktree_manager
                if current_workspace and current_workspace != "None":
                    wt_sess = default_worktree_manager.get_session(current_workspace)
                    if wt_sess and getattr(wt_sess, "is_auto_ephemeral", False):
                        default_worktree_manager.discard(current_workspace)
                        console.print("\n[dim yellow]● Cleaned up ephemeral worktree on interrupt.[/dim yellow]")
            except Exception:
                pass
            if 'voice_mode_active' in locals() and voice_mode_active:
                if 'vsession' in locals() and vsession is not None:
                    try:
                        vsession.stop_animation()
                    except Exception:
                        pass
                voice_mode_active = False
            console.print("\n[dim]Type 'exit' to quit.[/dim]")
        except EOFError:
            break

    if _cli_session_auto_started:
        try:
            from lmms.api.service import stop_server_daemon
            stop_res = stop_server_daemon(force=False, caller="cli")
            if stop_res.get("status") == "stopped":
                console.print("[dim]● Cleaned up auto-started local Super Engine daemon.[/dim]")
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "app-server":
        from lmms_server.server import run_app_server_cli
        sys.exit(run_app_server_cli(sys.argv[2:]))

    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        from lmms_server.audit_cli import handle_audit_cli
        sys.exit(handle_audit_cli(sys.argv[2:]))

    import argparse
    parser = argparse.ArgumentParser(description="LMMs Backend OS")
    parser.add_argument("--api", action="store_true", help="Run the Backend API Server alongside CLI")
    
    args = parser.parse_args()
    
    if args.api:
        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        
    try:
        run_cli()
    except SystemExit as e:
        if _cli_session_auto_started:
            try:
                from lmms.api.service import stop_server_daemon
                stop_server_daemon(force=False, caller="cli")
            except Exception:
                pass
        import os
        exit_code = e.code if isinstance(e.code, int) else 0
        os._exit(exit_code)
    except Exception:
        pass
    finally:
        if _cli_session_auto_started:
            try:
                from lmms.api.service import stop_server_daemon
                stop_server_daemon(force=False, caller="cli")
            except Exception:
                pass
        import os
        os._exit(0)
