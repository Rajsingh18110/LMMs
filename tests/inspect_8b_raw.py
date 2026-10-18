#!/usr/bin/env python3
import os
import sys
import json
from llama_cpp import Llama

model_path = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")
llm = Llama(model_path=model_path, n_ctx=2048, n_threads=6, n_gpu_layers=0, verbose=False)

messages = [
    {"role": "system", "content": "You are Qwen, a helpful assistant with tool capabilities.\nTo call a tool, use:\n<tool_call>{\"tool\": \"web_search\", \"kwargs\": {\"query\": \"...\"}}</tool_call>\nAvailable tools:\n- web_search: search query"},
    {"role": "user", "content": "Search for the latest Python documentation about asyncio."}
]

print("=== RAW OUTPUT WITHOUT MODIFICATIONS ===")
res = llm.create_chat_completion(messages=messages, max_tokens=200, temperature=0.0)
content = res["choices"][0]["message"]["content"]
print(repr(content))
print("--- PRINTED CONTENT ---")
print(content)
