"""
ToolSelector: Selects the minimum sufficient set of tools for the current task.
Prevents prompt bloat by injecting only authorized, relevant tool schemas.
Enforces context-budget awareness and records selection rationale.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from .registry import ToolRegistry, DynamicToolDefinition, ToolMetadata
from .router import IntentResult, IntentType


@dataclass
class SelectionResult:
    selected_tools: List[DynamicToolDefinition]
    selected_ids: List[str]
    rejected_ids: List[str]
    rationale: Dict[str, str] = field(default_factory=dict)
    total_estimated_tokens: int = 0
    instruction_modules: Set[str] = field(default_factory=set)


class ToolSelector:
    """
    Intelligent, budget-aware tool selector.
    Chooses the minimum required tools based on intent, dependencies, and budget.
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

        # Category mapping for intents
        self._intent_category_map = {
            IntentType.NORMAL_CHAT: [],
            IntentType.GENERAL_KNOWLEDGE: [],
            IntentType.CODING: [],  # By default, coding reasoning needs no tools
            IntentType.WORKSPACE_FILE_OPS: ["files", "terminal"],
            IntentType.WEB_SEARCH: ["search", "network"],
            IntentType.BROWSER_AUTOMATION: ["browser"],
            IntentType.DATA_ANALYSIS: ["terminal"],
            IntentType.MULTI_STEP_WORKFLOW: ["search", "network", "analysis", "report"],
            IntentType.TOOL_RESEARCH: ["security", "search", "network"],
        }

    def select(
        self,
        intent_result: IntentResult,
        max_tool_tokens: int = 1200,
        current_workspace: Optional[str] = None,
        permission_level: str = "medium",
        additional_requested_tools: Optional[List[str]] = None,
    ) -> SelectionResult:
        """
        Selects tools required for the intent without exceeding max_tool_tokens.
        """
        selected: List[DynamicToolDefinition] = []
        selected_ids: List[str] = []
        rejected_ids: List[str] = []
        rationale: Dict[str, str] = {}
        instruction_modules: Set[str] = set()
        accumulated_tokens = 0

        # Scenario A & B check: If intent does NOT require tools and no extra tools were requested
        if not intent_result.requires_tools and not additional_requested_tools:
            return SelectionResult(
                selected_tools=[],
                selected_ids=[],
                rejected_ids=[],
                rationale={"all": f"Intent '{intent_result.intent.value}' does not require tools (Zero-tool injection)."},
                total_estimated_tokens=0,
                instruction_modules=set()
            )

        candidate_ids: List[str] = []

        # 1. Add explicitly requested tools (e.g. from dynamic discovery or user prompt)
        if additional_requested_tools:
            for tid in additional_requested_tools:
                if tid not in candidate_ids:
                    candidate_ids.append(tid)

        # 2. Add candidates matching suggested categories or tags
        categories = intent_result.suggested_categories or self._intent_category_map.get(intent_result.intent, [])
        for cat in categories:
            for tool_def in self.registry._tools.values():
                if tool_def.category == cat or cat in tool_def.metadata.tags:
                    if tool_def.id not in candidate_ids:
                        candidate_ids.append(tool_def.id)


        # 3. If workspace is active and file ops or coding was detected, ensure file tools are considered
        if current_workspace and current_workspace != "None":
            if intent_result.intent in (IntentType.WORKSPACE_FILE_OPS, IntentType.CODING) and intent_result.requires_tools:
                for fid in ["files.read", "files.write", "terminal.run"]:
                    if fid not in candidate_ids:
                        candidate_ids.append(fid)

        # 4. Resolve tool dependencies (e.g. browser.click_element depends on browser.open_url)
        resolved_candidates: List[str] = []
        for tid in candidate_ids:
            tool = self.registry.get(tid)
            if tool:
                for dep in tool.metadata.dependencies:
                    if dep not in resolved_candidates and dep not in candidate_ids:
                        resolved_candidates.append(dep)
            if tid not in resolved_candidates:
                resolved_candidates.append(tid)

        # 5. Filter candidates against permissions, boundaries, and token budget
        for tid in resolved_candidates:
            tool = self.registry.get(tid)
            if not tool or not tool.enabled:
                rejected_ids.append(tid)
                rationale[tid] = "Tool not found or disabled in registry."
                continue

            # Permission level check
            if permission_level == "low" and tool.metadata.risk_level == "high":
                rejected_ids.append(tid)
                rationale[tid] = f"Rejected: risk level '{tool.metadata.risk_level}' exceeds permission level 'low'."
                continue

            # Budget check
            est_tokens = tool.metadata.estimated_tokens
            if accumulated_tokens + est_tokens > max_tool_tokens:
                rejected_ids.append(tid)
                rationale[tid] = f"Rejected: exceeds available tool token budget ({accumulated_tokens + est_tokens} > {max_tool_tokens})."
                continue

            # Tool is selected!
            selected.append(tool)
            selected_ids.append(tool.id)
            accumulated_tokens += est_tokens
            rationale[tool.id] = f"Selected for intent '{intent_result.intent.value}' (Category: {tool.category})."
            if tool.instruction_module:
                instruction_modules.add(tool.instruction_module)

        return SelectionResult(
            selected_tools=selected,
            selected_ids=selected_ids,
            rejected_ids=rejected_ids,
            rationale=rationale,
            total_estimated_tokens=accumulated_tokens,
            instruction_modules=instruction_modules
        )

    def discover_additional_tool(
        self,
        current_selection: SelectionResult,
        missing_capability: str,
        max_tool_tokens: int = 1200
    ) -> SelectionResult:
        """
        Progressively discover and add an extra tool capability during multi-step execution
        without reloading the model.
        """
        tool = self.registry.get(missing_capability)
        if not tool:
            # Search by tag or category
            for t in self.registry._tools.values():
                if missing_capability.lower() in t.id or missing_capability.lower() in t.metadata.tags:
                    tool = t
                    break

        if not tool:
            return current_selection

        if tool.id in current_selection.selected_ids:
            return current_selection

        new_selected = list(current_selection.selected_tools)
        new_ids = list(current_selection.selected_ids)
        new_rationale = dict(current_selection.rationale)
        new_modules = set(current_selection.instruction_modules)

        new_selected.append(tool)
        new_ids.append(tool.id)
        new_rationale[tool.id] = f"Dynamically discovered during execution: needed capability '{missing_capability}'"
        if tool.instruction_module:
            new_modules.add(tool.instruction_module)

        return SelectionResult(
            selected_tools=new_selected,
            selected_ids=new_ids,
            rejected_ids=current_selection.rejected_ids,
            rationale=new_rationale,
            total_estimated_tokens=current_selection.total_estimated_tokens + tool.metadata.estimated_tokens,
            instruction_modules=new_modules
        )
