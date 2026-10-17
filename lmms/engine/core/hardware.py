import os
import shutil
import subprocess
from typing import Dict, Any

class HardwareProfiler:
    """
    Implements Multi-Layer Hardware Detection.
    Priority: nvidia-smi / torch.cuda -> ROCm -> CPU-only.
    """
    @staticmethod
    def get_hardware_info() -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "gpu_detected": False,
            "gpu_name": "CPU Only",
            "vram_total_mb": 0.0,
            "vram_free_mb": 0.0,
            "ram_total_mb": 0.0,
            "ram_available_mb": 0.0,
            "detection_method": "none"
        }

        # 1. System RAM detection via psutil
        try:
            import psutil  # type: ignore
            mem = psutil.virtual_memory()
            info["ram_total_mb"] = round(mem.total / (1024 * 1024), 2)
            info["ram_available_mb"] = round(mem.available / (1024 * 1024), 2)
        except Exception:
            pass

        # 2. GPU Detection via PyTorch (if available)
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                info["gpu_detected"] = True
                info["gpu_name"] = torch.cuda.get_device_name(0)
                free_b, total_b = torch.cuda.mem_get_info()
                info["vram_free_mb"] = round(free_b / (1024 * 1024), 2)
                info["vram_total_mb"] = round(total_b / (1024 * 1024), 2)
                info["detection_method"] = "torch.cuda"
                return info
        except Exception:
            pass

        # 3. GPU Detection via nvidia-smi
        if shutil.which("nvidia-smi"):
            try:
                cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"]
                out = subprocess.check_output(cmd, encoding="utf-8").strip().split("\n")[0]
                parts = [p.strip() for p in out.split(",")]
                if len(parts) >= 3:
                    info["gpu_detected"] = True
                    info["gpu_name"] = parts[0]
                    info["vram_total_mb"] = float(parts[1])
                    info["vram_free_mb"] = float(parts[2])
                    info["detection_method"] = "nvidia-smi"
                    return info
            except Exception:
                pass

        return info

    def profile(self) -> Dict[str, Any]:
        return self.get_hardware_info()
