"""
Model-Driven Capability Benchmark Harness for LMMs.
Provides reproducible evaluations for the 8 required agent capability tasks:
1. Discover a non-obvious route from page DOM rather than guessing.
2. Recover from an invalid URL using page evidence.
3. Report identity and authentication status without false claims.
4. Create a multi-section document and verify its persisted content.
5. Handle a forced write failure without claiming success.
6. Complete a browser-to-file multi-step workflow.
7. Stop repeated tool calls after recurring failures.
8. Report tool results honestly when an action fails.
"""

import os
import sys
import json
import socket
import threading
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional, Tuple


class BenchmarkSiteHandler(BaseHTTPRequestHandler):
    """Local test website serving specific DOM structures for reproducible benchmark tasks."""

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logs
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            body = """<!DOCTYPE html>
<html>
<head><title>LMMs Benchmark Portal</title></head>
<body>
    <h1>Welcome to LMMs Benchmark Test Portal</h1>
    <p>This is a local fixture site for agent capability benchmarking.</p>
    <nav>
        <a href="/about" id="nav-about">About Us</a>
        <a href="/docs/guide" id="nav-docs">Documentation</a>
        <!-- Non-obvious route that cannot be guessed without DOM inspection -->
        <a href="/portal-v2-access" id="nav-portal">Member Portal (v2 Access)</a>
    </nav>
    <form action="/search" method="get">
        <input type="text" name="q" placeholder="Search benchmark..." />
        <button type="submit">Search</button>
    </form>
    <p class="login-prompt">Already a member? <a href="/login" id="link-login">Sign In</a></p>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/portal-v2-access":
            body = """<!DOCTYPE html>
<html>
<head><title>Member Portal Access</title></head>
<body>
    <h1>Member Portal Dashboard</h1>
    <p id="portal-secret">CONFIRMED_ACCESS_TOKEN: 8f2b-99c4-lmms</p>
    <p>You have successfully discovered and navigated to the non-obvious member portal route.</p>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/public-with-cookie":
            # Site that sets a guest session cookie, but has a visible Sign In button
            body = """<!DOCTYPE html>
<html>
<head><title>Public Page with Tracking Cookie</title></head>
<body>
    <h1>Public Storefront</h1>
    <p>Welcome guest visitor!</p>
    <a href="/login">Sign In / Log In</a>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Set-Cookie", "session=guest_temp_tracker_cookie_12345; Path=/")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/dashboard-authenticated":
            # Truly authenticated page with user profile and logout
            body = """<!DOCTYPE html>
<html>
<head><title>Authenticated Dashboard</title></head>
<body>
    <div data-testid="user-profile">Active User: benchmark_engineer@lmms.local</div>
    <a href="/logout">Log Out</a>
    <h2>Engineering Analytics</h2>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/interactive-button-demo":
            body = """<!DOCTYPE html>
<html>
<head><title>Interactive Button Demo</title></head>
<body>
    <h1>LMMs GUI Interaction Test</h1>
    <p>Discover the button below, click it, and verify the resulting state change.</p>
    <div id="status-container">Current Status: <span id="status-label">PENDING</span></div>
    <button id="btn-activate-service" onclick="document.getElementById('status-label').innerText = 'ACTIVATED_SUCCESSFULLY_TOKEN_9981'; document.getElementById('status-container').style.color='green';">Activate Feature Service</button>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path == "/interactive-form-demo":
            body = """<!DOCTYPE html>
<html>
<head><title>Interactive Registration Form</title></head>
<body>
    <h1>Member Registration Form</h1>
    <form action="/form-submit" method="POST">
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" placeholder="Enter username" />
        <label for="tier">Tier:</label>
        <input type="text" id="tier" name="tier" placeholder="Enter tier" />
        <button type="submit" id="btn-submit-form">Submit Registration</button>
    </form>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        elif path.startswith("/invalid-path"):
            # 404 page with recovery links
            body = """<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
    <h1>404 Not Found</h1>
    <p>The requested route does not exist.</p>
    <p>Use these valid links to navigate:</p>
    <a href="/" id="recover-home">Return to Home Portal</a>
    <a href="/sitemap" id="recover-sitemap">Sitemap Index</a>
</body>
</html>"""
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/form-submit":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            fields = urllib.parse.parse_qs(post_data)
            user = fields.get("username", ["anonymous"])[0]
            tier = fields.get("tier", ["standard"])[0]

            body = f"""<!DOCTYPE html>
<html>
<head><title>Registration Confirmation</title></head>
<body>
    <h1>Registration Completed</h1>
    <p id="confirm-msg">REGISTRATION_CONFIRMED: user={user}, tier={tier}</p>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class LocalBenchmarkServer:
    """Manages a background HTTP server on a random free port for isolated benchmarking."""

    def __init__(self):
        self.server: Optional[HTTPServer] = None
        self.port: int = 0
        self.thread: Optional[threading.Thread] = None

    def start(self) -> str:
        # Find an open port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()

        self.server = HTTPServer(("127.0.0.1", self.port), BenchmarkSiteHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass
            try:
                self.server.server_close()
            except Exception:
                pass
            self.server = None
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=2.0)
            except Exception:
                pass
            self.thread = None


def check_compatible_model_available() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Checks if a real, compatible model is configured and reachable through LMMs.
    Inspects OnlineModelRegistry (cloud providers/webhooks), offline models (~/.lmms/models.json),
    and local engine (port 11435).
    """
    # 1. Check configured online model in OnlineModelRegistry
    try:
        from lmms.backend.core.registry.online_models import OnlineModelRegistry
        active_online = OnlineModelRegistry.get_active_model()
        if active_online and OnlineModelRegistry.get_active_type() == "online" and active_online.get("enabled", True):
            model_id = active_online.get("id") or active_online.get("name")
            safe_config = {
                "provider": active_online.get("provider_name", "Online Provider"),
                "type": active_online.get("type", "openai_compatible"),
                "base_url": active_online.get("base_url", ""),
                "configured": True
            }
            return True, str(model_id), safe_config
    except Exception:
        pass

    # 2. Check ~/.lmms/models.json
    models_path = os.path.expanduser("~/.lmms/models.json")
    if os.path.exists(models_path):
        try:
            with open(models_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                active = data.get("active_model")
                if active and active != "None":
                    return True, str(active), {"provider": "local_offline", "config": data}
        except Exception:
            pass

    # 3. Check local engine port 11435
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", 11435))
        s.close()
        return True, "local-engine-11435", {"provider": "local_engine", "endpoint": "http://127.0.0.1:11435"}
    except Exception:
        pass

    return False, "None configured", {}


def run_agent_turn_loop(
    prompt: str,
    max_turns: int = 5,
    current_workspace: Optional[str] = None,
    permission_level: str = "medium"
) -> Dict[str, Any]:
    """
    Executes a prompt through LMMs' actual agent orchestration loop.
    Uses OrchestrationPipeline to route, select tools, format prompts, stream
    model completions, parse tool calls, execute them, and feed observations back.
    """
    from lmms.backend.core.registry.online_models import OnlineModelRegistry
    from lmms.backend.core.registry.online_models import OnlineModelRegistry
    from lmms.backend.providers.online_client import OnlineModelClient
    from lmms.backend.orchestration.pipeline import OrchestrationPipeline
    from lmms.backend.main import robust_parse_tool_call
    import re

    if current_workspace:
        os.environ["LMMS_ACTIVE_WORKSPACE"] = current_workspace

    pipeline = OrchestrationPipeline()
    active_online = OnlineModelRegistry.get_active_model()
    model_name = active_online["id"] if active_online else "default-model"

    assembled_ctx, intent_res, selection_res, budget = pipeline.prepare_request(
        model_name=model_name,
        user_query=prompt,
        conversation_history=[],
        current_workspace=current_workspace,
        permission_level=permission_level
    )

    messages = list(assembled_ctx.messages)
    tool_calls_executed: List[str] = []
    observations_recorded: List[str] = []
    turn_count = 0
    final_reply = ""

    for turn in range(max_turns):
        turn_count += 1
        chunks = []
        for attempt in range(3):
            chunks = []
            try:
                for chunk in OnlineModelClient.stream_chat(model_name, messages, max_tokens=2048, timeout=45):
                    line = chunk.decode("utf-8", errors="replace")
                    for sub in line.split("\n\n"):
                        if sub.startswith("data: ") and sub != "data: [DONE]":
                            try:
                                d = json.loads(sub[6:])
                                if "error" in d:
                                    err_msg = str(d["error"])
                                    if "429" in err_msg or "rate" in err_msg.lower():
                                        time.sleep(2.5 * (attempt + 1))
                                delta = d.get("choices", [{}])[0].get("delta", {})
                                c = delta.get("content") or ""
                                r = delta.get("reasoning_content") or ""
                                if c:
                                    chunks.append(c)
                                elif r:
                                    chunks.append(r)
                            except Exception:
                                pass
                if chunks:
                    break
                else:
                    time.sleep(2.0 * (attempt + 1))
            except Exception as e:
                if attempt == 2:
                    observations_recorded.append(f"Model streaming error: {str(e)}")
                time.sleep(2.0 * (attempt + 1))

        reply_text = "".join(chunks).strip()
        if not reply_text:
            break

        # Check for tool call
        tool_match = re.search(r"<tool_call>\s*(.*?)\s*(</tool_call>|$)", reply_text, re.DOTALL)
        if not tool_match:
            tool_match = re.search(r'(<function[=>\s].*?(?:</function>|$))', reply_text, re.DOTALL | re.IGNORECASE)

        if not tool_match:
            final_reply = reply_text
            break

        raw_tc = tool_match.group(1).strip() if tool_match.groups() else tool_match.group(0).strip()
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

        try:
            tc_data = robust_parse_tool_call(raw_tc)
        except Exception as parse_err:
            obs_text = f"Error parsing tool call: {str(parse_err)}. Please output valid tool call JSON in <tool_call>{{\"tool\": \"...\", \"kwargs\": {{...}}}}</tool_call>"
            observations_recorded.append(obs_text)
            messages.append({"role": "assistant", "content": reply_text})
            messages.append({"role": "user", "content": f"<observation>\n{obs_text}\n</observation>"})
            continue

        t_name = tc_data.get("tool", "")
        t_kwargs = tc_data.get("kwargs", {})

        if not t_name:
            final_reply = reply_text
            break

        tool_sig = f"{t_name}({json.dumps(t_kwargs, sort_keys=True)})"
        dup_count = tool_calls_executed.count(tool_sig)
        tool_calls_executed.append(tool_sig)

        if dup_count >= 1:
            # Loop breaker triggered
            obs_text = (
                f"[STOP_LOOP_WARNING: Tool '{t_name}' was repeated with identical arguments {dup_count + 1} times. "
                f"Further identical execution is blocked. Please synthesize observed results, report any errors honestly, "
                f"or proceed to the next step without repeating this tool call.]"
            )
            observations_recorded.append(obs_text)
            messages.append({"role": "assistant", "content": reply_text})
            messages.append({"role": "user", "content": f"<observation>\n{obs_text}\n</observation>"})
            continue

        # Execute tool through pipeline executor
        exec_res = pipeline.executor.execute(
            tool_name=t_name,
            kwargs=t_kwargs,
            permission_level=permission_level
        )
        obs_text = exec_res.formatted_observation or str(exec_res.data or exec_res.error or "No output")
        observations_recorded.append(obs_text)

        # Feed back to model wrapped in standard observation tags
        messages.append({"role": "assistant", "content": reply_text})
        messages.append({"role": "user", "content": f"<observation>\n{obs_text}\n</observation>"})

    return {
        "turns": turn_count,
        "tool_calls": tool_calls_executed,
        "observations": observations_recorded,
        "final_reply": final_reply
    }


class BenchmarkReport:
    """Compiles and exports structured benchmark execution telemetry."""

    def __init__(self, model_identifier: str, model_config: Dict[str, Any]):
        self.model_identifier = model_identifier
        self.model_config = model_config
        self.results: List[Dict[str, Any]] = []

    def record_task(
        self,
        task_id: int,
        task_name: str,
        status: str,
        turns: int = 0,
        tool_calls: Optional[List[str]] = None,
        observed_results: Optional[List[str]] = None,
        failure_reason: str = "",
        interaction_type: str = "DOM_DRIVEN",
        evaluation_type: str = "MODEL_DRIVEN"
    ):
        self.results.append({
            "task_id": task_id,
            "task_name": task_name,
            "status": status,
            "turns": turns,
            "tool_calls": tool_calls or [],
            "observed_results": observed_results or [],
            "failure_reason": failure_reason,
            "interaction_type": interaction_type,
            "evaluation_type": evaluation_type
        })

    def export_summary(self) -> Dict[str, Any]:
        return {
            "model_identifier": self.model_identifier,
            "model_config": self.model_config,
            "tasks_count": len(self.results),
            "passed": sum(1 for r in self.results if r["status"] == "PASSED"),
            "failed": sum(1 for r in self.results if r["status"] == "FAILED"),
            "not_tested": sum(1 for r in self.results if r["status"] == "NOT TESTED"),
            "tasks": self.results
        }
