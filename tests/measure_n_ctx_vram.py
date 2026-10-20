#!/usr/bin/env python3
"""
Measures VRAM usage and allocation for Qwen3-8B-Q4_K_M on native CUDA
across various context window sizes: n_ctx = 4096, 8192, 16384.
"""

import os
import sys
import time
import subprocess
from llama_cpp import Llama

def get_vram_used_mb() -> int:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            universal_newlines=True
        )
        return int(out.strip().split("\n")[0])
    except Exception as e:
        return -1

def get_vram_total_mb() -> int:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            universal_newlines=True
        )
        return int(out.strip().split("\n")[0])
    except Exception as e:
        return -1

MODEL_PATH = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")

def test_context_size(n_ctx: int):
    vram_before = get_vram_used_mb()
    print(f"\n--- Testing n_ctx = {n_ctx} ---")
    print(f"VRAM before: {vram_before} MiB")
    
    t0 = time.perf_counter()
    llm = None
    try:
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=n_ctx,
            n_gpu_layers=-1,
            verbose=False
        )
        load_time = time.perf_counter() - t0
        vram_after = get_vram_used_mb()
        delta = vram_after - vram_before
        print(f"Loaded successfully in {load_time:.2f}s!")
        print(f"VRAM after:  {vram_after} MiB (KV Cache + Model Delta: +{delta} MiB)")
        
        # Test inference token generation
        from typing import Any, cast
        res = cast(dict, llm.create_chat_completion(
            messages=[{"role": "user", "content": "Explain binary search in 1 paragraph.\n/no_think"}],  # type: ignore
            max_tokens=30,
            temperature=0.0
        ))
        text = cast(str, res["choices"][0]["message"].get("content", "") or "")
        vram_active = get_vram_used_mb()
        print(f"Inference verified: generated {len(text.split())} words. Peak VRAM: {vram_active} MiB")
        return {"n_ctx": n_ctx, "success": True, "vram_mb": vram_active, "delta_mb": delta}
    except Exception as e:
        print(f"FAILED for n_ctx={n_ctx}: {e}")
        return {"n_ctx": n_ctx, "success": False, "error": str(e)}
    finally:
        del llm
        import gc
        gc.collect()
        time.sleep(1)

def main():
    total_vram = get_vram_total_mb()
    print("=" * 80)
    print(f"GPU VRAM CONTEXT SCALING BENCHMARK (Total GPU VRAM: {total_vram} MiB)")
    print(f"Model: {MODEL_PATH}")
    print("=" * 80)

    results = []
    for ctx in [4096, 8192, 16384]:
        res = test_context_size(ctx)
        results.append(res)

    print("\n" + "=" * 80)
    print(f"{'n_ctx Size':<12} | {'Status':<10} | {'VRAM Used':<14} | {'Headroom Remaining':<20}")
    print("-" * 80)
    for r in results:
        if r["success"]:
            headroom = total_vram - r["vram_mb"]
            print(f"{r['n_ctx']:<12} | {'PASS':<10} | {r['vram_mb']:>5} MiB     | {headroom:>5} MiB ({headroom/total_vram*100:.1f}%)")
        else:
            print(f"{r['n_ctx']:<12} | {'OOM/FAIL':<10} | {'N/A':<14} | {r.get('error', '')[:20]}")
    print("=" * 80)

if __name__ == "__main__":
    main()
