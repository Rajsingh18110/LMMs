from lmms.backend.context.capabilities import ExecutionContext, TokenBudget

class ContextAssembler:
    def assemble(self, context: ExecutionContext) -> str:
        """
        Builds the final prompt package, validating against TokenBudget.
        This is a mock assembly. Real assembly requires tokenizer.
        """
        budget: TokenBudget = context.token_budget
        
        # Build System Prompt
        parts = []
        parts.append(f"<intent>{context.intent.name}</intent>")
        
        # Tasks (High Priority)
        parts.append(f"<tasks>{str(context.task_data)[:budget.task_tokens]}</tasks>")
        
        # Git
        parts.append(f"<git>{str(context.git_data)[:budget.git_tokens]}</git>")
        
        # Memory
        parts.append(f"<memory>{str(context.memory_data)[:budget.memory_tokens]}</memory>")
        
        # Tools
        parts.append(f"<tools>{str(context.tools)[:budget.tool_tokens]}</tools>")
        
        # The user's actual prompt
        parts.append(f"<user_prompt>{context.raw_prompt}</user_prompt>")
        
        context.assembled_prompt = "\n".join(parts)
        return context.assembled_prompt
