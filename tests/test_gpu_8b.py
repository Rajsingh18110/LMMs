#!/usr/bin/env python3
"""
Test Qwen3-8B-Q4_K_M with native CUDA and n_gpu_layers=-1.
Measures:
- VRAM before and after load (via nvidia-smi)
- TTFT and decode tokens/sec
"""

import os
import sys
import time
import subprocess
import pytest

llama_cpp = pytest.importorskip("llama_cpp")
Llama = llama_cpp.Llama

def get_vram_used_mb() -> int:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            universal_newlines=True
        )
        return int(out.strip().split("\n")[0])
    except Exception as e:
        print("nvidia-smi error:", e)
        return -1

model_path = os.path.expanduser("~/.lmms/models/Qwen3-8B-Q4_K_M.gguf")

@pytest.mark.skipif(not os.path.exists(model_path), reason="8B model file not found")
def test_gpu_8b_performance():
    vram_before = get_vram_used_mb()
    print(f"VRAM Used Before Load: {vram_before} MiB")

    print(f"Loading {model_path} with n_gpu_layers=-1...")
    t0 = time.perf_counter()
    try:
        llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=6,
            n_gpu_layers=-1,  # Offload all layers to GPU!
            use_mmap=True,
            verbose=False
        )
    except Exception as e:
        pytest.skip(f"Could not load 8B directly into CUDA (engine daemon active): {e}")
    t_load = time.perf_counter() - t0
    vram_after = get_vram_used_mb()
    print(f"Model loaded in {t_load:.2f}s.")
    print(f"VRAM Used After Load: {vram_after} MiB (Delta: +{vram_after - vram_before} MiB)")

    # Benchmark generation speed across 3 runs
    prompt = "Explain the difference between a mutex and a semaphore in operating systems in 3 concise paragraphs."

    for r in range(1, 4):
        print(f"\n--- Run {r} ---")
        t_start = time.perf_counter()
        ttft = None
        gen_text = ""
        gen_tokens = 0

        from typing import Any, cast
        stream = cast(Any, llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],  # type: ignore
            max_tokens=150,
            stream=True,
            temperature=0.0
        ))

        for chunk_raw in stream:
            chunk = cast(dict, chunk_raw)
            delta = chunk["choices"][0].get("delta", {})
            tok = delta.get("content", "")
            if tok:
                if ttft is None:
                    ttft = time.perf_counter() - t_start
                gen_text += tok
                gen_tokens += 1

        t_total = time.perf_counter() - t_start
        ttft = ttft if ttft is not None else t_total
        decode_time = t_total - ttft
        tok_per_sec = (gen_tokens - 1) / decode_time if (decode_time > 0 and gen_tokens > 1) else (gen_tokens / t_total)

        print(f"TTFT: {ttft:.3f}s | Tokens: {gen_tokens} | Total: {t_total:.2f}s | Decode Speed: {tok_per_sec:.2f} tok/s")

    vram_final = get_vram_used_mb()
    print(f"\nFinal VRAM Used: {vram_final} MiB")
