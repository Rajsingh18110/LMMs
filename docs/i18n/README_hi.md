<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS Logo" width="100%" />
  </a>
</div>

<p align="center">
  <strong>मॉडल्स के साथ निर्माण करें। एजेंट्स के साथ शिप करें।</strong><br>
  <em>फाउंडर राज सिंह (MarkanM) द्वारा निर्मित पायथन-नेटिव लोकल AI ऑपरेटिंग सिस्टम</em>
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
[![हिन्दी](https://img.shields.io/badge/Language-हिन्दी-ea580c?style=flat-square)](#)
[![Русский](https://img.shields.io/badge/Language-Русский-dc2626?style=flat-square)](README_ru.md)
[![中文](https://img.shields.io/badge/Language-中文-b91c1c?style=flat-square)](README_zh.md)
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
  <a href="https://lmms.markanm.com">वेबसाइट</a> ·
  <a href="#quick-start">क्विक स्टार्ट</a> ·
  <a href="#architecture-setup-wizard-lmms-install">आर्किटेक्चर सेटअप विज़ार्ड</a> ·
  <a href="#enterprise-infrastructure--super-host">एंटरप्राइज इंफ्रास्ट्रक्चर</a> ·
  <a href="#core-command-reference">कमांड रेफरेंस</a> ·
  <a href="#cli-slash-commands">स्लैश कमांड्स</a> ·
  <a href="#product-philosophy">फ़िलॉसफ़ी</a> ·
  <a href="#license">लाइसेंस</a>
</p>

---

## LMMs OS क्या है?

LMMs स्थानीय और दूरस्थ मॉडल निष्पादन के लिए एक पायथन-नेटिव AI ऑपरेटिंग लेयर है। संस्थापक राज सिंह (MarkanM) द्वारा निर्मित, यह एक वास्तविक डेस्कटॉप GUI स्टूडियो, एक स्मार्ट डेवलपर CLI, और एक परिपक्व इंजन रनटाइम को जोड़ता है ताकि डेवलपर्स और टीमें बिना किसी टेलीमेट्री और बिना क्लाउड लॉक-इन के बड़े मल्टीमॉडल मॉडल चला सकें।

* 🧠 **नेटिव डुअल इंजन कोर**: llama.cpp के साथ हाई-थ्रूपुट क्वांटाइज्ड GGUF इंफरेंस और PyTorch नेटिव safetensors रनटाइम।
* ⚡ **AirEngine के साथ असीमित स्केलिंग**: डायनेमिक लेयर-वाइज़ GPU, CPU, और Disk टेंसर ऑफलोडिंग साधारण लैपटॉप पर भी 70B+ मॉडल्स चलाने की सुविधा देता है।
* 🖥️ **डेस्कटॉप स्टूडियो (GUI)**: मोनाको कोड एडिटर, विज़ुअल डिफ्स, वर्कस्पेस Git इंटीग्रेशन, और टूल मैनेजमेंट।
* ⌨️ **टर्मिनल स्टूडियो (CLI)**: 30+ इंटरएक्टिव स्लैश कमांड्स, पेयर-प्रोग्रामिंग, सब-एजेंट ऑर्केस्ट्रेशन और सुरक्षित सैंडबॉक्सिंग।
* 🏢 **एंटरप्राइज रेडी**: प्राइवेट LAN/VPC नेटवर्क पर सेंट्रल होस्ट सर्वर और वर्कस्टेशन ऑटो-डिस्कवरी।

---

## क्विक स्टार्ट

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

## आर्किटेक्चर सेटअप विज़ार्ड (`lmms install`)

`lmms install` चलाने पर इंटरएक्टिव टर्मिनल विज़ार्ड खुलता है:

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

### [1] इंडिविजुअल वर्कस्टेशन कॉन्फ़िगरेशन

लोकल मशीन पर मॉडल और टूल्स निष्पादन के लिए 6 प्रमुख कंपोनेंट्स:

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

### [2] एंटरप्राइज इंफ्रास्ट्रक्चर और सुपर होस्ट

संगठनों, लैब्स और डेवलपर टीमों के लिए डिस्ट्रीब्यूटेड क्लस्टर:

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **सेंट्रलाइज्ड हैवी कंप्यूट**: कंपनी के हाई-एंड GPU सर्वर पर होस्ट डेमन `0.0.0.0:11435` पर चलता है। कंपनी अपना खुद का मॉडल होस्ट और ट्रेन कर सकती है।
* **रिमोट क्लाइंट स्टूडियो**: सभी कर्मचारी अपने लैपटॉप से लोकल LAN/VPC द्वारा ऑटो-डिस्कवरी से जुड़ते हैं।
* **डेटा गोपनीयता**: कोई भी कोड या प्रॉम्प्ट कंपनी के प्राइवेट नेटवर्क से बाहर नहीं जाता।
* **AirEngine इनफिनिट स्केलिंग**: मेमोरी की कोई बाधा नहीं — कितना भी बड़ा मॉडल VRAM, RAM और NVMe में स्ट्रीम होकर चलता है।

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

## कोर कमांड रेफरेंस

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

## CLI इंटरएक्टिव स्लैश कमांड्स

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

## प्रोडक्ट फिलॉसफी

1. **उपयोगी रहें**: वास्तविक एग्जीक्यूशन — फ़ाइल पैचिंग, AST सत्यापन, सैंडबॉक्स्ड टर्मिनल टास्क को प्राथमिकता दें।
1. **ईमानदार रहें**: शून्य टेलीमेट्री, कोई अनिवार्य सब्सक्रिप्शन नहीं, कोई बनावटी पेवॉल नहीं।
1. **लोकल-फ़र्स्ट**: आपके मॉडल्स, वेट्स, टोकन्स और कोड हमेशा आपकी मशीन पर सुरक्षित रहते हैं।
1. **क्लीन स्टैक**: बिना किसी ब्लोट के शुद्ध पायथन-नेटिव आर्किटेक्चर।

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
