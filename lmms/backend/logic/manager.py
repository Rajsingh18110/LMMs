from typing import Optional
from lmms.backend.contracts.runtime import ModelRuntime
from lmms.backend.contracts.memory import MemoryContract
from lmms.backend.contracts.provider import ProviderContract
from lmms.backend.contracts.workspace import WorkspaceContract

class BackendManager:
    """
    Central hub that coordinates all LMMs services.
    GUI, CLI, API, and Agents should only talk to this manager.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackendManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._runtime: Optional[ModelRuntime] = None
            self._memory: Optional[MemoryContract] = None
            self._provider: Optional[ProviderContract] = None
            self._workspace: Optional[WorkspaceContract] = None
            self._git_manager = None
            self._task_manager = None
            self._execution_pipeline = None
            self._agent_manager = None
            self._orchestration_manager = None
            self._config_manager = None
            self._coordination_manager = None
            self._tool_executor = None
            self._chat_router = None
            self._enforce_poison_pill()
            self._initialized = True

    def _enforce_poison_pill(self):
        import sys
        if "ollama" in sys.modules:
            pass
        sys.modules["ollama"] = None  # Block future imports

    @property
    def memory(self) -> MemoryContract:
        if self._memory is None:
            from lmms.backend.memory.providers.sqlite import Memory
            self._memory = Memory()
        return self._memory

    @property
    def workspace(self) -> WorkspaceContract:
        if self._workspace is None:
            from lmms.backend.db.workspace.manager import WorkspaceManager
            self._workspace = WorkspaceManager()
        return self._workspace

    @property
    def registry(self):
        # Always return the singleton registry service
        from lmms.backend.core.registry.service import RegistryService
        return RegistryService()

    @property
    def provider(self):
        if self._provider is None:
            from lmms.backend.providers.manager import ProviderManager
            self._provider = ProviderManager()
        return self._provider

    @property
    def connection(self):
        from lmms.engine.connection import ConnectionManager
        return ConnectionManager(self.registry)

    @property
    def events(self):
        from lmms.backend.services.core_services.services.events import event_bus
        return event_bus

    @property
    def git(self):
        if self._git_manager is None:
            from lmms.backend.git.manager import GitManager
            ws_id = self.workspace.get_active_workspace()
            if not ws_id:
                path = "."
            else:
                registry = self.workspace._load_registry()
                path = registry.get(ws_id, {}).get("path", ".")
            self._git_manager = GitManager(path, self.events)
        return self._git_manager

    @property
    def tasks(self):
        if self._task_manager is None:
            from lmms.backend.tasks.manager import TaskManager
            ws_id = self.workspace.get_active_workspace()
            if not ws_id:
                path = "."
            else:
                registry = self.workspace._load_registry()
                path = registry.get(ws_id, {}).get("path", ".")
            from lmms.backend.db.workspace.manager import WorkspaceManager
            ws_manager = WorkspaceManager()
            db = ws_manager.get_db(ws_id)
            self._task_manager = TaskManager(path, self.events, db)
        return self._task_manager

    @property
    def execution(self):
        if self._execution_pipeline is None:
            from lmms.backend.context.builder import ExecutionPipeline
            self._execution_pipeline = ExecutionPipeline(self)
        return self._execution_pipeline

    @property
    def agents(self):
        if self._agent_manager is None:
            from lmms.backend.agents.manager import AgentManager
            ws_id = self.workspace.get_active_workspace()
            db = self.workspace.get_db(ws_id)
            self._agent_manager = AgentManager(self, db)
        return self._agent_manager

    @property
    def orchestrator(self):
        if self._orchestration_manager is None:
            from lmms.backend.router.manager import OrchestrationManager
            ws_id = self.workspace.get_active_workspace()
            db = self.workspace.get_db(ws_id)
            self._orchestration_manager = OrchestrationManager(self, db)
        return self._orchestration_manager


    @property
    def cache(self):
        if not hasattr(self, '_cache') or self._cache is None:
            from lmms.engine.cache_manager import CacheManager
            self._cache = CacheManager()
        return self._cache

    @property
    def config(self):
        if self._config_manager is None:
            from lmms.backend.config.config import ConfigManager
            self._config_manager = ConfigManager()
        return self._config_manager

    @property
    def coordination(self):
        if self._coordination_manager is None:
            import lmms.backend.db.storage.coordination as coord
            self._coordination_manager = coord
        return self._coordination_manager

    @property
    def tools(self):
        if self._tool_executor is None:
            from lmms.backend.tools.core_tools.tools.registry import ToolRegistry
            from lmms.backend.tools.core_tools.tools.key_manager import KeyManager
            from lmms.backend.tools.core_tools.tools.executor import ToolExecutor
            km = KeyManager()
            registry = ToolRegistry(km)
            self._tool_executor = ToolExecutor(registry, km)
        return self._tool_executor

    @property
    def chat_router(self):
        if self._chat_router is None:
            from lmms.backend.logic.chat_router import ChatRouter
            self._chat_router = ChatRouter()
        return self._chat_router

    @property
    def runtime(self):
        if self._runtime is None:
            from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime
            self._runtime = LlamaCppRuntime()
            # Try to load default model, ignore if fails (let it be explicit)
            self._runtime.load_model("qwen1_5-0_5b-chat-q4_k_m.gguf")
        return self._runtime

    def register_runtime(self, runtime: ModelRuntime):
        self._runtime = runtime

    def register_memory(self, memory: MemoryContract):
        self._memory = memory

    def register_provider(self, provider: ProviderContract):
        self._provider = provider

    def register_workspace(self, workspace: WorkspaceContract):
        self._workspace = workspace


backend_manager = BackendManager()
