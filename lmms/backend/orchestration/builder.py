"""
ContextBuilder: Assembles modular context sections into canonical model inputs.
Enforces strict precedence, minimal base prompts, and zero unconditional tool schema bloat.
Prevents untrusted user inputs or tool observations from escalating to privileged system instructions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .registry import DynamicToolDefinition
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
    Modular, deterministic context assembler.
    """

    def __init__(self, version: str = "1.0.0"):
        self.version = version

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

    def format_tool_schemas(self, selected_tools: List[DynamicToolDefinition]) -> str:
        """
        Renders ReAct-style compact tool specifications for selected tools only.
        If zero tools are selected, returns an empty string.
        """
        if not selected_tools:
            return ""

        lines = [
            "## Available Tools",
            "To use a tool, output a raw JSON block wrapped in <tool_call> tags:",
            "<tool_call>{\"tool\": \"tool_name\", \"kwargs\": {...}}</tool_call>",
            "Tools will execute and return results wrapped in <observation> tags. Available tools:"
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
        active_mode: str = "/fast"
    ) -> AssembledContext:
        """
        Assembles all sections into a canonical message list with strict hierarchy.
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

        # 4. Tool schemas
        tool_schemas_str = self.format_tool_schemas(selection_result.selected_tools)

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
