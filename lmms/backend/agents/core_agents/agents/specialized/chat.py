from typing import Dict, Any, AsyncGenerator
import json
import requests
from lmms.backend.agents.core_agents.agents.base import BaseAgent
from lmms.backend.agents.core_agents.agents.context import ExecutionContext

class PlainChatAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="PlainChatAgent",
            description="Handles general conversation and simple questions that do not require specialized workflows.",
            capabilities=["chat", "text"]
        )

    def evaluate(self, context: ExecutionContext) -> float:
        # Fixed baseline score. If no specialized agent scores above 0.35, this agent will take over.
        return 0.35

    def plan(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "strategy": "Respond directly to the user's message using the base LLM without executing complex sub-agent tools.",
            "steps": ["Stream LLM response"]
        }

    async def execute(self, context: ExecutionContext) -> AsyncGenerator[Any, None]:
        active_model = context.selected_model
        
        # In a real environment we have access to BackendManager, but here we can instantiate ProviderManager
        # since it is a lightweight manager that relies on the RegistryService singleton.
        from lmms.backend.providers.manager import ProviderManager
        from lmms.backend.contracts.generation import GenerationRequest, Message
        from lmms.backend.contracts.generation import GenerationEvent
        
        # If no model provided, fallback or fail
        if not active_model or active_model == "LMMs Engine":
            yield "\n[Error]: No active model selected. Please select a model from the dropdown.\n"
            return
            
        provider_mgr = ProviderManager()
        
        if "::" in active_model:
            provider_id, model_id = active_model.split("::", 1)
        else:
            # Fallback if old format
            provider_id = "local_native"
            model_id = active_model
            
        provider = provider_mgr.get_provider(provider_id)
        if not provider:
            yield f"\n[Error]: Provider '{provider_id}' not found or not enabled.\n"
            return
            
        runtime = provider.get_runtime(model_id)
        if not runtime:
            yield f"\n[Error]: Could not initialize runtime for model '{model_id}' on provider '{provider_id}'.\n"
            return

        user_prompt = context.task.description if context.task else ""
        req = GenerationRequest(
            model_id=model_id,
            messages=[Message(role="user", content=user_prompt)],
            modality="text",
            execution_mode="FAST"
        )
        
        try:
            async for evt in runtime.stream(req):
                # We yield the GenerationEvent object directly to the ChatService
                yield evt
        except Exception as e:
            yield f"\n[Error during generation]: {e}\n"

