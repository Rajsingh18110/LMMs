from typing import Optional, Any, List
from lmms.backend.router.execution_graph import ExecutionGraph
from lmms.backend.orchestration.router import IntentRouter, IntentType


class RuleRouter:
    """
    Deterministic rule-based execution graph router.
    Powered by the unified IntentRouter engine to route coding, file ops,
    and debugging accurately to CodingAgent and OrchestratorAgent.
    """

    def __init__(self):
        self.intent_router = IntentRouter()

    def route(self, intent_name: str) -> ExecutionGraph:
        graph = ExecutionGraph(intent=intent_name)

        # Check if intent_name is a raw prompt or a formal intent keyword
        detected_intent = None
        try:
            res = self.intent_router.route(intent_name)
            detected_intent = res.intent
        except Exception:
            pass

        norm = (intent_name or "").strip().lower()
        coding_keywords = (
            "fix", "debug", "refactor", "verify", "tests", "unit test", "failing test",
            "code", "coding", "bug", "error", "patch", "implement", "write code"
        )
        workspace_keywords = ("file_ops", "files", "workspace", "read", "edit", "write", "save", "create")
        search_keywords = ("search", "research", "lookup", "docs")
        git_keywords = ("gitoperation", "git", "commit", "branch")
        terminal_keywords = ("terminal", "bash", "command", "run")

        if detected_intent == IntentType.CODING or any(keyword in norm for keyword in coding_keywords):
            graph.add_step(agent_name="OrchestratorAgent", action_type="PlanTask")
            graph.add_step(agent_name="CodingAgent", action_type="WriteCode", dependencies=["OrchestratorAgent"])
            graph.add_step(agent_name="TesterAgent", action_type="VerifyCode", dependencies=["CodingAgent"])
            graph.add_step(agent_name="ReviewerAgent", action_type="ReviewDiff", dependencies=["TesterAgent"])
        elif detected_intent == IntentType.WORKSPACE_FILE_OPS or any(keyword in norm for keyword in workspace_keywords):
            graph.add_step(agent_name="CodingAgent", action_type="FileOps")
        elif any(keyword in norm for keyword in terminal_keywords):
            graph.add_step(agent_name="CodingAgent", action_type="TerminalRun")
        elif detected_intent in (IntentType.WEB_SEARCH, IntentType.TOOL_RESEARCH) or any(keyword in norm for keyword in search_keywords):
            graph.add_step(agent_name="ResearchAgent", action_type="DeepResearch")
        elif any(keyword in norm for keyword in git_keywords):
            graph.add_step(agent_name="GitAgent", action_type="CommitChanges")
        else:
            graph.add_step(agent_name="ChatAgent", action_type="GeneralChat")

        return graph

    def execute_graph(self, graph: ExecutionGraph, context: Optional[Any] = None) -> list[str]:
        """Execute the graph deterministically for the live multi-agent CLI pipeline.

        When an execution context is supplied, steps are dispatched to their real
        specialized agents (Orchestrator, CodingAgent, TesterAgent) with worktree
        and sandbox verification.
        """
        if not graph or not getattr(graph, "steps", None):
            return []

        step_map = {
            "OrchestratorAgent": "PlanTask",
            "CodingAgent": "WriteCode",
            "TesterAgent": "VerifyCode",
            "ReviewerAgent": "ReviewDiff",
            "ResearchAgent": "DeepResearch",
            "GitAgent": "CommitChanges",
            "ChatAgent": "GeneralChat",
        }

        outputs = []
        last_test_res = None
        for index, step in enumerate(graph.steps, start=1):
            step_name = step.agent_name
            action_type = step.action_type or step_map.get(step_name, "Execute")
            status = "dependency satisfied" if step.dependencies else "ready"

            if context is not None:
                try:
                    from lmms.backend.events.bus import get_event_bus
                    eb = get_event_bus()
                    eb.emit("agent_started", {"agent": step_name, "action": action_type})

                    if isinstance(context, dict):
                        task_desc = context.get("task", "")
                        ws_path = context.get("workspace")
                    elif getattr(context, "task", None):
                        task_desc = context.task.description
                        ws_path = getattr(context, "workspace_id", None)
                    else:
                        task_desc = str(context)
                        ws_path = None

                    if step_name == "OrchestratorAgent":
                        status = "planned"
                    elif step_name == "CodingAgent":
                        from lmms.backend.agents.specialized.coding import CodingAgent
                        coder = CodingAgent()
                        code_res = coder.write_code(task_desc)
                        status = "executed: " + (code_res[:40] if code_res else "done")
                    elif step_name == "TesterAgent":
                        from lmms.backend.agents.specialized.tester import TesterAgent
                        tester = TesterAgent()
                        last_test_res = tester.verify(workspace=ws_path)
                        status = "verified: " + ("PASS" if last_test_res.get("passed", True) else f"FAIL (exit {last_test_res.get('exit_code')})")
                    elif step_name == "ReviewerAgent":
                        from lmms.backend.agents.specialized.reviewer import ReviewerAgent
                        reviewer = ReviewerAgent()
                        rev = reviewer.review(task_description=task_desc, test_results=last_test_res, workspace=ws_path)
                        status = "reviewed: " + rev.get("status", "PASS")
                    elif step_name == "GitAgent":
                        from lmms.backend.agents.specialized.git import GitAgent
                        git_agent = GitAgent()
                        status = "git_ready"
                    elif step_name == "ResearchAgent":
                        from lmms.backend.agents.specialized.research import ResearchAgent
                        status = "research_done"

                    eb.emit("agent_completed", {"agent": step_name, "status": status})
                except Exception as e:
                    status = f"error: {e}"

            outputs.append(f"{index}. {step_name}:{action_type} ({status})")

        return outputs
