import os
import struct
import psutil
from dataclasses import dataclass
from typing import Optional, Dict, Any
try:
    from lmms.backend.logic.manager import backend_manager
except ImportError:
    backend_manager = None

@dataclass
class ModelProfile:
    model_name: str
    file_path: str
    size_gb: float
    total_layers: int
    optimal_gpu_layers: int
    cpu_layers: int
    gpu_pct: float
    cpu_pct: float
    architecture: str
    context_length: int
    recommended_threads: int

    @property
    def total_layers_est(self) -> int:
        return self.total_layers

def parse_gguf_metadata(filepath: str) -> Dict[str, Any]:
    """Pure-Python zero-dependency GGUF header parser for exact metadata extraction."""
    metadata = {}
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            if magic != b'GGUF':
                return metadata
            version, tensor_count, kv_count = struct.unpack('<IQQ', f.read(20))
            metadata['version'] = version
            metadata['tensor_count'] = tensor_count
            
            def read_str():
                length = struct.unpack('<Q', f.read(8))[0]
                return f.read(length).decode('utf-8', errors='ignore')

            def read_val(val_type):
                if val_type == 0: return struct.unpack('<B', f.read(1))[0]
                elif val_type == 1: return struct.unpack('<b', f.read(1))[0]
                elif val_type == 2: return struct.unpack('<H', f.read(2))[0]
                elif val_type == 3: return struct.unpack('<h', f.read(2))[0]
                elif val_type == 4: return struct.unpack('<I', f.read(4))[0]
                elif val_type == 5: return struct.unpack('<i', f.read(4))[0]
                elif val_type == 6: return struct.unpack('<f', f.read(4))[0]
                elif val_type == 7: return struct.unpack('<?', f.read(1))[0]
                elif val_type == 8: return read_str()
                elif val_type == 9:
                    arr_type, arr_len = struct.unpack('<IQ', f.read(12))
                    return [read_val(arr_type) for _ in range(arr_len)]
                elif val_type == 10: return struct.unpack('<Q', f.read(8))[0]
                elif val_type == 11: return struct.unpack('<q', f.read(8))[0]
                elif val_type == 12: return struct.unpack('<d', f.read(8))[0]
                return None

            for _ in range(min(kv_count, 150)):
                try:
                    key = read_str()
                    val_type = struct.unpack('<I', f.read(4))[0]
                    val = read_val(val_type)
                    metadata[key] = val
                except Exception:
                    break
    except Exception as e:
        print(f"[AirLoader] Warning: Failed to parse GGUF binary header: {e}")
    return metadata

class AirLoader:
    def __init__(self, models_dir: str = "~/.lmms/models"):
        self.models_dir = os.path.expanduser(models_dir)

    def analyze_model(self, model_name: str) -> Optional[ModelProfile]:
        path = os.path.join(self.models_dir, f"{model_name}.gguf")
        if not os.path.exists(path):
            # Check direct path
            if os.path.exists(model_name):
                path = model_name
            else:
                return None

        size_gb = os.path.getsize(path) / (1024**3)
        print(f"\n[AirLoader] Analyzing model: {model_name} ({size_gb:.2f} GB)")

        # 1. Parse exact metadata from GGUF binary header
        meta = parse_gguf_metadata(path)
        arch = meta.get("general.architecture", "llama")
        
        # Extract block_count (total transformer layers)
        exact_layers = None
        for k, v in meta.items():
            if k.endswith(".block_count") and isinstance(v, int):
                exact_layers = v
                break

        # Fallback layer estimation if header was incomplete
        if exact_layers and exact_layers > 0:
            total_layers = exact_layers
            print(f"[AirLoader] Exact GGUF layers detected from header: {total_layers} layers (Arch: {arch})")
        else:
            # Architecture size-based estimation table for all known models (0.5B to 70B)
            if size_gb < 1.0:
                total_layers = 24  # 0.5B
            elif size_gb < 2.5:
                total_layers = 28  # 1.5B
            elif size_gb < 5.5:
                total_layers = 32  # 3B - 7B/8B
            elif size_gb < 12.0:
                total_layers = 48  # 14B Q4/Q5 (Qwen2.5-14B is 48 layers)
            elif size_gb < 24.0:
                total_layers = 64  # 32B
            else:
                total_layers = 80  # 70B
            print(f"[AirLoader] Estimated layers from architecture scale: {total_layers} layers")

        context_len = 4096
        for k, v in meta.items():
            if k.endswith(".context_length") and isinstance(v, int):
                context_len = min(v, 32768)
                break

        # 2. Hardware Profiling (GPU VRAM + System RAM + CPU Cores)
        stats = backend_manager.cache.get_stats() if backend_manager and hasattr(backend_manager, "cache") else {}
        vram_total_gb = stats.get("total_gb", 0.0)
        vram_available_gb = stats.get("available_gb", 0.0)
        
        # If stats doesn't have live PyTorch CUDA, probe torch directly
        if vram_total_gb <= 0:
            try:
                import torch
                if torch.cuda.is_available():
                    vram_total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    vram_available_gb = vram_total_gb - (torch.cuda.memory_allocated(0) / (1024**3))
            except Exception:
                pass

        sys_ram = psutil.virtual_memory()
        ram_available_gb = sys_ram.available / (1024**3)
        p_cores = psutil.cpu_count(logical=False) or 4  # P-core locking for Intel 13th Gen

        # 3. Dynamic Hybrid Memory Budgeting
        # Compute exact layer weight size
        layer_size_gb = size_gb / total_layers
        
        # Overhead: KV cache (Quantized Q8_0) + OS/Display VRAM buffer
        # With Q8_0 KV cache, overhead is ~0.45GB at 4K context, ~0.8GB at 8K context
        kv_overhead_gb = min(0.8, 0.45 * (min(context_len, 4096) / 4096.0))
        os_gpu_reserve_gb = 0.7  # Display buffer for desktop

        effective_vram_for_layers = max(0.0, vram_available_gb - os_gpu_reserve_gb - kv_overhead_gb)

        if vram_available_gb > 0 and effective_vram_for_layers >= size_gb:
            # Full GPU offload (100% in VRAM)
            optimal_gpu_layers = -1
            cpu_layers = 0
            gpu_pct = 100.0
            cpu_pct = 0.0
        elif vram_available_gb > 0:
            # Hybrid Offloading (Split dynamically across GPU VRAM and DDR5 CPU)
            allocated_gpu_layers = int(effective_vram_for_layers / layer_size_gb)
            allocated_gpu_layers = max(0, min(total_layers, allocated_gpu_layers))
            optimal_gpu_layers = allocated_gpu_layers
            cpu_layers = total_layers - allocated_gpu_layers
            gpu_pct = (allocated_gpu_layers / total_layers) * 100.0
            cpu_pct = 100.0 - gpu_pct
        else:
            # Pure CPU Fallback
            optimal_gpu_layers = 0
            cpu_layers = total_layers
            gpu_pct = 0.0
            cpu_pct = 100.0

        print(f"[AirPlanner] ================= HYBRID SCHEDULE =================")
        print(f"[AirPlanner] Model: {meta.get('general.name', model_name)} | Size: {size_gb:.2f} GB | Layers: {total_layers}")
        print(f"[AirPlanner] GPU VRAM: {vram_total_gb:.1f}GB total ({vram_available_gb:.1f}GB free)")
        print(f"[AirPlanner] System RAM: {ram_available_gb:.1f}GB available DDR5 | P-Cores: {p_cores}")
        print(f"[AirPlanner] Layer Assignment: GPU {optimal_gpu_layers if optimal_gpu_layers != -1 else total_layers} layers ({gpu_pct:.1f}%) | CPU {cpu_layers} layers ({cpu_pct:.1f}%)")
        print(f"[AirPlanner] KV Cache: Quantized Q8_0 FlashAttention (Est. VRAM footprint: ~{kv_overhead_gb:.2f}GB)")
        print(f"[AirPlanner] ===================================================")

        return ModelProfile(
            model_name=model_name,
            file_path=path,
            size_gb=size_gb,
            total_layers=total_layers,
            optimal_gpu_layers=optimal_gpu_layers,
            cpu_layers=cpu_layers,
            gpu_pct=gpu_pct,
            cpu_pct=cpu_pct,
            architecture=arch,
            context_length=context_len,
            recommended_threads=p_cores
        )

