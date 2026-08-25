import requests
import json
import time

try:
    resp = requests.post("http://localhost:11435/v1/chat/completions", json={
        "model_name": "NVIDIA-Nemotron3-Nano-4B-Q4_K_M",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
        "think": True,
        "mode": "deep"
    }, stream=True, timeout=10)
    
    for line in resp.iter_lines():
        if line:
            print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
