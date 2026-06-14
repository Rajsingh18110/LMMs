import os
import platform
import psutil
import subprocess

def detect_os():
    return {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }

def detect_cpu():
    return {
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
    }

def detect_ram():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2)
    }

def detect_gpu():
    try:
        # Check nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        if lines and lines[0]:
            parts = lines[0].split(",")
            name = parts[0].strip()
            vram_str = parts[1].strip()
            vram_mb = int(vram_str.replace(" MiB", ""))
            return {
                "detected": True,
                "name": name,
                "vram_gb": round(vram_mb / 1024, 2),
                "type": "nvidia"
            }
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
        
    return {
        "detected": False,
        "name": "None",
        "vram_gb": 0.0,
        "type": "none"
    }

def detect_cuda():
    try:
        result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, check=True)
        for line in result.stdout.split("\n"):
            if "release" in line:
                version = line.split("release")[1].strip().split(",")[0]
                return {"available": True, "version": version}
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
        
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=True)
        if "CUDA Version: " in result.stdout:
            version = result.stdout.split("CUDA Version: ")[1].split(" ")[0]
            return {"available": True, "version": version}
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return {"available": False, "version": None}

def detect_python():
    return {
        "version": platform.python_version()
    }

def detect_all():
    return {
        "os": detect_os(),
        "cpu": detect_cpu(),
        "ram": detect_ram(),
        "gpu": detect_gpu(),
        "cuda": detect_cuda(),
        "python": detect_python()
    }
