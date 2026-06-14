import time
import requests
import json
from typing import Dict, Any, List

class BenchmarkSuite:
    """
    Runs standard benchmark prompts against local LLMs to measure
    Tokens/Second (TPS) and Time-To-First-Token (TTFT).
    """
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.test_prompts = [
            "Write a Python script to compute the Fibonacci sequence up to 100.",
            "Explain quantum computing in simple terms.",
            "Translate 'Hello, how are you?' into French, German, and Spanish."
        ]

    def run_benchmark(self, model_name: str) -> Dict[str, Any]:
        """
        Executes benchmarks on the specified model.
        Requires the model to be already pulled.
        """
        results = {
            "model": model_name,
            "ttft_avg_ms": 0.0,
            "tps_avg": 0.0,
            "runs": []
        }
        
        total_ttft = 0
        total_tps = 0
        
        for prompt in self.test_prompts:
            start_time = time.time()
            ttft = 0
            tokens = 0
            
            try:
                # We use stream=True to measure TTFT
                res = requests.post(
                    f"{self.host}/api/chat",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                        "options": {"temperature": 0.0} # Deterministic
                    },
                    stream=True,
                    timeout=60
                )
                
                first_token_received = False
                for line in res.iter_lines():
                    if line:
                        if not first_token_received:
                            ttft = (time.time() - start_time) * 1000
                            first_token_received = True
                        
                        data = json.loads(line)
                        if not data.get("done"):
                            tokens += 1
                            
                end_time = time.time()
                total_time = end_time - start_time
                
                # Exclude TTFT from TPS calculation
                eval_time = total_time - (ttft / 1000)
                tps = tokens / eval_time if eval_time > 0 else 0
                
                total_ttft += ttft
                total_tps += tps
                
                results["runs"].append({
                    "prompt": prompt[:30] + "...",
                    "ttft_ms": round(ttft, 2),
                    "tps": round(tps, 2),
                    "tokens_generated": tokens
                })
                
            except Exception as e:
                print(f"Error benchmarking {model_name}: {e}")
                
        if len(self.test_prompts) > 0:
            results["ttft_avg_ms"] = round(total_ttft / len(self.test_prompts), 2)
            results["tps_avg"] = round(total_tps / len(self.test_prompts), 2)
            
        return results
