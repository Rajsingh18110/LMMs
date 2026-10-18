"""
IntentRouter: High-speed deterministic and heuristic classification of user intent.
Differentiates between discussing a capability and requesting its execution.
Uses conversation history to resolve ambiguous follow-ups without running a secondary LLM.
Includes action-verb fallbacks, Hinglish support, typo resilience, and confidence scoring.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set


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
    Fast, lightweight, deterministic intent classifier with action-verb fallback.
    Under 0.2ms evaluation latency. Zero secondary LLM overhead.
    """

    CONFIDENCE_THRESHOLD: float = 0.70

    # Core Action Verbs: English, Typos, and Hinglish
    ACTION_VERBS: Set[str] = {
        "open", "run", "fix", "check", "create", "delete", "search",
        "install", "send", "edit", "find", "cat", "view", "ls", "show",
        "grep", "debug", "patch", "execute", "test", "save", "write",
        "download", "scrape", "click", "inspect", "diff", "status",
        # Common typos
        "serach", "sreach", "opn", "fiel", "chekc", "chck", "brower",
        "repot", "fnd", "dlete",
        # Hinglish action verbs
        "kholo", "chalao", "theek", "dhundo", "banao", "hatao", "bhejo",
        "padh", "likho", "dikhao", "dekho", "khojo"
    }

    def __init__(self):
        # Greetings & chit-chat patterns (strict matches)
        self._greeting_patterns = [
            r"^(hi|hello|hey|howdy|hola|namaste|bonjour|greetings|yo|sup)\b[!?.]*$",
            r"^(good\s+(morning|afternoon|evening|day|night))\b[!?.]*$",
            r"^(how\s+are\s+you(\s+doing)?(\s+today)?|who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do)\b[!?.]*$",
            r"^(thank\s+you(\s+so\s+much)?|thanks(\s+a\s+lot)?|thx|cool|awesome|great(\s+job)?|ok|okay|nice)\b[!?.]*$",
            r"^(bye|goodbye|see\s+you(\s+later)?|later)\b[!?.]*$",
            r"^(kaise\s+ho(\s+bhai)?|kya\s+haal\s+hai|kya\s+chal\s+raha\s+hai)\b[!?.]*$",
            r"^(help|who\s+am\s+i\s+talking\s+to\??|are\s+you\s+an\s+ai\??)\b[!?.]*$",
        ]

        # Conceptual / discussion prefixes (discussing vs executing)
        self._discussion_prefixes = [
            r"^what\s+(is|are|was|were)\b",
            r"^what\s+does\b",
            r"^explain(\s+to\s+me)?\b",
            r"^how\s+(does|do|can|would|should)\b",
            r"^tell\s+me\s+about\b",
            r"^describe\b",
            r"^define\b",
            r"^why\s+(is|are|do|does)\b",
            r"^give\s+me\s+an\s+overview\s+of\b",
            r"^difference\s+between\b",
            r"^compare\s+[a-zA-Z0-9_-]+\s+(and|vs)\s+[a-zA-Z0-9_-]+\b",
            r"^who\s+(wrote|created|invented|discovered)\b",
        ]

        # File and workspace execution operations
        self._file_ops_patterns = [
            r"\b(read|open|inspect|cat|view|show|edit|write|save|delete|create)\s+(file|the\s+file|code\s+in|contents\s+of|lines?\s+\d+)\b",
            r"\b(git\s+(status|diff|add|commit|push|pull|branch|checkout|log))\b",
            r"\b(list\s+(all\s+)?(files|directory|folder|repo|workspace))\b",
            r"\b(find\s+all\s+\.[a-zA-Z0-9]+\s+files|grep\s+for|find\s+where)\b",
            r"\b(in\s+this\s+repo|in\s+this\s+workspace|in\s+the\s+project|in\s+file\s+['\"][^'\"]+['\"])\b",
            r"(\b(src|tests|docs|package\.json|setup\.py|requirements\.txt|README\.md|config\.json|main\.py|launcher\.py)\b)",
            r"^(ls(\s+-[a-zA-Z]+)?|status|diff|logs)\b",
            r"\b(disk\s+space|check\s+disk\s+space|install\s+dependencies|delete\s+(the\s+)?temporary\s+files)\b",
            r"\b(send\s+an?\s+email|create\s+a\s+new\s+python\s+file|edit\s+settings)\b",
            # Hinglish & Typos
            r"\b(ye\s+file|fiel|folder\s+me|directory\s+me|naya\s+directory|naya\s+file)\b.*?\b(open|read|check|kholo|dikhao|padh|banao)\b",
            r"\b(terminal\s+chalao|ls\s+karo|dir\s+karo|opn\s+file|chekc\s+git)\b",
        ]

        # Web search action patterns
        self._search_patterns = [
            r"\b(search\s+(the\s+web|online|for|google|ddg|duckduckgo))\b",
            r"\b(find|search|lookup)\s+(the\s+)?(documentation|docs|online|info)\b",
            r"\b(find\s+online|look\s+up\s+online|current\s+price|latest\s+news|weather\s+in|who\s+won|stock\s+price)\b",
            r"\b(search\s+for\s+the\s+latest\s+.*(documentation|news|feature))\b",
            r"\b(latest\s+(release|version|announcement|docs|news)\s+of)\b",
            r"\b(latest\s+news\s+on|release\s+notes)\b",
            # Hinglish & Typos
            r"\b(google|net|online)\s+(pe|par)\s+(dhundo|search|khojo)\b",
            r"\b(serach|sreach)\s+(the\s+web|online|latest|for)\b",
            r"\b(kuch\s+naya\s+information|search\s+for\s+documentation)\b",
        ]

        # Browser automation action patterns
        self._browser_patterns = [
            r"\b(open|navigate\s+to|browse\s+to|visit)\s+(https?://|www\.|this\s+website|the\s+website|webpage|[a-zA-Z0-9.-]+\.(org|com|net|io|edu|gov))\b",
            r"\b(click\s+(on\s+)?(button|link|element|tab|id|selector))\b",
            r"\b(fill\s+(in\s+)?(the\s+)?(form|input|field|login|password|email|username))\b",
            r"\b(take\s+(a\s+)?screenshot\b.*)",
            r"\b(scrape|extract\s+data\s+from)\s+(the\s+)?(live\s+)?(website|webpage|page|url|dom)\b",
            r"\b(get\s+interactive\s+dom|scrape\s+the\s+live\s+dom)\b",
            r"https?://[^\s]+",
            # Hinglish & Typos
            r"\b(website|webpage|page)\s+(kholo|open\s+karo)\b.*?\b(browser|dekho)\b",
            r"\b(browser|brower)\s+me\s+(open|kholo)\b",
            r"\b(opn\s+.*?\s+in\s+brower|brower\s+me)\b",
        ]

        # Coding keywords & concepts
        self._coding_patterns = [
            r"\b(explain|understand|how|write|create|implement|refactor|debug|fix|optimize)\s+.*?\b(python|javascript|typescript|c\+\+|rust|bash|sql|function|class|decorator|decorators|script|algorithm|regex)\b",
            r"\b(python|javascript|typescript|c\+\+|rust|bash|sql)\s+(decorator|decorators|generator|concurrency|asyncio|closure|pointer|memory|thread|mro)\b",
            r"\b(quicksort|binary\s+search|singleton\s+pattern|synchronous\s+and\s+asynchronous|interface\s+vs\s+type)\b",
            r"\bdef\s+[a-zA-Z_]\w*\(",
            r"\bfunction\s+[a-zA-Z_]\w*\(",
            r"\bclass\s+[a-zA-Z_]\w*[:\{]",
            r"\btraceback\s+\(most\s+recent\s+call\s+last\):",
            r"\b(syntaxerror|typeerror|valueerror|indexerror|keyerror|importerror|nameerror|attributeerror)\b",
            r"\b(script\s+fails|fix\s+the\s+bug|debug\s+the\s+syntax\s+error|refactor\s+the|write\s+unit\s+tests)\b",
            # Hinglish
            r"\b(script|code)\s+me\s+(error|bug)\b.*?\b(theek|fix)\s+karo\b",
            r"\bye\s+code\s+(debug|fix|theek)\s+karo\b",
        ]

        # Data analysis & charts
        self._data_analysis_patterns = [
            r"\b(draw|plot|create|show|generate)\s+(a\s+)?(terminal\s+)?(chart|graph|bar\s+chart|pie\s+chart|plotext|histogram|line\s+chart)\b",
            r"\b(plot|graph|chart|visualize)\s+.*?\b(plotext|cpu|memory|consumption|latency|tokens|data|trend|distribution)\b",
            r"\b(visualize\s+(this\s+)?data|analyze\s+the\s+csv|summary\s+statistics|distribution\s+of\s+tokens)\b",
            r"\b(chart\s+the\s+memory|chart\s+the\s+error\s+rate|plot\s+cpu\s+usage|plot\s+a\s+histogram|plot\s+chart)\b",
            # Hinglish
            r"\b(plotext\s+se\s+chart|terminal\s+me\s+graph\s+banao|plotext)\b",
        ]

        # Multi-step workflow patterns
        self._workflow_patterns = [
            r"\b(research\s+.*\s+and\s+(compare|generate\s+a\s+report|summarize\s+findings|synthesize|compile))\b",
            r"\b(step[- ]by[- ]step|plan\s+and\s+execute|multi[- ]step|comprehensive\s+audit)\b",
            r"\b(compare\s+(three|several|different)\s+(solutions|options|approaches|tools|models|databases)\s+and)\b",
            r"\b(investigate|analyze|research)\s+.*?\b(compare|findings\s+report|compile\s+a\s+report|synthesize|summary)\b",
            r"\b(first\s+.*,\s+then\s+.*,\s+finally\s+.*)\b",
            r"\b(investigate\s+.*\s+and\s+generate\s+a\s+report)\b",
            # Hinglish & Typos
            r"\b(repot\s+banao|report\s+banao)\s+.*?\b(compare|audit)\b",
        ]

        # Security & Tool research
        self._security_research_patterns = [
            r"\b(cve[-_]\d{4}[-_]\d+|cve\s+lookup|cve\s+details|vulnerability\s+details|exploit\s+db)\b",
            r"\b(kali\s+(tool|manual|doc|help)|nmap\s+options|wireshark\s+filter|metasploit\s+module|sqlmap\s+commands)\b",
            # Hinglish
            r"\b(nmap\s+options\s+explain|cve\s+details\s+search)\b",
        ]

        # Follow-up patterns (English & Hinglish)
        self._follow_up_patterns = [
            r"^(yes|yeah|yep|sure|proceed|continue|go\s+ahead|do\s+it|confirm|now)(\s+.*)?$",
            r"^(no|nope|cancel|stop|abort)\b[!?.]*$",
            r"^(next|step\s+\d+|now\s+do|now\s+click|now\s+read|now\s+open|now\s+summarize)\b",
            r"^(what\s+about\s+that(\s+other\s+file)?|summarize\s+(it|that|this))\b",
            # Hinglish
            r"^(ha|haan|theek\s+hai|sahi\s+hai|aage\s+badho|karo|chalo|ha\s+karo|haan\s+proceed\s+karo)\b",
            r"\b(step\s+\d+\s+execute\s+karo)\b",
        ]

    def _normalize_query(self, query: str) -> str:
        """Lightweight normalization for common typos without altering semantics."""
        q = query.lower()
        q = re.sub(r"\bserach\b|\bsreach\b", "search", q)
        q = re.sub(r"\bopn\b", "open", q)
        q = re.sub(r"\bfiel\b|\bflie\b", "file", q)
        q = re.sub(r"\bchekc\b|\bchck\b", "check", q)
        q = re.sub(r"\bbrower\b|\bborwser\b|\bbroswer\b", "browser", q)
        q = re.sub(r"\brepot\b|\breprt\b", "report", q)
        q = re.sub(r"\bfnd\b", "find", q)
        return q

    def _has_action_verbs(self, query_words: List[str]) -> bool:
        """Checks if the query contains any explicit action verbs."""
        for word in query_words:
            clean = re.sub(r"[^a-zA-Z0-9_]", "", word)
            if clean in self.ACTION_VERBS:
                return True
        return False

    def route(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        active_mode: str = "/fast",
        current_workspace: Optional[str] = None
    ) -> IntentResult:
        """
        Determines the IntentResult for a given query and history.
        Enforces confidence scoring and action-verb fallback.
        """
        clean_query = query.strip()
        lower_query = clean_query.lower()
        norm_query = self._normalize_query(lower_query)
        words = norm_query.split()

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
            if conversation_history and len(conversation_history) >= 1:
                inferred = self._resolve_follow_up_intent(clean_query, conversation_history)
                if inferred:
                    return inferred

        # 3. Check for Multi-step workflows
        for pattern in self._workflow_patterns:
            if re.search(pattern, norm_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.MULTI_STEP_WORKFLOW,
                    confidence=0.92,
                    requires_tools=True,
                    suggested_categories=["search", "analysis", "report"],
                    task_instructions="Plan multi-step execution. Formulate search queries, extract comparisons, and synthesize a structured report.",
                    reason="Matched multi-step research or workflow pattern"
                )

        # 4. Check for discussion of capabilities vs execution
        # "What is browser automation?" or "Explain how web search works"
        is_discussion = any(re.search(pat, norm_query) for pat in self._discussion_prefixes)
        
        # Check if discussion has an explicit execution clause (e.g. "why my script fails and fix it")
        has_execution_clause = any(k in norm_query for k in ["fix it", "fix karo", "and fix", "check why and fix", "solve it"])
        if has_execution_clause:
            is_discussion = False

        # 5. Check Browser Automation (Action)
        if not is_discussion:
            for pattern in self._browser_patterns:
                if re.search(pattern, norm_query, re.IGNORECASE):
                    return IntentResult(
                        intent=IntentType.BROWSER_AUTOMATION,
                        confidence=0.92,
                        requires_tools=True,
                        suggested_categories=["browser"],
                        task_instructions="The user requested browser navigation or interaction. Inspect the live DOM and interact cleanly.",
                        reason="Matched browser navigation/automation action"
                    )

        # 6. Check Web Search (Action)
        if not is_discussion:
            for pattern in self._search_patterns:
                if re.search(pattern, norm_query, re.IGNORECASE):
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
            if re.search(pattern, norm_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.DATA_ANALYSIS,
                    confidence=0.90,
                    requires_tools=True,
                    suggested_categories=["terminal", "python"],
                    task_instructions="Use terminal tools and plotext to create clear terminal-based visualizations.",
                    reason="Matched data analysis/charting pattern"
                )

        # 8. Check Security & Tool Research
        for pattern in self._security_research_patterns:
            if re.search(pattern, norm_query, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.TOOL_RESEARCH,
                    confidence=0.90,
                    requires_tools=True,
                    suggested_categories=["security", "search"],
                    task_instructions="Retrieve security vulnerability or tool reference documentation.",
                    reason="Matched security/tool lookup pattern"
                )

        # 9. Check Workspace / File Operations
        if not is_discussion:
            for pattern in self._file_ops_patterns:
                if re.search(pattern, norm_query, re.IGNORECASE):
                    return IntentResult(
                        intent=IntentType.WORKSPACE_FILE_OPS,
                        confidence=0.88,
                        requires_tools=True,
                        suggested_categories=["files", "terminal"],
                        task_instructions="Perform requested workspace file operations safely within boundary limits.",
                        reason="Matched workspace or file operation pattern"
                    )

        # 10. Check Coding / Debugging
        for pattern in self._coding_patterns:
            if re.search(pattern, norm_query, re.IGNORECASE):
                # If pure conceptual explanation (e.g. "Explain how Python decorators work"), no tools needed
                if is_discussion or "explain" in norm_query or "what is" in norm_query or "how does" in norm_query:
                    return IntentResult(
                        intent=IntentType.CODING,
                        confidence=0.90,
                        requires_tools=False,
                        suggested_categories=[],
                        task_instructions="Provide a clear, accurate technical explanation with high-quality code examples.",
                        reason="Matched coding explanation (pure reasoning, no filesystem/terminal execution needed)"
                    )
                # If explicit workspace editing/fixing is hinted:
                if any(k in norm_query for k in ["project", "repo", "file", "fix", "theek", "error", "bug", "script", "debug", "test"]):
                    return IntentResult(
                        intent=IntentType.CODING,
                        confidence=0.88,
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
                    task_instructions="Generate robust, well-documented code addressing user specifications.",
                    reason="Matched code generation query without file targets"
                )

        # 11. Discussion prefix -> General Knowledge (zero tools)
        if is_discussion:
            return IntentResult(
                intent=IntentType.GENERAL_KNOWLEDGE,
                confidence=0.88,
                requires_tools=False,
                suggested_categories=[],
                reason="Matched conceptual question/explanation prefix (zero tools)"
            )

        # 12. Mode overrides
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

        # 13. TASK 1b Action-Verb Fallback:
        # If the query contains action verbs, DO NOT inject zero tools!
        if self._has_action_verbs(words):
            # Check if it leans towards search vs workspace vs terminal
            if any(w in norm_query for w in ["search", "online", "net", "web", "dhundo", "news", "price"]):
                return IntentResult(
                    intent=IntentType.WEB_SEARCH,
                    confidence=0.72,
                    requires_tools=True,
                    suggested_categories=["search"],
                    reason="Action-verb fallback: detected online search request"
                )
            elif any(w in norm_query for w in ["fix", "debug", "error", "script", "code"]):
                return IntentResult(
                    intent=IntentType.CODING,
                    confidence=0.72,
                    requires_tools=True,
                    suggested_categories=["files", "terminal"],
                    reason="Action-verb fallback: detected coding/debug action request"
                )
            else:
                return IntentResult(
                    intent=IntentType.WORKSPACE_FILE_OPS,
                    confidence=0.70,
                    requires_tools=True,
                    suggested_categories=["search", "files", "terminal"],
                    reason="Action-verb fallback: injected safe default tool set (search, files, terminal)"
                )

        # 14. Safe default fallback: Normal conversation / General knowledge without tools
        return IntentResult(
            intent=IntentType.NORMAL_CHAT,
            confidence=0.60,
            requires_tools=False,
            suggested_categories=[],
            reason="Default safe fallback for unclassified general text"
        )

    def _is_short_follow_up(self, query: str) -> bool:
        """Determines if the query is a short follow-up or affirmation."""
        clean = re.sub(r"[^\w\s]", "", query).strip()
        words = clean.split()
        if len(words) > 12:
            return False
        for pat in self._follow_up_patterns:
            if re.search(pat, query, re.IGNORECASE) or re.search(pat, clean, re.IGNORECASE):
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
        # Search backwards through the last few assistant/user turns
        for msg in reversed(conversation_history[-4:]):
            content = str(msg.get("content", "")).lower()

            # Browser context
            if any(k in content for k in ["browser", "open_url", "webpage", "website", "dom", "click"]):
                return IntentResult(
                    intent=IntentType.FOLLOW_UP,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["browser"],
                    is_follow_up=True,
                    task_instructions="Continue the browser automation workflow based on previous turn state.",
                    reason="Follow-up continuing active browser interaction"
                )

            # Web search context
            if any(k in content for k in ["search", "results", "documentation", "online"]):
                return IntentResult(
                    intent=IntentType.FOLLOW_UP,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["search"],
                    is_follow_up=True,
                    reason="Follow-up continuing search / information retrieval"
                )

            # File/terminal context
            if any(k in content for k in ["file", "delete", "terminal", "patch", "edit", "save", "script", "test"]):
                return IntentResult(
                    intent=IntentType.FOLLOW_UP,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["files", "terminal"],
                    is_follow_up=True,
                    reason="Follow-up continuing file or terminal operations"
                )

            # Multi-step report context
            if any(k in content for k in ["report", "compare", "audit", "investigate"]):
                return IntentResult(
                    intent=IntentType.FOLLOW_UP,
                    confidence=0.88,
                    requires_tools=True,
                    suggested_categories=["search", "analysis", "report"],
                    is_follow_up=True,
                    reason="Follow-up continuing multi-step workflow"
                )

        # Default follow-up with tools enabled if conversation had any prior turns
        return IntentResult(
            intent=IntentType.FOLLOW_UP,
            confidence=0.75,
            requires_tools=True,
            suggested_categories=["search", "files"],
            is_follow_up=True,
            reason="Follow-up continuing active conversation: safe tool injection (search, files)"
        )
