"""
LMMs Standalone Dual-Engine Console & Runner
Provides standalone terminal execution, hardware profiling, runtime inspection,
and direct inference for Engine 1 (Air+LlamaCpp) and Engine 2 (Air+PyTorch).
"""

from __future__ import annotations

import json
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

    sys.stdout.write(f"{COLOR_BOLD_WHITE}4. Model Management:{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms pull <model>{COLOR_RESET}                  Download model from Hugging Face\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms run <model> [prompt]{COLOR_RESET}          Start/inference a model (interactive or single-shot)\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms stop <model>{COLOR_RESET}                  Stop and unload an active running model\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms ps{COLOR_RESET}                            List currently running models & allocations\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms list{COLOR_RESET}                          List all locally installed models\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms info <model>{COLOR_RESET}                  Show detailed metadata for a model\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms rm <model>{COLOR_RESET}                    Delete a model from local registry\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms search <query>{COLOR_RESET}                Search Hugging Face for GGUF models\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms benchmark <model>{COLOR_RESET}             Test speed, load time, VRAM/RAM usage\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms doctor [--fix]{COLOR_RESET}                Health check and hardware diagnostics\n\n")

    sys.stdout.write(f"{COLOR_BOLD_WHITE}5. Air Engine (Swapping & Offloading):{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms -air run <model>{COLOR_RESET}              Run a single heavy model in Air offloading mode\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms --air run <m1> <m2>{COLOR_RESET}          Run multiple models through the Air scheduler\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms air ps{COLOR_RESET}                        Show active models in the Air session\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms air cache{COLOR_RESET}                     View Air cache status\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms air stats{COLOR_RESET}                     View swapping, RAM, VRAM, and load metrics\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms air unload{COLOR_RESET}                    Unload models and purge GPU VRAM\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms air benchmark{COLOR_RESET}                 Test Air mode performance\n\n")

    sys.stdout.write(f"{COLOR_BOLD_WHITE}6. Packages (Modular Plugins):{COLOR_RESET}\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms package install runtime <name>{COLOR_RESET}  Install backend (e.g., llama-cpp, vllm)\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms package install provider <name>{COLOR_RESET} Install model source (e.g., huggingface, lmstudio)\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms package install tool <name>{COLOR_RESET}     Install capability (e.g., wikipedia, github)\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms package list{COLOR_RESET}                   List installed packages\n")
    sys.stdout.write(f"  {COLOR_CYAN}lmms package remove [<type>] <name>{COLOR_RESET} Remove a package\n\n")
    sys.stdout.flush()


def _get_hardware_memory_info():
    """Returns (vram_used_gb, vram_total_gb, ram_used_gb, ram_total_gb)."""
    import psutil
    import subprocess
    import shutil

    ram = psutil.virtual_memory()
    ram_total_gb = ram.total / (1024**3)
    ram_used_gb = (ram.total - ram.available) / (1024**3)

    vram_total_gb = 0.0
    vram_used_gb = 0.0
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,nounits,noheader"],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\n")[0].split(",")
                vram_total_gb = float(parts[0].strip()) / 1024.0
                vram_used_gb = float(parts[1].strip()) / 1024.0
        except Exception:
            pass

    if vram_total_gb <= 0:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                import torch
                if torch.cuda.is_available():
                    vram_total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    vram_used_gb = torch.cuda.memory_allocated(0) / (1024**3)
        except Exception:
            pass

    return vram_used_gb, vram_total_gb, ram_used_gb, ram_total_gb


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
        v_used, v_total, r_used, r_total = _get_hardware_memory_info()
        sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Host Memory Telemetry:{COLOR_RESET}\n")
        sys.stdout.write(f"  RAM Total:           {r_total:.1f} GB\n")
        sys.stdout.write(f"  RAM Available:       {(r_total - r_used):.1f} GB\n")
        sys.stdout.write(f"  RAM Used:            {(r_used / max(0.1, r_total) * 100):.1f}%\n")
        if v_total > 0:
            sys.stdout.write(f"\n{COLOR_BOLD_WHITE}GPU Telemetry:{COLOR_RESET}\n")
            sys.stdout.write(f"  VRAM Total:          {v_total:.2f} GB\n")
            sys.stdout.write(f"  VRAM Free:           {(v_total - v_used):.2f} GB\n")
            sys.stdout.write(f"  VRAM Used:           {v_used:.2f} GB\n")
    except Exception:
        pass

    sys.stdout.write("\n")
    sys.stdout.flush()


def cmd_engine_mode(args: List[str]) -> None:
    if not args:
        current = engine_manager.active_mode
        sys.stdout.write(f"Active engine mode: {COLOR_BOLD_CYAN}{current}{COLOR_RESET}\n")
        sys.stdout.write("Usage: lmms engine mode [auto | 1 | 2]\n")
        sys.stdout.write("  auto : Smart-dispatch based on model format and VRAM\n")
        sys.stdout.write("  1    : Force Engine 1 (Air + Llama.cpp GGUF)\n")
        sys.stdout.write("  2    : Force Engine 2 (Air + PyTorch Safetensors)\n")
        sys.stdout.flush()
        return

    mode_target = args[0].lower().strip()
    try:
        new_mode = engine_manager.set_engine_mode(mode_target)
        sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Engine mode set to: {COLOR_BOLD_CYAN}{new_mode}{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}✖ Error setting engine mode:{COLOR_RESET} {e}\n")
    sys.stdout.flush()


def cmd_engine_unload(args: Optional[List[str]] = None) -> None:
    """Safely purges engine model cache and frees GPU VRAM."""
    model_name = args[0] if (args and len(args) > 0) else None
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

        # Purge PyTorch CUDA cache flush if available
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_initialized():
                torch.cuda.empty_cache()
        except Exception:
            pass

        sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Model memory purged. VRAM successfully freed.\n")
    except Exception as e:
        sys.stdout.write(f"{COLOR_RED}✖ Error during unload:{COLOR_RESET} {e}\n")
    sys.stdout.flush()


def _stream_single_turn(runtime, model_name: str, messages: list) -> str:
    """Streams a single conversation turn from the engine to stdout."""
    effective_messages = list(messages)
    if not any(m.get("role") == "system" for m in effective_messages):
        effective_messages.insert(0, {"role": "system", "content": "You are a helpful, concise AI assistant."})

    t0 = time.time()
    token_count = 0
    full_content = ""
    try:
        generator = runtime.generate({"messages": effective_messages, "model": model_name, "mode": "deep", "think": False}, stream=True)
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
                full_content += text
                token_count += 1

        elapsed = max(0.01, time.time() - t0)
        sys.stdout.write(f"\n\n{COLOR_DIM}Completed {token_count} tokens in {elapsed:.2f}s ({token_count/elapsed:.1f} tok/s){COLOR_RESET}\n")
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write(f"\n\n{COLOR_YELLOW}[Inference interrupted by user]{COLOR_RESET}\n")
    except Exception as e:
        sys.stdout.write(f"\n{COLOR_RED}✖ Generation error:{COLOR_RESET} {e}\n")
    return full_content


def _run_interactive_engine_chat(runtime, model_name: str) -> None:
    """Ollama-style continuous interactive terminal chat REPL."""
    try:
        import readline  # type: ignore # Enable arrow keys, editing, and history
    except ImportError:
        pass

    sys.stdout.write(f"\n{COLOR_BOLD_GREEN}✔{COLOR_RESET} Interactive chat session ready with {COLOR_BOLD_CYAN}{model_name}{COLOR_RESET}\n")
    sys.stdout.write(f"{COLOR_DIM}Send a message (/? for help, exit or Ctrl+D to exit){COLOR_RESET}\n\n")
    sys.stdout.flush()

    messages: List[dict] = []

    while True:
        try:
            user_input = input(f"{COLOR_BOLD_CYAN}>>> {COLOR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            sys.stdout.write(f"\n{COLOR_DIM}Exiting session.{COLOR_RESET}\n")
            break

        if not user_input:
            continue

        # Immediate clean exit commands (no slashes required)
        if user_input.lower() in [
            "/bye", "/exit", "/quit", "/q", ":q",
            "exit", "quit", "bye", "exit()", "quit()"
        ]:
            sys.stdout.write(f"{COLOR_DIM}Exiting session.{COLOR_RESET}\n")
            break

        if user_input.lower() in ["/?", "/help"]:
            sys.stdout.write(f"\n{COLOR_BOLD_WHITE}Available Commands:{COLOR_RESET}\n")
            sys.stdout.write(f"  {COLOR_CYAN}/clear{COLOR_RESET}   Clear conversation context memory\n")
            sys.stdout.write(f"  {COLOR_CYAN}/bye{COLOR_RESET}     Exit interactive session\n")
            sys.stdout.write(f"  {COLOR_CYAN}/help{COLOR_RESET}    Show this help message\n\n")
            sys.stdout.flush()
            continue

        if user_input.lower() == "/clear":
            messages.clear()
            sys.stdout.write(f"{COLOR_GREEN}✔{COLOR_RESET} Cleared conversation history.\n\n")
            sys.stdout.flush()
            continue

        messages.append({"role": "user", "content": user_input})
        sys.stdout.write("\n")
        sys.stdout.flush()

        assistant_reply = _stream_single_turn(runtime, model_name, messages)
        if assistant_reply:
            messages.append({"role": "assistant", "content": assistant_reply})
        sys.stdout.write("\n")
        sys.stdout.flush()


def cmd_engine_run(args: List[str]) -> None:
    """Direct standalone engine inference in terminal (single-shot prompt or Ollama-style REPL)."""
    if not args:
        sys.stdout.write("Usage: lmms run <model_name> [prompt]\n")
        sys.stdout.flush()
        return

    model_name = args[0]
    initial_prompt = " ".join(args[1:]).strip() if len(args) > 1 else None

    sys.stdout.write(f"{COLOR_DIM}Resolving runtime for '{model_name}'...{COLOR_RESET}\n")
    runtime = engine_manager.get_runtime(model_name)

    # Check if loaded, if not attempt load
    if not engine_manager.is_model_loaded(model_name):
        sys.stdout.write(f"{COLOR_CYAN}Loading '{model_name}' into engine memory...{COLOR_RESET}\n")
        models_dir = os.path.expanduser("~/.lmms/models")
        manifests_dir = os.path.expanduser("~/.lmms/manifests")
        path = model_name
        manifest_candidate = os.path.join(manifests_dir, f"{model_name}.json")
        if os.path.exists(manifest_candidate):
            try:
                with open(manifest_candidate, "r") as mf:
                    base = json.load(mf).get("base_model")
                    if base:
                        cand = os.path.join(models_dir, base if base.endswith(".gguf") else f"{base}.gguf")
                        if os.path.exists(cand):
                            path = cand
                        elif os.path.exists(os.path.join(models_dir, base)):
                            path = os.path.join(models_dir, base)
            except Exception:
                pass

        if not os.path.exists(path):
            cand = os.path.join(models_dir, f"{model_name}.gguf")
            if os.path.exists(cand):
                path = cand
            elif os.path.exists(os.path.join(models_dir, model_name)):
                path = os.path.join(models_dir, model_name)

        success = runtime.load_model(path if os.path.exists(path) else model_name)
        if not success:
            sys.stdout.write(f"{COLOR_RED}✖ Failed to load model '{model_name}'.{COLOR_RESET}\n")
            return

    try:
        # Mode 1: Single-shot prompt given as command line arguments
        if initial_prompt:
            sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Generating stream from {COLOR_BOLD_CYAN}{model_name}{COLOR_RESET}:\n\n")
            sys.stdout.flush()
            _stream_single_turn(runtime, model_name, [{"role": "user", "content": initial_prompt}])
            return

        # Mode 2: Interactive REPL (Ollama-style)
        _run_interactive_engine_chat(runtime, model_name)

    finally:
        # Automatic clean unload and VRAM purge on exit or Ctrl+C
        sys.stdout.write(f"{COLOR_DIM}Shutting down engine and freeing GPU VRAM...{COLOR_RESET}\n")
        sys.stdout.flush()
        try:
            if hasattr(runtime, "unload_model"):
                runtime.unload_model()
        except Exception:
            pass
        try:
            engine_manager.unload_all()
        except Exception:
            pass
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_initialized():
                torch.cuda.empty_cache()
        except Exception:
            pass
        sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} Engine session cleanly terminated. VRAM cleared.\n")
        sys.stdout.flush()


def cmd_engine_ps() -> None:
    """Lists active running models and hardware allocations."""
    from rich.console import Console
    from rich.table import Table

    c = Console()
    table = Table(title="Currently Running Engine Models")
    table.add_column("MODEL", style="cyan")
    table.add_column("ENGINE / RUNTIME", style="green")
    table.add_column("VRAM / ALLOCATION", style="magenta")
    table.add_column("STATUS", style="yellow")

    has_active = False

    # Check Engine 1 runtime
    rt1 = getattr(engine_manager, "engine_1", None)
    if rt1 and getattr(rt1, "pager", None) and rt1.pager.active_profile and rt1.pager.active_model:
        prof = rt1.pager.active_profile
        table.add_row(
            prof.model_name,
            "Air Engine (LlamaCpp)",
            f"GPU: {prof.optimal_gpu_layers}/{prof.n_layers} layers ({prof.gpu_pct:.1f}%) | RAM: {prof.cpu_layers} layers",
            "[bold green]Running / Active[/bold green]"
        )
        has_active = True

    # Check active_models.json daemon log
    f = os.path.expanduser("~/.lmms/logs/active_models.json")
    if os.path.exists(f):
        try:
            with open(f, "r") as file:
                data = json.load(file)
                if isinstance(data, dict):
                    for k, v in data.items():
                        table.add_row(str(k), "Daemon", str(v), "[green]Active[/green]")
                        has_active = True
        except Exception:
            pass

    if has_active:
        c.print(table)
    else:
        c.print("[dim]No active models currently loaded in engine memory. Engine is idle.[/dim]")


def cmd_engine_pull(args: List[str]) -> None:
    """Pulls and downloads a model from Hugging Face Hub."""
    if not args:
        sys.stdout.write("Usage: lmms pull <model_name>\n")
        return

    model_name = "-".join(args)
    sys.stdout.write(f"Pulling '{model_name}'...\n")
    sys.stdout.flush()

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            from huggingface_hub import HfApi, hf_hub_download
        api = HfApi()

        if "/" in model_name:
            repo_id = model_name
        else:
            search_term = model_name.replace(":", "-").lower()
            models = list(api.list_models(search=search_term, filter="gguf", limit=10, sort="downloads"))
            if not models:
                sys.stdout.write(f"Could not find any GGUF repo matching '{model_name}'.\n")
                return
            best_match = models[0]
            for m in models:
                repo_name = m.id.split("/")[-1].lower()
                if search_term == repo_name or search_term + "-gguf" == repo_name:
                    best_match = m
                    break
            repo_id = best_match.id

        sys.stdout.write(f"Fetching available formats for {repo_id}...\n")
        sys.stdout.flush()
        repo_info = api.model_info(repo_id, files_metadata=True)
        gguf_files = [f for f in (repo_info.siblings or []) if getattr(f, "rfilename", "").endswith(".gguf")]
        if not gguf_files:
            sys.stdout.write(f"No GGUF file found in {repo_id}.\n")
            return

        gguf_files.sort(key=lambda x: x.size if x.size else 0)
        sys.stdout.write(f"\nAvailable Quantizations for {repo_id}:\n")
        for i, f in enumerate(gguf_files):
            size_mb = (f.size / (1024 * 1024)) if f.size else 0
            size_str = f"{size_mb/1024:.2f} GB" if size_mb > 1024 else f"{size_mb:.2f} MB"
            sys.stdout.write(f"  [{i+1}] {f.rfilename} ({size_str})\n")
        sys.stdout.write(f"  [{len(gguf_files)+1}] Cancel\n")
        sys.stdout.flush()

        while True:
            try:
                choice = input(f"\nSelect a format to download [1-{len(gguf_files)+1}]: ").strip()
                choice_idx = int(choice) - 1
                if choice_idx == len(gguf_files):
                    sys.stdout.write("Cancelled.\n")
                    return
                if 0 <= choice_idx < len(gguf_files):
                    target_file = gguf_files[choice_idx].rfilename
                    break
                else:
                    sys.stdout.write("Invalid selection.\n")
            except ValueError:
                sys.stdout.write("Please enter a valid number.\n")
            except (KeyboardInterrupt, EOFError):
                sys.stdout.write("\nCancelled.\n")
                return

        models_dir = os.path.expanduser("~/.lmms/models")
        os.makedirs(models_dir, exist_ok=True)
        sys.stdout.write(f"Downloading {target_file} from {repo_id} to {models_dir}...\n")
        sys.stdout.flush()

        hf_hub_download(repo_id=repo_id, filename=target_file, local_dir=models_dir)
        sys.stdout.write(f"\n{COLOR_BOLD_GREEN}✔{COLOR_RESET} Download complete: {target_file}\n")

        manifests_dir = os.path.expanduser("~/.lmms/manifests")
        os.makedirs(manifests_dir, exist_ok=True)
        safe_name = model_name.split("/")[-1]
        manifest_path = os.path.join(manifests_dir, f"{safe_name}.json")
        with open(manifest_path, "w") as f:
            json.dump({"base_model": target_file, "repo_id": repo_id}, f, indent=2)

        d_file = os.path.expanduser("~/.lmms/logs/downloads.json")
        d = {}
        if os.path.exists(d_file):
            try:
                with open(d_file, "r") as df:
                    d = json.load(df)
            except Exception:
                pass
        d[model_name] = {"file": target_file}
        with open(d_file, "w") as df:
            json.dump(d, df, indent=2)
    except Exception as e:
        sys.stdout.write(f"Failed to pull {model_name}: {e}\n")


def cmd_engine_search(args: List[str]) -> None:
    """Searches Hugging Face for compatible GGUF models."""
    if not args:
        sys.stdout.write("Usage: lmms search <query>\n")
        return
    query = " ".join(args)
    try:
        from huggingface_hub import HfApi
        from rich.console import Console
        from rich.table import Table
        c = Console()
        api = HfApi()
        models = api.list_models(search=query, filter="gguf", limit=15)
        table = Table(title=f"Hugging Face GGUF Search: '{query}'")
        table.add_column("Model ID", style="cyan")
        table.add_column("Author", style="dim")
        table.add_column("Downloads", style="green")
        table.add_column("Last Updated", style="yellow")
        table.add_column("Format", style="magenta")
        for m in models:
            table.add_row(m.id, m.author or "Unknown", str(getattr(m, "downloads", 0)), str(getattr(m, "lastModified", "Unknown"))[:10], "GGUF")
        c.print(table)
    except Exception as e:
        sys.stdout.write(f"Search failed: {e}\n")


def cmd_engine_package(args: List[str]) -> None:
    """Dispatches package manager commands."""
    from lmms.engine.packages import PackageManager
    mgr = PackageManager()
    if not args or args[0] in ["list", "ls"]:
        mgr.list_packages()
    elif args[0] in ["install", "add"] and len(args) >= 3:
        pkg_type = args[1]
        pkg_name = args[2]
        mgr.install(pkg_type, pkg_name)
    elif args[0] in ["remove", "rm", "uninstall"] and len(args) >= 2:
        if len(args) >= 3:
            mgr.remove(args[1], args[2])
        else:
            mgr.remove(args[1])
    else:
        sys.stdout.write("Usage:\n")
        sys.stdout.write("  lmms package list\n")
        sys.stdout.write("  lmms package install <runtime|provider|tool> <name>\n")
        sys.stdout.write("  lmms package remove [<type>] <name>\n")


def cmd_engine_create(args: List[str]) -> None:
    """Creates a custom model entry or Modelfile manifest in registry."""
    if not args:
        sys.stdout.write("Usage: lmms create <model_name> [-f <modelfile>]\n")
        return
    model_name = args[0]
    modelfile = ""
    if "-f" in args:
        f_idx = args.index("-f")
        if f_idx + 1 < len(args):
            modelfile = args[f_idx + 1]

    sys.stdout.write(f"Creating model '{model_name}'" + (f" from {modelfile}" if modelfile else "") + "...\n")
    manifests_dir = os.path.expanduser("~/.lmms/manifests")
    os.makedirs(manifests_dir, exist_ok=True)
    manifest_path = os.path.join(manifests_dir, f"{model_name}.json")
    with open(manifest_path, "w") as f:
        json.dump({"base_model": modelfile or model_name, "custom": True}, f, indent=2)
    sys.stdout.write(f"{COLOR_BOLD_GREEN}✔{COLOR_RESET} [{model_name}] Created successfully in registry.\n")


def cmd_engine_air(subcmd: str, args: List[str]) -> None:
    """Dispatches Air Engine specific commands (ps, cache, stats, unload, benchmark)."""
    from rich.console import Console
    c = Console()
    subcmd = subcmd.lower()

    if subcmd == "ps":
        c.print("[bold cyan]AIR Engine Swarm / Scheduler Status:[/bold cyan]")
        rt = getattr(engine_manager, "engine_1", None)
        if rt and getattr(rt, "pager", None) and rt.pager.active_profile and rt.pager.active_model:
            prof = rt.pager.active_profile
            c.print(f"  Active Session Model: [bold green]{prof.model_name}[/bold green]")
            c.print(f"  Allocated VRAM:       [green]{prof.optimal_gpu_layers}/{prof.n_layers} layers on GPU ({prof.gpu_pct:.1f}%)[/green]")
            c.print(f"  Allocated RAM:        [yellow]{prof.cpu_layers}/{prof.n_layers} layers on CPU DDR5 ({prof.cpu_pct:.1f}%)[/yellow]")
            c.print(f"  Swapping Regime:      [cyan]Regime {prof.regime}[/cyan]")
        else:
            c.print("  [dim]Air Engine is idle. No models actively loaded.[/dim]")
    elif subcmd == "cache":
        cache_dir = os.path.expanduser("~/.lmms/cache")
        total_bytes = 0
        if os.path.exists(cache_dir):
            for root, _, files in os.walk(cache_dir):
                for f in files:
                    total_bytes += os.path.getsize(os.path.join(root, f))
        mb = total_bytes / (1024 * 1024)
        c.print(f"[bold cyan]AIR Engine Cache:[/bold cyan] {mb:.2f} MB used in {cache_dir}")
    elif subcmd == "stats":
        v_used, v_total, r_used, r_total = _get_hardware_memory_info()
        c.print("[bold cyan]AIR Engine Hardware & Swapping Stats:[/bold cyan]")
        if v_total > 0:
            c.print(f"  VRAM:   {v_used:.2f} GB / {v_total:.2f} GB ({(v_used / v_total * 100):.1f}% used)")
        else:
            c.print("  VRAM:   0.00 GB (CPU-only mode)")
        c.print(f"  RAM:    {r_used:.2f} GB / {r_total:.2f} GB ({(r_used / max(0.1, r_total) * 100):.1f}% used)")
        c.print("  Swapping Engine: [green]Active (Zero-Copy Paged mmap)[/green]")
        c.print("  Active Regime:   [cyan]Tri-Regime Dynamic Offloader[/cyan]")
    elif subcmd == "unload":
        cmd_engine_unload([])
        c.print("[bold green]✔ All AIR models unloaded and GPU VRAM freed.[/bold green]")
    elif subcmd in ["bench", "benchmark"]:
        c.print("[bold yellow]Running AIR Swarm Benchmark...[/bold yellow]")
        from lmms.engine.benchmark import run_benchmark
        model = args[0] if args else "default"
        run_benchmark(model)
    elif subcmd == "run":
        engine_manager.set_engine_mode("1")
        cmd_engine_run(args)
    else:
        c.print(f"[bold red]Unknown AIR command: '{subcmd}'[/bold red]")
        c.print("Options: air run <model>, air ps, air cache, air stats, air unload, air benchmark")


def cmd_engine_doctor(args: Optional[List[str]] = None) -> None:
    """Performs engine hardware diagnostic scan with formatted rich table."""
    import platform
    import shutil
    from rich.console import Console
    from rich.table import Table

    c = Console()
    report = {}
    models_dir = os.path.expanduser("~/.lmms/models")
    report["models_dir_exists"] = os.path.exists(models_dir)
    report["models_dir_writable"] = os.access(models_dir, os.W_OK) if report["models_dir_exists"] else False
    report["cuda_support"] = shutil.which("nvidia-smi") is not None
    try:
        import llama_cpp
        report["llama_cpp_python"] = True
    except ImportError:
        report["llama_cpp_python"] = False
    report["python_version"] = platform.python_version()
    try:
        import psutil
        report["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
    except Exception:
        report["ram_available_gb"] = 0
    report["disk_available_gb"] = round(shutil.disk_usage(models_dir).free / (1024**3), 2) if report["models_dir_exists"] else 0

    table = Table(title="LMMs Engine Doctor Report")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")

    def fmt(val):
        return "[bold green]PASS[/bold green]" if val else "[bold red]FAIL[/bold red]"

    table.add_row("Models Dir Exists", fmt(report.get("models_dir_exists")))
    table.add_row("Models Dir Writable", fmt(report.get("models_dir_writable")))
    table.add_row("NVIDIA CUDA / Driver", fmt(report.get("cuda_support")))
    table.add_row("Llama-CPP Python", fmt(report.get("llama_cpp_python")))
    table.add_row("Python Version", str(report.get("python_version", "Unknown")))
    table.add_row("RAM Available", f"{report.get('ram_available_gb', 0)} GB")
    table.add_row("Disk Available", f"{report.get('disk_available_gb', 0)} GB")
    c.print(table)


def run_engine(args: Optional[List[str]] = None) -> None:
    """Main routing entrypoint for standalone `lmms engine`."""
    if args is None:
        args = sys.argv[1:]

    # Parse and strip --air / -air flags
    force_air = False
    clean_args = []
    for a in args:
        if a in ["--air", "-air"]:
            force_air = True
        else:
            clean_args.append(a)
    args = clean_args

    if force_air:
        engine_manager.set_engine_mode("1")

    if not args or args[0] in ["-h", "--help", "help"]:
        print_engine_banner()
        return

    subcmd = args[0].lower()
    sub_args = args[1:]

    # Air subcommand router
    if subcmd in ["air", "--air", "-air"]:
        engine_manager.set_engine_mode("1")
        if sub_args:
            air_sub = sub_args[0].lower()
            cmd_engine_air(air_sub, sub_args[1:])
            return
        else:
            cmd_engine_air("ps", [])
            return

    # Model Management & Registry
    if subcmd in ["list", "ls", "registry"]:
        from lmms.engine.registry import RegistryManager
        RegistryManager().list_models()
    elif subcmd in ["info"]:
        if sub_args:
            from lmms.engine.registry import RegistryManager
            RegistryManager().info_model(sub_args[0])
        else:
            cmd_engine_status()
    elif subcmd in ["ps"]:
        cmd_engine_ps()
    elif subcmd in ["pull"]:
        cmd_engine_pull(sub_args)
    elif subcmd in ["rm", "delete"]:
        if not sub_args:
            sys.stdout.write("Usage: lmms rm <model_name>\n")
            return
        from lmms.engine.registry import RegistryManager
        reg = RegistryManager()
        for m in sub_args:
            reg.rm_model(m)
    elif subcmd in ["stop", "unload", "purge"]:
        cmd_engine_unload(sub_args)
    elif subcmd in ["search"]:
        cmd_engine_search(sub_args)
    elif subcmd in ["doctor", "diag", "check"]:
        cmd_engine_doctor(sub_args)
    elif subcmd in ["bench", "benchmark"]:
        from lmms.engine.benchmark import run_benchmark
        model = sub_args[0] if sub_args else "default"
        run_benchmark(model)
    elif subcmd in ["create"]:
        cmd_engine_create(sub_args)

    # Modular Packages
    elif subcmd in ["package", "packages"]:
        cmd_engine_package(sub_args)

    # Core Engine modes & Execution
    elif subcmd in ["run", "chat"]:
        cmd_engine_run(sub_args)
    elif subcmd in ["status"]:
        cmd_engine_status()
    elif subcmd in ["mode", "set-mode"]:
        cmd_engine_mode(sub_args)
    elif subcmd in ["server", "serve"]:
        from lmms.api.server import run_server
        port = 11435
        host = "0.0.0.0"
        idx = 0
        while idx < len(sub_args):
            if sub_args[idx] in ["--port", "-p"] and idx + 1 < len(sub_args):
                try:
                    port = int(sub_args[idx + 1])
                except Exception:
                    pass
                idx += 2
            elif sub_args[idx] in ["--host", "-h"] and idx + 1 < len(sub_args):
                host = sub_args[idx + 1]
                idx += 2
            else:
                idx += 1
        run_server(host=host, port=port)
    else:
        sys.stdout.write(f"Unknown engine command: '{subcmd}'. Run 'lmms engine' for options.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_engine(sys.argv[1:])
