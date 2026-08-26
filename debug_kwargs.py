import sys, os
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime

runtime = LlamaCppRuntime()
path = "/home/kali/.lmms/models/Qwen3-8B-Q4_K_M.gguf"
kwargs = {"n_ctx": 128}

detected_format = runtime._detect_chat_format(path)
if detected_format:
    kwargs["chat_format"] = detected_format
elif "chatml" in os.path.basename(path).lower():
    kwargs["chat_format"] = "chatml"

print("kwargs is:", kwargs)
