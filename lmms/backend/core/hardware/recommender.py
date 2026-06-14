import psutil
import subprocess
from typing import Dict, Any, List

class HardwareProfiler:
    """
    Detects system hardware capabilities including CPU, RAM, and GPU.
    """
    def __init__(self):
        pass

    def get_system_specs(self) -> Dict[str, Any]:
        specs = {
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "gpu_info": self._detect_gpu()
        }
        return specs

    def _detect_gpu(self) -> Dict[str, Any]:
        """Attempt to detect GPU via nvidia-smi."""
        gpu_info = {"available": False, "name": "Unknown", "vram_total_gb": 0.0}
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 2:
                    gpu_info["available"] = True
                    gpu_info["name"] = parts[0].strip()
                    # Memory is returned in MiB
                    gpu_info["vram_total_gb"] = round(float(parts[1].strip()) / 1024, 2)
        except Exception:
            pass
        return gpu_info

class ModelRecommender:
    """
    Recommends optimal local LLMs based on Hardware profiles.
    """
    def __init__(self, profiler: HardwareProfiler = None):
        self.profiler = profiler or HardwareProfiler()

    def get_recommendations(self) -> List[Dict[str, str]]:
        specs = self.profiler.get_system_specs()
        ram = specs["ram_total_gb"]
        vram = specs["gpu_info"]["vram_total_gb"]
        
        # Total effective memory for loading models (we prioritize VRAM if available, otherwise RAM)
        effective_mem = vram if specs["gpu_info"]["available"] else ram
        
        recs = []
        
        if effective_mem >= 64:
            recs.append({"model": "llama3:70b-q4_K_M", "reason": "High-end system detected. Can run 70B models easily."})
            recs.append({"model": "mixtral:8x7b", "reason": "Great for complex reasoning on high memory systems."})
        elif effective_mem >= 32:
            recs.append({"model": "llama3:70b-q2_K", "reason": "32GB memory can squeeze 70B models with heavy quantization."})
            recs.append({"model": "qwen2.5:14b", "reason": "Excellent fast coding model that fits perfectly in 32GB."})
        elif effective_mem >= 16:
            recs.append({"model": "qwen2.5:14b-q4_K_M", "reason": "16GB sweet spot for 14B models."})
            recs.append({"model": "llama3:8b", "reason": "Blazing fast on 16GB systems."})
        elif effective_mem >= 8:
            recs.append({"model": "llama3:8b-q4_K_M", "reason": "Best balance of speed and intelligence for 8GB limits."})
            recs.append({"model": "phi3:mini", "reason": "Very fast, small footprint."})
        else:
            recs.append({"model": "phi3:mini-q4", "reason": "Low memory system, sticking to \u003c4B models."})
            recs.append({"model": "qwen2.5:0.5b", "reason": "Ultra lightweight model for basic tasks."})
            
        return recs
