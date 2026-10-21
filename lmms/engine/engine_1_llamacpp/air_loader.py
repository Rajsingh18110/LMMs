import os
import struct
import psutil  # type: ignore
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
    regime: int  # 1 = Pure GPU, 2 = Dynamic Hybrid, 3 = Sequential Layer Streaming
    w_embed_gb: float = 0.0
    w_layer_gb: float = 0.0
    kv_total_gb: float = 0.0
    compute_scratch_gb: float = 0.35
    v_layer_budget_gb: float = 0.0
    expected_decode_tps: float = 0.0
    expected_prefill_tps: float = 0.0

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

            fixed_sizes = {0: 1, 1: 1, 7: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 10: 8, 11: 8, 12: 8}

            def read_val(val_type):
                if val_type in fixed_sizes:
                    fmt = {0:'<B', 1:'<b', 7:'<?', 2:'<H', 3:'<h', 4:'<I', 5:'<i', 6:'<f', 10:'<Q', 11:'<q', 12:'<d'}[val_type]
                    return struct.unpack(fmt, f.read(fixed_sizes[val_type]))[0]
                elif val_type == 8:
                    return read_str()
                elif val_type == 9:
                    arr_type, arr_len = struct.unpack('<IQ', f.read(12))
                    if arr_len > 100:
                        # Fast skip large arrays (like vocab token list)
                        if arr_type in fixed_sizes:
                            f.seek(arr_len * fixed_sizes[arr_type], os.SEEK_CUR)
                        elif arr_type == 8:
                            for _ in range(arr_len):
                                s_len = struct.unpack('<Q', f.read(8))[0]
                                f.seek(s_len, os.SEEK_CUR)
                        return f"[Array of {arr_len} items]"
                    else:
                        return [read_val(arr_type) for _ in range(arr_len)]
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

    def resolve_path(self, model_name: str) -> Optional[str]:
        """Resolves model tag, alias, manifest or filename to canonical absolute path."""
        if os.path.exists(model_name):
            return os.path.abspath(model_name)

        path = os.path.join(self.models_dir, f"{model_name}.gguf")
        if os.path.exists(path):
            return os.path.abspath(path)

        path_raw = os.path.join(self.models_dir, model_name)
        if os.path.exists(path_raw):
            return os.path.abspath(path_raw)

        # Check manifests
        manifest_candidate = os.path.expanduser(f"~/.lmms/manifests/{model_name}.json")
        if os.path.exists(manifest_candidate):
            try:
                import json
                with open(manifest_candidate, "r") as mf:
                    base = json.load(mf).get("base_model")
                    if base:
                        cand = os.path.join(self.models_dir, base if base.endswith(".gguf") else f"{base}.gguf")
                        if os.path.exists(cand):
                            return os.path.abspath(cand)
                        cand_raw = os.path.join(self.models_dir, base)
                        if os.path.exists(cand_raw):
                            return os.path.abspath(cand_raw)
            except Exception:
                pass

        return None

    def analyze_model(self, model_name: str, target_context: int = 4096, verbose: bool = False) -> Optional[ModelProfile]:
        return self._analyze(model_name, target_context, verbose=verbose)

    def build_profile(self, model_name: str, target_context: int = 4096, verbose: bool = False) -> Optional[ModelProfile]:
        return self.analyze_model(model_name, target_context, verbose=verbose)

    def _analyze(self, model_name: str, target_context: int = 4096, verbose: bool = False) -> Optional[ModelProfile]:
        path = self.resolve_path(model_name)
        if not path:
            return None

        size_gb = os.path.getsize(path) / (1024**3)
        clean_model_name = os.path.splitext(os.path.basename(path))[0]
        show_full_schedule = verbose or os.environ.get("LMMS_AIR_DEBUG") == "1"

        if show_full_schedule:
            print(f"\n[AirLoader] Analyzing model: {model_name} ({size_gb:.2f} GB)")
        else:
            print(f"[AirLoader] Model: {clean_model_name} ({size_gb:.2f} GB)")

        # 1. Parse exact metadata from GGUF binary header
        meta = parse_gguf_metadata(path)
        arch = meta.get("general.architecture", "llama")
        
        # Extract architecture parameters
        total_layers = None
        d_model = None
        n_heads_kv = None
        d_head = 128
        context_len = target_context

        for k, v in meta.items():
            if k.endswith(".block_count") and isinstance(v, int):
                total_layers = v
            elif k.endswith(".embedding_length") and isinstance(v, int):
                d_model = v
            elif k.endswith(".attention.head_count_kv") and isinstance(v, int):
                n_heads_kv = v
            elif k.endswith(".attention.key_length") and isinstance(v, int):
                d_head = v
            elif k.endswith(".context_length") and isinstance(v, int):
                context_len = min(v, target_context)

        # Fallback estimation if binary metadata was stripped
        if not total_layers or total_layers <= 0:
            if size_gb < 1.0:
                total_layers = 24
            elif size_gb < 2.5:
                total_layers = 28
            elif size_gb < 5.5:
                total_layers = 32
            elif size_gb < 12.0:
                total_layers = 40  # Qwen3-14B has 40 layers
            elif size_gb < 24.0:
                total_layers = 64
            else:
                total_layers = 80  # 70B
        if show_full_schedule:
            if not total_layers or total_layers <= 0:
                print(f"[AirLoader] Estimated layers from architecture scale: {total_layers} layers")
            else:
                print(f"[AirLoader] Exact GGUF layers detected from header: {total_layers} layers (Arch: {arch})")

        d_model = d_model or 4096
        n_heads_kv = n_heads_kv or 8

        # 2. Hardware Profiling (GPU VRAM + System RAM + CPU P-Cores)
        stats = backend_manager.cache.get_stats() if backend_manager and hasattr(backend_manager, "cache") else {}
        is_cuda = str(stats.get("device", "")).lower() == "cuda"
        vram_total_gb = stats.get("total_gb", 0.0) if is_cuda else 0.0
        vram_available_gb = stats.get("available_gb", 0.0) if is_cuda else 0.0
        
        # Check nvidia-smi first (clean, fast, directly from driver without PyTorch CUDA driver mismatch warnings)
        if vram_total_gb <= 0:
            try:
                import subprocess
                smi_out = subprocess.check_output(
                    ['nvidia-smi', '--query-gpu=memory.total,memory.free', '--format=csv,nounits,noheader'],
                    text=True, timeout=2.0
                ).strip()
                if smi_out:
                    parts = smi_out.splitlines()[0].split(',')
                    vram_total_gb = float(parts[0].strip()) / 1024.0
                    vram_available_gb = float(parts[1].strip()) / 1024.0
            except Exception:
                pass

        # Fallback to torch only if nvidia-smi not available
        if vram_total_gb <= 0:
            try:
                import torch  # type: ignore
                if torch.cuda.is_available():
                    vram_total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    vram_available_gb = vram_total_gb - (torch.cuda.memory_allocated(0) / (1024**3))
            except Exception:
                pass

        sys_ram = psutil.virtual_memory()
        ram_total_gb = sys_ram.total / (1024**3)
        ram_available_gb = sys_ram.available / (1024**3)

        # Detect physical Performance Cores (P-cores) on hybrid CPUs (Intel 12th-14th Gen)
        # Only P-cores have hyperthreading (thread siblings). Restricting threads to P-cores
        # avoids thread barrier stalls on slower E-cores.
        p_cores = 4
        try:
            import glob
            p_core_set = set()
            for sib_path in glob.glob('/sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list'):
                try:
                    with open(sib_path, 'r') as sf:
                        sibs = sf.read().strip()
                    if ',' in sibs or '-' in sibs:
                        cid_path = sib_path.replace('thread_siblings_list', 'core_id')
                        with open(cid_path, 'r') as cf:
                            p_core_set.add(cf.read().strip())
                except Exception:
                    pass
            if p_core_set:
                p_cores = len(p_core_set)
            else:
                p_cores = min(psutil.cpu_count(logical=False) or 4, 6)
        except Exception:
            p_cores = min(psutil.cpu_count(logical=False) or 4, 6)

        # 3. Dynamic Safety Reserves Formulation (Proportional to any user's hardware)
        v_reserve_gb = min(1.0, max(0.25, 0.04 * vram_total_gb)) if vram_total_gb > 0 else 0.0
        r_reserve_gb = min(4.0, max(1.2, 0.08 * ram_total_gb))
        
        v_usable_gb = max(0.0, vram_available_gb - v_reserve_gb)
        r_usable_gb = max(0.0, ram_available_gb - r_reserve_gb)

        # 4. Weight & Buffer Decomposition
        if size_gb < 10.0:
            w_embed_gb = 0.145 * size_gb
        else:
            w_embed_gb = 0.015 * size_gb  # MoE architecture has small embed/head relative to expert layers
            
        w_layers_total_gb = max(0.0, size_gb - w_embed_gb)
        w_layer_gb = w_layers_total_gb / total_layers

        # KV Cache: Q8_0 requires 1.0625 bytes per element
        # M_KV(C) = 2 * L * C * n_kv_heads * d_head * 1.0625 bytes
        kv_elem_bytes = 1.0625
        kv_total_bytes = 2 * total_layers * context_len * n_heads_kv * d_head * kv_elem_bytes
        kv_total_gb = kv_total_bytes / (1024**3)
        kv_layer_gb = kv_total_gb / total_layers

        # Compute & Context Workspace: CUDA runtime context + scratch graph + buffers
        compute_scratch_gb = min(1.0, max(0.25, 0.03 * size_gb))

        # Total working memory if 100% on GPU
        m_working_gpu = size_gb + kv_total_gb + compute_scratch_gb
        m_working_total = size_gb + kv_total_gb + compute_scratch_gb

        # 5. Tri-Regime Selection Architecture
        # Total combined memory available for inference (Usable VRAM + Usable RAM)
        total_sys_capacity_gb = v_usable_gb + r_usable_gb

        # Condition 1: Pure GPU Offload (Regime 1)
        # Model + KV Cache + Scratch buffer comfortably fits in GPU VRAM
        fits_in_gpu = vram_available_gb > 0 and (
            m_working_gpu <= v_usable_gb or 
            m_working_gpu <= vram_available_gb * 0.92 or
            (size_gb + compute_scratch_gb <= v_usable_gb and kv_total_gb <= v_usable_gb * 0.25)
        )

        if fits_in_gpu:
            # REGIME 1: PURE GPU OFFLOAD
            regime = 1
            optimal_gpu_layers = -1
            cpu_layers = 0
            gpu_pct = 100.0
            cpu_pct = 0.0
            v_layer_budget_gb = v_usable_gb - w_embed_gb - compute_scratch_gb
            expected_decode_tps = min(120.0, 140.0 / max(size_gb, 0.5))
            expected_prefill_tps = expected_decode_tps * 4.0

        elif total_sys_capacity_gb >= m_working_total:
            # REGIME 2: DYNAMIC HYBRID PARTITIONING (GPU VRAM + DDR5 System RAM with mmap)
            # Fits in combined memory. Dynamically offload as many layers as fit in available VRAM,
            # and place the remainder in CPU RAM. No hardcoded caps for any GPU/RAM size.
            regime = 2
            v_layer_budget_gb = max(0.0, v_usable_gb - w_embed_gb - compute_scratch_gb)
            s_layer_gpu = w_layer_gb + kv_layer_gb
            
            allocated_gpu_layers = int(v_layer_budget_gb / s_layer_gpu) if (s_layer_gpu > 0 and vram_available_gb > 0) else 0
            allocated_gpu_layers = max(0, min(total_layers, allocated_gpu_layers))
            
            optimal_gpu_layers = allocated_gpu_layers
            cpu_layers = total_layers - allocated_gpu_layers
            gpu_pct = (allocated_gpu_layers / total_layers) * 100.0 if total_layers > 0 else 0.0
            cpu_pct = 100.0 - gpu_pct
            
            # Hybrid throughput model: bounded by slowest layer (CPU DDR5 throughput)
            # GPU layers run at ~120 GB/s, CPU layers run at ~35 GB/s DDR5
            t_gpu_part = (gpu_pct / 100.0) * (size_gb / 120.0)
            t_cpu_part = (cpu_pct / 100.0) * (size_gb / 35.0)
            expected_decode_tps = 1.0 / max(t_gpu_part + t_cpu_part, 0.01)
            expected_prefill_tps = expected_decode_tps * 3.0

        else:
            # REGIME 3: SEQUENTIAL LAYER STREAMING (AirEngine)
            # Model exceeds total memory. Stream 1 layer at a time from NVMe SSD.
            regime = 3
            optimal_gpu_layers = 1  # 1 layer active in double buffer at a time
            cpu_layers = 0
            gpu_pct = (1.0 / total_layers) * 100.0
            cpu_pct = 0.0
            v_layer_budget_gb = 2.0 * w_layer_gb + kv_total_gb + compute_scratch_gb
            
            # Decode is strictly disk-bandwidth bound: Throughput ~ BW_NVMe / Size_GB
            nvme_bw_gb_s = 5.0  # PCIe 4.0 NVMe typical read speed
            expected_decode_tps = nvme_bw_gb_s / max(size_gb, 1.0)
            # Prefill streams weights once for all tokens in prompt batch
            expected_prefill_tps = 512.0 / ((size_gb / nvme_bw_gb_s) + 1.5)

        regime_names = {
            1: "Regime 1 (Pure GPU Offload)",
            2: "Regime 2 (Dynamic Hybrid Partitioning)",
            3: "Regime 3 (Sequential Layer Streaming)"
        }
        gpu_l = optimal_gpu_layers if optimal_gpu_layers != -1 else total_layers

        if show_full_schedule:
            print(f"\n[AirPlanner] ================= MATHEMATICAL AIR SCHEDULE =================")
            print(f"[AirPlanner] Model: {meta.get('general.name', model_name)} | Size: {size_gb:.2f} GB | Layers: {total_layers}")
            print(f"[AirPlanner] Architecture: {arch} | Hidden: {d_model} | KV-Heads: {n_heads_kv} | Ctx: {context_len}")
            print(f"[AirPlanner] GPU VRAM: {vram_total_gb:.1f}GB total ({vram_available_gb:.1f}GB free, Reserve: {v_reserve_gb:.2f}GB, Usable: {v_usable_gb:.2f}GB)")
            print(f"[AirPlanner] System RAM: {ram_total_gb:.1f}GB total ({ram_available_gb:.1f}GB free, Reserve: {r_reserve_gb:.2f}GB, Usable: {r_usable_gb:.2f}GB)")
            print(f"[AirPlanner] Weight Breakdown: Embeddings/Head: {w_embed_gb:.2f}GB | Layer: {w_layer_gb*1000:.1f}MB | KV Total: {kv_total_gb*1000:.1f}MB")
            print(f"[AirPlanner] Scratch Buffer: {compute_scratch_gb*1000:.1f}MB | VRAM Layer Budget: {v_layer_budget_gb:.2f}GB")
            print(f"[AirPlanner] Selected Regime: {regime_names[regime]}")
            print(f"[AirPlanner] Layer Assignment: GPU {gpu_l} layers ({gpu_pct:.1f}%) | CPU {cpu_layers} layers ({cpu_pct:.1f}%)")
            print(f"[AirPlanner] Performance Estimate: Decode: ~{expected_decode_tps:.2f} tok/s | Prefill: ~{expected_prefill_tps:.1f} tok/s")
            print(f"[AirPlanner] ==================================================================\n")
        else:
            print(f"[AirPlanner] {regime_names[regime]}: {gpu_l} GPU layers ({gpu_pct:.1f}%) | {cpu_layers} CPU DDR5 layers ({cpu_pct:.1f}%) [~{expected_decode_tps:.1f} tok/s]")

        clean_model_name = os.path.splitext(os.path.basename(model_name))[0]
        return ModelProfile(
            model_name=clean_model_name,
            file_path=path,
            size_gb=size_gb,
            total_layers=total_layers,
            optimal_gpu_layers=optimal_gpu_layers,
            cpu_layers=cpu_layers,
            gpu_pct=gpu_pct,
            cpu_pct=cpu_pct,
            architecture=arch,
            context_length=context_len,
            recommended_threads=p_cores,
            regime=regime,
            w_embed_gb=w_embed_gb,
            w_layer_gb=w_layer_gb,
            kv_total_gb=kv_total_gb,
            compute_scratch_gb=compute_scratch_gb,
            v_layer_budget_gb=v_layer_budget_gb,
            expected_decode_tps=expected_decode_tps,
            expected_prefill_tps=expected_prefill_tps
        )
