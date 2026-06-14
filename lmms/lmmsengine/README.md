<div align="center">
  <h1>LMMs Engine</h1>
  <p><strong>Local Machine Model Studio - A Distributed LLM Engine by MarkanM</strong></p>
</div>

LMMs Engine (Local Machine Model Studio) is a highly optimized, cross-platform backend orchestrator for running Large Language Models and Vision-Language Models locally. Built on top of `llama_cpp`, it features an advanced CLI, an interactive Chat Repl, distributed swarm execution (Air Engine), and automated hardware profiling.

---

## ⚡ Features
- **Cross-Platform**: Runs on Linux, Windows, and macOS.
- **Hardware Auto-Detection**: Automatically tunes CUDA layers and context size based on your specific GPU/CPU and RAM.
- **Interactive Chat REPL**: Beautiful terminal interface powered by `rich` with multi-line input and streaming output.
- **Modelfile Support**: Create and customize model personalities using Dockerfile-like syntax (e.g., `FROM Qwen3:8B-VL`).
- **Distributed Inference (Air)**: Split large models (like 70B parameters) across multiple machines using the Air Engine.
- **Engine Server**: Run the engine as a background FastAPI service for UI integration.

## 🚀 Installation

For the best experience, install the Engine globally using our official Builder:

```bash
pip install lmms-builder
lmms-builder --autoset
```

This will automatically detect your OS, download the correct highly-optimized compiled binary, and configure it globally on your system.

## 💻 Manual Installation (Source Code)

If you wish to run the raw Python code directly:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MarkanM-Official/LMMs-engine.git
   cd LMMs-engine
   ```

2. **Install core dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Llama C++ Python (Crucial):**
   ```bash
   pip install llama-cpp-python
   ```
   *Note: For CUDA GPU acceleration, set `CMAKE_ARGS="-DGGML_CUDA=on"` before installing `llama-cpp-python`.*

4. **Run the Engine:**
   ```bash
   python3 main.py help
   ```

## 🛠️ Command Reference

| Command | Description |
|---------|-------------|
| `run <model>` | Boot up a model interactively. (e.g. `lmms run Qwen3:8B-VL -f`) |
| `pull <model>` | Download a `.gguf` model from HuggingFace to your local cache. |
| `create` | Create a customized model using a `Modelfile`. |
| `ps` | View currently loaded models and VRAM usage. |
| `stop <model>` | Unload a specific model from memory. |
| `doctor` | Run comprehensive engine health and dependency checks. |
| `serve` | Start the engine REST API server in the foreground. |

### Chat Modes
When running a model interactively, you can enforce specific personality profiles using flags:
- `-f` / `--fast`: Quick, direct answers without conversational filler.
- `-c` / `--code`: Expert programmer mode. Returns only code and technical documentation.
- `-r` / `--research`: Deep analytical mode for complex reasoning.

## 🏗️ Architecture

LMMs Engine operates as a standalone orchestrator. It uses `ctypes` bindings via `llama_cpp` to interface directly with optimized C++ execution graphs. 

When compiled via PyInstaller, the Engine bundles the C++ `.so` or `.dll` shared libraries natively, meaning end-users do not need Python, C-compilers, or dependencies installed on their machine!

## 📜 License
This project is licensed under the Apache License, Version 2.0.
See the [LICENSE](LICENSE) file for details.
Developed by Raj Singh (MarkanM).
Copyright (c) 2026.
