"""
LMMs Standalone Dual-Engine Console & Runner
Provides standalone terminal execution, hardware profiling, runtime inspection,
and direct inference for Engine 1 (Air+LlamaCpp) and Engine 2 (Air+PyTorch).
"""

from __future__ import annotations

import os
import sys
import time
from typing import List, Optional

from lmms.engine.manager import engine_manager

# Typography
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_GREEN = "\033[1;32m"
COLOR_BOLD_WHITE = "\033[1;37m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"


def print_engine_banner() -> None:
    status = engine_manager.status()
    mode = status.get("active_mode", "auto")
    loaded = status.get("loaded_models", [])

    sys.stdout.write(f"\n{COLOR_BOLD_WHITE}lmms-engine{COLOR_RESET} {COLOR_DIM}v1.0.0 (Standalone Dual-Engine Runtime){COLOR_RESET}\n")
    sys.stdout.write(f"{COLOR_DIM}────────────────────────────────────────────────────────────────────{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_BOLD_CYAN}Active Mode:{COLOR_RESET}     {mode.upper()}\n")
    sys.stdout.write(f"  {COLOR_BOLD_CYAN}Engine 1:{COLOR_RESET}        Air + Llama.cpp (GGUF & Tri-Regime Pager)\n")
    sys.stdout.write(f"  {COLOR_BOLD_CYAN}Engine 2:{COLOR_RESET}        Air + PyTorch (Safetensors & Multimodal)\n")
    loaded_str = ", ".join(loaded) if loaded else f"{COLOR_DIM}None (idle){COLOR_RESET}"
    sys.stdout.write(f"  {COLOR_BOLD_CYAN}Loaded Models:{COLOR_RESET}   {loaded_str}\n\n")

    sys.stdout.write(f"{COLOR_BOLD_WHITE}Engine Commands:{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine status{COLOR_RESET}                 Show dual-engine telemetry & VRAM state\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine mode [auto|1|2]{COLOR_RESET}        Switch active runtime (auto, llamacpp, pytorch)\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine run <model> [prompt]{COLOR_RESET}   Direct standalone inference via active engine\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine unload [model]{COLOR_RESET}         Unload models from memory & release GPU VRAM\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine benchmark <model>{COLOR_RESET}      Run hardware tokens/sec & latency benchmark\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms engine doctor{COLOR_RESET}                 Hardware diagnostic & GPU compatibility check\n\n")
    sys.stdout.flush()


def cmd_engine_status() -> None:
    """Print comprehensive engine status, hardware, and active cache."""
    status = engine_manager.status()
    e1_health = status.get("engine_1", {})
    e2_health = status.get("engine_2", {})
    loaded = status.get("loaded_models", [])

    sys.stdout.write(f"\n{COLOR_BOLD_WHITE}LMMs Dual-Engine Runtime Status{COLOR_RESET}\n")
    sys.stdout.write(f"{COLOR_DIM}────────────────────────────────────────────────────────────────────{COLOR_RESET}\n")
    sys.stdout.write(f"  Mode:                {COLOR_BOLD_CYAN}{status.get('active_mode', 'auto')}{COLOR_RESET}\n")
    sys.stdout.write(f"  Engine 1 (LlamaCpp): {COLOR_BOLD_GREEN if e1_health.get('status') == 'ok' else COLOR_YELLOW}{e1_health.get('status', 'unknown')}{COLOR_RESET}\n")
    sys.stdout.write(f"  Engine 2 (PyTorch):  {COLOR_BOLD_GREEN if e2_health.get('status') == 'ok' else COLOR_YELLOW}{e2_health.get('status', 'unknown')}{COLOR_RESET}\n")
    sys.stdout.write(f"  Loaded Models:       {COLOR_BOLD_WHITE}{len(loaded)}{COLOR_RESET}\n")

    if loaded:
        for m in loaded:
            sys.stdout.write(f"    • {COLOR_CYAN}{m}{COLOR_RESET}\n")

    # Hardware stats
    try:
        import psutil
        ram = psutil.virtual_memory()
        sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Host Memory Telemetry:{COLOR_RESET}\n")
        sys.stdout.write(f"  RAM Total:           {ram.total / (1024**3):.1f} GB\n")
        sys.stdout.write(f"  RAM Available:       {ram.available / (1024**3):.1f} GB\n")
        sys.stdout.write(f"  RAM Used:            {ram.percent}%\n")
    except Exception:
        pass

    try:
        import torch
        if torch.cuda.is_available():
            dev_name = torch.cuda.get_device_name(0)
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            alloc_vram = torch.cuda.memory_allocated(0) / (1024**3)
            sys.stdout.write(f"\n{COLOR_BOLD_WHITE}GPU Telemetry (Device 0):{COLOR_RESET}\n")
            sys.stdout.write(f"  Device:              {COLOR_BOLD_CYAN}{dev_name}{COLOR_RESET}\n")
            sys.stdout.write(f"  VRAM Total:          {total_vram:.2f} GB\n")
            sys.stdout.write(f"  VRAM Allocated:      {alloc_vram:.2f} GB\n")
            sys.stdout.write(f"  VRAM Free:           {(total_vram - alloc_vram):.2f} GB\n")
    except Exception:
        pass

    sys.stdout.write(f"\n")
    sys.stdout.flush()


def cmd_engine_mode(args: List[str]) -> None:
    if not args:
        current = engine_manager.active_mode
        sys.stdout.write(f"Active engine mode: {COLOR_BOLD_CYAN}{current}{COLOR_RESET}\n")
        sys.stdout.write(f"Usage: lmms engine mode [auto | 1 | 2]\n")
        sys.stdout.write(f"  auto : Smart-dispatch based on model format and VRAM\n")
        sys.stdout.write(f"  1    : Force Engine 1 (Air + Llama.cpp GGUF)\n")
        sys.stdout.write(f"  2    : Force Engine 2 (Air + PyTorch Safetensors)\n")
        sys.stdout.flush()
        return

    mode_target = args[0].lower().strip()
    try:
        new_mode = engine_manager.set_engine_mode(mode_target)
        sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Engine mode set to: {COLOR_BOLD_CYAN}{new_mode}{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}✖ Error setting engine mode:{COLOR_RESET} {e}\n")
    sys.stdout.flush()


def cmd_engine_unload(args: List[str]) -> None:
    """Unloads active models and releases GPU VRAM."""
    model_name = args[0] if args else None
    sys.stdout.write(f"{COLOR_CYAN}Unloading model memory and releasing VRAM...{COLOR_RESET}\n")
    sys.stdout.flush()

    try:
        # Engine 1 unload
        if hasattr(engine_manager.engine_1, "unload_model"):
            engine_manager.engine_1.unload_model(model_name)
        # Engine 2 unload
        if hasattr(engine_manager.engine_2, "unload_model"):
            engine_manager.engine_2.unload_model(model_name)

        # Clear cache
        for m in list(engine_manager.cache.loaded_models.keys()):
            if model_name is None or m == model_name:
                engine_manager.cache.unload_model(m)

        # Force PyTorch CUDA cache flush if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Model memory purged. VRAM successfully freed.\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}✖ Error during unload:{COLOR_RESET} {e}\n")
    sys.stdout.flush()


def cmd_engine_run(args: List[str]) -> None:
    """Direct standalone engine inference in terminal."""
    if not args:
        sys.stdout.write("Usage: lmms engine run <model_name> [prompt]\n")
        sys.stdout.flush()
        return

    model_name = args[0]
    prompt = " ".join(args[1:]) if len(args) > 1 else "Hello, who are you and what engine are you running on?"

    sys.stdout.write(f"{COLOR_DIM}Resolving runtime for '{model_name}'...{COLOR_RESET}\n")
    runtime = engine_manager.get_runtime(model_name)

    # Check if loaded, if not attempt load
    if not engine_manager.is_model_loaded(model_name):
        sys.stdout.write(f"{COLOR_CYAN}Loading '{model_name}' into engine memory...{COLOR_RESET}\n")
        models_dir = os.path.expanduser("~/.lmms/models")
        path = os.path.join(models_dir, f"{model_name}.gguf")
        if not os.path.exists(path):
            path = os.path.join(models_dir, model_name)

        success = runtime.load_model(path if os.path.exists(path) else model_name)
        if not success:
            sys.stdout.write(f"{COLOR_RED}✖ Failed to load model '{model_name}'.{COLOR_RESET}\n")
            return

    sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Generating stream from {COLOR_BOLD_CYAN}{model_name}{COLOR_RESET}:\n\n")
    sys.stdout.flush()

    messages = [{"role": "user", "content": prompt}]
    try:
        t0 = time.time()
        token_count = 0
        generator = runtime.generate({"messages": messages, "mode": "deep", "think": False}, stream=True)
        for chunk in generator:
            text = ""
            if isinstance(chunk, dict):
                content = chunk.get("message", {}).get("content", "")
                if not content and "choices" in chunk:
                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                text = content
            elif isinstance(chunk, str):
                text = chunk

            if text:
                sys.stdout.write(text)
                sys.stdout.flush()
                token_count += 1

        elapsed = max(0.01, time.time() - t0)
        sys.stdout.write(f"\n\n{COLOR_DIM}Completed {token_count} tokens in {elapsed:.2f}s ({token_count/elapsed:.1f} tok/s){COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"\n{COLOR_RED}✖ Generation error:{COLOR_RESET} {e}\n")
    sys.stdout.flush()


def cmd_engine_doctor() -> None:
    """Performs engine hardware diagnostic scan."""
    sys.stdout.write(f"\n{COLOR_BOLD_WHITE}LMMs Dual-Engine Diagnostics (Doctor){COLOR_RESET}\n")
    sys.stdout.write(f"{COLOR_DIM}────────────────────────────────────────────────────────────────────{COLOR_RESET}\n")

    # Check 1: Python environment
    sys.stdout.write(f"  Python Runtime:      {sys.version.split()[0]} ({sys.executable})\n")

    # Check 2: CUDA support
    has_cuda = False
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        status_str = f"{COLOR_BOLD_GREEN}Available ({torch.cuda.get_device_name(0)}){COLOR_RESET}" if has_cuda else f"{COLOR_YELLOW}Not Available (CPU mode){COLOR_RESET}"
        sys.stdout.write(f"  PyTorch CUDA:        {status_str}\n")
    except Exception as e:
        sys.stdout.write(f"  PyTorch:             {COLOR_RED}Not installed ({e}){COLOR_RESET}\n")

    # Check 3: Llama.cpp binding
    try:
        import llama_cpp
        sys.stdout.write(f"  llama.cpp binding:   {COLOR_BOLD_GREEN}Available (v{getattr(llama_cpp, '__version__', 'native')}){COLOR_RESET}\n")
    except Exception:
        sys.stdout.write(f"  llama.cpp binding:   {COLOR_YELLOW}Fallback to Air Engine Pager{COLOR_RESET}\n")

    # Check 4: Models folder
    models_dir = os.path.expanduser("~/.lmms/models")
    if os.path.exists(models_dir):
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        sys.stdout.write(f"  Local Models:        {COLOR_BOLD_CYAN}{len(files)} GGUF file(s){COLOR_RESET} at {models_dir}\n")
    else:
        sys.stdout.write(f"  Local Models:        {COLOR_YELLOW}Directory missing (~/.lmms/models){COLOR_RESET}\n")

    sys.stdout.write(f"\n{COLOR_BOLD_GREEN}✔ Diagnostics complete.{COLOR_RESET}\n\n")
    sys.stdout.flush()


def run_engine(args: Optional[List[str]] = None) -> None:
    """Main routing entrypoint for standalone `lmms engine`."""
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] in ["-h", "--help", "help"]:
        print_engine_banner()
        return

    subcmd = args[0].lower()
    sub_args = args[1:]

    if subcmd in ["status", "info"]:
        cmd_engine_status()
    elif subcmd in ["mode", "set-mode"]:
        cmd_engine_mode(sub_args)
    elif subcmd in ["run", "chat"]:
        cmd_engine_run(sub_args)
    elif subcmd in ["unload", "stop", "purge"]:
        cmd_engine_unload(sub_args)
    elif subcmd in ["doctor", "diag", "check"]:
        cmd_engine_doctor()
    elif subcmd in ["bench", "benchmark"]:
        from lmms.engine.benchmark import run_benchmark
        model = sub_args[0] if sub_args else "default"
        run_benchmark(model)
    else:
        sys.stdout.write(f"Unknown engine command: '{subcmd}'. Run 'lmms engine' for options.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_engine(sys.argv[1:])
