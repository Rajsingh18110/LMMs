import os
import psutil  # type: ignore
from typing import Dict, Any, Optional

class AirGuardrails:
    """
    Deterministic Hardware Guardrails for Air Engine.
    Prevents OS lockups, CUDA OOM crashes, kernel panics, and disk exhaustion.
    """
    
    @staticmethod
    def validate_regime_safety(
        model_size_gb: float, 
        regime: int, 
        v_usable_gb: float, 
        r_usable_gb: float,
        model_path: Optional[str] = None
    ) -> bool:
        # Regime 1 or 2: Must fit in usable working memory
        if regime in (1, 2):
            total_usable = v_usable_gb + r_usable_gb
            if model_size_gb > total_usable:
                raise MemoryError(
                    f"[AirGuardrails] Model size ({model_size_gb:.2f} GB) exceeds total usable memory "
                    f"({total_usable:.2f} GB = {v_usable_gb:.2f}GB VRAM + {r_usable_gb:.2f}GB RAM). "
                    f"Must escalate to Regime 3 (Sequential Layer Streaming)."
                )
            return True

        # Regime 3: Model is streamed layer-by-layer from disk
        elif regime == 3:
            # Check host RAM headroom (needs at least 2.5 GB for OS + DMA ring buffer)
            sys_ram = psutil.virtual_memory()
            free_ram_gb = sys_ram.available / (1024**3)
            if free_ram_gb < 2.0:
                raise MemoryError(
                    f"[AirGuardrails] Critical: Free system RAM ({free_ram_gb:.2f} GB) is below 2.0 GB safety threshold. "
                    f"Aborting Regime 3 execution to prevent OS freeze."
                )

            # Check disk space on the model partition (needs at least 5 GB free for temp KV cache & swap)
            check_path = model_path if model_path and os.path.exists(model_path) else "/"
            disk_stat = psutil.disk_usage(os.path.dirname(os.path.abspath(check_path)))
            free_disk_gb = disk_stat.free / (1024**3)
            if free_disk_gb < 5.0:
                raise IOError(
                    f"[AirGuardrails] Critical: Available disk space ({free_disk_gb:.2f} GB) is below 5.0 GB safety threshold."
                )
            return True

        return True

    @staticmethod
    def check_live_vram_headroom(min_headroom_gb: float = 0.40) -> bool:
        """Called before memory-intensive steps to protect against external app memory spikes."""
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                free_b, total_b = torch.cuda.mem_get_info()
                free_gb = free_b / (1024**3)
                if free_gb < min_headroom_gb:
                    print(f"[AirGuardrails] Warning: Low VRAM detected ({free_gb:.2f} GB free < {min_headroom_gb:.2f} GB). Triggering garbage collection.")
                    import gc
                    gc.collect()
                    torch.cuda.empty_cache()
                    free_b, _ = torch.cuda.mem_get_info()
                    return (free_b / (1024**3)) >= min_headroom_gb
        except Exception:
            pass
        return True
