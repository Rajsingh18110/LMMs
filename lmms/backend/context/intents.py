from typing import Dict, Any
from lmms.backend.context.capabilities import IntentContext

class IntentDetector:
    def __init__(self, backend_manager):
        self.backend = backend_manager

    def detect(self, raw_prompt: str) -> IntentContext:
        """
        Layered intent detection:
        1. Rule Based
        2. Embedding (Stubbed for future)
        3. Control Model (Stubbed for future)
        """
        prompt_lower = raw_prompt.lower()
        
        # Layer 1: Rule Based
        if "bug" in prompt_lower or "fix" in prompt_lower or "code" in prompt_lower:
            return IntentContext(
                name="Coding",
                confidence=0.9,
                required_capabilities=["Text", "Coding", "ToolCalling"],
                required_tools=["view_file", "write_to_file", "grep_search"]
            )
        elif "git" in prompt_lower or "commit" in prompt_lower or "branch" in prompt_lower:
            return IntentContext(
                name="GitOperation",
                confidence=0.85,
                required_capabilities=["Text", "Git"],
                required_tools=["git_status", "git_commit"]
            )
        
        # Default fallback
        return IntentContext(
            name="GeneralChat",
            confidence=0.5,
            required_capabilities=["Text"],
            required_tools=[]
        )
