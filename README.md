# LMMs Unified Architecture

```
       ██╗     ███╗   ███╗███╗   ███╗███████╗
       ██║     ████╗ ████║████╗ ████║██╔════╝
       ██║     ██╔████╔██║██╔████╔██║███████╗
       ██║     ██║╚██╔╝██║██║╚██╔╝██║╚════██║
       ███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║███████║
       ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝
```

<div align="center">
  <a href="https://LMMs.MarkanM.com">
    🌐 Visit Our Official Website: LMMs.MarkanM.com
  </a>
</div>

<br>

**LMMs** is an advanced, multi-component agentic AI ecosystem designed to run any open-source language model — from 1B to 350B+ parameters — and instantly equip it with autonomous agent capabilities like web search, code execution, API calling, file management, vector memory, and state tracking. We never modify the model itself. Instead, our Engine and Backend layer wraps around any model and gives it superpowers.

---

## 👑 Founders

| Role | Name |
|------|------|
| Founder | **Raj Singh** |
| Co-Founder | **Adarsh Singh** |
| Co-Founder | **Yash Raj** |

---

## 🏗️ How LMMs Works — Deep Architecture Overview

LMMs is built around a core philosophy: **the model should never need to be modified or fine-tuned to gain new capabilities**. Instead, all intelligence is injected through the architecture itself. Here is a deep breakdown of every layer:

---

### ⚙️ Layer 1: LMMs Engine — The Execution Core

The Engine is the lowest level of LMMs. It is responsible for actually loading and running the AI model on your hardware. Because AI models come in wildly different sizes and architectures — from tiny 1B models to massive 350B behemoths — LMMs uses a **Dual Engine Architecture** to handle all of them efficiently:

#### 🦙 Engine A: `llama.cpp` Runtime
- **Used for:** Older, smaller, and quantized GGUF models (typically up to ~30B on consumer hardware).
- **Why llama.cpp?** It is a C++ inference engine that is highly optimized for CPUs and consumer GPUs. It supports 4-bit, 5-bit, and 8-bit quantization, meaning you can run a 7B model on just 4GB of VRAM or even pure CPU.
- **Best for:** Fast responses, low hardware, and running classic model families like Llama 2/3, Mistral, Phi, Gemma (GGUF format).

#### 🔥 Engine B: `PyTorch` Runtime
- **Used for:** New model architectures, multimodal models (vision + text), and very large models that require full GPU clusters or advanced memory management.
- **Why PyTorch?** Many cutting-edge models (such as advanced Qwen, DeepSeek, Gemma-3, and Mixtral variants) ship in HuggingFace format and use novel attention mechanisms or architecture quirks that llama.cpp has not yet implemented. PyTorch gives full flexibility and access to the entire HuggingFace ecosystem.
- **Best for:** Latest frontier models, multimodal models, research models, and models >30B that need advanced memory offloading.

#### 🌬️ Engine C: `AirLLM` (Air Engine) — Distributed / Disk-Offloading
- **Used for:** Running extremely large models (70B, 130B, 350B+) on hardware that would normally be completely unable to handle them.
- **How it works:** AirLLM layers the model weights across disk, CPU RAM, and GPU VRAM in chunks, streaming them as needed. This lets a single consumer PC run models that normally require a server cluster.
- **Best for:** Power users and researchers who want to run frontier-class models locally without spending tens of thousands on hardware.

> **Key Insight:** You can select which engine to use at model load time using `lmms run <model> -use l` (llama.cpp) or `lmms run <model> -use p` (PyTorch). The Engine auto-detects the best runtime if you omit the flag.

---

### 🧠 Layer 2: LMMs Backend — The Brain of the Agent

The Backend is the most important layer. It sits between the user and the Engine, intercepting every message and response. It is what transforms a plain language model into a fully autonomous AI agent — without touching the model's weights at all.

Here is what the Backend injects into every session:

#### 🔍 Web Search
The model can call a live web search tool during any conversation. When the user asks something that requires current information (e.g., "What happened in the news today?"), the Backend fires a real search query, retrieves results, and injects them into the model's context before it replies.

#### 🌐 API Calling
The Backend exposes a structured API-calling tool that the model can invoke. The model can form HTTP requests (GET, POST, etc.), read the JSON responses, and chain multiple API calls together to complete tasks — all without the user needing to write any code.

#### 💻 Code Execution & Autonomous Coding
Like Claude Code or Cursor AI, the LMMs Backend gives the model the ability to:
- Read, write, create, and delete files on your filesystem.
- Execute code in sandboxed subprocesses and observe the output.
- Iterate on its own code until tests pass.
- Navigate and modify entire codebases across multiple files.

This is all powered by the Backend's tool-calling engine — the model emits structured `<tool_call>` requests, the Backend intercepts and executes them, and the results are fed back as `<observation>` blocks for the next reasoning step.

#### 🗂️ Vector DB & RAG (Retrieval-Augmented Generation)
The Backend contains a built-in **FAISS-based Vector Database**. It can:
- Index any documents, files, codebases, or user-provided data.
- Perform semantic similarity search over the vector store in real time.
- Inject the most relevant retrieved chunks into the model's context window automatically.

This means even a 1B model can "know" about a 100,000-line codebase — because the Backend finds and provides only the relevant parts on demand, instead of trying to fit everything in the context window at once.

#### 📋 State Tracking & Session Memory
The Backend constantly records the session state: what the user said, what the model did, what tools were called, what files were modified, and when. This creates a persistent session log that allows:
- Full undo/redo of AI actions.
- Long-term memory across conversations.
- Reproducible audit trails of everything the agent did.

#### 🔄 Intelligent Orchestration
For very complex tasks, the Backend's orchestrator dynamically routes work between the llama.cpp runtime (fast, lightweight) and the PyTorch runtime (deep, context-heavy) based on estimated token load vs. the model's context window size. Heavy RAG-augmented queries automatically get routed to the more capable runtime.

> **The Big Picture:** Because all of this lives in the Backend — not the model — you can swap the underlying model at any time. A user can start a conversation with a 1B model for speed, switch mid-chat to a 70B model for a complex reasoning task using `/ml -s <modelname>`, and the entire agentic toolset carries over instantly. The model changes, but the agent's capabilities do not.

---

### 🖥️ Layer 3: LMMs CLI — The Smart Terminal *(Beta — Ready for Use)*

The CLI is the primary interface for LMMs. It is **fully functional** and considered ready for general use in its current beta state. It gives you a rich, interactive terminal session where you can chat with any model, switch models live, and orchestrate the full backend toolset.

**Status: ✅ Beta — Stable & Ready**

---

### 🖼️ Layer 4: LMMs GUI — The AI Workspace IDE *(Under Active Development)*

The GUI is a PyQt6-based graphical AI Workspace IDE. It is designed to be a visual environment where you can:

- **Download models** directly from HuggingFace or the LMMs model hub with one click.
- **Run and test models** with a visual chat interface.
- **Browse and manage** your local model library.
- **Monitor VRAM, CPU, and RAM** usage in real time.
- **Configure the Backend** tools, vector DB indexes, and session settings visually.
- **View session state** and conversation history in a structured graph view.
- **Edit and run code** generated by the AI in an integrated editor.

> **Status: 🚧 Under Active Development** — The GUI is currently in an early development phase. Core features like model downloading and basic chat are being built. It is not yet ready for production use, but it is available in the repository as a sandbox for contributors.

---

## 📦 Component Summary

| Component | Description | Status |
|---|---|---|
| **LMMs Engine** | AI execution layer (llama.cpp + PyTorch + AirLLM) | ✅ Stable |
| **LMMs Backend** | Agentic brain: tools, RAG, web search, state tracking | ✅ Stable |
| **LMMs CLI** | Smart terminal interface for all interactions | ✅ Beta |
| **LMMs GUI** | PyQt6 graphical AI Workspace IDE | 🚧 In Development |

---

## 🛠️ Installation

LMMs uses a unified pip-based package manager. You do not need to manually clone this repository or compile any code. The `LMMs-builder` automatically downloads the correct pre-compiled standalone binary for your OS (Windows, Mac, or Linux).

```bash
# Step 1: Install the official LMMs Builder
pip install LMMs-builder

# Step 2: Check OS and hardware compatibility
LMMs-builder -check

# Step 3: Install the full LMMs ecosystem
LMMs-builder install --all
```

---

## 💻 Commands Reference

### 1) Builder / Installer Commands

| Command | Description |
|---|---|
| `LMMs-builder -check` | Detect OS, hardware, and installed components |
| `LMMs-builder install --engine` | Install only the Engine |
| `LMMs-builder install --backend` | Install only the Backend |
| `LMMs-builder install --gui` | Install only the GUI |
| `LMMs-builder install --all` | Install the full LMMs stack |
| `LMMs-builder update --all` | Download and apply the latest release |

### 2) Repair & Rebuild

| Command | Description |
|---|---|
| `LMMs-repair LMMs -<component>` | Repair a component without losing saved data |
| `LMMs-rebuild LMMs` | Factory reset — deletes everything and reinstalls |
| `LMMs-rebuild LMMs -ds` | Data-safe reset — rebuilds code but keeps your models, chats, and persona files |

### 3) Uninstall

| Command | Description |
|---|---|
| `LMMs-uninstall --<component>` | Remove a specific component |
| `LMMs-uninstall -all --purge` | **⚠️ Danger:** Remove all LMMs binaries and all user data |

### 4) LMMs Core Launcher Commands

| Command | Description |
|---|---|
| `LMMs` | Launch your configured default interface |
| `LMMs --cli` | Launch the CLI directly for this session |
| `LMMs --gui` | Launch the GUI directly for this session |
| `LMMs --engine` | Launch the Engine directly for this session |
| `LMMs -set --cli` | Set CLI as your permanent default |
| `LMMs -set --gui` | Set GUI as your permanent default |
| `LMMs-cl` | Show the full command list |

---

## 🧠 CLI Slash Commands *(Inside the LMMs Terminal)*

These commands are typed inside an active LMMs CLI chat session.

| Command | Description |
|---|---|
| `/fast` | Switch to **FAST** mode — quick responses with no tool use |
| `/deep` | Switch to **DEEP** mode — full reasoning loop with all tools enabled (default) |
| `/model <name>` | Switch to a different model for this session (e.g., `/model llama3`) |
| `/ml -l` | List all models downloaded on your system |
| `/ml -s <modelname>` | **Live model switch** — swap the active model mid-conversation without losing context |
| `/folder <name>` | Attach an entire folder to the agent's context (e.g., `/folder src`) |
| `/code` | Enter focused code generation and editing mode for complex programming tasks |
| `/undo` | Undo the last AI action or file edit |
| `/redo` | Redo the last undone action |
| `/exit` | Exit the LMMs CLI session |

> **Note:** Only the commands listed above are currently implemented and functional. Legacy or planned commands that are not yet available have been removed from this reference to avoid confusion.

---

## ⚙️ Engine Terminal Commands

These commands are run directly in your system terminal (not inside the chat session) to manage models and the engine.

### Core Model Management

| Command | Description |
|---|---|
| `lmms pull <model>` | Auto-detect the best quantization and download a model |
| `lmms run <model>` | Load and start a chat with a model (auto-selects engine) |
| `lmms run <model> -use l` | Force llama.cpp engine |
| `lmms run <model> -use p` | Force PyTorch engine |
| `lmms stop <model>` | Unload a model from memory |
| `lmms ps` | Show all currently loaded models |
| `lmms list` | List all locally downloaded models |
| `lmms info <model>` | Show metadata, parameter count, and quant info for a model |
| `lmms rm <model>` | Delete a model from disk |
| `lmms search <query>` | Search the model hub |
| `lmms benchmark <model>` | Run a speed test on a model |
| `lmms doctor [--fix]` | Diagnose and optionally repair engine health |
| `lmms create <model> -f <file>` | Create a custom model from a Modelfile |
| `lmms server` | Start the LMMs API server / webhook dashboard |

### Air Engine (AirLLM — Disk Offloading for 70B+ Models)

| Command | Description |
|---|---|
| `lmms -air run <model>` | Run a large model using disk-offloading via AirLLM |
| `lmms --air run <m1> <m2>` | Run two models in cluster/scheduled mode |
| `lmms air ps` | Show Air Engine active sessions |
| `lmms air cache` | Show disk cache usage |
| `lmms air stats` | Show memory and throughput metrics |
| `lmms air unload` | Unload Air Engine models from memory |
| `lmms air benchmark` | Benchmark a model under Air Engine |

---

## 🚀 CI/CD Pipeline (GitHub Actions)

Every push to the `main` branch automatically triggers the LMMs build pipeline. It:

1. Compiles the Python source into standalone binaries using PyInstaller:
   - **Windows:** `.exe` files
   - **Linux:** Native ELF binaries
   - **macOS:** `.app` bundles
2. Produces **12 build artifacts** (one per component per platform).
3. Publishes all artifacts directly to the **GitHub Releases** page.
4. Your local `LMMs-builder` tool checks the Releases page on `LMMs-builder update` and downloads the latest build automatically — no Git required.

---

## 📄 License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for full details.
