import uuid
from datetime import datetime

from lmms.backend.context.capabilities import ExecutionContext
from lmms.backend.context.intents import IntentDetector
from lmms.backend.context.retrieval import RetrievalEngine
from lmms.backend.context.ranking import RankingEngine
from lmms.backend.context.budgeting import BudgetEngine
from lmms.backend.context.assembler import ContextAssembler

class ExecutionPipeline:
    """
    Mandatory pipeline for all model execution.
    No component may execute a model directly without passing through here.
    """
    def __init__(self, backend_manager):
        self.backend = backend_manager
        self.intents = IntentDetector(backend_manager)
        self.retrieval = RetrievalEngine(backend_manager)
        self.ranking = RankingEngine()
        self.budgeting = BudgetEngine()
        self.assembler = ContextAssembler()

    def process_request(self, raw_prompt: str, branch_id: str, workspace_id: str, runtime_profile: str = "default_4k") -> ExecutionContext:
        """
        Executes the mandatory pipeline.
        """
        # 1. Initialize Context
        ctx = ExecutionContext(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            raw_prompt=raw_prompt,
            runtime_profile=runtime_profile
        )

        # 2. Intent Detection
        ctx.intent = self.intents.detect(raw_prompt)

        # 3. Retrieval (Tasks, Git, Memory, Files)
        raw_data = self.retrieval.retrieve_all(ctx.intent, branch_id, workspace_id)

        # 4. Ranking
        ranked_data = self.ranking.rank(raw_data)
        ctx.task_data = ranked_data["priority_1_tasks"]
        ctx.git_data = ranked_data["priority_2_git"]
        ctx.memory_data = ranked_data["priority_3_memory"]
        ctx.file_data = ranked_data["priority_4_files"]
        ctx.chat_history = ranked_data["priority_5_history"]

        # 5. Tool Discovery (Stubbed dynamic registry)
        ctx.tools = [
            {"name": tool, "description": f"Capability {tool}"} 
            for tool in ctx.intent.required_tools
        ]

        # 6. Budget Allocation
        ctx.token_budget = self.budgeting.allocate(runtime_profile)

        # 7. Context Assembly
        self.assembler.assemble(ctx)

        # Emit event for trace proof
        self.backend.events.publish("ExecutionPipelineCompleted", {
            "request_id": ctx.request_id,
            "intent": ctx.intent.name,
            "assembled_length": len(ctx.assembled_prompt)
        })

        return ctx

    def execute(self, raw_prompt: str, branch_id: str, workspace_id: str):
        """
        Runs the pipeline and sends the ExecutionContext to the Model Runtime.
        """
        ctx = self.process_request(raw_prompt, branch_id, workspace_id)
        
        # This is where we would call self.backend.runtime.generate(ctx)
        # For Phase H proof, we return the context object.
        return ctx
