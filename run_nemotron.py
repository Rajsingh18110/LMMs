import sys
import json
sys.path.append('.')
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime

try:
    print("Loading model...")
    runtime = LlamaCppRuntime()
    runtime.load_model('NVIDIA-Nemotron3-Nano-4B-Q4_K_M')
    print("Model loaded. Generating...")
    
    gen = list(runtime._models.values())[0].create_chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
        temperature=0.8,
        top_p=0.95
    )
    
    for chunk in gen:
        token = chunk['choices'][0]['delta'].get('content', '')
        if token:
            print(f"TOKEN: {repr(token)}")
except Exception as e:
    import traceback
    traceback.print_exc()
