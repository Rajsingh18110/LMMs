<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>基于模型构建。通过智能体交付。</strong><br>
  <em>由创始人 Raj Singh (MarkanM) 构建的 Python 原生本地 AI 操作系统</em>
</p>

<p align="center">
  <a href="https://lmms.markanm.com"><img src="https://img.shields.io/badge/Official_Website-lmms.markanm.com-0284c7?style=flat-square&logo=googlechrome&logoColor=white" alt="Website" /></a>
  <a href="https://pypi.org/project/lmms"><img src="https://img.shields.io/badge/PyPI-lmms_builder-334155?style=flat-square&logo=pypi&logoColor=white" alt="PyPI" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-Apache_2.0-16a34a?style=flat-square&logo=apache&logoColor=white" alt="License" /></a>
  <img src="https://img.shields.io/badge/Architecture-Local--First_&_Enterprise-6366f1?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/Offloading-Infinite_AirEngine-d97706?style=flat-square" alt="AirEngine" />
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
  <a href="#system-architecture">系统架构</a> ·
  <a href="#deep-technical-capabilities">核心能力</a> ·
  <a href="#quick-start">快速开始</a> ·
  <a href="#architecture-setup-wizard-lmms-install">安装向导</a> ·
  <a href="#enterprise-infrastructure--super-host">企业级架构</a> ·
  <a href="#core-command-reference">命令指南</a> ·
  <a href="#cli-slash-commands">Slash 命令</a> ·
  <a href="#license">开源许可</a>
</p>

---

## 什么是 LMMs OS？

LMMs 是用于本地和远程模型执行的 Python 原生 AI 操作层。由创始人 Raj Singh (MarkanM) 打造，结合了真正的桌面 GUI 工作台、智能开发者 CLI 和成熟的底层引擎运行时，助力开发者和企业完全脱离云端锁定，私密运行大规模多模态模型。

* **原生双引擎核心**：结合 llama.cpp 高吞吐量量化 GGUF 推理与 PyTorch 原生 safetensors 精度执行。
* **AirEngine 无限扩展**：动态分层 GPU、CPU 与磁盘张量卸载，即使在普通笔记本上也能流畅运行 70B+ 大模型。
* **桌面工作台 (GUI)**：Monaco 代码编辑器、可视化 diff 对比、工作区 Git 集成与工具管理面板。
* **终端工作台 (CLI)**：交互式 AI Shell，提供 30+ 快捷命令、结对编程、子智能体编排与沙箱隔离。
* **企业级集群就绪**：支持在私有局域网/VPC 中一键部署中心主机与分布式客户端自动发现。

---

## 系统架构设计

下图详细展示了 LMMs OS 在用户界面、后端服务、模型推理与智能体能力四大子系统的端到端拓扑结构：

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **用户界面层**：`GUI workspace [main_window.py]`（基于 Monaco 的代码编辑与可视化审查）与 `CLI [commands.py]`（交互式终端 Shell）。
2. **API 与后端调度层**：`HTTP API [server.py]`（监听 11435 端口的 FastAPI 守护进程）、`Backend session [main.py]`（会话与上下文管理器）和 `Backend services [manager.py]`。
3. **模型推理子系统**：`Runtime selection [manager.py]`、`AirEngine [runtime.py]`（多级张量卸载调度器）、`Model registry [registry.py]`、`llama.cpp 运行时` 和 `PyTorch 运行时`。
4. **智能体能力子系统**：`Request orchestration [pipeline.py]`、`Vector retrieval [rag.py]`、`Agent routing [manager.py]`、`Tool execution [executor.py]`、`Session memory [core_memory.py]`、`Web research [engine.py]` 和 `Workspace & Git [manager.py]`。

---

## 深度技术能力 (Deep Technical Capabilities)

### 1. 多模态视觉引擎 (`/vision`, `/image`)
LMMs 原生集成多模态视觉处理管线：
* **UI 与布局智能解析**：截取前端网页或桌面应用图像，自动分析排版偏差、CSS 渲染缺陷及视觉 Bug。
* **系统架构与流程图提取**：自动读取流程图、ER 图与 UML 序列图，直接将其转录为可执行的 Mermaid 代码或数据结构。
* **离线文档 OCR 提取**：在本地安全提取图像与 PDF 中的结构化表格与文字，绝不向云端发送任何图像数据。

### 2. 离线语音与音频交互 (`/mic`)
* **本地语音转文本**：基于量化本地 Whisper 模型提供毫秒级离线语音识别。
* **零延迟语音输入**：直接通过麦克风录入工程指令并实时转写到 CLI 对话提示词中。

### 3. 代码仓库感知与 Worktree 隔离安全 (`/git`, `/scope`)
* **只读安全守卫**：除非获得显式授权，智能体默认仅能执行无害只读指令（`cat`, `git diff`, `grep`）。
* **临时 Git Worktree 沙箱**：代码生成与修改操作在独立的临时克隆分支中进行，只有单元测试全部通过后才合并回主工作流。
* **彩色 Diff 预审**：所有磁盘写入前均自动呈现统一彩色补丁对比。

### 4. 确定性 Checkpoint 检查点与瞬间回滚 (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **轮次级状态快照**：在执行任何文件修改前自动记录不可篡改的备份镜像。
* **毫秒级安全回滚**：若生成的补丁引发测试失败或语法错误，`/rollback` 或 `/undo` 可在一秒内恢复到原始纯净状态。

### 5. 自治子智能体与多智能体协同 (`/agent`, `/orchestrate`)
* **后台任务独立派发**：派生拥有独立上下文与权限受限的后台子智能体执行长耗时任务。
* **多层级协同编排**：主编排器将测试、文档整理、代码重构等专项任务分派给各子智能体，并自动合并验证结果。

### 6. 本地语义检索与矢量知识库 RAG (`/research`)
* **代码语义索引**：自动对本地仓库建立矢量索引，快速检索类、函数与类型签名。
* **无幻觉离线文档检索**：抓取并索引本地 API 文档，杜绝大模型代码幻觉。

---

## Quick Start

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

| 命令 | 用途 | 目标组件 |
|---|---|---|
| `lmms install` | 启动交互式终端架构安装向导 | 交互式配置菜单 |
| `lmms install --all` | 安装完整生态系统 | 桌面工作台、CLI、语音、Super Engine |
| `lmms install --gui` | 安装桌面 GUI 工作台 | PyQt6 GUI、Monaco 编辑器、引擎客户端 |
| `lmms install --cli` | 安装终端 CLI 开发者套件 | 交互式 Shell、开发工具链、引擎客户端 |
| `lmms install --engine` | 安装 Super Engine 混合运行时 | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | 安装轻量级推理引擎 | llama.cpp + AirEngine (GGUF 专用) |
| `lmms install --engine2` | 安装 PyTorch 深度学习引擎 | PyTorch + Transformers + AirEngine |
| `lmms install --host` | 安装企业级中心主机服务 | 中央守护进程，监听 0.0.0.0:11435 |
| `lmms install --client-gui` | 安装企业桌面客户端 | 配置为自动连接局域网远端主机的 GUI |
| `lmms install --client-cli` | 安装企业终端客户端 | 配置为自动连接局域网远端主机的 CLI |
| `lmms update` | 拉取最新代码并热更新 | 当前所在分支代码更新 |
| `lmms update --all` | 全分支强制同步更新 | 所有组件与 GitHub 远程保持一致 |
| `lmms -check` | 运行硬件与环境综合诊断 | 检测 CPU、GPU、VRAM、AVX 及磁盘指标 |
| `lmms-uninstall -all` | 安全卸载源码 | 仅删除代码，保留 pip 包及用户数据模型缓存 |
| `lmms-uninstall -all --purge` | 恢复出厂设置与彻底清除 | 彻底清空所有配置、下载模型与会话数据 |

---

## 核心命令参考

### LMMs Core Launcher Commands

| 命令 | 描述 |
|---|---|
| `lmms` | 启动系统预设的默认组件界面 |
| `lmms --gui` | 直接启动桌面 GUI 工作台 |
| `lmms --cli` | 直接启动开发者终端交互式 Shell |
| `lmms --engine` | 直接启动底层推理引擎服务 |
| `lmms set --gui` | 将桌面 GUI 设置为系统默认启动模式 |
| `lmms set --cli` | 将终端 CLI 设置为系统默认启动模式 |
| `lmms set --engine` | 将推理引擎设置为系统默认启动模式 |
| `lmms stop` | 优雅停止正在后台运行的 LMMs 引擎守护进程 |
| `lmms --help` | 打印启动器的完整帮助文档 |

---

### 引擎运行时与模型管理 (Engine Runtime & Model Management)

| 命令 | 描述 |
|---|---|
| `lmms run <model>` | 在交互式会话或单次评估中运行指定模型 |
| `lmms stop <model>` | 停止指定正在运行的模型实例 |
| `lmms list` | 查看本地已下载的大语言模型清单 |
| `lmms ps` | 展示当前活跃模型、显存占用与资源分配 |
| `lmms pull <model>` | 从 Hugging Face 或官方模型库高速下载模型 |
| `lmms info <model>` | 查看模型的元数据、上下文长度与量化规格 |
| `lmms rm <model>` | 删除本地已下载存储的模型文件 |
| `lmms search <query>` | 搜索云端可下载的开源模型仓库 |
| `lmms benchmark <model>` | 基准测试推理速度 (token/秒) 与首字延迟 |
| `lmms doctor [--fix]` | 诊断引擎健康状态并自动修复微小问题，验证 CUDA 与显卡驱动 |
| `lmms create <model> -f <file>` | 根据 GGUF、Safetensors 或清单文件注册新模型 |

---

### Air Engine (智能内存 / 显存分层交换调度)

借助智能内存交换和动态多级 GPU/CPU/磁盘张量卸载，运行远超物理显存的大型模型。

| 命令 | 描述 |
|---|---|
| `lmms -air run <model> [prompt]` | 借助 AirEngine 内存分层技术运行超大规模模型 |
| `lmms --air run <m1> <m2>` | 通过 Air 调度器并行加载并运行多个大模型 |
| `lmms air ps` | 监控 Air 会话的模型层分配及 GPU/CPU 调度 |
| `lmms air stats` | 实时查看硬件张量卸载吞吐与内存流速统计 |
| `lmms air cache` | 查看 Air 磁盘高速缓存占用与存储利用率 |
| `lmms air unload` | 立即卸载所有 Air 模型并完全清空显存缓存 |
| `lmms air benchmark <model>` | 在 Air 动态调度模式下基准测试吞吐量表现 |

---

### Server / Daemon

| 命令 | 描述 |
|---|---|
| `lmms server` | 启动 API / Web 守护服务 |
| `lmms server status` | 检查服务端点状态、监听端口与在线时长 |
| `lmms engine status` | 查看底层引擎执行模式及活跃内存占用 |
| `lmms engine unload [model]` | 强制从显存释放模型并清理张量缓存 |
| `lmms server start [--port 11435]` | 在指定端口后台启动 FastAPI 引擎守护服务 |
| `lmms server stop` | 平稳终止正在后台运行的服务进程 |

---

## CLI 交互式 Slash 快捷命令

| 命令 | 描述 |
|---|---|
| `/fast` | 切换为快速简答模式，减少复杂工具调用以提升响应流速 |
| `/deep` | 切换为深度推理模式，启用完整的多步规划与深度工具链 |
| `/model <name>` | 为当前会话即时切换到另一款不同的本地大模型 |
| `/ml -l` | 在会话中直接列出所有已下载的模型 |
| `/ml -s <name>` | 热切换正在运行的模型并完整保留当前对话上下文 |
| `/folder <path>` | 将指定工作区目录挂载到智能体的实时上下文环境中 |
| `/code` | 进入专注代码生成与自动补丁审查编辑模式 |
| `/chat` | 列出并查看历史对话会话列表 |
| `/newchat` | 重置并开启一段全新的空白会话 |
| `/chat -r <id> <name>` | 重命名指定的历史会话记录 |
| `/chat -d <id>` | 永久删除指定的历史会话记录 |
| `/undo` | 安全回滚智能体执行的最近一次代码修改或补丁 |
| `/redo` | 重新应用刚才被撤销的代码变更动作 |
| `/exit` | 安全退出交互式终端会话 |
| `/reboot` | 重启后台引擎服务并刷新当前会话连接 |
| `/mic` | 启动麦克风录制语音并自动实时转写为文本提示词 |
| `/vision 或 /image` | 切换为多模态视觉分析模式以审查图像与 UI 界面 |
| `/research` | 切换为研究模式，自动检索技术文档与网络最新资讯 |
| `/read <file>` | 将本地文件内容无损载入到会话上下文中 |
| `/task` | 管理后台执行的长耗时任务与子智能体执行目标 |
| `/git` | 通过安全审查管道调用经过审计的 Git 操作 |
| `/scope` | 查看并动态调整智能体的工具调用执行边界 |
| `/tools list` | 列出所有已挂载的原生工具与 MCP 工具端点 |
| `/report` | 生成一份包含操作签名与审计证明的安全性报告 |
| `/checkpoint` | 为当前工作区状态创建不可篡改的快照检查点 |
| `/checkpoints` | 查看本地保存的所有历史检查点列表 |
| `/rollback` | 一键将整个代码仓库还原至指定的检查点版本 |
| `/status` | 查看引擎与宿主操作系统的实时硬件运行健康状态 |
| `/doctor` | 运行全面的系统环境诊断与自动修复工具 |
| `/pair` | 开启双人协同结对编程 (Pair Programming) 模式 |
| `/perm <level>` | 调整沙箱工具执行的安全权限等级 (`strict`, `ask`, `full`) |
| `/agent` | 派生并管理执行并发子任务的自主子智能体 |
| `/orchestrate` | 调度多智能体分工协同工作流与任务交付控制 |

---

## 产品理念与价值观

1. **专注实用**：优先支持代码补丁、AST 语法验证及安全沙箱任务。
2. **坦诚透明**：零遥测数据收集，无强制付费墙。
3. **本地优先**：模型权重与数据资产完全归属用户自身掌控。
4. **极简精练**：Python 原生架构，杜绝臃肿的外来依赖。

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
