CAPABILITIES = {
    "text":       "General text generation",
    "coding":     "Code generation + debugging",
    "vision":     "Image understanding",
    "audio":      "Speech to text / TTS",
    "reasoning":  "Multi-step logical reasoning",
    "tool_use":   "Can call external tools/APIs",
    "embedding":  "Generate vector embeddings",
    "reranking":  "Rerank search results",
}

class CapabilityRegistry:
    def __init__(self):
        self._map = {} # model_id -> list of capabilities
        
    def assign(self, model_id: str, 
               caps: list[str]):
        # Store model → capabilities mapping
        self._map[model_id] = [c for c in caps if c in CAPABILITIES]

    def models_with(self, 
                    capability: str) -> list[str]:
        # Return all models that have this capability
        return [mid for mid, caps in self._map.items() if capability in caps]

    def can(self, model_id: str, 
            capability: str) -> bool:
        # Check if model has capability
        return capability in self._map.get(model_id, [])
