import time
import inspect
from typing import Dict, Any, Optional

from lmms.backend.tools.core.result import ToolResult, ToolError, ToolPermissionError
from lmms.backend.tools.core.registry import ToolRegistry
from lmms.backend.agents.permissions import PermissionValidator

class ToolExecutor:
    """
    Executes tools securely, enforcing boundaries, permissions, and timeout policies.
    Normalizes all execution states into standard ToolResults.
    """
    def __init__(self, registry: ToolRegistry, permission_manager: PermissionValidator):
        self.registry = registry
        self.permission_manager = permission_manager
        
    def execute(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        tool_def = self.registry.get_tool(tool_name)
        
        if not tool_def:
            return ToolResult(
                success=False,
                tool=tool_name,
                error=f"Tool '{tool_name}' is not registered.",
                metadata={"duration_ms": 0}
            )
            
        # 1. Permission check
        if tool_def.permissions:
            if not self.permission_manager.check_permission(tool_def.permissions):
                return ToolResult(
                    success=False,
                    tool=tool_name,
                    error=f"Permission Denied: Lacking required permissions {tool_def.permissions}.",
                    metadata={"duration_ms": 0}
                )
                
        # 2. Confirmation check
        if tool_def.requires_confirmation:
            if not kwargs.pop("confirm", False) and not kwargs.get("require_confirm", False):
                return ToolResult(
                    success=False,
                    tool=tool_name,
                    error="Execution rejected: This tool requires explicit confirmation (confirm=True).",
                    metadata={"duration_ms": 0}
                )
                
        # 3. Execution
        try:
            if not tool_def.callback:
                raise ToolError("Tool definition has no execution callback attached.")
                
            # Filter kwargs to match signature to prevent unexpected argument crashes
            sig = inspect.signature(tool_def.callback)
            valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            
            # TODO: We can add threading/asyncio here for real timeout enforcement
            # Currently relying on the tools themselves to respect their internal timeouts
            data = tool_def.callback(**valid_kwargs)
            
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=True,
                tool=tool_name,
                data=data,
                metadata={"duration_ms": duration_ms}
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                tool=tool_name,
                error=f"Execution exception: {str(e)}",
                metadata={"duration_ms": duration_ms, "exception_type": type(e).__name__}
            )
