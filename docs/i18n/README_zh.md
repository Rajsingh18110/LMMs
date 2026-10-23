<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS Logo" width="100%" />
  </a>
</div>

<p align="center">
  <strong>基于模型构建。通过智能体交付。</strong><br>
  <em>由创始人 Raj Singh (MarkanM) 构建的 Python 原生本地 AI 操作系统</em>
</p>

<p align="center">
  <a href="https://lmms.markanm.com"><img src="https://img.shields.io/badge/Official_Website-lmms.markanm.com-0ea5e9?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Website" /></a>
  <a href="https://pypi.org/project/lmms"><img src="https://img.shields.io/badge/PyPI-lmms_builder-3776ab?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-Apache_2.0-22c55e?style=for-the-badge&logo=apache&logoColor=white" alt="License" /></a>
  <img src="https://img.shields.io/badge/Architecture-Local--First_&_Enterprise-8b5cf6?style=for-the-badge" alt="Architecture" />
  <img src="https://img.shields.io/badge/Offloading-Infinite_AirEngine-f59e0b?style=for-the-badge" alt="AirEngine" />
</p>

---

### 🌐 Select Language / भाषा चुनें / Выберите язык / 选择语言

<div align="center">

[![English](https://img.shields.io/badge/Language-English-0284c7?style=flat-square)](../../README.md)
[![हिन्दी](https://img.shields.io/badge/Language-हिन्दी-ea580c?style=flat-square)](README_hi.md)
[![Русский](https://img.shields.io/badge/Language-Русский-dc2626?style=flat-square)](README_ru.md)
[![中文](https://img.shields.io/badge/Language-中文-b91c1c?style=flat-square)](#)
[![Français](https://img.shields.io/badge/Language-Français-2563eb?style=flat-square)](README_fr.md)
[![Español](https://img.shields.io/badge/Language-Español-ca8a04?style=flat-square)](README_es.md)
[![Deutsch](https://img.shields.io/badge/Language-Deutsch-475569?style=flat-square)](README_de.md)
[![日本語](https://img.shields.io/badge/Language-日本語-0f172a?style=flat-square)](README_ja.md)
[![한국어](https://img.shields.io/badge/Language-한국어-16a34a?style=flat-square)](README_ko.md)
[![العربية](https://img.shields.io/badge/Language-العربية-059669?style=flat-square)](README_ar.md)
[![Português](https://img.shields.io/badge/Language-Português-15803d?style=flat-square)](README_pt.md)
[![Italiano](https://img.shields.io/badge/Language-Italiano-0d9488?style=flat-square)](README_it.md)
[![Türkçe](https://img.shields.io/badge/Language-Türkçe-e11d48?style=flat-square)](README_tr.md)
[![Tiếng Việt](https://img.shields.io/badge/Language-Tiếng_Việt-d97706?style=flat-square)](README_vi.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-be123c?style=flat-square)](README_id.md)
[![বাংলা](https://img.shields.io/badge/Language-বাংলা-047857?style=flat-square)](README_bn.md)
[![ਪੰਜਾਬੀ](https://img.shields.io/badge/Language-ਪੰਜਾਬੀ-c2410c?style=flat-square)](README_pa.md)
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](README_mr.md)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">官方网站</a> ·
  <a href="#quick-start">快速开始</a> ·
  <a href="#architecture-setup-wizard-lmms-install">架构安装向导</a> ·
  <a href="#enterprise-infrastructure--super-host">企业级基础设施</a> ·
  <a href="#core-command-reference">命令参考</a> ·
  <a href="#cli-slash-commands">Slash 交互命令</a> ·
  <a href="#product-philosophy">产品理念</a> ·
  <a href="#license">开源许可</a>
</p>

---

## 什么是 LMMs OS？

LMMs 是用于本地和远程模型执行的 Python 原生 AI 操作层。由创始人 Raj Singh (MarkanM) 打造，结合了真正的桌面 GUI 工作台、智能开发者 CLI 和成熟的底层引擎运行时，助力开发者和企业完全脱离云端锁定，私密运行大规模多模态模型。

* 🧠 **原生双引擎核心**：结合 llama.cpp 高吞吐量量化 GGUF 推理与 PyTorch 原生 safetensors 精度执行。
* ⚡ **AirEngine 无限扩展**：动态分层 GPU、CPU 与磁盘张量卸载，即使在普通笔记本上也能流畅运行 70B+ 大模型。
* 🖥️ **桌面工作台 (GUI)**：Monaco 代码编辑器、可视化 diff 对比、工作区 Git 集成与工具管理面板。
* ⌨️ **终端工作台 (CLI)**：交互式 AI Shell，提供 30+ 快捷命令、结对编程、子智能体编排与沙箱隔离。
* 🏢 **企业级集群就绪**：支持在私有局域网/VPC 中一键部署中心主机与分布式客户端自动发现。

---

## 快速开始

```bash
# 1. Clone repository
git clone https://github.com/Rajsingh18110/LMMs.git
cd LMMs

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch default interface
python main.py

# Or launch specific components directly
python main.py --gui       # Desktop GUI Studio
python main.py --cli       # Developer Terminal Shell
python main.py --engine    # Core Inference Engine Daemon
```

```bash
pip install lmms
lmms check      # Hardware & prerequisite diagnostic check
lmms install    # Interactive Architecture Setup Wizard
lmms            # Launch configured interface
```

---

## 架构安装向导 (`lmms install`)

运行 `lmms install` 即可唤起交互式终端架构向导：

```text
  LMMs Installer · Architecture Setup Wizard
  For more details, visit: https://lmms.markanm.com
  ──────────────────────────────────────────────────────────────────────
  Controls: [↑/↓] Navigate  ·  [Enter] Select  ·  [1-2] Quick Select  ·  [Q] Exit

  ? Select Deployment Architecture:

  ❯ [1] Individual Workstation
        Single workstation deployment with local hardware acceleration & offloading.

    [2] Enterprise Infrastructure
        Distributed client-server infrastructure for teams across LAN/VPC networks.
  ──────────────────────────────────────────────────────────────────────
```

---

### [1] 个人工作站部署配置

提供 6 种针对本地硬件优化的核心组件选项：

```text
  ? Select Component Configuration:

  ❯ [1] Engine 1 (Lightweight Runtime)
        llama.cpp + AirEngine (GGUF format, low RAM footprint, pure API on port 11435)

    [2] Engine 2 (PyTorch Native)
        PyTorch + Transformers + AirEngine (Full-precision Safetensors model runtime)

    [3] Super Engine (Unified Runtimes)
        All runtimes unified (llama.cpp + PyTorch + AirEngine) in a single service

    [4] Desktop Studio (GUI)
        Monaco Editor + Local Engine Client + Git Integration (gui/ branch)

    [5] Terminal Studio (CLI)
        Interactive AI Shell + Developer Toolchain + Local Engine Client (cli/ branch)

    [6] Complete Ecosystem Suite
        Full installation: Desktop Studio, Terminal CLI, Voice & Super Engine

  ──────────────────────────────────────────────────────────────────────
    [B] ◄ Back to Architecture Selection
```

---

### [2] 企业级基础设施与超级主机

专为企业、实验室与研发团队设计的分布式集群：

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **集中式高算力枢纽**：在公司 GPU 服务器上运行守护进程（监听 `0.0.0.0:11435`），支持企业自主运行与微调私有模型。
* **轻量客户端工作台**：团队员工通过桌面客户端或 CLI 自动通过局域网连接主机。
* **数据隐私主权**：所有提示词与业务代码 100% 留存在内部网络中。
* **AirEngine 突破硬件限制**：模型权重跨 VRAM、内存与 NVMe 动态流式调度，可运行超大规模模型。

---

### Pip & Installer Command Matrix

| Command | Purpose | Target Component |
|---|---|---|
| `lmms install` | Interactive Architecture Wizard | Interactive Menu |
| `lmms install --all` | Install full ecosystem | Desktop Studio, CLI, Voice, Super Engine |
| `lmms install --gui` | Install Desktop Studio | PyQt6 GUI, Monaco Editor, Engine client |
| `lmms install --cli` | Install Terminal Studio | Interactive Shell, dev tools, Engine client |
| `lmms install --engine` | Install Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Install Lightweight Engine | llama.cpp + AirEngine (GGUF runner) |
| `lmms install --engine2` | Install PyTorch Engine | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Install Enterprise Host Daemon | Central server daemon listening on `0.0.0.0:11435` |
| `lmms install --client-gui` | Install Enterprise Desktop Client | GUI configured for LAN/VPC remote host |
| `lmms install --client-cli` | Install Enterprise Terminal Client | CLI configured for LAN/VPC remote host |
| `lmms update` | Pull latest code & update | Current branch update |
| `lmms update --all` | Full update across branches | All components synced with GitHub |
| `lmms -check` | Hardware diagnostics | CPU, GPU, VRAM, AVX, disk telemetry |
| `lmms-uninstall -all` | Clean removal | Removes code, preserves pip and user cache |
| `lmms-uninstall -all --purge` | Factory reset | Complete purge of all config, models, and data |

---

## 核心命令参考指南

### LMMs Core Launcher Commands

| Command | Description |
|---|---|
| `lmms` | Launch configured default interface |
| `lmms --gui` | Launch desktop GUI studio |
| `lmms --cli` | Launch developer CLI shell |
| `lmms --engine` | Launch inference engine directly |
| `lmms set --gui` | Set Desktop Studio as the default launch mode |
| `lmms set --cli` | Set Terminal Studio as the default launch mode |
| `lmms set --engine` | Set Engine Daemon as the default launch mode |
| `lmms stop` | Gracefully stop active background LMMs engine |
| `lmms -check` | Run hardware profile and prerequisite validation |
| `lmms update` | Smart update from current branch |
| `lmms update --all` | Force update and re-sync from GitHub |
| `lmms --help` | Show comprehensive launcher help |

---

### Engine Runtime & Air Engine

| Command | Description |
|---|---|
| `lmms run <model>` | Run model in interactive chat or single-shot evaluation |
| `lmms list` | List locally downloaded models |
| `lmms ps` | Show active running models, allocation state, and VRAM |
| `lmms pull <model>` | Download model from Hugging Face / Model Hub |
| `lmms info <model>` | Inspect model metadata, context window, and quantization |
| `lmms search <query>` | Search available model repositories |
| `lmms benchmark <model>` | Benchmark token generation speed (t/s) and latency |
| `lmms doctor` | Run engine health checks and diagnose driver/CUDA issues |
| `lmms -air run <model>` | Run ultra-large models with Air dynamic hybrid offloading |
| `lmms air ps` | Display active Air session models and layer allocation |
| `lmms air stats` | View real-time hardware telemetry and offload statistics |
| `lmms air unload` | Unload all Air models and immediately flush VRAM/RAM cache |

---

## CLI 终端交互式 Slash 命令表

| Command | Description |
|---|---|
| `/fast` | FAST mode with quick responses and lightweight tool use |
| `/deep` | DEEP mode with full multi-step reasoning and tool access |
| `/model <name>` | Switch to a different model for the current conversation |
| `/ml -l` | List all downloaded local models |
| `/ml -s <name>` | Live-switch active model while preserving conversation history |
| `/folder <path>` | Attach a directory to the agent's working context |
| `/code` | Enter focused code generation and editing mode |
| `/chat` | List and review past chat sessions |
| `/newchat` | Start a fresh empty chat session |
| `/undo` | Safely undo the last AI file edit or patch |
| `/redo` | Redo the last undone file action |
| `/mic` | Record voice audio and transcribe directly into the prompt |
| `/vision` | Switch to multimodal vision mode for image and UI analysis |
| `/research` | Switch to research mode for web and documentation exploration |
| `/read <file>` | Read an arbitrary workspace file directly into the session |
| `/git` | Execute safe, audited Git operations through the agent |
| `/checkpoint` | Save an immutable checkpoint of the current workspace state |
| `/rollback` | Roll back repository and files to a previous checkpoint |
| `/doctor` | Run comprehensive system diagnostics and repair checks |
| `/pair` | Enter interactive pair-programming mode |
| `/perm <level>` | Adjust sandbox permission level (`strict`, `ask`, `full`) |
| `/agent` | Spawn and manage autonomous subagents for parallel execution |

---

## 产品理念

1. **专注实用**：优先支持代码补丁、AST 语法验证及安全沙箱任务。
1. **坦诚透明**：零遥测数据收集，无强制付费墙。
1. **本地优先**：模型权重与数据资产完全归属用户自身掌控。
1. **极简精练**：Python 原生架构，杜绝臃肿的外来依赖。

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
