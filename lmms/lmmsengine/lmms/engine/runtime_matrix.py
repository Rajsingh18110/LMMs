RUNTIME_CAPABILITIES = {
    "llama_cpp": {
        "vision": False,
        "tool_calling": True,
        "embedding": True,
        "requires_gpu": False
    },
    "vllm": {
        "vision": True,
        "tool_calling": True,
        "embedding": True,
        "requires_gpu": True
    },
    "air": {
        "vision": False,
        "tool_calling": True,
        "embedding": True,
        "requires_gpu": False
    }
}
