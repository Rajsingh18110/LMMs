# LMMs Unified Architecture
==================================================
       ██╗     ███╗   ███╗███╗   ███╗███████╗
       ██║     ████╗ ████║████╗ ████║██╔════╝
       ██║     ██╔████╔██║██╔████╔██║███████╗
       ██║     ██║╚██╔╝██║██║╚██╔╝██║╚════██║
       ███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║███████║
       ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝
==================================================

<div align="center">
  <a href="https://LMMs.MarkanM.com" style="color: #00e5ff; font-weight: bold; font-size: 1.5em; text-decoration: none;">
    🌐 Visit Our Official Website: LMMs.MarkanM.com
  </a>
</div>

<br>

**LMMs** is an advanced, multi-component agentic AI ecosystem natively designed to integrate directly with OS-level capabilities and automated browser testing. This repository serves as the master monorepo for all LMMs components, fully decoupling the source code into optimized standalone binaries.

## 👑 Founders
- **Raj Singh** – Founder
- **Adarsh Singh** – Co-Founder
- **Yash Raj** – Co-Founder

---

## 📦 Architecture Components
This repository compiles into 4 distinct applications dynamically based on your needs:

- **LMMs-All-in-One (LMMs):** The core application merging Engine, Backend, CLI, and GUI together.
- **LMMs-Engine:** The AI execution layer utilizing PyTorch and LLaMA integrations.
- **LMMs-Backend:** The brain of the AI agent which interprets user commands and manages OS tools.
- **LMMs-GUI:** The frontend PyQt6 graphical user interface.

---

## 🛠️ Installation
LMMs now uses a unified pip-based package manager. You don't need to manually clone this repository or compile any code. The LMMs-builder will automatically download the correct pre-compiled standalone binary for your OS (Windows, Mac, or Linux).

```bash
# 1. Install the official LMMs Builder package
pip install LMMs-builder

# 2. Check compatibility
LMMs-builder -check

# 3. Install LMMs
LMMs-builder install --all
```

---

## 💻 Commands Reference

### 1) Builder / Installer Commands
The standalone LMMs-builder application controls your entire installation securely.

- `LMMs-builder -check` : Automatically detects OS, hardware compatibility, and installed LMMs components.
- `LMMs-builder install --<component>` : Downloads and installs a specific component (`--engine`, `--backend`, `--gui`). Automatically installs dependencies.
- `LMMs-builder install --all` : Downloads and installs the entire merged LMMs ecosystem.
- `LMMs-builder update --all` : Forces a download of the latest code/binary version from GitHub Releases.

### 2) Repair & Rebuild
These commands help you manage corruption without losing precious data.

- `LMMs-repair LMMs -<component>` : Repairs a corrupted component seamlessly without deleting your saved data (chats, persona, models, db).
- `LMMs-rebuild LMMs` : Factory Reset. Completely deletes the LMMs project and ALL your saved user data, then installs a fresh copy.
- `LMMs-rebuild LMMs -ds` : Data-Safe Reset. Rebuilds the code structure and standalone apps but keeps your saved user data, downloaded models, and persona files intact.

### 3) Uninstall
- `LMMs-uninstall --<component>` : Deletes a specific component from your system.
- `LMMs-uninstall -all --purge` : Completely removes all LMMs binaries, code, and user data from your PC. Use with caution!

### 4) LMMs Core Launcher Commands
Once installed, the LMMs standalone app routes traffic to the engine, CLI, or GUI depending on your preference.

- `LMMs -set --gui | --cli | --engine` : Sets the default component that starts when you simply type `LMMs`.
- `LMMs --gui | --cli | --engine` : Directly runs the specified component for this session (overriding the default).
- `LMMs` : Runs your configured default component.
- `LMMs-cl` : Shows the complete command list.

---

## 🧠 AI Shell & CLI Slash Commands
These commands are used inside the LMMs CLI interface for workflow orchestration.

- `/fast` : Switch to FAST mode (quick response, no tools).
- `/deep` : Switch to DEEP mode (reasoning with tools, default).
- `/dual` : Switch to DUAL mode (multi-model debate).
- `/qwen` : Set text model to qwen3:8b.
- `/gemma` : Set text model to gemma4.
- `/model <name>` : Switch to any Ollama model (e.g., `/model llama3`).
- `/history` : Show the recent chat history.
- `/clear` : Clear the context/memory of the current session.
- `/attach` : Open GUI file picker to attach a file to context.
- `/file <name>` : Attach a specific file to context (e.g., `/file main.py`).
- `/folder <name>` : Attach an entire folder to context (e.g., `/folder src`).
- `/connector` : Manage Cloud API connectors (OpenAI, Anthropic).
- `/download` : Search and download GGUF models directly from HuggingFace.
- `/airllm` : Run extremely large models (70B+) via AirLLM disk-offloading.
- `/undo` : Undo the last AI action or code edit.
- `/redo` : Redo the last AI action or code edit.
- `/copy` : Copy the AI's last response to clipboard.
- `/paste` : Paste text or images from the clipboard into the prompt.
- `/models` : Show status table of all local and cloud models.
- `/autoset` : Automatically install all missing dependencies.
- `/vscode` : Open the current project in VS Code with LMMs integration.
- `/canvas` : Show a rich terminal rendering of the context graph.
- `/code` : Enter deep code generation/editing mode for complex tasks.
- `/smart` : Toggle Smart Chat mode (Intelligent Agent Routing).
- `/screenshot` : Take a screenshot of the screen and attach it to context.
- `/status` : Show system status, VRAM usage, and capabilities.
- `/doctor` : Diagnose system dependencies, permissions, and tools.
- `/cloud <provider>` : Switch backend to a cloud API (e.g., `/cloud openai`).
- `/routing` : Toggle intelligent background agent routing.
- `/gui` : Launch the graphical user interface (PyQt6).
- `/exit` : Exit LMMs CLI.

---

## ⚙️ LMMs Engine Commands
The core AI execution layer (LMMs-Engine) can also be controlled directly from the terminal.

### Core Engine (Dual Engine Architecture)
- `lmms pull <model>` : Auto-detect best quant & download.
- `lmms run <model> [-use l|p]` : Load & chat (`-use l`: llama.cpp, `-use p`: pytorch).
- `lmms stop <model>` : Unload model.
- `lmms ps` : Show active loaded models.
- `lmms list` : List local downloaded models.
- `lmms info <model>` : Metadata for a model.
- `lmms rm <model>` : Delete a model.
- `lmms search <query>` : Search hub.
- `lmms benchmark <model>` : Engine speed test.
- `lmms doctor [--fix]` : Fix engine health.
- `lmms create <model> -f <file>` : Create from Modelfile.
- `lmms server` : Start API Webhook Server (Dashboard).

### Air Engine (Distributed)
- `lmms -air run <model>` : Run heavy model with swapping.
- `lmms --air run <m1> <m2>` : Cluster mode scheduling.
- `lmms air ps / cache / stats` : Air metrics.
- `lmms air unload / benchmark` : Air management.

### Package Management
- `lmms package install runtime <x>`
- `lmms package install provider <x>`
- `lmms package install tool <x>`
- `lmms package list/remove`

### Orchestration
- `lmms task create/list/show` : Workflow.
- `lmms git status/commits/explain` : Git intel.
- `lmms agent run <type>` : Predefined agents.
- `lmms route / orchestrate` : Handoff flow.

---

## 🚀 Automated CI/CD (GitHub Actions)
Every push to the main branch triggers our powerful GitHub Actions pipeline. The CI/CD automatically:

- Compiles the python code into 4 distinct `.exe` (Windows), Linux, and macOS binaries using PyInstaller.
- Uploads the 12 artifacts directly to the Releases page.
- Your local `LMMs-builder` syncs with these releases to download updates instantly without Git.

## 📄 License
This project is licensed under the Apache License 2.0. See the LICENSE file for details.
