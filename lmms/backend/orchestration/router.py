"""
IntentRouter: High-speed deterministic and heuristic classification of user intent.
Differentiates between discussing a capability and requesting its execution.
Uses conversation history to resolve ambiguous follow-ups without running a secondary LLM.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class IntentType(str, Enum):
    NORMAL_CHAT = "normal_chat"
    GENERAL_KNOWLEDGE = "general_knowledge"
    CODING = "coding"
    WORKSPACE_FILE_OPS = "workspace_file_ops"
    WEB_SEARCH = "web_search"
    BROWSER_AUTOMATION = "browser_automation"
    DATA_ANALYSIS = "data_analysis"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"
    TOOL_RESEARCH = "tool_research"
    FOLLOW_UP = "follow_up"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    requires_tools: bool
    suggested_categories: List[str] = field(default_factory=list)
    is_follow_up: bool = False
    task_instructions: Optional[str] = None
    reason: str = ""


class IntentRouter:
    """
    Fast, lightweight, deterministic intent classifier.
    Under 1ms evaluation latency. Zero secondary LLM overhead.
    """

    def __init__(self):
        # Greetings & chit-chat patterns
        self._greeting_patterns = [
            r"^(hi|hello|hey|howdy|hola|namaste|bonjour|greetings|yo)\b[!?.]*$",
            r"^(good\s+(morning|afternoon|evening|day|night))\b[!?.]*$",
            r"^(how\s+are\s+you|who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do)\b[!?.]*$",
            r"^(thank\s+you|thanks|thx|cool|awesome|great|ok|okay|nice)\b[!?.]*$",
            r"^(bye|goodbye|see\s+you|later)\b[!?.]*$",
        ]

        # Conceptual / discussion patterns (discussing vs executing)
        self._discussion_prefixes = [
            r"^what\s+(is|are|was|were)\b",
            r"^explain(\s+to\s+me)?\b",
            r"^how\s+(does|do|can|would|should)\b",
            r"^tell\s+me\s+about\b",
            r"^describe\b",
            r"^define\b",
            r"^why\s+(is|are|do|does)\b",
            r"^give\s+me\s+an\s+overview\s+of\b",
            r"^difference\s+between\b",
            r"^compare\s+[a-zA-Z0-9_-]+\s+and\s+[a-zA-Z0-9_-]+\b",
        ]

        # Coding keywords & concepts
        self._coding_patterns = [
            r"\b(explain|understand|how|write|create|implement|refactor|debug|fix|optimize)\s+.*?\b(python|javascript|typescript|c\+\+|rust|bash|sql|function|class|decorator|decorators|script|algorithm|regex)\b",
            r"\b(python|javascript|typescript|c\+\+|rust|bash|sql)\s+(decorator|decorators|generator|concurrency|asyncio|closure|pointer|memory|thread)\b",
            r"\bdef\s+[a-zA-Z_]\w*\(",
            r"\bfunction\s+[a-zA-Z_]\w*\(",
            r"\bclass\s+[a-zA-Z_]\w*[:\{]",
            r"\btraceback\s+\(most\s+recent\s+call\s+last\):",
            r"\b(syntaxerror|typeerror|valueerror|indexerror|keyerror|importerror|nameerror|attributeerror)\b",
        ]

        # File and workspace execution operations
        self._file_ops_patterns = [
            r"\b(read|open|inspect|cat|view|show|edit|write|save|delete|create)\s+(file|the\s+file|code\s+in|contents\s+of)\b",
            r"\b(git\s+(status|diff|add|commit|push|pull|branch|checkout|log))\b",
            r"\b(list\s+(files|directory|folder|repo|workspace))\b",
            r"\b(in\s+this\s+repo|in\s+this\s+workspace|in\s+the\s+project|in\s+file\s+['\"][^'\"]+['\"])\b",
            r"(\b(src|tests|docs|package\.json|setup\.py|requirements\.txt|README\.md)\b)",
        ]

        # Web search action patterns
        self._search_patterns = [
            r"\b(search\s+(the\s+web|online|for|google|ddg|duckduckgo))\b",
            r"\b(find|search|lookup)\s+(the\s+)?(documentation|docs|online|info)\b",
            r"\b(find\s+online|look\s+up\s+online|current\s+price|latest\s+news|weather\s+in|who\s+won|stock\s+price)\b",
            r"\b(search\s+for\s+the\s+latest\s+.*documentation)\b",
            r"\b(latest\s+(release|version|announcement|docs)\s+of)\b",
        ]


        # Browser automation action patterns
        self._browser_patterns = [
            r"\b(open|navigate\s+to|browse\s+to|visit)\s+(https?://|www\.|this\s+website|the\s+website|webpage)\b",
            r"\b(click\s+(on\s+)?(button|link|element|tab|id|selector))\b",
            r"\b(fill\s+(in\s+)?(the\s+)?(form|input|field|login|password|email))\b",
            r"\b(take\s+(a\s+)?screenshot\s+of\s+(the\s+)?(page|website|browser))\b",
            r"\b(scrape|extract\s+data\s+from)\s+(the\s+)?(live\s+)?(website|webpage|page|url|dom)\b",
            r"https?://[^\s]+",
        ]

        # Data analysis & charts
        self._data_analysis_patterns = [
            r"\b(draw|plot|create|show|generate)\s+(a\s+)?(terminal\s+)?(chart|graph|bar\s+chart|pie\s+chart|plotext|histogram)\b",
            r"\b(visualize\s+(this\s+)?data|analyze\s+the\s+csv|summary\s+statistics)\b",
        ]

        # Multi-step workflow patterns
        self._workflow_patterns = [
            r"\b(research\s+.*\s+and\s+(compare|generate\s+a\s+report|summarize\s+findings))\b",
            r"\b(step[- ]by[- ]step|plan\s+and\s+execute|multi[- ]step|comprehensive\s+audit)\b",
            r"\b(compare\s+(three|several|different)\s+(solutions|options|approaches|tools)\s+and)\b",
            r"\b(first\s+.*,\s+then\s+.*,\s+finally\s+.*)\b",
        ]

        # Security & Tool research
        self._security_research_patterns = [
            r"\b(cve[-_]\d{4}[-_]\d+|cve\s+lookup|vulnerability\s+details|exploit\s+db)\b",
            r"\b(kali\s+(tool|manual|doc|help)|nmap\s+options|wireshark\s+filter)\b",
        ]

        # Follow-up patterns
        self._follow_up_patterns = [
            r"^(yes|yeah|yep|sure|proceed|continue|go\s+ahead|do\s+it|confirm)\b[!?.]*$",
            r"^(no|nope|cancel|stop|abort)\b[!?.]*$",
            r"^(next|step\s+\d+|now\s+do|now\s+click|now\s+read|now\s+open)\b",
            r"^(what\s+about\s+that|summarize\s+(it|that|this))\b",
        ]

    def route(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        active_mode: str = "/fast",
        current_workspace: Optional[str] = None
    ) -> IntentResult:
        """
        Determines the IntentResult for a given query and history.
        """
        clean_query = query.strip()
        lower_query = clean_query.lower()

        # 1. Check for normal chat greetings first (deterministic, zero tools)
        for pattern in self._greeting_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.NORMAL_CHAT,
                    confidence=0.98,
                    requires_tools=False,
                    suggested_categories=[],
                    reason="Matched conversational greeting pattern"
                )

        # 2. Check for short follow-up messages using conversation history
        if self._is_short_follow_up(lower_query):
            if conversation_history and len(conversation_history) >= 2:
                inferred = self._resolve_follow_up_intent(clean_query, conversation_history)
                if inferred:
                    return inferred

        # 3. Check for Multi-step workflows
        for pattern in self._workflow_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.MULTI_STEP_WORKFLOW,
                    confidence=0.92,
                    requires_tools=True,
                    suggested_categories=["search", "analysis", "report"],
                    task_instructions="Plan the multi-step execution. Formulate search queries, extract key comparisons, and synthesize a structured report.",
                    reason="Matched multi-step research or workflow pattern"
                )

        # 4. Check for discussion of capabilities vs execution
        # "What is browser automation?" or "Explain how web search works"
        is_discussion = any(re.search(pat, lower_query) for pat in self._discussion_prefixes)

        # 5. Check Browser Automation (Action)
        if not is_discussion:
            for pattern in self._browser_patterns:
                if re.search(pattern, lower_query, re.IGNORECASE):
                    return IntentResult(
                        intent=IntentType.BROWSER_AUTOMATION,
                        confidence=0.90,
                        requires_tools=True,
                        suggested_categories=["browser"],
                        task_instructions="The user requested browser navigation or interaction. Inspect the live DOM and interact cleanly.",
                        reason="Matched browser navigation/automation action"
                    )

        # 6. Check Web Search (Action)
        if not is_discussion:
            for pattern in self._search_patterns:
                if re.search(pattern, lower_query, re.IGNORECASE):
                    return IntentResult(
                        intent=IntentType.WEB_SEARCH,
                        confidence=0.90,
                        requires_tools=True,
                        suggested_categories=["search"],
                        task_instructions="Search online for current information and return relevant, accurate summaries.",
                        reason="Matched web search action pattern"
                    )

        # 7. Check Data Analysis / Terminal Plots
        for pattern in self._data_analysis_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.DATA_ANALYSIS,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["terminal", "python"],
                    task_instructions="Use terminal tools and plotext to create clear terminal-based visualizations.",
                    reason="Matched data analysis/charting pattern"
                )

        # 8. Check Security & Tool Research
        for pattern in self._security_research_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.TOOL_RESEARCH,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["security", "search"],
                    task_instructions="Retrieve security vulnerability or tool reference documentation.",
                    reason="Matched security/tool lookup pattern"
                )

        # 9. Check Workspace / File Operations
        for pattern in self._file_ops_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.WORKSPACE_FILE_OPS,
                    confidence=0.85,
                    requires_tools=True,
                    suggested_categories=["files", "terminal"],
                    task_instructions="Perform requested workspace file operations safely within boundary limits.",
                    reason="Matched workspace or file operation pattern"
                )

        # 10. Check Coding / Debugging
        for pattern in self._coding_patterns:
            if re.search(pattern, lower_query, re.IGNORECASE):
                # If it's pure explanation (e.g. "Explain how Python decorators work"), no tools needed
                if is_discussion or "explain" in lower_query or "how does" in lower_query or "what is" in lower_query:
                    return IntentResult(
                        intent=IntentType.CODING,
                        confidence=0.90,
                        requires_tools=False,
                        suggested_categories=[],
                        task_instructions="Provide a clear, accurate technical explanation with high-quality code examples.",
                        reason="Matched coding explanation (pure reasoning, no filesystem/terminal execution needed)"
                    )
                # If explicit workspace editing is hinted and workspace is set:
                if current_workspace and current_workspace != "None" and any(k in lower_query for k in ["project", "repo", "file", "fix"]):
                    return IntentResult(
                        intent=IntentType.CODING,
                        confidence=0.85,
                        requires_tools=True,
                        suggested_categories=["files", "terminal"],
                        task_instructions="Inspect code in workspace, diagnose the issue, and apply tested fixes.",
                        reason="Matched coding task targeting workspace files"
                    )
                return IntentResult(
                    intent=IntentType.CODING,
                    confidence=0.85,
                    requires_tools=False,
                    suggested_categories=[],
                    task_instructions="Generate robust, well-documented code addressing the user's specification.",
                    reason="Matched code generation/debugging query without workspace file targets"
                )

        # 11. Discussion prefix -> General Knowledge
        if is_discussion:
            return IntentResult(
                intent=IntentType.GENERAL_KNOWLEDGE,
                confidence=0.85,
                requires_tools=False,
                suggested_categories=[],
                reason="Matched conceptual question/explanation prefix"
            )

        # 12. Check explicit CLI mode overrides
        if active_mode == "/code":
            return IntentResult(
                intent=IntentType.CODING,
                confidence=0.80,
                requires_tools=bool(current_workspace and current_workspace != "None"),
                suggested_categories=["files", "terminal"] if current_workspace and current_workspace != "None" else [],
                reason="Active CLI mode is /code"
            )
        elif active_mode == "/research":
            return IntentResult(
                intent=IntentType.WEB_SEARCH,
                confidence=0.80,
                requires_tools=True,
                suggested_categories=["search"],
                reason="Active CLI mode is /research"
            )

        # 13. Safe default fallback: Normal conversation / General knowledge without tools
        return IntentResult(
            intent=IntentType.NORMAL_CHAT,
            confidence=0.60,
            requires_tools=False,
            suggested_categories=[],
            reason="Default safe fallback for unclassified general text"
        )

    def _is_short_follow_up(self, query: str) -> bool:
        if len(query.split()) > 10:
            return False
        for pat in self._follow_up_patterns:
            if re.search(pat, query, re.IGNORECASE):
                return True
        return False

    def _resolve_follow_up_intent(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[IntentResult]:
        """
        Inspect recent turns to identify active tool context for short follow-ups.
        """
        # Search backwards through the last few assistant/tool turns
        for msg in reversed(conversation_history[-4:]):
            content = str(msg.get("content", ""))
            
            # If previous message contained browser observations or tool calls
            if "browser." in content or "open_url" in content or "<observation>" in content and "DOM" in content:
                return IntentResult(
                    intent=IntentType.BROWSER_AUTOMATION,
                    confidence=0.85,
                    requires_tools=True,
                    suggested_categories=["browser"],
                    is_follow_up=True,
                    task_instructions="Continue the browser automation workflow based on previous turn state.",
                    reason="Follow-up continuing active browser interaction"
                )

            # If previous message was web search
            if "web_search" in content or "Search results" in content:
                return IntentResult(
                    intent=IntentType.WEB_SEARCH,
                    confidence=0.80,
                    requires_tools=True,
                    suggested_categories=["search"],
                    is_follow_up=True,
                    reason="Follow-up continuing search / information retrieval"
                )

            # If previous message was file/terminal
            if "files." in content or "terminal.run" in content:
                return IntentResult(
                    intent=IntentType.WORKSPACE_FILE_OPS,
                    confidence=0.80,
                    requires_tools=True,
                    suggested_categories=["files", "terminal"],
                    is_follow_up=True,
                    reason="Follow-up continuing file or terminal operations"
                )

        return None
