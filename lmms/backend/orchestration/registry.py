"""
ToolRegistry: Centralized registry for dynamic tool injection.
Separates lightweight discovery metadata from heavy full schemas.
Prevents unconditional injection of full schemas into prompt context.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import json


@dataclass
class ToolMetadata:
    """Lightweight metadata used for intent routing and candidate discovery."""
    id: str
    name: str
    category: str
    summary: str
    tags: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high
    requires_confirmation: bool = False
    estimated_tokens: int = 40
    dependencies: List[str] = field(default_factory=list)


@dataclass
class DynamicToolDefinition:
    """Full tool definition containing complete JSON parameter schema and callback."""
    metadata: ToolMetadata
    parameters: Dict[str, Any]  # JSON Schema format
    callback: Optional[Callable] = None
    instruction_module: Optional[str] = None
    enabled: bool = True
    available: bool = True

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def category(self) -> str:
        return self.metadata.category

    def to_openai_format(self) -> Dict[str, Any]:
        """Converts to standard OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.metadata.id,
                "description": self.metadata.summary,
                "parameters": self.parameters,
            }
        }

    def to_compact_prompt_format(self) -> str:
        """Compact single-line format for ReAct prompting."""
        # e.g. web_search: {"tool": "web_search", "kwargs": {"query": "str", "max_results": 5}}
        props = self.parameters.get("properties", {})
        sample_kwargs = {}
        for prop_name, prop_def in props.items():
            prop_type = prop_def.get("type", "string")
            if prop_type == "string":
                sample_kwargs[prop_name] = prop_def.get("default", "...")
            elif prop_type == "integer":
                sample_kwargs[prop_name] = prop_def.get("default", 0)
            elif prop_type == "boolean":
                sample_kwargs[prop_name] = prop_def.get("default", False)
            elif prop_type == "object":
                sample_kwargs[prop_name] = prop_def.get("default", {})
            else:
                sample_kwargs[prop_name] = "..."
        example_call = json.dumps({"tool": self.metadata.id, "kwargs": sample_kwargs})
        return f"- {self.metadata.id}: {example_call} ({self.metadata.summary})"


class ToolRegistry:
    """
    Central repository for all available tools in LMMs.
    Provides fast lookup, category indexing, and schema formatting.
    """

    def __init__(self):
        self._tools: Dict[str, DynamicToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}
        self._register_default_tools()

    def register(self, tool: DynamicToolDefinition, aliases: Optional[List[str]] = None):
        """Registers a tool definition."""
        self._tools[tool.id] = tool
        cat = tool.category
        if cat not in self._categories:
            self._categories[cat] = []
        if tool.id not in self._categories[cat]:
            self._categories[cat].append(tool.id)

        if aliases:
            for alias in aliases:
                self._aliases[alias] = tool.id

    def get(self, tool_id: str) -> Optional[DynamicToolDefinition]:
        """Resolves tool by ID or registered alias."""
        if tool_id in self._tools:
            return self._tools[tool_id]
        if tool_id in self._aliases:
            canonical_id = self._aliases[tool_id]
            return self._tools.get(canonical_id)

        # On-demand resolution for MCP tools (e.g. mcp__server__tool or server__tool)
        if tool_id.startswith("mcp__") or ("__" in tool_id and not tool_id.startswith("_")):
            parts = tool_id.split("__")
            server = parts[1] if parts[0] == "mcp" and len(parts) >= 3 else parts[0]
            name = parts[2] if parts[0] == "mcp" and len(parts) >= 3 else parts[1]
            dyn_def = DynamicToolDefinition(
                metadata=ToolMetadata(
                    id=tool_id,
                    name=f"MCP: {server}/{name}",
                    category=f"mcp_{server}",
                    summary=f"Dynamic MCP Tool {name} on {server}",
                    tags=["mcp", server, name],
                    risk_level="medium"
                ),
                parameters={"type": "object", "properties": {}}
            )
            setattr(dyn_def, "_is_mcp", True)
            setattr(dyn_def, "_mcp_server", server)
            setattr(dyn_def, "_mcp_orig_name", name)
            self.register(dyn_def)
            return dyn_def

        return None

    def sync_mcp_tools(self, mcp_manager: Any = None) -> int:
        """
        Dynamically imports and registers tools discovered from configured MCP servers.
        Exposes them as mcp__{server}__{tool} with clean aliases.
        """
        try:
            if mcp_manager is None:
                from lmms_mcp.manager import default_mcp_manager
                mcp_manager = default_mcp_manager

            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    tools = pool.submit(lambda: asyncio.run(mcp_manager.list_all_tools())).result()
            else:
                tools = loop.run_until_complete(mcp_manager.list_all_tools())

            count = 0
            for t in tools:
                server = t.get("server", "mcp")
                orig_name = t.get("name", "")
                if not orig_name:
                    continue

                tool_id = f"mcp__{server}__{orig_name}"
                alias1 = f"{server}.{orig_name}"
                alias2 = f"{server}__{orig_name}"
                aliases = [alias1, alias2]
                if orig_name not in self._tools and orig_name not in self._aliases:
                    aliases.append(orig_name)

                tool_def = DynamicToolDefinition(
                    metadata=ToolMetadata(
                        id=tool_id,
                        name=f"MCP: {server}/{orig_name}",
                        category=f"mcp_{server}",
                        summary=t.get("description", f"MCP Tool from {server} server: {orig_name}"),
                        tags=["mcp", server, orig_name],
                        risk_level="medium",
                        estimated_tokens=50
                    ),
                    parameters=t.get("inputSchema", {"type": "object", "properties": {}}),
                    callback=None
                )
                setattr(tool_def, "_is_mcp", True)
                setattr(tool_def, "_mcp_server", server)
                setattr(tool_def, "_mcp_orig_name", orig_name)
                self.register(tool_def, aliases=aliases)
                count += 1
            return count
        except Exception:
            return 0

    def get_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        tool = self.get(tool_id)
        return tool.metadata if tool else None

    def list_all_metadata(self) -> List[ToolMetadata]:
        return [tool.metadata for tool in self._tools.values() if tool.enabled]

    def get_by_category(self, category: str) -> List[DynamicToolDefinition]:
        tool_ids = self._categories.get(category, [])
        return [self._tools[tid] for tid in tool_ids if tid in self._tools and self._tools[tid].enabled]

    def get_metadata_by_category(self, category: str) -> List[ToolMetadata]:
        return [tool.metadata for tool in self.get_by_category(category)]

    def _register_default_tools(self):
        """Pre-registers the core built-in tools of LMMs."""
        # 1. Web Search
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="web_search",
                    name="Web Search",
                    category="search",
                    summary="Search the web for up-to-date online information, documentation, and news.",
                    tags=["search", "web", "online", "docs"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query terms"},
                        "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                    },
                    "required": ["query"]
                }
            ),
            aliases=["web.search", "search_web", "google_search"]
        )

        # 1b. DNS Enumeration & Domain Intelligence
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="dns.enumerate",
                    name="DNS Enumeration",
                    category="network",
                    summary="Discover and verify DNS records (A, AAAA, MX, NS, TXT, SOA) and validate active subdomains using authoritative DNS resolvers. Avoids blind HTTP probing.",
                    tags=["dns", "network", "domain", "subdomain", "records"],
                    risk_level="low",
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Target domain name (e.g. 'example.com')"},
                        "query_type": {"type": "string", "description": "Query scope: 'records', 'subdomains', or 'all'", "default": "all"},
                        "candidates": {"type": "array", "items": {"type": "string"}, "description": "Optional custom subdomain prefix candidates to validate"}
                    },
                    "required": ["domain"]
                },
                instruction_module="dns"
            ),
            aliases=["dns_enumerate", "dns.lookup", "dns_lookup", "enumerate_subdomains"]
        )

        # 2. Browser Navigation
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.open_url",
                    name="Browser Open URL",
                    category="browser",
                    summary="Open a website in browser runtime and return its interactive DOM.",
                    tags=["browser", "web", "dom", "navigate"],
                    risk_level="low",
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Full HTTP or HTTPS web address to navigate to"},
                        "headless": {"type": "boolean", "description": "Run browser headlessly or show UI", "default": False}
                    },
                    "required": ["url"]
                },
                instruction_module="browser"
            ),
            aliases=["open_url", "browser_open"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.get_interactive_dom",
                    name="Browser Get Interactive DOM",
                    category="browser",
                    summary="Extract clickable and input DOM elements labeled with discrete numerical IDs.",
                    tags=["browser", "dom", "elements"],
                    risk_level="low",
                    estimated_tokens=40,
                    dependencies=["browser.open_url"]
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Optional URL if navigating to a new page"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.click_element",
                    name="Browser Click Element",
                    category="browser",
                    summary="Click a button, link, or interactive element by numerical ID or selector.",
                    tags=["browser", "click", "interact"],
                    risk_level="low",
                    estimated_tokens=45,
                    dependencies=["browser.open_url"]
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Element ID number (e.g. '1') or CSS selector"},
                        "url": {"type": "string", "description": "Active page URL"}
                    },
                    "required": ["selector"]
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.fill_form",
                    name="Browser Fill Form",
                    category="browser",
                    summary="Fill multiple text inputs or form fields by ID number or selector.",
                    tags=["browser", "form", "input"],
                    risk_level="medium",
                    estimated_tokens=50,
                    dependencies=["browser.open_url"]
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "fields": {"type": "object", "description": "Key-value mapping of field IDs to input values"},
                        "url": {"type": "string", "description": "Active page URL"}
                    },
                    "required": ["fields"]
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.type",
                    name="Browser Type Text",
                    category="browser",
                    summary="Type text into a designated element and optionally press enter.",
                    tags=["browser", "type", "keyboard"],
                    risk_level="low",
                    estimated_tokens=45,
                    dependencies=["browser.open_url"]
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Target element ID or selector"},
                        "text": {"type": "string", "description": "Text to type"},
                        "press_enter": {"type": "boolean", "description": "Whether to press enter after typing", "default": False}
                    },
                    "required": ["selector", "text"]
                },
                instruction_module="browser"
            ),
            aliases=["browser.type_text"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.scrape_live",
                    name="Browser Scrape Live",
                    category="browser",
                    summary="Scrape text content from a live JavaScript-rendered webpage.",
                    tags=["browser", "scrape", "extract"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target webpage URL"},
                        "selector": {"type": "string", "description": "Optional CSS selector to narrow scraping scope"}
                    },
                    "required": ["url"]
                },
                instruction_module="browser"
            ),
            aliases=["browser.scrape"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.crawl_url",
                    name="Browser Deep Web Crawler",
                    category="browser",
                    summary="Autonomous deep web crawler using Crawl4AI. Extracts clean, full markdown text, author/metadata, and links from any website, article, or documentation page.",
                    tags=["browser", "crawl", "crawl4ai", "scrape", "research", "web"],
                    risk_level="low",
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Webpage URL to crawl"},
                        "css_selector": {"type": "string", "description": "Optional CSS selector to narrow crawling focus"},
                        "depth": {"type": "integer", "description": "Crawl depth for following links", "default": 1},
                        "max_pages": {"type": "integer", "description": "Maximum pages to crawl", "default": 1},
                        "include_images": {"type": "boolean", "description": "Include image links", "default": False},
                        "include_css": {"type": "boolean", "description": "Include CSS", "default": False}
                    },
                    "required": ["url"]
                },
                instruction_module="browser"
            ),
            aliases=["browser.crawl", "crawl_url", "crawl4ai"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="rag.search",
                    name="RAG Semantic Search",
                    category="rag",
                    summary="Search indexed workspace documents and crawled web knowledge using semantic vector search.",
                    tags=["rag", "search", "vector", "memory", "knowledge"],
                    risk_level="safe",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Semantic query to search for in vector memory"},
                        "k": {"type": "integer", "description": "Number of top results to retrieve", "default": 5}
                    },
                    "required": ["query"]
                },
                instruction_module="rag"
            ),
            aliases=["vector_db.search"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="rag.crawl_url",
                    name="RAG Ingest Web URL",
                    category="rag",
                    summary="Crawl an external website or documentation URL with Crawl4AI and ingest it into the workspace vector knowledge base for RAG.",
                    tags=["rag", "crawl", "ingest", "web", "learn"],
                    risk_level="low",
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target webpage or documentation URL to crawl and index"},
                        "css_selector": {"type": "string", "description": "Optional CSS selector"},
                        "depth": {"type": "integer", "description": "Crawl depth for following links", "default": 1},
                        "max_pages": {"type": "integer", "description": "Maximum pages to crawl", "default": 1},
                        "include_images": {"type": "boolean", "description": "Include images in extraction", "default": False},
                        "include_css": {"type": "boolean", "description": "Include CSS stylesheets", "default": False}
                    },
                    "required": ["url"]
                },
                instruction_module="rag"
            ),
            aliases=["rag.ingest_url"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.screenshot",
                    name="Browser Screenshot",
                    category="browser",
                    summary="Capture a PNG screenshot of the current browser viewport.",
                    tags=["browser", "screenshot", "image"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "save_path": {"type": "string", "description": "Filepath to save the screenshot", "default": "/tmp/lmms_browser.png"},
                        "url": {"type": "string", "description": "Optional webpage URL"}
                    }
                }
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.scroll",
                    name="Browser Scroll",
                    category="browser",
                    summary="Scroll the browser viewport up or down by a specified pixel amount.",
                    tags=["browser", "scroll", "view"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "Scroll direction: 'up' or 'down'", "default": "down"},
                        "amount": {"type": "integer", "description": "Pixel scroll amount", "default": 1000},
                        "url": {"type": "string", "description": "Optional page URL"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.press_key",
                    name="Browser Press Key",
                    category="browser",
                    summary="Press a keyboard key (Enter, Tab, Escape, Backspace) on the active page.",
                    tags=["browser", "keyboard", "key"],
                    risk_level="low",
                    estimated_tokens=35
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Key name (e.g. 'Enter', 'Tab', 'Escape')", "default": "Enter"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.open_authenticated",
                    name="Browser Open Authenticated",
                    category="browser",
                    summary="Open a browser session using existing saved user profile or session cookies.",
                    tags=["browser", "auth", "session", "profile"],
                    risk_level="high",
                    requires_confirmation=True,
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Web address to open"},
                        "user_data_dir": {"type": "string", "description": "Path to user browser data directory", "default": "~/.lmms/browser_profile"},
                        "profile_name": {"type": "string", "description": "Profile directory name", "default": "Default"},
                        "headless": {"type": "boolean", "description": "Run in background", "default": True}
                    },
                    "required": ["url"]
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.observe_page",
                    name="Browser Observe Page",
                    category="browser",
                    summary="Extract comprehensive website-independent observation: URL, title, forms, inputs, contenteditable editors, and live action buttons.",
                    tags=["browser", "dom", "observe", "editor", "form"],
                    risk_level="safe",
                    estimated_tokens=55
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Optional URL to observe"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.verify_editor_content",
                    name="Browser Verify Editor Content",
                    category="browser",
                    summary="Verifies whether an editor, textarea, or contenteditable area on the active page actually contains the drafted content.",
                    tags=["browser", "editor", "verify", "content"],
                    risk_level="safe",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Element ID number or selector of editor"},
                        "expected_substring": {"type": "string", "description": "Substring expected to be present in the editor"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.save_draft",
                    name="Browser Save Draft",
                    category="browser",
                    summary="Dynamically discovers and clicks the website's draft saving control, then verifies that the draft was persisted.",
                    tags=["browser", "draft", "save", "persist"],
                    risk_level="medium",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "button_selector": {"type": "string", "description": "Optional explicit selector or ID for the save button"}
                    }
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="browser.request_publication_approval",
                    name="Request Publication Approval",
                    category="browser",
                    summary="Pauses and asks for explicit human approval before clicking a public submit/publish button on any website.",
                    tags=["browser", "publish", "approval", "confirm"],
                    risk_level="medium",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "target_selector": {"type": "string", "description": "Selector or ID of the publish button"},
                        "action_type": {"type": "string", "description": "Type of action (publish_post, ask_question, submit_form)", "default": "publish_post"},
                        "content_summary": {"type": "string", "description": "Brief summary of the content to be published"}
                    },
                    "required": ["target_selector"]
                },
                instruction_module="browser"
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="account.get_current_identity",
                    name="Get Current Account Identity",
                    category="system",
                    summary="Safely retrieve the user's available browser profile accounts and environment identity (e.g. primary email, git config user, browser profiles). Does NOT expose passwords or session keys.",
                    tags=["account", "identity", "email", "user", "profile"],
                    risk_level="low",
                    estimated_tokens=35
                ),
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                instruction_module="browser"
            ),
            aliases=["browser.get_account_context"]
        )

        # 3. File Operations
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.read",
                    name="File Read",
                    category="files",
                    summary="Read contents of a file within the workspace boundary.",
                    tags=["files", "read", "fs"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file to read"}
                    },
                    "required": ["path"]
                }
            ),
            aliases=["file.read", "read_file"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.write",
                    name="File Write",
                    category="files",
                    summary="Write text content to a file within the workspace boundary.",
                    tags=["files", "write", "fs"],
                    risk_level="medium",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file to write"},
                        "content": {"type": "string", "description": "Text content to save"}
                    },
                    "required": ["path", "content"]
                }
            ),
            aliases=["file.write", "write_file"]
        )

        # 8b. Surgical File Tools
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.view_file_outline",
                    name="View File Outline",
                    category="files",
                    summary="View structural outline of a file showing all classes, methods, and functions with exact line ranges (uses AST for Python).",
                    tags=["files", "outline", "ast", "code"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file to inspect"}
                    },
                    "required": ["path"]
                }
            ),
            aliases=["view_file_outline", "file.view_outline", "view_outline"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.read_file_lines",
                    name="Read File Lines",
                    category="files",
                    summary="Read a specific range of lines from a file with line numbers prefixed.",
                    tags=["files", "read", "lines", "slice"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file to read"},
                        "start_line": {"type": "integer", "description": "Starting line number (1-indexed)"},
                        "end_line": {"type": "integer", "description": "Ending line number (inclusive)"}
                    },
                    "required": ["path", "start_line", "end_line"]
                }
            ),
            aliases=["read_file_lines", "file.read_lines", "read_lines"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.replace_in_file",
                    name="Replace in File",
                    category="files",
                    summary="Surgically replace a code block in a file with built-in AST compile validation.",
                    tags=["files", "edit", "replace", "patch", "diff"],
                    risk_level="medium",
                    estimated_tokens=50
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file to modify"},
                        "old_code": {"type": "string", "description": "Exact block of code to search and replace"},
                        "new_code": {"type": "string", "description": "New replacement code block"}
                    },
                    "required": ["path", "old_code", "new_code"]
                }
            ),
            aliases=["replace_in_file", "file.replace", "replace_code"]
        )

        # 4. Codex-Grade Apply Patch Engine
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="patch.apply",
                    name="Apply Patch",
                    category="files",
                    summary="Apply multi-file patches using OpenAI Codex format ('*** Begin Patch') or Unified Diff with AST validation and atomic rollback.",
                    tags=["patch", "diff", "edit", "codex", "surgical", "files"],
                    risk_level="medium",
                    estimated_tokens=55
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "patch": {"type": "string", "description": "Patch content in OpenAI Codex format (*** Begin Patch ... *** End Patch) or Unified Diff format"},
                        "dry_run": {"type": "boolean", "description": "Pre-flight validation without modifying files on disk", "default": False}
                    },
                    "required": ["patch"]
                }
            ),
            aliases=["apply_patch", "patch", "apply_diff"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.list",
                    name="File List",
                    category="files",
                    summary="List files and folder tree structure within the workspace directory.",
                    tags=["files", "list", "fs", "ls"],
                    risk_level="low",
                    estimated_tokens=35
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to directory to list", "default": "."}
                    }
                }
            ),
            aliases=["files.list_folder", "list_folder", "file.list", "fs.list"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="files.delete",
                    name="File Delete",
                    category="files",
                    summary="Safely delete a file or directory within workspace boundary (requires confirm=True).",
                    tags=["files", "delete", "rm"],
                    risk_level="high",
                    requires_confirmation=True,
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File or folder path to delete"},
                        "confirm": {"type": "boolean", "description": "Explicit confirmation flag", "default": False}
                    },
                    "required": ["path"]
                }
            ),
            aliases=["file.delete", "delete_file"]
        )

        # 4. Terminal Commands
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="terminal.run",
                    name="Terminal Run",
                    category="terminal",
                    summary="Execute a sandboxed shell command inside the workspace directory.",
                    tags=["terminal", "shell", "bash", "command"],
                    risk_level="high",
                    requires_confirmation=False,
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Bash command string to execute"}
                    },
                    "required": ["command"]
                }
            ),
            aliases=["system.terminal", "run_terminal"]
        )

        # 5. Desktop App Launcher
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="app.launch",
                    name="App Launch",
                    category="apps",
                    summary="Launch a desktop application or open a file/URL in the desktop environment.",
                    tags=["app", "desktop", "launch", "os"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name_or_target": {"type": "string", "description": "Application name (e.g. 'calculator', 'chrome', 'code') or target URL"}
                    },
                    "required": ["app_name_or_target"]
                }
            ),
            aliases=["os.launch_app", "launch_app"]
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="app.list",
                    name="App List",
                    category="apps",
                    summary="List installed desktop applications matching an optional filter.",
                    tags=["app", "desktop", "list"],
                    risk_level="low",
                    estimated_tokens=35
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "filter_query": {"type": "string", "description": "Filter application names", "default": ""}
                    }
                }
            )
        )

        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="app.close",
                    name="App Close",
                    category="apps",
                    summary="Terminate or close a running desktop application by name or window title.",
                    tags=["app", "desktop", "close", "kill"],
                    risk_level="medium",
                    estimated_tokens=35
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Application process or window name to terminate"}
                    },
                    "required": ["app_name"]
                }
            ),
            aliases=["close_app", "kill_app"]
        )

        # 6. Messaging & Alerts
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="message.send",
                    name="Message Send",
                    category="messaging",
                    summary="Send a desktop notification or chat message.",
                    tags=["message", "alert", "notification"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "description": "Target platform: 'desktop', 'telegram', 'discord', 'slack'", "default": "desktop"},
                        "message": {"type": "string", "description": "Notification message body"},
                        "recipient": {"type": "string", "description": "Optional recipient or notification title"}
                    },
                    "required": ["message"]
                }
            )
        )

        # 7. Security Report Generation
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="security.generate_report",
                    name="Generate Security Report",
                    category="security",
                    summary="Generate a comprehensive markdown report summarizing audit findings.",
                    tags=["security", "report", "markdown"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "findings_summary": {"type": "string", "description": "Executive summary of findings to include"}
                    },
                    "required": ["findings_summary"]
                }
            )
        )

        # 8. Vector DB / RAG Search
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="vector_db.search",
                    name="Vector DB Search",
                    category="rag",
                    summary="Search indexed workspace codebase knowledge using vector embeddings.",
                    tags=["rag", "vector", "search", "codebase"],
                    risk_level="low",
                    estimated_tokens=45
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Semantic search query string"}
                    },
                    "required": ["query"]
                }
            )
        )

        # 9. Dynamic Discovery Meta-Tool
        self.register(
            DynamicToolDefinition(
                metadata=ToolMetadata(
                    id="discover_additional_tool",
                    name="Discover Additional Tool",
                    category="meta",
                    summary="Request and dynamically load an additional tool capability into your active context at runtime.",
                    tags=["meta", "discover", "tools", "capability"],
                    risk_level="low",
                    estimated_tokens=40
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "capability": {
                            "type": "string",
                            "description": "Name or capability of the missing tool required (e.g., 'browser.open_url', 'web_search', 'files.read', 'terminal.run')."
                        }
                    },
                    "required": ["capability"]
                }
            ),
            aliases=["discover_tool", "request_tool", "load_tool"]
        )

