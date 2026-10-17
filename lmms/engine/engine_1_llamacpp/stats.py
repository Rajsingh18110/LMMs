import psutil
try:
    import torch
except ImportError:
    torch = None

class AirStats:
    @staticmethod
    def get_system_stats():
        stats = {
            "vram_total_gb": 0.0,
            "vram_used_gb": 0.0,
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "device": "CPU"
        }
        if torch and torch.cuda.is_available():
            stats["device"] = "CUDA"
            stats["vram_total_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            try:
                # To get global VRAM used, not just pytorch
                import subprocess
                res = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
                    encoding="utf-8"
                )
                stats["vram_used_gb"] = round(float(res.strip()) / 1024, 2)
            except Exception:
                stats["vram_used_gb"] = round(torch.cuda.memory_allocated(0) / (1024**3), 2)
                
        return stats
