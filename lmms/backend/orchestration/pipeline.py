"""
OrchestrationPipeline: The central intelligent coordinator for LMMs.
Unifies Intent Routing, Dynamic Tool Injection, Context Assembly,
Precise Budgeting, Cache Telemetry, Compaction, and Execution.
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Callable

from .router import IntentRouter, IntentResult, IntentType
from .registry import ToolRegistry, DynamicToolDefinition
from .selector import ToolSelector, SelectionResult
from .budget import TokenBudgetManager, BudgetBreakdown, ContextOverflowError
from .builder import ContextBuilder, AssembledContext
from .executor import UnifiedToolExecutor, ExecutionResult
from .compactor import ContextCompactor, CompactionReport
from .cache import PromptCacheManager
from .adapter import InferenceAdapter, StreamingChunk
from .observability import TraceLogger, RequestTrace, get_trace_logger


@dataclass
class OrchestrationResponse:
    request_id: str
    reply_text: str
    intent: IntentType
    selected_tool_ids: List[str]
    tool_calls_made: int
    prompt_tokens: int
    ttft_ms: int
    total_duration_ms: int
    was_compacted: bool
    error: Optional[str] = None


class OrchestrationPipeline:
    """
    Production-grade end-to-end orchestration pipeline.
    Replaces monolithic ad-hoc prompt bloat with dynamic, intent-driven capability injection.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        engine_url: str = "http://localhost:11435",
        debug_mode: bool = False
    ):
        self.registry = registry or ToolRegistry()
        self.router = IntentRouter()
        self.selector = ToolSelector(self.registry)
        self.builder = ContextBuilder()
        self.budget_manager = TokenBudgetManager(engine_url=engine_url)
        self.compactor = ContextCompactor()
        self.prompt_cache = PromptCacheManager()
        self.adapter = InferenceAdapter(engine_url=engine_url)
        self.executor = UnifiedToolExecutor(self.registry)
        self.trace_logger = get_trace_logger(debug_mode=debug_mode)

    def prepare_request(
        self,
        model_name: str,
        user_query: str,
        conversation_history: List[Dict[str, Any]],
        current_workspace: Optional[str] = None,
        permission_level: str = "medium",
        active_mode: str = "/fast",
        conversation_id: Optional[str] = None,
        is_planning_mode: bool = False
    ) -> tuple[AssembledContext, IntentResult, SelectionResult, BudgetBreakdown]:
        """
        Runs Intent Routing -> Dynamic Tool Selection -> Context Assembly -> Budget Enforcement.
        Guarantees that normal chat injects 0 tools, and prompt does not overflow the model context.
        """
        if is_planning_mode and active_mode == "/fast":
            active_mode = "/plan"

        # 1. Intent Routing (Fast deterministic check)
        t_route_start = time.time()
        intent_res = self.router.route(
            query=user_query,
            conversation_history=conversation_history,
            active_mode=active_mode,
            current_workspace=current_workspace
        )
        routing_ms = int((time.time() - t_route_start) * 1000)


        # 2. Tool Selection & Context Assembly
        if os.environ.get("LMMS_LEGACY_PROMPT") == "1":
            all_tools = list(self.registry._tools.values())
            selection_res = SelectionResult(
                selected_tools=all_tools,
                selected_ids=[t.id for t in all_tools],
                rejected_ids=[],
                rationale={"legacy": "LMMS_LEGACY_PROMPT=1 forced all tools"},
                total_estimated_tokens=sum(t.metadata.estimated_tokens for t in all_tools),
                instruction_modules=set(["browser", "files", "search", "terminal"])
            )
            t_asm_start = time.time()
            assembled_ctx = self.builder.assemble_legacy(
                model_name=model_name,
                user_query=user_query,
                all_tools=all_tools,
                conversation_history=conversation_history,
                current_workspace=current_workspace,
                active_mode=active_mode
            )
            assembly_ms = int((time.time() - t_asm_start) * 1000)
        else:
            # Dynamic Tool Selection (Inject only sufficient tools)
            selection_res = self.selector.select(
                intent_result=intent_res,
                current_workspace=current_workspace,
                permission_level=permission_level
            )

            # Context Assembly (Modular assembly without bloating)
            t_asm_start = time.time()
            assembled_ctx = self.builder.assemble(
                model_name=model_name,
                user_query=user_query,
                intent_result=intent_res,
                selection_result=selection_res,
                conversation_history=conversation_history,
                current_workspace=current_workspace,
                active_mode=active_mode
            )
            assembly_ms = int((time.time() - t_asm_start) * 1000)

        # 4. Token Budget Calculation & Pre-inference Protection
        budget = self.budget_manager.calculate_budget(
            model_name=model_name,
            base_prompt=assembled_ctx.base_system_prompt,
            task_instructions=assembled_ctx.task_instructions,
            tool_schemas=assembled_ctx.tool_schemas_str,
            history_messages=conversation_history,
            user_query=user_query
        )

        # 5. Compaction if budget pressure detected
        if budget.is_overflow:
            compacted_messages, report = self.compactor.compact(
                messages=assembled_ctx.messages,
                usable_budget=budget.usable_context,
                current_prompt_tokens=budget.total_prompt_tokens,
                model_name=model_name
            )
            assembled_ctx.messages = compacted_messages

            # Recalculate budget post-compaction
            budget = self.budget_manager.calculate_budget(
                model_name=model_name,
                base_prompt=assembled_ctx.base_system_prompt,
                task_instructions=assembled_ctx.task_instructions,
                tool_schemas=assembled_ctx.tool_schemas_str,
                history_messages=compacted_messages[1:-1],  # exclude system and current user turn
                user_query=user_query
            )

            # If still overflowed after compaction, raise explicit error
            self.budget_manager.verify_or_raise(budget)

        # 6. Check Prefix Cache Compatibility
        self.prompt_cache.check_prefix_compatibility(
            model_name=model_name,
            base_system_prompt=assembled_ctx.base_system_prompt,
            tool_schemas_str=assembled_ctx.tool_schemas_str,
            selected_tool_ids=selection_res.selected_ids
        )

        return assembled_ctx, intent_res, selection_res, budget
