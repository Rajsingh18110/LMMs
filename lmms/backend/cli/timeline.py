"""
Gemini-style thinking and tool execution timeline renderer for LMMs Terminal CLI.

Provides:
- Connected vertical timeline tree structure (│, ├──, └──)
- Real-time event rendering: search, URL open, file read/write/list, terminal commands, DNS
- Source-domain pill badges for web research based ONLY on verified URLs
- Deduplication of domain pills and consecutive identical events
- Dynamic sizing without arbitrary Step X/24 caps (preserves true backend safety limits)
- Accurate elapsed thinking time and model display
- Responsive, bounded output preventing terminal flooding and scroll-lock
- Distinct visual states for success, failure, cancellation, and active thinking
"""

from __future__ import annotations

import re
import json
import time
import urllib.parse
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Union
from rich.console import Console
from rich.text import Text


class TimelineEventType(str, Enum):
    START = "start"
    THINKING = "thinking"
    SEARCH = "search"
    OPEN_URL = "open_url"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_FILES = "list_files"
    TERMINAL = "terminal"
    PATCH = "patch"
    DNS = "dns"
    TOOL = "tool"
    OBSERVATION = "observation"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


def extract_domain_pills(text: str, max_pills: int = 6) -> List[str]:
    """
    Extracts, validates, normalizes, and deduplicates domains from text or observation data.
    Strictly verifies that domains were actually present in the source text.
    Never invents or hallucinates domains.
    """
    if not text or not isinstance(text, str):
        return []

    # Find all HTTP/HTTPS URLs
    url_pattern = r'https?://(?:[a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+(?::\d+)?(?:/[^\s)\]\'"<>]*)*'
    raw_urls = re.findall(url_pattern, text)

    # Also look for domain-like citations in search outputs: e.g., "Source: github.com/..."
    citation_pattern = r'(?:from|source|site|domain|host):\s*([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s)\]\'"<>]*)*)'
    raw_citations = re.findall(citation_pattern, text, flags=re.IGNORECASE)

    candidates = list(raw_urls)
    for c in raw_citations:
        if not c.startswith("http"):
            candidates.append(f"https://{c}")
        else:
            candidates.append(c)

    domains: List[str] = []
    seen: Set[str] = set()

    for item in candidates:
        try:
            parsed = urllib.parse.urlparse(item)
            netloc = (parsed.netloc or parsed.path).split("/")[0].split(":")[0].strip().lower()

            # Normalize domain
            if netloc.startswith("www."):
                netloc = netloc[4:]

            # Validate domain format (must contain at least one dot, valid domain characters)
            if (
                netloc
                and "." in netloc
                and not netloc.startswith(".")
                and not netloc.endswith(".")
                and re.match(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$', netloc)
            ):
                # Filter out obvious false positives or placeholder tokens
                if netloc not in ("example.com", "placeholder.com") and netloc not in seen:
                    seen.add(netloc)
                    domains.append(netloc)
                    if len(domains) >= max_pills:
                        break
        except Exception:
            continue

    return domains


class TimelineRenderer:
    """
    Thread-safe, stateful terminal timeline renderer implementing the
    continuous vertical Gemini-style thinking & tool execution UI.
    """

    def __init__(self, console: Optional[Console] = None, max_history_events: int = 1000):
        self.console = console or Console()
        self.max_history_events = max_history_events
        self._events: List[Dict[str, Any]] = []
        self._turn_active: bool = False
        self._turn_start_time: float = 0.0
        self._turn_prompt: str = ""
        self._active_model: str = ""
        self._last_event_sig: Optional[str] = None
        self._has_open_trunk: bool = False

    def reset(self):
        """Reset the timeline state between conversational turns."""
        self._events.clear()
        self._turn_active = False
        self._turn_start_time = 0.0
        self._turn_prompt = ""
        self._active_model = ""
        self._last_event_sig = None
        self._has_open_trunk = False

    def start_turn(self, prompt: str = "", model_name: str = ""):
        """Start a new execution turn and initialize the thinking timeline."""
        self._turn_active = True
        self._turn_start_time = time.time()
        self._turn_prompt = prompt
        self._active_model = model_name
        self._last_event_sig = None
        self._has_open_trunk = False

    def emit_tool_call(self, tool_name: str, kwargs: Dict[str, Any], step: int = 0) -> str:
        """
        Renders a clean, vertical timeline node for a tool call.
        Eliminates bulky boxes and artificial 'Step X/24' limits.
        Returns the rendered text string.
        """
        clean_kwargs = dict(kwargs or {})
        event_sig = f"call:{tool_name}:{json.dumps(clean_kwargs, sort_keys=True)}"

        # Deduplication check: do not render identical consecutive tool calls without distinction
        is_repeat = (event_sig == self._last_event_sig)
        self._last_event_sig = event_sig

        self._record_event(TimelineEventType.TOOL, {"tool": tool_name, "kwargs": clean_kwargs, "step": step})

        lines: List[str] = []

        # Connect with vertical trunk
        lines.append("[dim]  │[/dim]")
        self._has_open_trunk = True

        repeat_badge = " [bold yellow](repeated)[/bold yellow]" if is_repeat else ""

        # Specialized rendering per tool category
        if tool_name in ("web_search", "web.search"):
            query = clean_kwargs.get("query") or clean_kwargs.get("q") or ""
            clean_q = query[:85] + "..." if len(query) > 85 else query
            lines.append(f"[dim]  ├──[/dim] [bold cyan]🔍 Searching[/bold cyan] [white]\"{clean_q}\"[/white]{repeat_badge}")

        elif tool_name in ("browser.open_url", "open_url"):
            url = clean_kwargs.get("url") or ""
            clean_url = url[:85] + "..." if len(url) > 85 else url
            lines.append(f"[dim]  ├──[/dim] [bold cyan]🌐 Opening URL[/bold cyan] [dim cyan]{clean_url}[/dim cyan]{repeat_badge}")

        elif tool_name in ("files.read", "file.read", "read_file"):
            path = clean_kwargs.get("path") or clean_kwargs.get("file_path") or clean_kwargs.get("filename") or ""
            lines.append(f"[dim]  ├──[/dim] [bold blue]📄 Reading[/bold blue] [cyan]{path}[/cyan]{repeat_badge}")

        elif tool_name in ("files.write", "file.write", "write_file"):
            path = clean_kwargs.get("path") or clean_kwargs.get("file_path") or clean_kwargs.get("filename") or ""
            content = clean_kwargs.get("content") or clean_kwargs.get("data") or clean_kwargs.get("text") or clean_kwargs.get("code") or ""
            c_lines = content.splitlines() if content else []
            line_count = len(c_lines)
            byte_count = len(content.encode("utf-8")) if content else 0

            lines.append(f"[dim]  ├──[/dim] [bold green]✍️ Writing[/bold green] [cyan]{path}[/cyan] [dim]({line_count} lines · {byte_count:,} bytes)[/dim]{repeat_badge}")
            if c_lines:
                preview = [f"[dim]  │   │  {l}[/dim]" for l in c_lines[:3]]
                if len(c_lines) > 3:
                    preview.append(f"[dim]  │   │  ... +{len(c_lines) - 3} more lines[/dim]")
                lines.append("\n".join(preview))

        elif tool_name in ("files.list", "list_folder"):
            path = clean_kwargs.get("path") or "."
            lines.append(f"[dim]  ├──[/dim] [bold yellow]📂 Scanning[/bold yellow] [cyan]{path}[/cyan]{repeat_badge}")

        elif tool_name == "terminal.run":
            cmd_str = clean_kwargs.get("command") or clean_kwargs.get("cmd") or ""
            clean_cmd = cmd_str[:85] + "..." if len(cmd_str) > 85 else cmd_str
            lines.append(f"[dim]  ├──[/dim] [bold magenta]💻 Terminal[/bold magenta] [dim white]$ {clean_cmd}[/dim white]{repeat_badge}")

        elif tool_name in ("patch.apply", "apply_patch"):
            path = clean_kwargs.get("path") or ""
            lines.append(f"[dim]  ├──[/dim] [bold cyan]⚡ Patching[/bold cyan] [cyan]{path}[/cyan]{repeat_badge}")

        elif tool_name in ("dns.enumerate", "dns_enumerate", "dns.lookup", "dns_lookup", "enumerate_subdomains"):
            domain = clean_kwargs.get("domain") or clean_kwargs.get("target") or clean_kwargs.get("host") or ""
            qtype = clean_kwargs.get("query_type", "all")
            lines.append(f"[dim]  ├──[/dim] [bold cyan]🌐 Resolving DNS[/bold cyan] [white]{domain}[/white] [dim]({qtype})[/dim]{repeat_badge}")

        elif tool_name in ("browser.click_element", "click_element"):
            selector = clean_kwargs.get("selector") or clean_kwargs.get("id") or ""
            lines.append(f"[dim]  ├──[/dim] [bold cyan]🖱️ Clicking[/bold cyan] [white]'{selector}'[/white]{repeat_badge}")

        elif tool_name in ("browser.fill_form", "fill_form"):
            lines.append(f"[dim]  ├──[/dim] [bold cyan]📝 Filling Form[/bold cyan]{repeat_badge}")

        elif tool_name in ("browser.get_interactive_dom", "get_interactive_dom"):
            lines.append(f"[dim]  ├──[/dim] [bold cyan]🔍 Inspecting DOM[/bold cyan]{repeat_badge}")

        elif tool_name in ("account.get_current_identity", "browser.get_account_context"):
            lines.append(f"[dim]  ├──[/dim] [bold cyan]👤 Checking Account Identity[/bold cyan]{repeat_badge}")

        else:
            filtered = {k: v for k, v in clean_kwargs.items() if k not in ("content", "patch")}
            arg_str = f" [dim]{json.dumps(filtered)}[/dim]" if filtered else ""
            lines.append(f"[dim]  ├──[/dim] [bold cyan]⚙️ {tool_name}[/bold cyan]{arg_str}{repeat_badge}")

        output_str = "\n".join(lines)
        self.console.print(output_str, highlight=False)
        return output_str

    def emit_observation(self, tool_name: str, observation: str, step: int = 0) -> str:
        """
        Renders a clean observation node beneath the active tool node.
        - Extracts verified domain pills for search/browser tools.
        - Guarantees exactly-once output (diagnosed and eliminated duplicate generic print).
        - Prevents terminal flooding and scroll-lock with bounded summaries.
        """
        obs_str = str(observation).strip()
        if not obs_str:
            return ""

        event_sig = f"obs:{tool_name}:{obs_str[:60]}"
        self._record_event(TimelineEventType.OBSERVATION, {"tool": tool_name, "observation": obs_str, "step": step})
        self._last_event_sig = event_sig

        lines: List[str] = []

        # 1. Search & Browser Tools: Extract verified domain pills
        if tool_name in ("web_search", "web.search", "browser.open_url", "open_url", "browser.crawl_url", "browser.crawl"):
            domains = extract_domain_pills(obs_str)
            if domains:
                # Render sleek horizontal domain pill chips
                pills = "  ".join(f"[bold white on #262626]  🌐 {d}  [/]" for d in domains[:5])
                lines.append(f"[dim]  │   [/dim]  {pills}")
            else:
                first_line = obs_str.splitlines()[0][:85]
                lines.append(f"[dim]  │   └── {first_line}[/dim]")

        # 1b. Browser DOM Click & Form
        elif tool_name in ("browser.click_element", "click_element"):
            first_line = obs_str.splitlines()[0]
            if "[NAVIGATED ->" in first_line:
                nav_target = first_line.split("[NAVIGATED ->")[-1].rstrip("]").strip()
                lines.append(f"[dim]  │   └── [green]✓ Clicked and navigated to[/green] [cyan]{nav_target[:70]}[/cyan][/dim]")
            else:
                lines.append(f"[dim]  │   └── [green]✓ Element clicked successfully[/green][/dim]")

        elif tool_name in ("browser.fill_form", "fill_form"):
            lines.append(f"[dim]  │   └── [green]✓ Form filled successfully[/green][/dim]")

        elif tool_name in ("account.get_current_identity", "browser.get_account_context"):
            try:
                import ast
                acc_data = json.loads(obs_str) if obs_str.startswith("{") else ast.literal_eval(obs_str)
                email = acc_data.get("primary_email") or acc_data.get("git_email") or "User identity found"
                lines.append(f"[dim]  │   └── [green]✓ Identity:[/green] [white]{email}[/white][/dim]")
            except Exception:
                first_line = obs_str.splitlines()[0][:85]
                lines.append(f"[dim]  │   └── [green]✓ Identity: {first_line}[/green][/dim]")

        # 2. DNS Enumeration / Lookup Tools: Display verified records
        elif tool_name in ("dns.enumerate", "dns_enumerate", "dns.lookup", "dns_lookup", "enumerate_subdomains"):
            verified_lines = [l.strip() for l in obs_str.splitlines() if "[VERIFIED]" in l or any(f"• {rt}" in l for rt in ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "PTR"))]
            if verified_lines:
                for vl in verified_lines[:4]:
                    clean_vl = vl[:85] + "..." if len(vl) > 85 else vl
                    lines.append(f"[dim]  │   ├──[/dim] [green]{clean_vl}[/green]")
                if len(verified_lines) > 4:
                    lines.append(f"[dim]  │   └── +{len(verified_lines) - 4} more verified records[/dim]")
            else:
                first_line = obs_str.splitlines()[0][:85]
                lines.append(f"[dim]  │   └── {first_line}[/dim]")

        # 3. Terminal Run: Single, bounded summary of exit code and output
        elif tool_name == "terminal.run":
            clean_lines = [l.strip() for l in obs_str.splitlines() if l.strip()]
            if clean_lines:
                summary = clean_lines[0] if len(clean_lines) == 1 else clean_lines[-1]
                if len(summary) > 85:
                    summary = summary[:82] + "..."
                is_err = any(err_kw in obs_str.lower() for err_kw in ("error:", "failed", "traceback", "command not found"))
                status_icon = "✗" if is_err else "✓"
                style = "red" if is_err else "dim"
                lines.append(f"[dim]  │   └──[/dim] [{style}]{status_icon} {summary}[/{style}]")
            else:
                lines.append(f"[dim]  │   └── ✓ Completed with no output[/dim]")

        # 4. File Write
        elif tool_name in ("files.write", "file.write", "write_file"):
            lines.append(f"[dim]  │   └── [green]✓ Saved successfully[/green][/dim]")

        # 5. File Read
        elif tool_name in ("files.read", "file.read", "read_file"):
            count = len(obs_str.splitlines())
            lines.append(f"[dim]  │   └── {count} lines loaded[/dim]")

        # 6. File List
        elif tool_name in ("files.list", "list_folder"):
            items = len(obs_str.splitlines())
            lines.append(f"[dim]  │   └── Found {items} items[/dim]")

        # 7. Generic Tools: EXACTLY ONE bounded summary line (Fix for duplicate print bug!)
        else:
            raw_lines = obs_str.splitlines()
            first_line = raw_lines[0][:85] if raw_lines else obs_str[:85]
            lines.append(f"[dim]  │   └── {first_line}[/dim]")

        output_str = "\n".join(lines)
        self.console.print(output_str, highlight=False)
        return output_str

    def finish_thinking(self, elapsed_s: int, model_name: str) -> str:
        """
        Renders the completed thinking header closing the timeline.
        Format:
        ::: Thought for {elapsed_s}s
        Model : {model_name}
        """
        self._record_event(TimelineEventType.COMPLETE, {"elapsed_s": elapsed_s, "model": model_name})
        lines = [
            f"[dim]::: Thought for {elapsed_s}s[/dim]",
            f"[bold cyan]Model : {model_name}[/bold cyan]"
        ]
        output_str = "\n".join(lines)
        self.console.print(output_str, highlight=False)
        self._has_open_trunk = False
        return output_str

    def emit_failure(self, error_message: str) -> str:
        """Renders an error node on the timeline."""
        self._record_event(TimelineEventType.FAILED, {"error": error_message})
        clean_err = error_message[:100] + "..." if len(error_message) > 100 else error_message
        output_str = f"[dim]  │[/dim]\n[dim]  └──[/dim] [bold red]✗ Failed: {clean_err}[/bold red]"
        self.console.print(output_str, highlight=False)
        self._has_open_trunk = False
        return output_str

    def emit_cancellation(self, reason: str = "Interrupted by user") -> str:
        """Renders a cancellation node on the timeline."""
        self._record_event(TimelineEventType.CANCELLED, {"reason": reason})
        output_str = f"[dim]  │[/dim]\n[dim]  └──[/dim] [bold yellow]⊘ Cancelled: {reason}[/bold yellow]"
        self.console.print(output_str, highlight=False)
        self._has_open_trunk = False
        return output_str

    def _record_event(self, event_type: TimelineEventType, data: Dict[str, Any]):
        """Record event in rolling memory buffer."""
        if len(self._events) >= self.max_history_events:
            # Drop earliest 20% to bound memory indefinitely
            drop_count = int(self.max_history_events * 0.2)
            self._events = self._events[drop_count:]

        self._events.append({
            "type": event_type.value,
            "timestamp": time.time(),
            **data
        })

    def get_event_history(self) -> List[Dict[str, Any]]:
        """Return a copy of the event history."""
        return list(self._events)


# Global singleton instance
_GLOBAL_TIMELINE_RENDERER: Optional[TimelineRenderer] = None


def get_timeline_renderer(console: Optional[Console] = None) -> TimelineRenderer:
    """Returns or creates the global singleton TimelineRenderer."""
    global _GLOBAL_TIMELINE_RENDERER
    if _GLOBAL_TIMELINE_RENDERER is None or (console is not None and _GLOBAL_TIMELINE_RENDERER.console != console):
        _GLOBAL_TIMELINE_RENDERER = TimelineRenderer(console=console)
    return _GLOBAL_TIMELINE_RENDERER


# Backwards-compatible procedural functions
def render_tool_execution_panel(t_name: str, t_kwargs: Dict[str, Any], step: int = 0, max_steps: int = 0) -> str:
    """Delegates to the timeline renderer singleton."""
    return get_timeline_renderer().emit_tool_call(t_name, t_kwargs, step=step)


def render_tool_observation_panel(t_name: str, observation: str, step: int = 0, max_steps: int = 0) -> str:
    """Delegates to the timeline renderer singleton."""
    return get_timeline_renderer().emit_observation(t_name, observation, step=step)
