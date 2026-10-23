<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>मॉडेल्ससह तयार करा. एजंट्ससह वितरित करा.</strong><br>
  <em>संस्थापक राज सिंग (MarkanM) द्वारे विकसित पायथन-नेटिव्ह लोकल AI ऑपरेटिंग सिस्टम</em>
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
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](#)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">अधिकृत संकेतस्थळ</a> ·
  <a href="#system-architecture">सिस्टम आर्किटेक्चर</a> ·
  <a href="#deep-technical-capabilities">मुख्य क्षमता</a> ·
  <a href="#quick-start">जलद सुरुवात</a> ·
  <a href="#architecture-setup-wizard-lmms-install">इन्स्टॉलेशन विझार्ड</a> ·
  <a href="#enterprise-infrastructure--super-host">एंटरप्राइझ</a> ·
  <a href="#core-command-reference">कमांड संदर्भ</a> ·
  <a href="#cli-slash-commands">स्लॅश कमांड्स</a> ·
  <a href="#license">परवाना</a>
</p>

---

## LMMs OS काय आहे?

LMMs हा स्थानिक आणि दूरस्थ मॉडेल एक्झिक्यूशनसाठी एक पायथन-नेटिव्ह AI ऑपरेटिंग लेयर आहे. संस्थापक राज सिंग (MarkanM) यांनी तयार केलेला, हा प्लॅटफॉर्म रिअल डेस्कटॉप GUI स्टुडिओ, स्मार्ट डेव्हलपर CLI, आणि परिपक्व इंजिन रनटाइम एकत्र आणतो जेणेकरून डेव्हलपर्स आणि संस्था कोणत्याही टेलिमेट्री किंवा क्लाउड बंधनाशिवाय मोठे मल्टिमोडल मॉडेल्स चालवू शकतील.

* **नेटिव्ह ड्युअल इंजिन कोअर**: llama.cpp सह हाय-थ्रूपूट क्वांटाइज्ड GGUF इन्फरन्स आणि PyTorch नेटिव्ह safetensors रनटाइम.
* **AirEngine सह अमर्याद स्केलिंग**: GPU, CPU आणि डिस्क दरम्यान डायनॅमिक टेन्सर ऑफलोडिंग सामान्य लॅपटॉपवरही 70B+ मॉडेल्स चालवण्यास सक्षम करते.
* **डेस्कटॉप स्टुडिओ (GUI)**: मोनॅको कोड एडिटर, व्हिज्युअल diff तुलना, Git इंटिग्रेशन आणि बिल्ट-इन टूल व्यवस्थापन.
* **टर्मिनल स्टुडिओ (CLI)**: ३०+ पेक्षा जास्त स्लॅश कमांड्स, पेअर प्रोग्रामिंग, सब-एजंट ऑर्केस्ट्रेशन आणि सुरक्षित सँडबॉक्स.
* **एंटरप्राइझसाठी सज्ज**: खाजगी LAN/VPC नेटवर्कवर मध्यवर्ती होस्ट आणि ऑटो-डिस्कव्हरीसह वितरित क्लायंट-सर्व्हर क्लस्टर.

---

## सिस्टम आर्किटेक्चर

खालील आकृती LMMs OS च्या युझर इंटरफेस, बॅकएंड सर्व्हिसेस, मॉडेल इन्फरन्स आणि एजंट क्षमतांचे संपूर्ण आर्किटेक्चर दर्शवते:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **युझर इंटरफेसेस**: `GUI workspace [main_window.py]` (मोनॅको आयडीई आणि diff पुनरावलोकन) आणि `CLI [commands.py]` (परस्परसंवादी टर्मिनल शेल).
2. **API आणि बॅकएंड लेयर**: `HTTP API [server.py]` (पोर्ट 11435 वरील FastAPI डिमन), `Backend session [main.py]` (सत्र समन्वयक), आणि `Backend services [manager.py]`.
3. **मॉडेल इन्फरन्स सब-सिस्टम**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (टेन्सर ऑफलोडिंग), `Model registry [registry.py]`, `llama.cpp रनटाइम` आणि `PyTorch रनटाइम`.
4. **एजंट क्षमता सब-सिस्टम**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` आणि `Workspace & Git [manager.py]`.

---

## सखोल तांत्रिक क्षमता (Deep Technical Capabilities)

### 1. मल्टिमोडल व्हिजन इंजिन (`/vision`, `/image`)
LMMs मध्ये स्थानिक इंजिनमध्ये थेट मल्टिमोडल प्रोसेसिंग समाविष्ट आहे:
* **UI आणि लेआउट विश्लेषण**: व्हिज्युअल त्रुटी आणि CSS रेंडरिंग दोष शोधण्यासाठी वेब किंवा डेस्कटॉप स्क्रीनशॉट तपासणे.
* **आर्किटेक्चर आणि आकृत्यांचे निष्कर्षण**: फ्लोचार्ट, ER डायग्राम आणि UML अनुक्रमांचे विश्लेषण करून थेट मर्मेड कोडमध्ये रूपांतर करणे.
* **स्थानिक दस्तऐवज OCR**: क्लाउडवर कोणताही डेटा न पाठवता थेट प्रतिमा आणि PDF मधून मजकूर आणि सारण्या सुरक्षितपणे काढणे.

### 2. ऑफलाइन व्हॉइस आणि ऑडिओ इनपुट (`/mic`)
* **स्थानिक स्पीच-टू-टेक्स्ट**: क्वांटाइज्ड स्थानिक Whisper मॉडेल्सद्वारे हाय-स्पीड ऑफलाइन व्हॉइस ट्रान्सक्रिप्शन.
* **हँड्स-फ्री प्रॉम्प्टिंग**: शून्य नेटवर्क विलंबासह थेट सक्रिय CLI सत्रात व्हॉइस सूचना रेकॉर्ड करा.

### 3. Git सजगता आणि Worktree अलगीकरण (`/git`, `/scope`)
* **फक्त-वाचनीय सुरक्षा रक्षक**: स्पष्ट परवानगी नसल्यास एजंटच्या कृती सुरक्षित वाचनीय कमांड्सपुरत्या (`cat`, `git diff`, `grep`) मर्यादित ठेवतो.
* **तात्पुरते Git Worktrees**: कोड बदल वेगळ्या क्लोनमध्ये चालवले जातात आणि चाचण्या यशस्वी झाल्यानंतरच मुख्य शाखेत विलीन केले जातात.
* **रंगीत Diff पूर्वावलोकन**: डिस्कवर बदल सेव्ह करण्यापूर्वी रंगीत युनिफाइड diff दाखवतो.

### 4. निश्चित चेकपॉईंट्स आणि त्वरित रोलबॅक (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **प्रत्येक पायरीचा स्नॅपशॉट**: प्रत्येक फाइल बदलापूर्वी अपरिवर्तनीय बॅकअप स्नॅपशॉट जतन केला जातो.
* **मिलीसेकंदात रोलबॅक**: कोणताही पॅच अयशस्वी झाल्यास, `/rollback` किंवा `/undo` कोड त्वरित पूर्वीच्या मूळ स्थितीत परत आणतो.

### 5. स्वायत्त सब-एजंट्स आणि मल्टी-एजंट समन्वय (`/agent`, `/orchestrate`)
* **पार्श्वभूमी कार्ये**: स्वतंत्र टोकन बजेट आणि फाइल परवानग्यांसह पार्श्वभूमीत स्वतंत्र सब-एजंट चालवणे.
* **श्रेणीबद्ध समन्वय**: मुख्य समन्वयक विशिष्ट कार्ये (चाचणी, दस्तऐवजीकरण) सब-एजंट्सना सोपवतो आणि पडताळलेले निकाल एकत्र करतो.

### 6. स्थानिक संशोधन आणि व्हेक्टर मेमरी RAG (`/research`)
* **सिमॅंटिक कोडबेस इंडेक्सिंग**: फंक्शन्स आणि क्लासेस त्वरित शोधण्यासाठी प्रोजेक्ट फाइल्स स्थानिक व्हेक्टर डेटाबेसमध्ये इंडेक्स करणे.
* **भ्रम-मुक्त दस्तऐवज शोध**: मॉडेलच्या खोट्या उत्तरांना रोखण्यासाठी स्थानिक आणि वेब API दस्तऐवज थेट अभ्यासणे.

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

## आर्किटेक्चर इन्स्टॉलेशन विझार्ड (`lmms install`)

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

### [1] वैयक्तिक वर्कस्टेशन संरचना

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

### [2] एंटरप्राइझ इन्फ्रास्ट्रक्चर आणि सुपर होस्ट

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **केंद्रीकृत शक्तिशाली संगणन**: होस्ट डिमन कंपनीच्या केंद्रीय GPU सर्व्हरवर (`0.0.0.0:11435`) चालतो जो खाजगी मॉडेल्स चालवतो आणि प्रशिक्षित करतो.
* **रिमोट क्लायंट स्टुडिओ**: कर्मचारी त्यांच्या लॅपटॉपवरून LAN/VPC द्वारे ऑटो-डिस्कव्हरीने सहजपणे कनेक्ट होतात.
* **पूर्ण डेटा गोपनीयता**: कोणताही कोड किंवा प्रॉम्प्ट कंपनीच्या अंतर्गत नेटवर्कच्या बाहेर जात नाही.
* **AirEngine अमर्याद मेमरी**: VRAM, RAM आणि जलद NVMe द्वारे महाकाय मॉडेल्स अखंडपणे चालतात.

---

### Pip & Installer Command Matrix

| कमांड | उद्देश | लक्ष्य घटक |
|---|---|---|
| `lmms install` | परस्परसंवादी आर्किटेक्चर सेटअप विझार्ड सुरू करा | परस्परसंवादी संरचना मेनू |
| `lmms install --all` | संपूर्ण इकोसिस्टम इन्स्टॉल करा | डेस्कटॉप स्टुडिओ, CLI, व्हॉइस, सुपर इंजिन |
| `lmms install --gui` | डेस्कटॉप स्टुडिओ (GUI) इन्स्टॉल करा | PyQt6 GUI, मोनॅको एडिटर, इंजिन क्लायंट |
| `lmms install --cli` | टर्मिनल स्टुडिओ (CLI) इन्स्टॉल करा | शेल, डेव्हलपर टूल्स, इंजिन क्लायंट |
| `lmms install --engine` | सुपर इंजिन रनटाइम इन्स्टॉल करा | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | लाइटवेट इंजिन इन्स्टॉल करा | llama.cpp + AirEngine (फक्त GGUF साठी) |
| `lmms install --engine2` | PyTorch नेटिव्ह इंजिन इन्स्टॉल करा | PyTorch + Transformers + AirEngine |
| `lmms install --host` | एंटरप्राइझ केंद्रीय होस्ट डिमन इन्स्टॉल करा | केंद्रीय सर्व्हर 0.0.0.0:11435 वर सक्रिय |
| `lmms install --client-gui` | एंटरप्राइझ डेस्कटॉप क्लायंट इन्स्टॉल करा | रिमोट होस्टशी कनेक्ट होणारा GUI |
| `lmms install --client-cli` | एंटरप्राइझ टर्मिनल क्लायंट इन्स्टॉल करा | रिमोट होस्टशी कनेक्ट होणारा CLI |
| `lmms update` | नवीनतम कोड डाउनलोड आणि अपडेट करा | वर्तमान सक्रिय शाखेचे अपडेट |
| `lmms update --all` | सर्व शाखांवर सक्तीचे पूर्ण अपडेट | GitHub रेपॉजिटरीशी पूर्ण समक्रमण |
| `lmms -check` | हार्डवेअर आणि पूर्वतयारी तपासणी | CPU, GPU, VRAM, AVX आणि डिस्क टेलिमेट्री |
| `lmms-uninstall -all` | सोर्स कोड सुरक्षितपणे काढून टाका | कोड हटवतो, pip पॅकेजेस आणि मॉडेल्स कॅश ठेवतो |
| `lmms-uninstall -all --purge` | फॅक्टरी रीसेट आणि संपूर्ण स्वच्छता | सर्व सेटिंग्ज, मॉडेल्स आणि डेटा कायमचा हटवा |

---

## मुख्य कमांड संदर्भ (Core Command Reference)

### LMMs Core Launcher Commands

| कमांड | वर्णन |
|---|---|
| `lmms` | कॉन्फिगर केलेला डीफॉल्ट इंटरफेस सुरू करा |
| `lmms --gui` | डेस्कटॉप GUI स्टुडिओ थेट सुरू करा |
| `lmms --cli` | डेव्हलपर CLI शेल थेट सुरू करा |
| `lmms --engine` | इन्फरन्स इंजिन डिमन थेट सुरू करा |
| `lmms set --gui` | डेस्कटॉप स्टुडिओला डीफॉल्ट लाँच मोड बनवा |
| `lmms set --cli` | टर्मिनल स्टुडिओला डीफॉल्ट लाँच मोड बनवा |
| `lmms set --engine` | इंजिन डिमनला डीफॉल्ट लाँच मोड बनवा |
| `lmms stop` | पार्श्वभूमीत चालू असलेले LMMs इंजिन सुरक्षितपणे थांबवा |
| `lmms -check` | हार्डवेअर प्रोफाइल आणि आवश्यकता तपासा |
| `lmms update` | वर्तमान शाखेतून स्मार्ट अपडेट करा |
| `lmms update --all` | GitHub वरून सर्व घटक सक्तीने अपडेट करा |
| `lmms --help` | लाँचची संपूर्ण मदत मार्गदर्शिका पहा |

---

### Engine Runtime & Air Engine

| कमांड | वर्णन |
|---|---|
| `lmms run <model>` | परस्परसंवादी चॅट किंवा सिंगल प्रॉम्प्टमध्ये मॉडेल चालवा |
| `lmms list` | स्थानिक पातळीवर डाउनलोड केलेल्या मॉडेल्सची सूची पहा |
| `lmms ps` | चालू असलेले मॉडेल्स आणि VRAM स्थिती पहा |
| `lmms pull <model>` | Hugging Face किंवा अधिकृत हबवरून मॉडेल डाउनलोड करा |
| `lmms info <model>` | मॉडेल मेटाडेटा, संदर्भ विंडो आणि क्वांटायझेशन तपासा |
| `lmms search <query>` | उपलब्ध मुक्त स्रोत मॉडेल रेपॉजिटरी शोधा |
| `lmms benchmark <model>` | टोकन निर्मिती गती (t/s) आणि लेटन्सी मोजा |
| `lmms doctor` | इंजिन आरोग्य तपासणी आणि CUDA ड्राइव्हर निदान करा |
| `lmms create <model> -f <file>` | GGUF किंवा Safetensors फाइलमधून कस्टम मॉडेल नोंदवा |
| `lmms -air run <model> [prompt]` | Air मेमरी ऑफलोडिंगसह प्रचंड मॉडेल्स चालवा |
| `lmms --air run <m1> <m2>` | Air शेड्युलरद्वारे एकाच वेळी अनेक मॉडेल्स चालवा |
| `lmms air ps` | सक्रिय Air सत्रे आणि GPU/CPU लेयर वाटप पहा |
| `lmms air stats` | रिअल-टाइम हार्डवेअर टेलिमेट्री आणि ऑफलोड आकडेवारी पहा |
| `lmms air cache` | Air डिस्क कॅशे आकार आणि वापर तपासा |
| `lmms air unload` | सर्व Air मॉडेल्स अनलोड करा आणि VRAM कॅशे त्वरित रिकामी करा |
| `lmms air benchmark <model>` | Air शेड्युलर अंतर्गत प्रोसेसिंग गती मोजा |

---

### Server / Daemon

| कमांड | वर्णन |
|---|---|
| `lmms server` | API / वेब सर्व्हर डिमन सुरू करा |
| `lmms server status` | सर्व्हर स्थिती, पोर्ट, अपटाइम आणि आरोग्य तपासा |
| `lmms engine status` | सक्रिय इंजिन मोड आणि मेमरी आकडेवारी पहा |
| `lmms engine unload [model]` | मेमरीमधून मॉडेल्स काढून टाका आणि VRAM मोकळी करा |
| `lmms server start [--port 11435]` | नियुक्त पोर्टवर पार्श्वभूमी FastAPI सर्व्हर सुरू करा |
| `lmms server stop` | चालू असलेला पार्श्वभूमी सर्व्हर डिमन थांबवा |

---

## परस्परसंवादी CLI स्लॅश कमांड्स

| कमांड | वर्णन |
|---|---|
| `/fast` | जलद उत्तरांसाठी आणि हलक्या टूल्ससाठी FAST मोडवर जा |
| `/deep` | सखोल विचार आणि पूर्ण टूल ॲक्सेससाठी DEEP मोडवर जा |
| `/model <name>` | वर्तमान संभाषणासाठी वेगळे मॉडेल निवडा |
| `/ml -l` | डाउनलोड केलेल्या सर्व स्थानिक मॉडेल्सची सूची चॅटमध्ये पहा |
| `/ml -s <name>` | संभाषणाचा संदर्भ न गमावता त्वरित मॉडेल बदला |
| `/folder <path>` | एजंटच्या कार्य संदर्भाशी एक फोल्डर जोडा |
| `/code` | कोड निर्मिती आणि संपादन मोडमध्ये प्रवेश करा |
| `/chat` | मागील चॅट सत्रांचा इतिहास पहा आणि पुनरावलोकन करा |
| `/newchat` | एक नवीन आणि स्वच्छ चॅट सत्र सुरू करा |
| `/chat -r <id> <name>` | एका विशिष्ट चॅट सत्राचे नाव बदला |
| `/chat -d <id>` | विशिष्ट चॅट सत्र कायमचे हटवा |
| `/undo` | AI ने केलेला शेवटचा फाइल बदल सुरक्षितपणे मागे घ्या |
| `/redo` | मागे घेतलेली फाइल कृती पुन्हा लागू करा |
| `/exit` | टर्मिनल सत्रातून सुरक्षितपणे बाहेर पडा |
| `/reboot` | बॅकएंड इंजिन रीबूट करा आणि सत्र पुन्हा कनेक्ट करा |
| `/mic` | मायक्रोफोनमधून व्हॉइस रेकॉर्ड करा आणि थेट मजकुरात रूपांतरित करा |
| `/vision किंवा /image` | प्रतिमा विश्लेषण आणि UI तपासणीसाठी व्हिजन मोडवर जा |
| `/research` | वेब आणि तांत्रिक दस्तऐवज शोधासाठी रिसर्च मोडवर जा |
| `/read <file>` | प्रकल्प फाइल थेट चॅट संदर्भात वाचा |
| `/task` | पार्श्वभूमीतील स्वायत्त कार्ये आणि उद्दिष्टे व्यवस्थापित करा |
| `/git` | एजंटद्वारे सुरक्षित आणि तपासलेल्या Git कृती करा |
| `/scope` | टूल अंमलबजावणी परवानग्यांची मर्यादा तपासा आणि बदला |
| `/tools list` | उपलब्ध सर्व स्थानिक टूल्स आणि सक्रिय MCP सर्व्हर्स पहा |
| `/report` | सुरक्षा आणि कृती ऑडिट अहवाल तयार करा |
| `/checkpoint` | सध्याच्या कार्यक्षेत्राचा एक अपरिवर्तनीय चेकपॉईंट जतन करा |
| `/checkpoints` | जतन केलेल्या सर्व चेकपॉईंट्सची सूची पहा |
| `/rollback` | रेपॉजिटरी आणि फाइल्स मागील चेकपॉईंटवर परत आणा |
| `/status` | इंजिन आणि हार्डवेअरचे रिअल-टाइम आरोग्य तपासा |
| `/doctor` | संपूर्ण सिस्टम निदान आणि स्वयंचलित दुरुस्ती चाचण्या चालवा |
| `/pair` | परस्परसंवादी पेअर-प्रोग्रामिंग मोड सुरू करा |
| `/perm <level>` | सँडबॉक्स परवानगी स्तर सेट करा (`strict`, `ask`, `full`) |
| `/agent` | समांतर कार्यांसाठी स्वायत्त सब-एजंट तयार करा आणि चालवा |
| `/orchestrate` | अनेक एजंट्समधील समन्वित कार्यप्रवाह व्यवस्थापित करा |

---

## उत्पादन तत्त्वज्ञान (Product Philosophy)

1. **प्रत्यक्ष उपयुक्तता सर्वप्रथम**: वास्तविक कोड पॅचिंग, AST पडताळणी आणि सुरक्षित सँडबॉक्सिंग.
2. **प्रामाणिकपणा आणि पारदर्शकता**: शून्य टेलिमेट्री, कोणतेही लपलेले शुल्क किंवा सबस्क्रिप्शन नाही.
3. **कट्टर लोकल-फर्स्ट**: तुमचे सर्व मॉडेल्स, वेट्स आणि कोड नेहमी तुमच्या मशीनवर सुरक्षित असतात.
4. **स्वच्छ आर्किटेक्चर**: अनावश्यक भार नसलेली शुद्ध पायथन-आधारित रचना.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
