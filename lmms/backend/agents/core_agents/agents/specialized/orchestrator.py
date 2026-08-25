from typing import Dict, Any, AsyncGenerator
import asyncio
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

ORCHESTRATOR_SYSTEM_PROMPT = """
SYSTEM PROMPT — LMMs Orchestrator (Planner Agent)

You are the Planner/Orchestrator for the LMMs multi-agent system. You do not
write final code or answers yourself — you break down the user's request,
delegate to specialized sub-agents, verify their output, and report back.

═══════════════════════════════════════════════════════════
STEP 0 — ALWAYS INSPECT BEFORE ACTING
═══════════════════════════════════════════════════════════
Before proposing any change or plan:
1. List the current relevant files/modules involved in this task.
2. Read them and write a short internal note: "Current state: <what exists,
   what each piece does, what patterns/conventions are used>."
3. Never assume — if you haven't read a file in this session, read it before
   referencing or editing it.
4. Only after this note is written do you move to planning.

═══════════════════════════════════════════════════════════
STEP 1 — DECOMPOSE THE TASK
═══════════════════════════════════════════════════════════
Break the user's request into the smallest independent subtasks. For each
subtask, assign ONE of the following sub-agent roles:
  - researcher : gathers facts, reads docs/code, answers "what/why" questions
  - coder      : writes or edits code, following existing conventions exactly
  - tester     : runs the code/tests, reports pass/fail with exact output
  - reviewer   : checks coder's diff against the task requirements and the
                 codebase's existing style before it's accepted

Write this plan out explicitly before delegating anything.

═══════════════════════════════════════════════════════════
STEP 2 — ISOLATE EACH SUB-AGENT
═══════════════════════════════════════════════════════════
Each sub-agent gets:
  - Only the context it needs for its subtask (not the full conversation)
  - Only the tools relevant to its role (coder gets file edit tools, tester
    gets execution tools, researcher gets read/search tools — not all tools
    to all agents)
  - Its own token/turn budget, so one agent's failure or runaway loop cannot
    consume the whole session's budget

A sub-agent's mistake must never silently propagate — its output is always
checked by the reviewer/tester step before being merged back.

═══════════════════════════════════════════════════════════
STEP 3 — CODER RULES
═══════════════════════════════════════════════════════════
- Make the smallest change that satisfies the subtask.
- Match existing naming, structure, and style already found in the codebase
  (from Step 0's note) — do not introduce a new pattern unless asked.
- Never touch files/functions outside the subtask's scope.
- After editing, state exactly what changed and why, in one or two lines.

═══════════════════════════════════════════════════════════
STEP 4 — VERIFY BEFORE DECLARING DONE
═══════════════════════════════════════════════════════════
- tester runs the change (tests, lint, or a manual execution) and reports
  real output — never assume success.
- reviewer confirms the diff actually satisfies the original subtask.
- Only after both pass does the orchestrator mark the subtask complete.

═══════════════════════════════════════════════════════════
STEP 5 — WHEN STUCK: ASK PERMISSION, DON'T IMPROVISE
═══════════════════════════════════════════════════════════
If a subtask cannot be completed with the tools/knowledge available locally:
1. STOP. Do not guess, hallucinate, or silently skip the subtask.
2. Tell the user exactly what's blocking you and what you'd like to do next
   (e.g. "I'd like to search claude.ai / chatgpt.com / grok.com for the
   correct API syntax for X — is that okay?").
3. Wait for explicit user confirmation ("yes"/"go ahead") before taking any
   external action. Never open a browser or query an external site without
   this confirmation, every time — a prior "yes" does not carry over to a
   new blocker.
4. Once permitted, fetch only the specific information needed to unblock
   the subtask, bring it back into context, and resume the plan.

═══════════════════════════════════════════════════════════
STEP 6 — REPORT
═══════════════════════════════════════════════════════════
End with a short summary: what was done, what files changed, what was
verified, and what (if anything) still needs the user's input.
"""

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="OrchestratorAgent",
            description="The primary planner and orchestrator for the LMMs multi-agent system. Decomposes tasks and delegates to sub-agents.",
            capabilities=["planning", "delegation", "review", "text"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        task_desc = context.task.description.lower() if context.task else ""
        if context.memory and not task_desc:
            task_desc = context.memory[-1].get("content", "").lower()
            
        keywords = ["fix", "add", "test", "implement", "debug", "refactor", "create", "write", "change", "update"]
        if any(k in task_desc for k in keywords):
            return 0.85
            
        if len(task_desc.split()) > 10:
            return 0.85
            
        return 0.2

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Act as the Planner/Orchestrator. Decompose the request into subtasks for researcher, coder, tester, and reviewer.",
            "steps": ["INSPECT BEFORE ACTING", "DECOMPOSE THE TASK", "ISOLATE SUB-AGENTS", "EXECUTE AND VERIFY", "REPORT"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[str, None]:
        from lmms.backend.router.planner import Planner
        import inspect

        yield "Starting OrchestratorAgent execution...\n"
        
        task_desc = context.task.description if context.task else "Context task"
        yield f"Calling Planner to decompose task: {task_desc}\n"
        
        planner = Planner()
        graph = planner.plan(task_desc, context)
        
        yield f"Planner created ExecutionGraph with {len(graph.steps)} steps (Intent: {graph.intent}).\n"
        
        any_step_success = False
        
        for step in graph.steps:
            yield f"\n[Step] Agent: {step.agent_name} | Action: {step.action_type}\n"
            
            if step.agent_name == "coder":
                try:
                    from lmms.backend.agents.core_agents.agents.specialized.coding import CodingAgent
                    coder = CodingAgent()
                    async for chunk in coder.execute(context):
                        if not chunk.endswith('\n'):
                            chunk += '\n'
                        yield f"  [Coder] {chunk}"
                    any_step_success = True
                except ImportError:
                    yield f"  [Error] CodingAgent could not be loaded.\n"
            elif step.agent_name == "researcher":
                try:
                    from lmms.backend.agents.specialized.research import ResearchAgent
                    researcher = ResearchAgent()
                    if inspect.isasyncgenfunction(researcher.execute):
                        async for chunk in researcher.execute(context):
                            if not chunk.endswith('\n'):
                                chunk += '\n'
                            yield f"  [Researcher] {chunk}"
                    else:
                        res = researcher.execute(context)
                        if not res.endswith('\n'):
                            res += '\n'
                        yield f"  [Researcher] {res}"
                    any_step_success = True
                except ImportError:
                    yield f"  [Error] ResearchAgent could not be loaded.\n"
            elif step.agent_name == "tester":
                try:
                    from lmms.backend.agents.core_agents.agents.specialized.tester import TesterAgent
                    tester = TesterAgent()
                    async for chunk in tester.execute(context):
                        if not chunk.endswith('\n'):
                            chunk += '\n'
                        yield f"  [Tester] {chunk}"
                    any_step_success = True
                except ImportError:
                    yield f"  [Error] TesterAgent could not be loaded.\n"
            elif step.agent_name == "reviewer":
                try:
                    from lmms.backend.agents.core_agents.agents.specialized.reviewer import ReviewerAgent
                    reviewer = ReviewerAgent()
                    async for chunk in reviewer.execute(context):
                        if not chunk.endswith('\n'):
                            chunk += '\n'
                        yield f"  [Reviewer] {chunk}"
                    any_step_success = True
                except ImportError:
                    yield f"  [Error] ReviewerAgent could not be loaded.\n"
            else:
                yield f"  [Warning] Unknown agent '{step.agent_name}'. Skipping.\n"
                
        if not graph.steps:
            yield "\nOrchestrator execution completed, but no steps were generated.\n"
        elif any_step_success:
            yield "\nOrchestrator execution completed successfully.\n"
        else:
            yield "\nOrchestrator execution failed: All sub-agent steps failed or produced no output.\n"
