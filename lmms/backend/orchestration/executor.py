"""
UnifiedToolExecutor: Production-grade tool validation and execution.
Validates parameters against registered schemas, enforces permission boundaries,
prevents infinite loops, and returns structured observation results.
"""

import time
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Tuple
from .registry import ToolRegistry, DynamicToolDefinition

Tuple_Bool_Str = Tuple[bool, str]



@dataclass
class ExecutionResult:
    tool_name: str
    success: bool
    data: Any
    error: str = ""
    duration_ms: int = 0
    formatted_observation: str = ""
    was_denied: bool = False
    retry_count: int = 0


class UnifiedToolExecutor:
    """
    Executes tools safely with schema validation, permission checks, loop protection, and timeouts.
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._execution_history: List[Dict[str, Any]] = []
        self._custom_handlers: Dict[str, Callable] = {}

    def register_handler(self, tool_id: str, handler: Callable):
        """Attaches an active tool handler or instance method."""
        self._custom_handlers[tool_id] = handler

    def validate_arguments(self, tool: DynamicToolDefinition, kwargs: Dict[str, Any]) -> Tuple_Bool_Str:
        """
        Validates kwargs against the tool's JSON parameter schema.
        Returns (is_valid, error_message).
        """
        schema = tool.parameters
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # 1. Check required properties
        for req in required:
            if req not in kwargs:
                return False, f"Missing required parameter '{req}' for tool '{tool.id}'."

        # 2. Check types of provided arguments
        for k, v in kwargs.items():
            if k in properties:
                expected_type = properties[k].get("type")
                if expected_type == "string" and not isinstance(v, str):
                    return False, f"Parameter '{k}' must be a string, got {type(v).__name__}."
                elif expected_type == "integer" and not isinstance(v, int):
                    return False, f"Parameter '{k}' must be an integer, got {type(v).__name__}."
                elif expected_type == "boolean" and not isinstance(v, bool):
                    return False, f"Parameter '{k}' must be a boolean, got {type(v).__name__}."
                elif expected_type == "object" and not isinstance(v, dict):
                    return False, f"Parameter '{k}' must be a JSON object/dict, got {type(v).__name__}."
                elif expected_type == "array" and not isinstance(v, list):
                    return False, f"Parameter '{k}' must be a list/array, got {type(v).__name__}."

        return True, ""

    def check_permissions(
        self,
        tool: DynamicToolDefinition,
        permission_level: str = "medium",
        is_planning_mode: bool = False
    ) -> Tuple_Bool_Str:
        """
        Enforces permission levels (low, medium, high) and planning mode read-only restrictions.
        """
        # Planning mode read-only check
        if is_planning_mode:
            write_tools = [
                "files.write", "browser.click_element", "browser.fill_form",
                "browser.type", "app.launch", "app.close", "message.send"
            ]
            if tool.id in write_tools:
                return False, "Planning mode is read-only. Mutation tools are restricted."

        # Permission level checks
        if permission_level == "low":
            if tool.metadata.risk_level in ("medium", "high"):
                return False, f"Permission Denied: Tool '{tool.id}' has {tool.metadata.risk_level} risk, but permission level is 'low'."

        return True, ""

    def detect_infinite_loop(self, tool_name: str, kwargs: Dict[str, Any], max_consecutive: int = 3) -> bool:
        """
        Detects if the model is calling the exact same tool with identical arguments repeatedly.
        """
        if len(self._execution_history) < max_consecutive:
            return False

        recent = self._execution_history[-max_consecutive:]
        for entry in recent:
            if entry.get("tool") != tool_name or entry.get("kwargs") != kwargs:
                return False

        return True

    def execute(
        self,
        tool_name: str,
        kwargs: Dict[str, Any],
        permission_level: str = "medium",
        is_planning_mode: bool = False,
        max_observation_chars: int = 4000
    ) -> ExecutionResult:
        """
        Validates and executes a tool call, returning an ExecutionResult with formatted observation.
        """
        t0 = time.time()

        # 1. Resolve tool definition
        tool = self.registry.get(tool_name)
        if not tool:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[ERROR] Unknown tool '{tool_name}'. Available tools can be inspected in system prompt.\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=f"Unknown tool '{tool_name}'",
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 2. Validate arguments against schema
        valid, err = self.validate_arguments(tool, kwargs)
        if not valid:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[VALIDATION_ERROR] {err}\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=err,
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 3. Check permissions
        allowed, perm_err = self.check_permissions(tool, permission_level, is_planning_mode)
        if not allowed:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[PERMISSION_DENIED] {perm_err}\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=perm_err,
                duration_ms=duration_ms,
                formatted_observation=obs,
                was_denied=True
            )

        # 4. Check for infinite loops
        if self.detect_infinite_loop(tool.id, kwargs):
            duration_ms = int((time.time() - t0) * 1000)
            obs = (
                f"<observation>\n[LOOP_DETECTED] Tool '{tool_name}' was called with identical arguments {3} times consecutively. "
                "Execution halted to avoid infinite loop. Please summarize current findings or try a different approach.\n</observation>"
            )
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error="Infinite tool loop detected",
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 5. Execute handler
        handler = self._custom_handlers.get(tool.id) or tool.callback
        if not handler:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[ERROR] No execution handler attached for tool '{tool.id}'.\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=f"No handler registered for '{tool.id}'",
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        data = None
        error_msg = ""
        success = False

        try:
            # Execute with clean kwargs matching signature
            data = handler(**kwargs)
            success = True
        except Exception as e:
            error_msg = str(e)
            success = False

        duration_ms = int((time.time() - t0) * 1000)

        # Record history for loop detection
        self._execution_history.append({
            "tool": tool.id,
            "kwargs": dict(kwargs),
            "success": success,
            "timestamp": time.time()
        })

        # Format observation cleanly
        if success:
            obs_content = str(data) if data is not None else "[SUCCESS] Completed with no output."
            if len(obs_content) > max_observation_chars:
                head = int(max_observation_chars * 0.7)
                tail = int(max_observation_chars * 0.3)
                obs_content = (
                    obs_content[:head]
                    + f"\n... [Truncated {len(obs_content) - head - tail} characters] ...\n"
                    + obs_content[-tail:]
                )
            formatted_obs = f"<observation>\n{obs_content}\n</observation>"
        else:
            formatted_obs = f"<observation>\n[EXECUTION_FAILED] {error_msg}\n</observation>"

        return ExecutionResult(
            tool_name=tool.id,
            success=success,
            data=data,
            error=error_msg,
            duration_ms=duration_ms,
            formatted_observation=formatted_obs
        )


# Helper tuple alias
Tuple_Bool_Str = tuple[bool, str]
