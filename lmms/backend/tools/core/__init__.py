from lmms.backend.tools.core.registry import ToolRegistry
from lmms.backend.tools.core.executor import ToolExecutor
from lmms.backend.agents.permissions import PermissionValidator, Permission
from lmms.backend.tools.core.definitions import ToolDefinition
from lmms.backend.tools.core.result import ToolResult, ToolError, ToolPermissionError

# Global instances for canonical tool runtime
default_registry = ToolRegistry()
default_permission_manager = PermissionValidator()
default_executor = ToolExecutor(default_registry, default_permission_manager)
