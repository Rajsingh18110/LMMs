import json
import asyncio
from typing import Dict, Any, AsyncGenerator

from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class UniversalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="UniversalAgent",
            description="Agentic chat mode capable of utilizing the full suite of system tools autonomously.",
            capabilities=["chat", "text", "tool_use"]
        )
        self.max_iterations = 10

    def evaluate(self, context: ExecutionContext) -> float:
        # Routing to UniversalAgent is handled by explicit UI toggle (Agent Mode), 
        # so this returns 0 by default for normal evaluation, but we will force route to it 
        # when the toggle is active.
        return 0.0

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Engage in normal chat with the capability to autonomously trigger and execute system tools when needed.",
            "steps": ["Stream LLM response", "Execute tool calls if requested", "Iterate until complete"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[Any, None]:
        active_model = context.selected_model
        
        from lmms.backend.providers.manager import ProviderManager
        from lmms.backend.contracts.generation import GenerationRequest, Message, ToolCall
        from lmms.backend.contracts.generation import GenerationEvent
        from lmms.backend.tools.core import default_registry, default_executor
        from lmms.backend.agents.permissions import Permission
        
        if not active_model or active_model == "LMMs Engine":
            yield "\n[Error]: No active model selected. Please select a model from the dropdown.\n"
            return
            
        provider_mgr = ProviderManager()
        
        if "::" in active_model:
            provider_id, model_id = active_model.split("::", 1)
        else:
            provider_id = "local_native"
            model_id = active_model
            
        provider = provider_mgr.get_provider(provider_id)
        if not provider:
            yield f"\n[Error]: Provider '{provider_id}' not found or not enabled.\n"
            return
            
        runtime = provider.get_runtime()
        if not runtime:
            yield f"\n[Error]: Could not initialize runtime for model '{model_id}' on provider '{provider_id}'.\n"
            return

        # Prepare tools in OpenAI format
        tools_list = []
        registered_tools = default_registry.list_tools()
        for t in registered_tools:
            tools_list.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": {k: {"type": "string", "description": v} for k, v in t.parameters.items()},
                        "required": list(t.parameters.keys())
                    }
                }
            })

        # Base messages
        messages = [{"role": "system", "content": "You are a helpful assistant with access to system tools. Use tools if necessary to help the user."}]
        for msg in context.memory:
            # Clean up the memory to match basic message schema
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        if context.task and context.task.description:
            # If the last message was the same as task desc, don't duplicate
            if not messages or messages[-1].get("content") != context.task.description:
                messages.append({"role": "user", "content": context.task.description})

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Convert dicts to Message objects
            msg_objs = []
            for m in messages:
                tc = m.get("tool_calls")
                if tc:
                    tc = [ToolCall(**t) for t in tc]
                msg_objs.append(Message(
                    role=m["role"],
                    content=m.get("content", ""),
                    tool_calls=tc,
                    tool_call_id=m.get("tool_call_id")
                ))

            req = GenerationRequest(
                model_id=model_id,
                messages=msg_objs,
                modality="text",
                execution_mode="FAST",
                tools=tools_list if tools_list else None
            )
            
            try:
                # We need to collect the full response to check for tool calls
                full_content = ""
                full_reasoning = ""
                current_tool_calls = {}

                async for evt in runtime.stream(req):
                    if evt.type == "content_delta":
                        full_content += evt.content
                    elif evt.type == "thinking_delta" or evt.type == "reasoning_delta":
                        full_reasoning += (evt.reasoning or evt.content)
                    elif evt.type == "tool_call_delta" or evt.type == "tool_call_started":
                        if evt.tool_call:
                            tc_id = evt.tool_call.id
                            if tc_id not in current_tool_calls:
                                current_tool_calls[tc_id] = {"id": tc_id, "name": evt.tool_call.name, "arguments": ""}
                            if evt.tool_call.arguments:
                                current_tool_calls[tc_id]["arguments"] += evt.tool_call.arguments
                    
                    yield evt

                # If no tool calls, we are done
                if not current_tool_calls:
                    break
                
                # Append assistant message with tool calls
                asst_msg = {"role": "assistant", "content": full_content, "tool_calls": []}
                for tc in current_tool_calls.values():
                    asst_msg["tool_calls"].append({
                        "id": tc["id"],
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    })
                messages.append(asst_msg)

                # Execute tool calls
                for tc in current_tool_calls.values():
                    tool_name = tc["name"]
                    args_str = tc["arguments"]
                    
                    try:
                        args = json.loads(args_str) if args_str else {}
                    except Exception as e:
                        args = {}
                        yield GenerationEvent(type="content_delta", content=f"\n[Tool Execution Error: Failed to parse arguments for {tool_name}]\n")
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": f"Failed to parse JSON arguments: {str(e)}"})
                        continue
                        
                    yield GenerationEvent(type="content_delta", content=f"\n[Executing Tool: {tool_name}({args_str})]\n")
                    
                    # Need a way to inject confirmation context for UI if required
                    # We will implement confirmation in ChatService or rely on a global callback, 
                    # but for now we execute and catch Permission Denied if require_confirm is needed.
                    
                    # Pass require_confirm flag if the tool is high risk
                    tdef = default_registry.get_tool(tool_name)
                    if tdef and (Permission.WRITE_FILE in tdef.permissions or Permission.TERMINAL in tdef.permissions or Permission.GIT_COMMIT in tdef.permissions):
                        if hasattr(context, "request_confirmation"):
                            yield GenerationEvent(type="content_delta", content=f"\n[Awaiting UI Confirmation for {tool_name}...]\n")
                            approved = await context.request_confirmation(tool_name, args)
                            if not approved:
                                yield GenerationEvent(type="content_delta", content=f"[Tool Result: Failed - User Denied Permission]\n")
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": "Execution rejected: User denied permission via UI dialog."
                                })
                                continue
                            else:
                                args["confirm"] = True
                        else:
                            # Fallback if no UI hook
                            args["require_confirm"] = True
                        
                    res = default_executor.execute(tool_name, args)
                    
                    res_str = ""
                    if res.success:
                        res_str = json.dumps(res.data) if isinstance(res.data, (dict, list)) else str(res.data)
                        yield GenerationEvent(type="content_delta", content=f"[Tool Result: Success]\n")
                    else:
                        res_str = f"Error: {res.error}"
                        yield GenerationEvent(type="content_delta", content=f"[Tool Result: Failed - {res.error}]\n")
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": res_str
                    })

            except Exception as e:
                yield GenerationEvent(type="content_delta", content=f"\n[Error during generation]: {e}\n")
                break

        if iteration >= self.max_iterations:
            yield GenerationEvent(type="content_delta", content=f"\n[System]: Reached maximum autonomous iterations ({self.max_iterations}). Stopping.\n")
