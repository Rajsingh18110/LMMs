import sys
import os
import subprocess
import json

def get_installed_components():
    return {
        "Backend": True,
        "Engine": True,
        "GUI": False,
        "CLI": True,
        "Air": False
    }

def print_detect():
    print("System Manager: Component Detection")
    print("-----------------------------------")
    comps = get_installed_components()
    for comp, is_inst in comps.items():
        mark = "✓" if is_inst else "✗"
        print(f"{mark} {comp}")
    print("\nHardware Detection:")
    try:
        import psutil
        print(f"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB")
    except ImportError:
        print("RAM: psutil not installed")
        
    try:
        res = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"GPU: {res.stdout.strip()}")
        else:
            print("GPU: No NVIDIA GPU detected")
    except FileNotFoundError:
        print("GPU: nvidia-smi not found")

def install(component):
    comps = get_installed_components()
    if component.capitalize() in comps and comps[component.capitalize()]:
        print(f"{component.capitalize()} already installed")
        return
        
    print(f"Installing {component}...")
    if component == "engine":
        print("Installing Engine dependencies (llama-cpp-python)...")
        # Assuming Debian/Ubuntu standard setup
        cmd = "CMAKE_ARGS='-DGGML_CUDA=on' pip install llama-cpp-python --force-reinstall --no-cache-dir"
        print(f"Running: {cmd}")
        # subprocess.run(cmd, shell=True) # Skipped for mockup
        print("Installation successful.")
    elif component == "gui":
        print("GUI installation sequence started...")
    elif component == "air":
        print("Air engine installation sequence started...")
    else:
        print(f"Unknown component: {component}")

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print('''
LMMs System Manager (Builder)
Usage: python builder.py [command] [options]

Commands:
  detect         Detect installed components and hardware
  compatibility  Check model compatibility with current hardware
  doctor         Run system diagnostics
  benchmark      Run hardware stress test
  install        Install a component (--engine, --gui, --air, --full)
''')
        sys.exit(0)

    cmd = args[0]
    if cmd == "detect":
        print_detect()
    elif cmd == "compatibility":
        print("Compatibility check not fully implemented natively yet.")
    elif cmd == "doctor":
        subprocess.run(["python3", "main.py", "doctor"])
    elif cmd == "benchmark":
        subprocess.run(["python3", "main.py", "benchmark"])
    elif cmd == "install":
        for flag in ["--engine", "--gui", "--cli", "--air", "--full"]:
            if flag in args:
                if flag == "--full":
                    for c in ["engine", "gui", "air"]: install(c)
                else:
                    install(flag.replace("--", ""))
    else:
        print(f"Unknown builder command: {cmd}")

if __name__ == "__main__":
    main()
