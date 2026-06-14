import time
from typing import Dict, Any
from rich.console import Console
from rich.table import Table

class BenchmarkEngine:
    def run_real_benchmark(self, model_name: str):
        c = Console()
        c.print(f"[cyan]Starting benchmark for {model_name}...[/cyan]")
        
        import requests
        
        # We will hit the API to generate 10 tokens and measure TTFT and Token/s
        # Since we just want to measure load_time + generation, we can measure the first chunk time
        payload = {
            "model_name": model_name,
            "messages": [{"role": "user", "content": "Write a long poem."}],
            "mode": "fast",
            "think": False
        }
        
        t0 = time.time()
        try:
            res = requests.post("http://localhost:11435/v1/chat/completions", json=payload, stream=True, timeout=120)
            res.raise_for_status()
        except Exception as e:
            c.print(f"[red]Failed to connect to engine or benchmark model: {e}[/red]")
            return
            
        load_time = -1
        tokens_generated = 0
        
        t1 = time.time()
        for line in res.iter_lines():
            if line:
                if load_time == -1:
                    load_time = time.time() - t0
                tokens_generated += 1
                if tokens_generated >= 10:
                    break
                    
        gen_time = time.time() - t1
        tok_sec = tokens_generated / gen_time if gen_time > 0 else 0
        
        # Get memory stats via HTTP
        vram_used = 0.0
        try:
            stats_res = requests.get("http://localhost:11435/v1/air/stats")
            if stats_res.status_code == 200:
                vram_used = stats_res.json().get("vram_used_gb", 0.0)
        except Exception:
            pass
        
        # Print
        table = Table(title=f"Benchmark: {model_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Result", style="green")
        table.add_row("TTFT (Load+First Token)", f"{load_time:.2f} s")
        table.add_row("Tokens/sec", f"{tok_sec:.2f} t/s")
        table.add_row("VRAM Used", f"{vram_used:.2f} GB")
        
        c.print(table)
