<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>मॉडल्स के साथ निर्माण करें। एजेंट्स के साथ शिप करें।</strong><br>
  <em>संस्थापक राज सिंह (MarkanM) द्वारा निर्मित पायथन-नेटिव लोकल AI ऑपरेटिंग सिस्टम</em>
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
  <a href="#system-architecture">सिस्टम आर्किटेक्चर</a> ·
  <a href="#deep-technical-capabilities">कोर क्षमताएं</a> ·
  <a href="#quick-start">क्विक स्टार्ट</a> ·
  <a href="#architecture-setup-wizard-lmms-install">सेटअप विज़ार्ड</a> ·
  <a href="#enterprise-infrastructure--super-host">एंटरप्राइज</a> ·
  <a href="#core-command-reference">कमांड्स</a> ·
  <a href="#cli-slash-commands">स्लैश कमांड्स</a> ·
  <a href="#license">लाइसेंस</a>
</p>

---

## LMMs OS क्या है?

LMMs स्थानीय और दूरस्थ मॉडल निष्पादन के लिए एक पायथन-नेटिव AI ऑपरेटिंग लेयर है। संस्थापक राज सिंह (MarkanM) द्वारा निर्मित, यह एक वास्तविक डेस्कटॉप GUI स्टूडियो, एक स्मार्ट डेवलपर CLI, और एक परिपक्व इंजन रनटाइम को जोड़ता है ताकि डेवलपर्स और टीमें बिना किसी टेलीमेट्री और बिना क्लाउड लॉक-इन के बड़े मल्टीमॉडल मॉडल चला सकें।

* **नेटिव डुअल इंजन कोर**: llama.cpp के साथ हाई-थ्रूपुट क्वांटाइज्ड GGUF इंफरेंस और PyTorch नेटिव safetensors रनटाइम।
* **AirEngine के साथ असीमित स्केलिंग**: डायनेमिक लेयर-वाइज़ GPU, CPU, और Disk टेंसर ऑफलोडिंग साधारण लैपटॉप पर भी 70B+ मॉडल्स चलाने की सुविधा देता है।
* **डेस्कटॉप स्टूडियो (GUI)**: मोनाको कोड एडिटर, विज़ुअल डिफ्स, वर्कस्पेस Git इंटीग्रेशन, और टूल मैनेजमेंट।
* **टर्मिनल स्टूडियो (CLI)**: 30+ इंटरएक्टिव स्लैश कमांड्स, पेयर-प्रोग्रामिंग, सब-एजेंट ऑर्केस्ट्रेशन और सुरक्षित सैंडबॉक्सिंग।
* **एंटरप्राइज इंफ्रास्ट्रक्चर**: प्राइवेट LAN/VPC नेटवर्क पर सेंट्रल होस्ट सर्वर और वर्कस्टेशन ऑटो-डिस्कवरी।

---

## सिस्टम आर्किटेक्चर

निम्न आरेख LMMs OS के यूज़र इंटरफ़ेस, बैकएंड सेवाओं, मॉडल इंफरेंस और एजेंट क्षमताओं के सब-सिस्टम्स को दर्शाता है:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **यूज़र इंटरफ़ेस**: `GUI workspace [main_window.py]` (मोनाको एडिटर और विज़ुअल डिफ्स) और `CLI [commands.py]` (इंटरएक्टिव डेवलपर टर्मिनल शेल)।
2. **API और बैकएंड लेयर**: `HTTP API [server.py]` (FastAPI डेमन port 11435), `Backend session [main.py]` (सेशन कोऑर्डिनेटर), और `Backend services [manager.py]`।
3. **मॉडल इंफरेंस सब-सिस्टम**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (GPU/CPU/Disk ऑफलोडिंग), `Model registry [registry.py]`, `llama.cpp runtime`, और `PyTorch runtime`।
4. **एजेंट क्षमता सब-सिस्टम**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]`, और `Workspace & Git [manager.py]`।

---

## गहन तकनीकी क्षमताएं (Deep Technical Capabilities)

### 1. मल्टीमॉडल विज़न इंजन (`/vision`, `/image`)
LMMs में नेटिव मल्टीमॉडल प्रोसेसिंग शामिल है। विज़न मोड में:
* **UI और लेआउट पार्सिंग**: वेब या डेस्कटॉप UI स्क्रीनशॉट का विश्लेषण करके विज़ुअल बग्स, गलत अलाइनमेंट और CSS रेंडरिंग त्रुटियों का पता लगाना।
* **आर्किटेक्चर और डायग्राम निष्कर्षण**: फ्लोचार्ट, ER डायग्राम और UML का विश्लेषण कर सीधे वैध मर्मेड या कोड संरचना बनाना।
* **दस्तावेज़ OCR**: स्थानीय छवियों और PDF से साफ़ टेक्स्ट और तालिकाओं को बिना क्लाउड पर भेजे निकालना।

### 2. ऑफलाइन वॉइस और ऑडियो (`/mic`)
* **लोकल स्पीच-टू-टेक्स्ट**: क्वांटाइज़्ड लोकल व्हिस्पर मॉडल्स द्वारा हाई-स्पीड ऑफलाइन ट्रांसक्रिप्शन।
* **हैंड्स-फ्री प्रॉम्प्टिंग**: बिना नेटवर्क विलंबता के सक्रिय CLI सेशन में सीधे वॉइस निर्देश रिकॉर्ड करना।

### 3. रेपो-अवेयर गिट इंजन और वर्क-ट्री आइसोलेशन (`/git`, `/scope`)
* **रीड-ओनली बनाम म्यूटेटिंग गार्ड**: जब तक स्पष्ट रूप से अनुमति न दी जाए, केवल सुरक्षित कमांड्स (`cat`, `git diff`, `grep`) की अनुमति।
* **एफेमरल गिट वर्क-ट्री**: कोड संशोधन अलग वर्क-ट्री क्लोन में निष्पादित होते हैं। टेस्ट पास होने पर ही मुख्य ब्रांच में मर्ज होते हैं।
* **यूनिफाइड डिफ पूर्वावलोकन**: डिस्क में बदलाव करने से पहले रंगीन डिफ पूर्वावलोकन दिखाता है।

### 4. डिटरमिनिस्टिक चेकपॉइंट और रोलबैक सुरक्षा (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **टर्न-आधारित चेकपॉइंट**: हर संशोधन से पहले फ़ाइलों का अपरिवर्तनीय बैकअप स्नैपशॉट लिया जाता है।
* **त्वरित रोलबैक**: यदि कोई पैच विफल होता है, तो `/rollback` या `/undo` कुछ ही मिलीसेकंड में रेपो को वापस पूर्व स्थिति में ला देता है।

### 5. स्वायत्त सब-एजेंट्स और मल्टी-एजेंट ऑर्केस्ट्रेशन (`/agent`, `/orchestrate`)
* **बैकग्राउंड टास्क**: सीमित फ़ाइल अनुमतियों और टोकन बजट के साथ सब-एजेंट्स चलाना।
* **पदानुक्रमित समन्वय**: मुख्य ऑर्केस्ट्रेटर विशेष कार्यों (टेस्टिंग, डॉक्स) को सब-एजेंट्स को सौंपता है और सत्यापित परिणाम वापस लेता है।

### 6. लोकल रिसर्च और वेक्टर मेमोरी RAG (`/research`)
* **सिमेंटिक कोडबेस इंडेक्सिंग**: त्वरित खोज के लिए वर्कस्पेस फ़ाइलों को लोकल वेक्टर स्टोर में इंडेक्स करना।
* **प्राइवेट वेब रिसर्च**: बिना किसी भ्रम (hallucination) के सटीक संदर्भ प्राप्त करना।

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

## आर्किटेक्चर सेटअप विज़ार्ड (`lmms install`)

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

| कमांड | उद्देश्य | लक्षित कंपोनेंट |
|---|---|---|
| `lmms install` | इंटरएक्टिव आर्किटेक्चर विज़ार्ड | इंटरएक्टिव मेनू |
| `lmms install --all` | पूर्ण इकोसिस्टम इंस्टॉल करें | डेस्कटॉप स्टूडियो, CLI, वॉइस, सुपर इंजन |
| `lmms install --gui` | डेस्कटॉप स्टूडियो इंस्टॉल करें | PyQt6 GUI, मोनाको एडिटर, इंजन क्लाइंट |
| `lmms install --cli` | टर्मिनल स्टूडियो इंस्टॉल करें | इंटरएक्टिव शेल, देव टूल्स, इंजन क्लाइंट |
| `lmms install --engine` | सुपर इंजन इंस्टॉल करें | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | लाइटवेट इंजन इंस्टॉल करें | llama.cpp + AirEngine (GGUF रनर) |
| `lmms install --engine2` | PyTorch इंजन इंस्टॉल करें | PyTorch + Transformers + AirEngine |
| `lmms install --host` | एंटरप्राइज होस्ट डेमन इंस्टॉल करें | सेंट्रल सर्वर डेमन (0.0.0.0:11435) |
| `lmms install --client-gui` | एंटरप्राइज डेस्कटॉप क्लाइंट इंस्टॉल करें | रिमोट होस्ट के लिए कॉन्फ़िगर GUI |
| `lmms install --client-cli` | एंटरप्राइज टर्मिनल क्लाइंट इंस्टॉल करें | रिमोट होस्ट के लिए कॉन्फ़िगर CLI |
| `lmms update` | नवीनतम कोड अपडेट करें | वर्तमान ब्रांच अपडेट |
| `lmms update --all` | सभी कंपोनेंट्स अपडेट करें | GitHub से सिंक |
| `lmms -check` | हार्डवेयर डायग्नोस्टिक्स | CPU, GPU, VRAM, AVX, डिस्क टेलीमेट्री |
| `lmms-uninstall -all` | सुरक्षित निष्कासन | कोड हटाता है, pip और कैश सुरक्षित रखता है |
| `lmms-uninstall -all --purge` | फैक्ट्री रीसेट | सभी कॉन्फ़िगरेशन, मॉडल्स और डेटा को पूरी तरह मिटाएं |

---

## कोर कमांड रेफरेंस

### LMMs Core Launcher Commands

| कमांड | विवरण |
|---|---|
| `lmms` | कॉन्फ़िगर किया गया डिफ़ॉल्ट इंटरफ़ेस लॉन्च करें |
| `lmms --gui` | डेस्कटॉप GUI स्टूडियो लॉन्च करें |
| `lmms --cli` | डेवलपर CLI शेल लॉन्च करें |
| `lmms --engine` | सीधे इन्फरेंस इंजन लॉन्च करें |
| `lmms set --gui` | डेस्कटॉप स्टूडियो को डिफ़ॉल्ट मोड के रूप में सेट करें |
| `lmms set --cli` | टर्मिनल स्टूडियो को डिफ़ॉल्ट मोड के रूप में सेट करें |
| `lmms set --engine` | इंजन डेमन को डिफ़ॉल्ट मोड के रूप में सेट करें |
| `lmms stop` | सक्रिय बैकग्राउंड LMMs इंजन डेमन को सुरक्षित रूप से बंद करें |
| `lmms --help` | व्यापक लॉन्चर सहायता दिखाएं |

---

### इंजन रनटाइम और मॉडल प्रबंधन (Engine Runtime & Model Management)

| कमांड | विवरण |
|---|---|
| `lmms run <model>` | इंटरएक्टिव चैट या सिंगल-शॉट में मॉडल चलाएं |
| `lmms stop <model>` | सक्रिय रूप से चल रहे मॉडल इंस्टेंस को बंद करें |
| `lmms list` | स्थानीय रूप से डाउनलोड किए गए मॉडल्स की सूची देखें |
| `lmms ps` | सक्रिय रूप से चल रहे मॉडल्स और VRAM स्थिति देखें |
| `lmms pull <model>` | मॉडल हब / Hugging Face से मॉडल डाउनलोड करें |
| `lmms info <model>` | मॉडल मेटाडेटा, संदर्भ विंडो और क्वांटाइजेशन जांचें |
| `lmms rm <model>` | स्थानीय रूप से संग्रहीत मॉडल को हटाएं |
| `lmms search <query>` | उपलब्ध मॉडल रिपॉजिटरी खोजें |
| `lmms benchmark <model>` | टोकन जनरेशन स्पीड (t/s) और लेटेंसी बेंचमार्क करें |
| `lmms doctor [--fix]` | स्वास्थ्य जांच चलाएं और छोटी समस्याओं को स्वतः ठीक करें, CUDA व ड्राइवर जांचें |
| `lmms create <model> -f <file>` | कस्टम मॉडल एंट्री या मेनिफेस्ट बनाएं |

---

### Air Engine (इंटेलिजेंट RAM/VRAM स्वैपिंग)

इंटेलिजेंट RAM/VRAM स्वैपिंग और डायनेमिक लेयर-वाइज़ हाइब्रिड GPU/CPU/Disk ऑफलोडिंग के साथ भारी मॉडल चलाएं।

| कमांड | विवरण |
|---|---|
| `lmms -air run <model> [prompt]` | Air हाइब्रिड GPU/CPU/Disk ऑफलोडिंग के साथ विशाल मॉडल चलाएं |
| `lmms --air run <m1> <m2>` | Air शेड्यूलर के माध्यम से कई समवर्ती मॉडल चलाएं |
| `lmms air ps` | सक्रिय Air सेशन मॉडल्स और लेयर आवंटन प्रदर्शित करें |
| `lmms air stats` | रीयल-टाइम हार्डवेयर टेलीमेट्री और ऑफलोड आँकड़े देखें |
| `lmms air cache` | Air डिस्क कैश आकार और उपयोग देखें |
| `lmms air unload` | सभी Air मॉडल्स को अनलोड करें और VRAM/RAM साफ़ करें |
| `lmms air benchmark <model>` | Air ऑफलोड शेड्यूलर के तहत प्रदर्शन बेंचमार्क करें |

---

### Server / Daemon

| कमांड | विवरण |
|---|---|
| `lmms server` | API/वेब सर्वर डेमन शुरू करें |
| `lmms server status` | डेमन स्थिति, पोर्ट, अपटाइम और स्वास्थ्य जांचें |
| `lmms engine status` | सक्रिय इंजन मोड और मेमोरी आँकड़े देखें |
| `lmms engine unload [model]` | सक्रिय मॉडल्स को मेमोरी से हटाएं और VRAM साफ़ करें |
| `lmms server start [--port 11435]` | बैकग्राउंड FastAPI इंजन डेमन शुरू करें |
| `lmms server stop` | चल रहे बैकग्राउंड सर्वर डेमन को बंद करें |

---

## CLI इंटरएक्टिव स्लैश कमांड्स

| कमांड | विवरण |
|---|---|
| `/fast` | तेज़ प्रतिक्रिया और हल्के टूल उपयोग के साथ FAST मोड में स्विच करें |
| `/deep` | गहन बहु-चरणीय तर्क और पूर्ण टूल एक्सेस के साथ DEEP मोड में स्विच करें |
| `/model <name>` | वर्तमान बातचीत के लिए किसी भिन्न मॉडल पर स्विच करें |
| `/ml -l` | सभी डाउनलोड किए गए स्थानीय मॉडल्स की सूची बनाएं |
| `/ml -s <name>` | बातचीत का संदर्भ बनाए रखते हुए लाइव मॉडल स्विच करें |
| `/folder <path>` | एजेंट के कार्य संदर्भ में एक फ़ोल्डर संलग्न करें |
| `/code` | केंद्रित कोड जनरेशन और संपादन मोड में प्रवेश करें |
| `/chat` | पिछले चैट सेशन्स की सूची बनाएं और समीक्षा करें |
| `/newchat` | एक नया खाली चैट सेशन शुरू करें |
| `/chat -r <id> <name>` | किसी विशिष्ट चैट सेशन का नाम बदलें |
| `/chat -d <id>` | किसी विशिष्ट चैट सेशन को हटाएं |
| `/undo` | अंतिम AI फ़ाइल संपादन या पैच को सुरक्षित रूप से पूर्ववत (undo) करें |
| `/redo` | अंतिम पूर्ववत की गई फ़ाइल कार्रवाई को पुनः करें (redo) |
| `/exit` | इंटरएक्टिव CLI सेशन से बाहर निकलें |
| `/reboot` | इंजन को रीबूट करें और सेशन पुनः आरंभ करें |
| `/mic` | वॉइस ऑडियो रिकॉर्ड करें और सीधे प्रॉम्प्ट में ट्रांसक्राइब करें |
| `/vision या /image` | छवि और UI विश्लेषण के लिए मल्टीमॉडल विज़न मोड में स्विच करें |
| `/research` | वेब और स्थानीय दस्तावेज़ खोज के लिए रिसर्च मोड में स्विच करें |
| `/read <file>` | वर्कस्पेस फ़ाइल को सीधे सेशन संदर्भ में पढ़ें |
| `/task` | स्वायत्त बैकग्राउंड टास्क और सब-एजेंट लक्ष्यों का प्रबंधन करें |
| `/git` | एजेंट के माध्यम से सुरक्षित, ऑडिट किए गए Git ऑपरेशन्स चलाएं |
| `/scope` | सक्रिय टूल निष्पादन सीमाओं का निरीक्षण और प्रबंधन करें |
| `/tools list` | सभी उपलब्ध नेटिव टूल्स और MCP एंडपॉइंट्स की सूची बनाएं |
| `/report` | सुरक्षा और एक्शन ऑडिट रिपोर्ट तैयार करें |
| `/checkpoint` | वर्तमान वर्कस्पेस स्थिति का अपरिवर्तनीय चेकपॉइंट सहेजें |
| `/checkpoints` | सभी सहेजे गए वर्कस्पेस चेकपॉइंट्स की सूची बनाएं |
| `/rollback` | रिपॉजिटरी और फ़ाइलों को पिछले चेकपॉइंट पर रोलबैक करें |
| `/status` | रीयल-टाइम इंजन और सिस्टम हार्डवेयर स्थिति जांचें |
| `/doctor` | व्यापक सिस्टम डायग्नोस्टिक्स और मरम्मत जांच चलाएं |
| `/pair` | इंटरएक्टिव पेयर-प्रोग्रामिंग मोड में प्रवेश करें |
| `/perm <level>` | सैंडबॉक्स अनुमति स्तर (`strict`, `ask`, `full`) समायोजित करें |
| `/agent` | समानांतर निष्पादन के लिए स्वायत्त सब-एजेंट्स बनाएं और प्रबंधित करें |
| `/orchestrate` | मल्टी-एजेंट समन्वय वर्कफ़्लो और हैंडऑफ़ का प्रबंधन करें |

---

## प्रोडक्ट फिलॉसफी

1. **उपयोगी रहें**: वास्तविक एग्जीक्यूशन — फ़ाइल पैचिंग, AST सत्यापन, सैंडबॉक्स्ड टर्मिनल टास्क को प्राथमिकता दें।
2. **ईमानदार रहें**: शून्य टेलीमेट्री, कोई अनिवार्य सब्सक्रिप्शन नहीं, कोई बनावटी पेवॉल नहीं।
3. **लोकल-फ़र्स्ट**: आपके मॉडल्स, वेट्स, टोकन्स और कोड हमेशा आपकी मशीन पर सुरक्षित रहते हैं।
4. **क्लीन स्टैक**: बिना किसी ब्लोट के शुद्ध पायथन-नेटिव आर्किटेक्चर।

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
