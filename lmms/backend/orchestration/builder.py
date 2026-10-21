"""
ContextBuilder: Assembles modular context sections into canonical model inputs.
Enforces strict precedence, minimal base prompts, and zero unconditional tool schema bloat.
Prevents untrusted user inputs or tool observations from escalating to privileged system instructions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .registry import DynamicToolDefinition, ToolRegistry
from .router import IntentResult, IntentType
from .selector import SelectionResult


@dataclass
class AssembledContext:
    messages: List[Dict[str, Any]]
    base_system_prompt: str
    task_instructions: str
    tool_schemas_str: str
    selected_tool_ids: List[str]
    prefix_hash: str
    section_breakdown: Dict[str, str] = field(default_factory=dict)


class ContextBuilder:
    """
    Modular, deterministic context assembler with compact tool catalog indexing.
    """

    def __init__(self, version: str = "1.0.0", tool_registry: Optional[ToolRegistry] = None):
        self.version = version
        self.registry = tool_registry

    def build_base_prompt(self, model_name: str) -> str:
        """
        Constructs a minimal, version-controlled base system prompt.
        Target: ~100-140 tokens.
        """
        return (
            f"You are {model_name}, an AI assistant running inside LMMs (Local Model Machine Studio).\n"
            "Respond naturally, concisely, and directly. Do not volunteer identity disclaimers unless explicitly asked.\n"
            "When performing tasks, provide clear and accurate answers."
        )

    def build_task_instructions(
        self,
        intent_result: IntentResult,
        instruction_modules: set,
        active_mode: str = "/fast"
    ) -> str:
        """
        Constructs specialized task-specific instructions only when relevant.
        """
        sections = []

        # 1. Mode-specific guidelines
        if active_mode == "/deep":
            sections.append("Think deeply and reason step-by-step before answering.")
        elif active_mode == "/code":
            sections.append("Focus on production-grade, secure, and idiomatic code implementations.")

        # 2. Browser navigation instructions (only if browser tools are active)
        if "browser" in instruction_modules or intent_result.intent == IntentType.BROWSER_AUTOMATION:
            sections.append(
                "## Browser Interaction Rules\n"
                "To interact with a webpage:\n"
                "1. First open the URL or inspect the live DOM to see element IDs like [ID 1], [ID 2].\n"
                "2. Click buttons or links using `browser.click_element` with the ID string.\n"
                "3. Fill forms using `browser.fill_form` with field ID mappings.\n"
                "4. Live JS content can be retrieved using `browser.scrape_live`."
            )

        # 2b. Web search & information retrieval guidelines
        if "web_search" in instruction_modules or intent_result.intent in (IntentType.WEB_SEARCH, IntentType.TOOL_RESEARCH):
            sections.append(
                "## Search Rules\n"
                "1. Keep search queries specific and focused.\n"
                "2. Execute at most 1-2 searches. Once observation results are returned, immediately synthesize them into a clear, direct answer for the user.\n"
                "3. DO NOT repeatedly call web search with slightly different variations if you already have relevant information."
            )

        # 3. Multi-step progress rules (only for multi-step workflows)
        if intent_result.intent == IntentType.MULTI_STEP_WORKFLOW:
            sections.append(
                "## Multi-Step Workflow Rules\n"
                "1. State your plan in 1-2 concise lines before executing tools.\n"
                "2. Print concise status updates as you complete intermediate steps.\n"
                "3. Synthesize findings into a well-structured final summary report."
            )

        # 4. Custom task instructions from intent
        if intent_result.task_instructions:
            sections.append(f"Task Note: {intent_result.task_instructions}")

        return "\n\n".join(sections)

    def build_compact_tool_index(self, all_tools: Optional[List[DynamicToolDefinition]] = None) -> str:
        """
        Constructs a lightweight, compact tool index (~150-250 tokens) containing:
        - name + one-line description for all registered tools
        - discover_additional_tool syntax for lazy schema loading
        Injected on every turn to prevent zero-tool traps (dangerous errors).
        """
        if all_tools is None:
            if hasattr(self, "registry") and self.registry:
                all_tools = list(self.registry._tools.values())
            else:
                all_tools = list(ToolRegistry()._tools.values())

        lines = [
            "## Tool Catalog (Index)",
            "Available tools:",
        ]
        for tool in all_tools:
            if tool.id != "discover_additional_tool" and tool.enabled:
                lines.append(f"- {tool.id}: {tool.metadata.summary}")

        lines.append(
            "\nTo request full schema or invoke any tool from the catalog above:\n"
            "- <tool_call>{\"tool\": \"discover_additional_tool\", \"kwargs\": {\"capability\": \"<tool_name>\"}}</tool_call>"
        )
        return "\n".join(lines)

    def format_tool_schemas(self, selected_tools: List[DynamicToolDefinition]) -> str:
        """
        Renders ReAct-style full parameter schemas for routed / active tools.
        If zero tools are selected, returns an empty string.
        """
        if not selected_tools:
            return ""

        lines = [
            "## Active Tools (Full Schemas)",
            "To use an active tool, output a raw JSON block wrapped in <tool_call> tags:",
            "<tool_call>{\"tool\": \"tool_name\", \"kwargs\": {...}}</tool_call>",
            "Active tool schemas:"
        ]

        for tool in selected_tools:
            lines.append(tool.to_compact_prompt_format())

        return "\n".join(lines)

    def assemble(
        self,
        model_name: str,
        user_query: str,
        intent_result: IntentResult,
        selection_result: SelectionResult,
        conversation_history: List[Dict[str, Any]],
        current_workspace: Optional[str] = None,
        active_mode: str = "/fast",
        all_tools: Optional[List[DynamicToolDefinition]] = None,
        include_tool_index: bool = True
    ) -> AssembledContext:
        """
        Assembles all sections into a canonical message list with strict hierarchy.
        Injects compact tool catalog on every turn, and full schemas for routed tools.
        """
        # 1. Base prompt
        base_prompt = self.build_base_prompt(model_name)

        # 2. Workspace boundary context
        workspace_context = ""
        if current_workspace and current_workspace != "None":
            workspace_context = f"\nActive Workspace Directory: {current_workspace}"

        # 3. Task instructions
        task_instructions = self.build_task_instructions(
            intent_result,
            selection_result.instruction_modules,
            active_mode=active_mode
        )

        # 4. Tool schemas: compact index + full schemas for routed tools
        tool_section_blocks = []
        if include_tool_index:
            compact_index = self.build_compact_tool_index(all_tools)
            if compact_index:
                tool_section_blocks.append(compact_index)

        active_schemas_str = self.format_tool_schemas(selection_result.selected_tools)
        if active_schemas_str:
            tool_section_blocks.append(active_schemas_str)

        tool_schemas_str = "\n\n".join(tool_section_blocks)

        # Combine into complete system prompt
        system_blocks = [base_prompt]
        if workspace_context:
            system_blocks.append(workspace_context)
        if task_instructions:
            system_blocks.append(task_instructions)
        if tool_schemas_str:
            system_blocks.append(tool_schemas_str)

        full_system_content = "\n\n".join(b.strip() for b in system_blocks if b.strip())

        # Construct final messages list
        final_messages: List[Dict[str, Any]] = []
        final_messages.append({"role": "system", "content": full_system_content})

        # Add recent conversation history (excluding any previous system prompt)
        for msg in conversation_history:
            if msg.get("role") != "system":
                final_messages.append(dict(msg))

        # Add current user query as final turn
        final_messages.append({"role": "user", "content": user_query})

        # Generate deterministic prefix hash
        import hashlib
        prefix_hash = hashlib.sha256((base_prompt + tool_schemas_str).encode("utf-8")).hexdigest()

        return AssembledContext(
            messages=final_messages,
            base_system_prompt=base_prompt,
            task_instructions=task_instructions,
            tool_schemas_str=tool_schemas_str,
            selected_tool_ids=selection_result.selected_ids,
            prefix_hash=prefix_hash,
            section_breakdown={
                "base_prompt": base_prompt,
                "workspace": workspace_context,
                "task_instructions": task_instructions,
                "tool_schemas": tool_schemas_str,
                "user_query": user_query
            }
        )

    def assemble_legacy(
        self,
        model_name: str,
        user_query: str,
        all_tools: List[DynamicToolDefinition],
        conversation_history: List[Dict[str, Any]],
        current_workspace: Optional[str] = None,
        active_mode: str = "/fast"
    ) -> AssembledContext:
        """
        Reconstructs the original monolithic prompt (4,139 tokens) for A/B benchmarking.
        Injects all 22 tool schemas, few-shot browser examples, persona rules, and search guidelines.
        """
        base_prompt = (
            f"You are {model_name}, an AI assistant running inside LMMs.\n"
            "Respond naturally, concisely, and directly.\n"
        )
        if current_workspace and current_workspace != "None":
            base_prompt += f"\nActive Workspace Directory: {current_workspace}\n"

        tool_schemas = self.format_tool_schemas(all_tools)

        few_shots = (
            "## Few-Shot Examples (How to use tools)\n"
            "Example 1 - Launch Desktop App:\n"
            "User: open calculator / launch chrome\n"
            "Assistant: <tool_call>{\"tool\": \"app.launch\", \"kwargs\": {\"app_name_or_target\": \"calculator\"}}</tool_call>\n"
            "Observation: [SUCCESS] Launched 'gnome-calculator' successfully (PID: 12345).\n"
            "Assistant: I have launched the calculator application for you.\n\n"
            "Example 2 - Live Web Navigation, DOM Elements & Form Login:\n"
            "User: open github and login\n"
            "Assistant: <tool_call>{\"tool\": \"browser.open_url\", \"kwargs\": {\"url\": \"https://github.com/login\", \"headless\": False}}</tool_call>\n"
            "Observation: [Page Loaded: Sign in to GitHub]\n[ID 1] <input name='login' type='text'>\n[ID 2] <input name='password' type='password'>\n[ID 3] <input type='submit' value='Sign in'>\n"
            "Assistant: <tool_call>{\"tool\": \"browser.fill_form\", \"kwargs\": {\"fields\": {\"1\": \"user@example.com\", \"2\": \"secretpassword\"}}}</tool_call>\n"
            "Observation: [FILL_SUCCESS] Filled fields: [data-lmms-id='1'], [data-lmms-id='2'].\n"
            "Assistant: <tool_call>{\"tool\": \"browser.click_element\", \"kwargs\": {\"selector\": \"3\"}}</tool_call>\n"
            "Observation: [CLICK_SUCCESS] Clicked '3'.\n"
            "Assistant: I have filled in your credentials and clicked Sign In.\n\n"
            "Example 3 - Send Desktop Notification or Telegram Alert:\n"
            "User: notify me that the build finished\n"
            "Assistant: <tool_call>{\"tool\": \"message.send\", \"kwargs\": {\"platform\": \"desktop\", \"message\": \"Build completed successfully!\", \"recipient\": \"Build Alert\"}}</tool_call>\n"
            "Observation: [SUCCESS] Desktop notification displayed: 'Build Alert: Build completed successfully!'.\n"
            "Assistant: I have sent a desktop notification to alert you.\n\n"
            "Example 4 - Web Search & Info Extraction:\n"
            "User: search what is current gold price\n"
            "Assistant: <tool_call>{\"tool\": \"web_search\", \"kwargs\": {\"query\": \"current gold price\"}}</tool_call>\n"
            "Observation: [Search Results...]\n"
            "Assistant: The current gold price is...\n\n"
        )

        persona_rules = (
            "\n## Principal Software Engineer Persona (Claude Code Killer)\n"
            "You are an elite, autonomous software engineer capable of full-repo management. Do not just act like a chatbot; act like a lead developer.\n"
            "1. **Full Autonomy**: If asked to build a project, clone repositories (`git clone`), compile binaries, and install dependencies autonomously using `terminal.run`.\n"
            "2. **Architectural Understanding**: Before writing code, map out the workspace using AST parsing or grep.\n"
            "3. **Proactive Bug Fixing & TDD**: If asked to fix a bug, DO NOT just write code. First write a test using `files.write`, run it with `terminal.run`, fix code, and run it until passing.\n"
            "4. **Iterative Loops**: Never ask user to test your code if you can test it yourself. Loop your tools until 100% done.\n"
            "5. **CRITICAL ANTI-ADVICE RULE**: NEVER write instructions for the user to run manually. If you know what command needs to run, run it yourself.\n"
            "6. **Error Recovery**: If a command fails with a missing module, immediately install it and retry.\n"
            "7. **Docker awareness**: ALWAYS prefer docker compose over docker-compose.\n"
            "8. **Python projects**: Check for requirements.txt and run pip install before starting.\n"
        )

        search_rules = (
            "\n## Autonomous Deep Research & Anti-Hallucination Rules\n"
            "1. **Never Guess or Surrender**: DO NOT guess, hallucinate, or claim 'I cannot find information' without doing deep research.\n"
            "2. **Autonomous Deep Crawling**: When `web_search` returns URLs (e.g. for questions about companies, people, founders, docs, technical details), DO NOT just read the short snippet if the answer is missing! IMMEDIATELY and AUTONOMOUSLY call `browser.crawl_url` (powered by Crawl4AI) on the top relevant URLs (like /team, /about, /contact, or docs) to extract the full markdown content.\n"
            "3. **Multi-Hop Investigation**: If the first URL does not have the answer, crawl the other URLs found in search results or search with a more specific query.\n"
            "4. **RAG Integration**: Use `rag.search` to query local workspace documentation, and `rag.crawl_url` to index long documentation sites into vector memory.\n"
        )

        full_system = f"{base_prompt}\n\n{tool_schemas}\n\n{few_shots}\n\n{persona_rules}\n\n{search_rules}"

        final_messages: List[Dict[str, Any]] = [{"role": "system", "content": full_system}]
        for msg in conversation_history:
            if msg.get("role") != "system":
                final_messages.append(dict(msg))
        final_messages.append({"role": "user", "content": user_query})

        import hashlib
        prefix_hash = hashlib.sha256(full_system.encode("utf-8")).hexdigest()

        return AssembledContext(
            messages=final_messages,
            base_system_prompt=base_prompt,
            task_instructions=few_shots + persona_rules + search_rules,
            tool_schemas_str=tool_schemas,
            selected_tool_ids=[t.id for t in all_tools],
            prefix_hash=prefix_hash,
            section_breakdown={
                "base_prompt": base_prompt,
                "workspace": current_workspace or "",
                "task_instructions": few_shots + persona_rules + search_rules,
                "tool_schemas": tool_schemas,
                "user_query": user_query
            }
        )
