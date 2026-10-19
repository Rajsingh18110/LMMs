# LMMs Compute Engine Architecture

The **LMMs Compute Engine** is a high-performance, modular machine learning compute layer supporting both ultra-fast quantized local inference and enterprise-grade full-precision training/multimodal workflows.

---

## 🏛️ Two-Engine Modular Architecture

```
                               ┌─────────────────────────────┐
                               │     Unified Engine Manager  │
                               │   (Smart Auto-Dispatcher)   │
                               └──────────────┬──────────────┘
                                              │
                 ┌────────────────────────────┴────────────────────────────┐
                 ▼                                                         ▼
  ┌─────────────────────────────┐                           ┌─────────────────────────────┐
  │   Engine 1: Air + LlamaCpp  │                           │   Engine 2: Air + PyTorch   │
  ├─────────────────────────────┤                           ├─────────────────────────────┤
  │ • Model Format: GGUF        │                           │ • Model Format: Safetensors │
  │ • Core: C++ llama.cpp       │                           │ • Core: PyTorch / HF        │
  │ • Pager: Q8_0 KV Cache      │                           │ • Streamer: Layer Streaming │
  │ • Memory: Zero-latency mmap │                           │ • Training: LoRA / QLoRA    │
  │ • Footprint: ~150 MB        │                           │ • Footprint: ~4.5 GB (Opt)  │
  └─────────────────────────────┘                           └─────────────────────────────┘
```

---

## 📁 Directory Structure

```text
lmms/engine/
├── core/                       # Shared hardware detection, OOM guardrails, virtual memory
│   ├── base.py                 # Abstract RuntimeContract interface
│   ├── hardware.py             # Multi-layer VRAM / RAM / CUDA profiler
│   ├── guardrails.py           # Universal OOM prevention and safety nets
│   └── memory_map.py           # Zero-latency OS virtual memory mmap parser
│
├── engine_1_llamacpp/          # 🌟 ENGINE 1: AIR + LLAMACPP (GGUF Fast Inference)
│   ├── runtime.py              # AirLlamaCppRuntime (Main Engine 1 executor)
│   ├── air_pager.py            # Dynamic Q8_0 KV Cache Pager & FlashAttention
│   ├── air_loader.py           # Tri-Regime Memory Calculator & GGUF metadata parser
│   ├── scheduler.py            # Multi-model group routing & P-core affinity
│   ├── prefetch.py             # Async predictive layer prefetching
│   └── stats.py                # Live throughput & VRAM/RAM telemetry
│
├── engine_2_pytorch/           # 🌟 ENGINE 2: AIR + PYTORCH (Safetensors & Training)
│   ├── runtime.py              # AirPyTorchRuntime (Main Engine 2 executor)
│   ├── air_streamer.py         # AirEngine layer-by-layer Safetensors offloading
│   ├── trainer.py              # Enterprise PEFT / LoRA fine-tuning offloader
│   └── hf_vision.py            # Multimodal vision processor
│
├── manager.py                  # Auto-Dispatcher & Engine Switcher
├── modelfile.py                # Modelfile parser & compiler
├── cache_manager.py            # High-level model cache eviction
└── registry.py                 # Local model registry manager
```

---

## ⚙️ How Engine Selection Works

### 1. Auto-Dispatcher (`mode="auto"` - Default)
The system inspects the model being loaded:
- If file is `.gguf` or points to a GGUF format $\to$ Routes to **Engine 1 (Air + LlamaCpp)**.
- If model is a HuggingFace repo ID, Safetensors file, or training task $\to$ Routes to **Engine 2 (Air + PyTorch)**.

### 2. Manual Override
Users or developers can explicitly force an engine:
- `engine_manager.set_engine_mode("1")` $\to$ Forces Engine 1 (Air + Llama.cpp).
- `engine_manager.set_engine_mode("2")` $\to$ Forces Engine 2 (Air + PyTorch).
- `engine_manager.set_engine_mode("auto")` $\to$ Restores smart hardware routing.

---

## 🧩 Extending the Engine for New Developers

### Adding a Feature to Engine 1 (GGUF / LlamaCpp)
Work inside `lmms/engine/engine_1_llamacpp/`. All KV cache paging, GGUF tensor mapping, and token generation live here.

### Adding a Feature to Engine 2 (PyTorch / Training / Safetensors)
Work inside `lmms/engine/engine_2_pytorch/`. All transformer layer streaming, LoRA adapters, and gradient offloading live here.
