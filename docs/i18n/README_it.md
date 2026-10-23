<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS Logo" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Costruisci con i modelli. Distribuisci con gli agenti.</strong><br>
  <em>Il sistema operativo AI locale nativo in Python creato da Raj Singh (MarkanM)</em>
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
[![中文](https://img.shields.io/badge/Language-中文-b91c1c?style=flat-square)](README_zh.md)
[![Français](https://img.shields.io/badge/Language-Français-2563eb?style=flat-square)](README_fr.md)
[![Español](https://img.shields.io/badge/Language-Español-ca8a04?style=flat-square)](README_es.md)
[![Deutsch](https://img.shields.io/badge/Language-Deutsch-475569?style=flat-square)](README_de.md)
[![日本語](https://img.shields.io/badge/Language-日本語-0f172a?style=flat-square)](README_ja.md)
[![한국어](https://img.shields.io/badge/Language-한국어-16a34a?style=flat-square)](README_ko.md)
[![العربية](https://img.shields.io/badge/Language-العربية-059669?style=flat-square)](README_ar.md)
[![Português](https://img.shields.io/badge/Language-Português-15803d?style=flat-square)](README_pt.md)
[![Italiano](https://img.shields.io/badge/Language-Italiano-0d9488?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">Sito Ufficiale</a> ·
  <a href="#quick-start">Guida Rapida</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Procedura Guidata Architettura</a> ·
  <a href="#enterprise-infrastructure--super-host">Infrastruttura Aziendale</a> ·
  <a href="#core-command-reference">Comandi Principali</a> ·
  <a href="#cli-slash-commands">Comandi Slash</a> ·
  <a href="#product-philosophy">Filosofia</a> ·
  <a href="#license">Licenza</a>
</p>

---

## Cos'è LMMs OS?

LMMs è uno strato operativo AI nativo in Python per l'esecuzione locale e remota di modelli. Creato da Raj Singh (MarkanM), unisce un ambiente grafico desktop, una CLI avanzata e un motore di inferenza efficiente senza tracciamento dati né vincoli cloud.

* 🧠 **Doppio Motore Nativo**: Inferenza GGUF quantizzata (llama.cpp) ed esecuzione ad alta precisione PyTorch safetensors.
* ⚡ **Scalabilità Infinita con AirEngine**: Offloading dinamico tra GPU, CPU e disco per eseguire modelli da oltre 70B su normali laptop.
* 🖥️ **Studio Desktop (GUI)**: Editor di codice Monaco, visualizzatore di differenze, integrazione con Git e pannello strumenti.
* ⌨️ **Studio Terminale (CLI)**: Shell interattiva con oltre 30 comandi slash, pair programming e sandbox sicuro.
* 🏢 **Pronto per l'Azienda**: Architettura distribuita client-server su reti private LAN/VPC con rilevamento automatico.

---

## Guida Rapida

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

## Configurazione dell'Architettura (`lmms install`)

Il comando `lmms install` avvia una procedura guidata interattiva da terminale:

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

### [1] Configurazioni per Postazioni di Lavoro Individuali

6 componenti essenziali per l'esecuzione in locale:

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

### [2] Infrastruttura Enterprise e Super Host

Cluster distribuito ideale per aziende e team di ricerca:

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Calcolo Centralizzato**: Demone server in ascolto su `0.0.0.0:11435` su server GPU interni per ospitare e addestrare modelli proprietari.
* **Client Remoti Leggeri**: I colleghi si collegano direttamente dai loro laptop tramite rilevamento automatico in rete LAN.
* **Riservatezza Totale dei Dati**: Nessun frammento di codice o prompt lascia mai la rete aziendale.
* **AirEngine Senza Limiti di VRAM**: Modelli enormi eseguiti tramite streaming di tensori tra RAM e disco NVMe.

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

## Riferimento dei Comandi Fondamentali

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

## Comandi Slash Interattivi da Terminale

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

## Filosofia del Prodotto

1. **Utilità Concreta**: Modifica reale di codice, validazione AST e compiti protetti.
1. **Integrità Assoluta**: Zero telemetria e nessun abbonamento forzato.
1. **Locale al 100%**: Modelli e informazioni riservate rimangono sempre sui tuoi dispositivi.
1. **Architettura Pulita**: Puro Python senza librerie ingombranti o inutili.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
