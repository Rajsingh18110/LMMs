<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>মডেল দিয়ে তৈরি করুন। এজেন্টের সাথে শিপ করুন।</strong><br>
  <em>প্রতিষ্ঠাতা রাজ সিং (MarkanM) দ্বারা নির্মিত পাইথন-নেটিভ লোকাল এআই অপারেটিং সিস্টেম</em>
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
[![বাংলা](https://img.shields.io/badge/Language-বাংলা-047857?style=flat-square)](#)
[![ਪੰਜਾਬੀ](https://img.shields.io/badge/Language-ਪੰਜਾਬੀ-c2410c?style=flat-square)](README_pa.md)
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](README_mr.md)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">অফিসিয়াল ওয়েবসাইট</a> ·
  <a href="#system-architecture">সিস্টেম আর্কিটেকচার</a> ·
  <a href="#deep-technical-capabilities">মূল ক্ষমতা</a> ·
  <a href="#quick-start">দ্রুত শুরু</a> ·
  <a href="#architecture-setup-wizard-lmms-install">ইনস্টলেশন উইজার্ড</a> ·
  <a href="#enterprise-infrastructure--super-host">এন্টারপ্রাইজ</a> ·
  <a href="#core-command-reference">কমান্ড রেফারেন্স</a> ·
  <a href="#cli-slash-commands">স্ল্যাশ কমান্ড</a> ·
  <a href="#license">লাইসেন্স</a>
</p>

---

## LMMs OS কী?

LMMs হলো স্থানীয় এবং দূরবর্তী মডেল এক্সিকিউশনের জন্য একটি পাইথন-নেটিভ এআই অপারেটিং লেয়ার। প্রতিষ্ঠাতা রাজ সিং (MarkanM) দ্বারা নির্মিত, এটি একটি বাস্তব ডেস্কটপ GUI স্টুডিও, একটি স্মার্ট ডেভেলপার CLI, এবং একটি পরিপক্ব ইঞ্জিন রানটাইমকে একত্রিত করে যাতে ডেভেলপাররা ক্লাউড নির্ভরতা এবং টেলিমেট্রি ছাড়াই মাল্টিমোডাল মডেল চালাতে পারেন।

* **নেটিভ ডুয়াল ইঞ্জিন কোর**: llama.cpp এর সাথে হাই-থ্রুপুট কোয়ান্টাইজড GGUF ইনফারেন্স এবং PyTorch নেটিভ safetensors রানটাইম।
* **AirEngine এর সাথে অসীম স্কেলিং**: GPU, CPU, এবং ডিস্কের মধ্যে ডায়নামিক টেনসর অফলোডিং সাধারণ ল্যাপটপেও 70B+ মডেল চালানোর সুযোগ দেয়।
* **ডেস্কটপ স্টুডিও (GUI)**: মোনাকো কোড এডিটর, ভিজ্যুয়াল diff প্রিভিউ, গিট ইন্টিগ্রেশন এবং বিল্ট-ইন টুল ম্যানেজার।
* **টার্মিনাল স্টুডিও (CLI)**: ৩০টিরও বেশি স্ল্যাশ কমান্ড সহ ইন্টারেক্টিভ শেল, পেয়ার প্রোগ্রামিং, সাব-এজেন্ট অর্কেস্ট্রেশন এবং সুরক্ষিত স্যান্ডবক্স।
* **এন্টারপ্রাইজ উপযোগী**: প্রাইভেট LAN/VPC নেটওয়ার্কে সেন্ট্রাল হোস্ট এবং স্বয়ংক্রিয় ক্লায়েন্ট ডিসকভারি সহ ডিস্ট্রিবিউটেড ক্লাস্টার।

---

## সিস্টেম আর্কিটেকচার (System Architecture)

নিচের ডায়াগ্রামটি LMMs OS-এর ইউজার ইন্টারফেস, ব্যাকএন্ড সার্ভিস, মডেল ইনফারেন্স এবং এজেন্ট ক্যাপাবিলিটি সাবসিস্টেমের পূর্ণাঙ্গ আর্কিটেকচার প্রদর্শন করে:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **ইউজার ইন্টারফেস**: `GUI workspace [main_window.py]` (মোনাকো এডিটর ও diff রিভিউ) এবং `CLI [commands.py]` (ইন্টারেক্টিভ ডেভেলপার টার্মিনাল শেল)।
2. **API ও ব্যাকএন্ড লেয়ার**: `HTTP API [server.py]` (FastAPI ডেমন পোর্ট 11435), `Backend session [main.py]` (সেশন সমন্বয়ক), এবং `Backend services [manager.py]`।
3. **মডেল ইনফারেন্স সাবসিস্টেম**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (GPU/CPU/ডিস্ক অফলোডিং), `Model registry [registry.py]`, `llama.cpp ইঞ্জিন` এবং `PyTorch ইঞ্জিন`।
4. **এজেন্ট সক্ষমতা সাবসিস্টেম**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` এবং `Workspace & Git [manager.py]`।

---

## গভীর প্রযুক্তিগত সক্ষমতা (Deep Technical Capabilities)

### 1. মাল্টিমোডাল ভিশন ইঞ্জিন (`/vision`, `/image`)
LMMs স্থানীয় ইঞ্জিনের ভেতরে সরাসরি মাল্টিমোডাল প্রসেসিং অন্তর্ভুক্ত করে:
* **UI ও লেআউট বিশ্লেষণ**: ভিজ্যুয়াল বাগ এবং CSS রেন্ডারিং ত্রুটি শনাক্ত করতে ওয়েব বা ডেস্কটপ UI স্ক্রিনশট পরীক্ষা করে।
* **আর্কিটেকচার ও ডায়াগ্রাম নিষ্কাশন**: ফ্লোচার্ট, ER ডায়াগ্রাম এবং UML সিকোয়েন্স বিশ্লেষণ করে সরাসরি কার্যকরী Mermaid কোডে রূপান্তর করে।
* **স্থানীয় ডকুমেন্ট OCR**: ক্লাউডে কোনো ছবি না পাঠিয়ে সরাসরি ডিভাইস থেকে টেক্সট এবং টেবিল নিরাপদে বের করে।

### 2. অফলাইন ভয়েস ও অডিও ইনপুট (`/mic`)
* **লোকাল স্পিচ-টু-টেক্সট**: কোয়ান্টাইজড লোকাল Whisper মডেল দ্বারা হাই-স্পিড অফলাইন ভয়েস ট্রান্সক্রিপশন।
* **হ্যান্ডস-ফ্রি প্রম্পটিং**: শূন্য নেটওয়ার্ক ল্যাটেন্সিতে সরাসরি সক্রিয় CLI সেশনে ভয়েস নির্দেশ রেকর্ড করুন।

### 3. গিট সচেতনতা এবং Worktree আইসোলেশন (`/git`, `/scope`)
* **রিড-অনলি সুরক্ষা গার্ড**: স্পষ্ট অনুমতি না থাকলে এজেন্টের কাজকে নিরাপদ রিড কমান্ডে (`cat`, `git diff`, `grep`) সীমাবদ্ধ রাখে।
* **অস্থায়ী Git Worktree**: কোড পরিবর্তনগুলি পৃথক worktree ক্লোনে সম্পন্ন হয় এবং টেস্ট পাস করার পরেই মূল ব্রাঞ্চে যুক্ত হয়।
* **রঙিন Diff প্রিভিউ**: ডিস্কে কোনো পরিবর্তন লেখার আগে রঙিন ইউনিফাইড diff প্রদর্শন করে।

### 4. ডিটারমিনিস্টিক চেকপয়েন্ট ও তাৎক্ষণিক রোলব্যাক (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **পদক্ষেপভিত্তিক স্ন্যাপশট**: প্রতিটি ফাইল পরিবর্তনের আগে অপরিবর্তনীয় ব্যাকআপ স্ন্যাপশট সংরক্ষণ করা হয়।
* **মিলি-সেকেন্ডে রোলব্যাক**: কোনো প্যাচ ত্রুটি তৈরি করলে `/rollback` বা `/undo` তাত্ক্ষণিকভাবে কোডকে পূর্বাবস্থায় ফিরিয়ে আনে।

### 5. স্বায়ত্তশাসিত সাব-এজেন্ট এবং মাল্টি-এজেন্ট সমন্বয় (`/agent`, `/orchestrate`)
* **ব্যাকগ্রাউন্ড টাস্ক**: নির্দিষ্ট টোকেন বাজেট এবং ফাইল অনুমতি সহ ব্যাকগ্রাউন্ডে স্বাধীন সাব-এজেন্ট পরিচালনা করে।
* **শ্রেণীবদ্ধ সমন্বয়**: প্রধান অর্কেস্ট্রেটর বিশেষায়িত কাজগুলি (টেস্টিং, ডকুমেন্টিং) সাব-এজেন্টদের অর্পণ করে ফলাফল সংগ্রহ করে।

### 6. স্থানীয় গবেষণা এবং ভেক্টর মেমোরি RAG (`/research`)
* **কোডবেস ভেক্টর ইনডেক্সিং**: ফাংশন এবং ক্লাস দ্রুত খুঁজে পেতে স্থানীয় ভেক্টর ডাটাবেসে ফাইলগুলি ইনডেক্স করে।
* **বিভ্রান্তিমুক্ত ডকু অনুসন্ধান**: কৃত্রিম তথ্যের বিভ্রান্তি এড়াতে স্থানীয় এবং ওয়েব API ডকুমেন্টেশন সরাসরি পড়ে।

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

## আর্কিটেকচার ইনস্টলেশন উইজার্ড (`lmms install`)

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

### [1] একক ওয়ার্কস্টেশন কনফিগারেশন

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

### [2] এন্টারপ্রাইজ ইনফ্রাস্ট্রাকচার ও সুপার হোস্ট

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **কেন্দ্রীভূত শক্তিশালী কম্পিউট**: হোস্ট ডেমন কেন্দ্রীয় GPU সার্ভারে (`0.0.0.0:11435`) চলে যা নিজস্ব মডেল ট্রেনিং ও সার্ভিং নিশ্চিত করে।
* **রিমোট ক্লায়েন্ট স্টুডিও**: কর্মীরা নিজস্ব ল্যাপটপ থেকে LAN/VPC নেটওয়ার্কে অটো-ডিসকভারির মাধ্যমে যুক্ত হন।
* **সম্পূর্ণ ডেটা গোপনীয়তা**: কোনো কোড বা প্রম্পট প্রতিষ্ঠানের অভ্যন্তরীণ নেটওয়ার্কের বাইরে যায় না।
* **AirEngine সীমাহীন মেমরি**: VRAM, RAM এবং NVMe স্টোরেজের মাধ্যমে বিশালাকার মডেলগুলো নির্বিঘ্নে চলে।

---

### Pip & Installer Command Matrix

| কমান্ড | উদ্দেশ্য | টার্গেট কম্পোনেন্ট |
|---|---|---|
| `lmms install` | ইন্টারেক্টিভ আর্কিটেকচার সেটআপ উইজার্ড চালু করুন | ইন্টারেক্টিভ কনফিগারেশন মেনু |
| `lmms install --all` | সম্পূর্ণ ইকোসিস্টেম ইনস্টল করুন | ডেস্কটপ স্টুডিও, CLI, ভয়েস, সুপার ইঞ্জিন |
| `lmms install --gui` | ডেস্কটপ স্টুডিও (GUI) ইনস্টল করুন | PyQt6 GUI, মোনাকো এডিটর, ইঞ্জিন ক্লায়েন্ট |
| `lmms install --cli` | টার্মিনাল স্টুডিও (CLI) ইনস্টল করুন | ইন্টারেক্টিভ শেল, ডেভ টুলস, ইঞ্জিন ক্লায়েন্ট |
| `lmms install --engine` | সুপার ইঞ্জিন রানটাইম ইনস্টল করুন | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | লাইটওয়েট ইঞ্জিন ইনস্টল করুন | llama.cpp + AirEngine (GGUF ডেডিকেটেড) |
| `lmms install --engine2` | PyTorch নেটিভ ইঞ্জিন ইনস্টল করুন | PyTorch + Transformers + AirEngine |
| `lmms install --host` | এন্টারপ্রাইজ কেন্দ্রীয় হোস্ট ডেমন ইনস্টল করুন | সেন্ট্রাল সার্ভার ডেমন 0.0.0.0:11435 এ চলমান |
| `lmms install --client-gui` | এন্টারপ্রাইজ ডেস্কটপ ক্লায়েন্ট ইনস্টল করুন | দূরবর্তী হোস্টের সাথে সংযোগকারী GUI |
| `lmms install --client-cli` | এন্টারপ্রাইজ টার্মিনাল ক্লায়েন্ট ইনস্টল করুন | দূরবর্তী হোস্টের সাথে সংযোগকারী CLI |
| `lmms update` | সর্বশেষ সোর্স কোড ডাউনলোড ও আপডেট করুন | বর্তমান সক্রিয় ব্রাঞ্চের আপডেট |
| `lmms update --all` | সব ব্রাঞ্চে বাধ্যতামূলক পূর্ণাঙ্গ আপডেট | GitHub রিপোজিটরির সাথে সম্পূর্ণ সিঙ্ক |
| `lmms -check` | হার্ডওয়্যার ডায়াগনস্টিকস এবং পূর্বশর্ত পরীক্ষা | CPU, GPU, VRAM, AVX এবং ডিস্ক টেলিমেট্রি |
| `lmms-uninstall -all` | নিরাপদে সোর্স কোড আনইনস্টল করুন | কোড মুছে ফেলে, pip প্যাকেজ ও মডেল ক্যাশ রাখে |
| `lmms-uninstall -all --purge` | ফ্যাক্টরি রিসেট ও সম্পূর্ণ পরিচ্ছন্নতা | সমস্ত কনফিগারেশন, মডেল এবং ডেটা স্থায়ীভাবে মোছা |

---

## মূল কমান্ড নির্দেশিকা (Core Command Reference)

### LMMs Core Launcher Commands

| কমান্ড | বিবরণ |
|---|---|
| `lmms` | কনফিগার করা ডিফল্ট ইন্টারফেস চালু করুন |
| `lmms --gui` | ডেস্কটপ GUI স্টুডিও সরাসরি চালু করুন |
| `lmms --cli` | ডেভেলপার CLI শেল সরাসরি চালু করুন |
| `lmms --engine` | ইনফারেন্স ইঞ্জিন ডেমন সরাসরি চালু করুন |
| `lmms set --gui` | ডেস্কটপ স্টুডিওকে ডিফল্ট লঞ্চ মোড হিসেবে সেট করুন |
| `lmms set --cli` | টার্মিনাল স্টুডিওকে ডিফল্ট লঞ্চ মোড হিসেবে সেট করুন |
| `lmms set --engine` | ইঞ্জিন ডেমনকে ডিফল্ট লঞ্চ মোড হিসেবে সেট করুন |
| `lmms stop` | চলমান ব্যাকগ্রাউন্ড LMMs ইঞ্জিন ডেমন নিরাপদে বন্ধ করুন |
| `lmms --help` | লঞ্চারের বিস্তারিত সহায়তা নির্দেশিকা দেখুন |

---

### ইঞ্জিন রানটাইম এবং মডেল পরিচালনা

| কমান্ড | বিবরণ |
|---|---|
| `lmms run <model>` | ইন্টারেক্টিভ চ্যাট বা একক প্রম্পটে মডেল চালান |
| `lmms stop <model>` | চলমান সক্রিয় মডেলের ইন্সট্যান্স বন্ধ করুন |
| `lmms list` | স্থানীয়ভাবে ডাউনলোড করা মডেলের তালিকা দেখুন |
| `lmms ps` | চলমান মডেল, মেমরি বরাদ্দ এবং VRAM স্ট্যাটাস দেখুন |
| `lmms pull <model>` | Hugging Face বা অফিসিয়াল হাব থেকে মডেল ডাউনলোড করুন |
| `lmms info <model>` | মডেল মেটাডেটা, কনটেক্সট উইন্ডো এবং কোয়ান্টাইজেশন দেখুন |
| `lmms rm <model>` | স্থানীয়ভাবে সংরক্ষিত মডেল মুছে ফেলুন |
| `lmms search <query>` | উপলব্ধ ওপেন সোর্স মডেল সংগ্রহস্থলে অনুসন্ধান করুন |
| `lmms benchmark <model>` | টোকেন জেনারেশন স্পিড (t/s) এবং লেটেন্সি পরিমাপ করুন |
| `lmms doctor [--fix]` | স্বাস্থ্য পরীক্ষা চালান, ছোট সমস্যা স্বয়ংক্রিয়ভাবে সমাধান করুন এবং CUDA যাচাই করুন |
| `lmms create <model> -f <file>` | GGUF বা Safetensors ফাইল থেকে কাস্টম মডেল রেজিস্টার করুন |

---

### Air Engine (বুদ্ধিমান RAM/VRAM অদলবদল)

গতিশীল হাইব্রিড GPU/CPU/ডিস্ক অফলোডিং ব্যবহার করে ফিজিক্যাল VRAM ছাড়িয়ে যাওয়া বিশাল মডেলগুলি চালান।

| কমান্ড | বিবরণ |
|---|---|
| `lmms -air run <model> [prompt]` | Air মেমরি ডায়নামিক অফলোডিং সহ বিশাল মডেল চালান |
| `lmms --air run <m1> <m2>` | Air শিডিউলারের মাধ্যমে একাধিক মডেল একসাথে চালান |
| `lmms air ps` | সক্রিয় Air সেশন এবং GPU/CPU লেয়ার বরাদ্দ পর্যবেক্ষণ করুন |
| `lmms air stats` | রিয়েল-টাইম হার্ডওয়্যার টেলিমেট্রি এবং অফলোড পরিসংখ্যান দেখুন |
| `lmms air cache` | Air ডিস্ক ক্যাশের আকার এবং স্টোরেজ ব্যবহার পরীক্ষা করুন |
| `lmms air unload` | সমস্ত Air মডেল আনলোড করুন এবং অবিলম্বে VRAM ক্যাশ খালি করুন |
| `lmms air benchmark <model>` | Air শিডিউলারের অধীনে প্রসেসিং গতি পরিমাপ করুন |

---

### Server / Daemon

| কমান্ড | বিবরণ |
|---|---|
| `lmms server` | API / ওয়েব সার্ভার ডেমন শুরু করুন |
| `lmms server status` | সার্ভারের অবস্থা, পোর্ট, আপটাইম এবং স্বাস্থ্য পরীক্ষা করুন |
| `lmms engine status` | সক্রিয় ইঞ্জিন মোড এবং মেমরি পরিসংখ্যান দেখুন |
| `lmms engine unload [model]` | মেমরি থেকে মডেল আনলোড করুন এবং VRAM খালি করুন |
| `lmms server start [--port 11435]` | নির্দিষ্ট পোর্টে ব্যাকগ্রাউন্ড FastAPI সার্ভার চালু করুন |
| `lmms server stop` | চলমান ব্যাকগ্রাউন্ড সার্ভার ডেমন বন্ধ করুন |

---

## ইন্টারেক্টিভ CLI স্ল্যাশ কমান্ডসমূহ

| কমান্ড | বিবরণ |
|---|---|
| `/fast` | দ্রুত প্রতিক্রিয়া এবং হালকা টুলের জন্য FAST মোডে পরিবর্তন করুন |
| `/deep` | গভীর যুক্তি এবং সম্পূর্ণ টুল অ্যাক্সেসের জন্য DEEP মোডে পরিবর্তন করুন |
| `/model <name>` | বর্তমান কথোপকথনের জন্য অন্য একটি মডেলে পরিবর্তন করুন |
| `/ml -l` | ডাউনলোড করা সমস্ত লোকাল মডেলের তালিকা চ্যাটের ভেতর দেখুন |
| `/ml -s <name>` | কথোপকথনের প্রসঙ্গ অক্ষুণ্ণ রেখে তাত্ক্ষণিক মডেল পরিবর্তন করুন |
| `/folder <path>` | এজেন্টের কাজের প্রসঙ্গের সাথে একটি ডিরেক্টরি সংযুক্ত করুন |
| `/code` | কোড তৈরি এবং স্বয়ংক্রিয় প্যাচিং মোডে প্রবেশ করুন |
| `/chat` | পূর্ববর্তী চ্যাট সেশনগুলির ইতিহাস দেখুন এবং পর্যালোচনা করুন |
| `/newchat` | একটি সম্পূর্ণ নতুন ও পরিষ্কার চ্যাট সেশন শুরু করুন |
| `/chat -r <id> <name>` | একটি নির্দিষ্ট চ্যাট সেশনের নাম পরিবর্তন করুন |
| `/chat -d <id>` | একটি নির্দিষ্ট চ্যাট সেশন স্থায়ীভাবে মুছে ফেলুন |
| `/undo` | এআই দ্বারা করা সর্বশেষ ফাইল পরিবর্তন বা প্যাচ নিরাপদে বাতিল করুন |
| `/redo` | বাতিল করা ফাইল সম্পাদনা পুনরায় প্রয়োগ করুন |
| `/exit` | ইন্টারেক্টিভ CLI সেশন থেকে নিরাপদে প্রস্থান করুন |
| `/reboot` | ব্যাকএন্ড ইঞ্জিন রিবুট করুন এবং সেশন পুনরায় সংযুক্ত করুন |
| `/mic` | মাইক্রোফোন থেকে ভয়েস রেকর্ড করুন এবং সরাসরি টেক্সটে রূপান্তর করুন |
| `/vision বা /image` | ছবি বিশ্লেষণ এবং UI পরিদর্শনের জন্য মাল্টিমোডাল ভিশন মোডে যান |
| `/research` | ওয়েব ও টেকনিক্যাল ডকুমেন্টেশন অনুসন্ধানের জন্য রিসার্চ মোডে যান |
| `/read <file>` | ওয়ার্কস্পেসের যেকোনো ফাইল সরাসরি চ্যাট প্রসঙ্গে লোড করুন |
| `/task` | ব্যাকগ্রাউন্ডের স্বায়ত্তশাসিত সাব-টাস্ক এবং লক্ষ্য পরিচালনা করুন |
| `/git` | এজেন্টের মাধ্যমে নিরীক্ষিত ও নিরাপদ Git অপারেশন পরিচালনা করুন |
| `/scope` | টুল এক্সিকিউশনের অনুমতির পরিধি পর্যালোচনা ও পরিবর্তন করুন |
| `/tools list` | উপলব্ধ সমস্ত নেটিভ টুল এবং সক্রিয় MCP এন্ডপয়েন্ট দেখুন |
| `/report` | ক্রিপ্টোগ্রাফিকভাবে স্বাক্ষরিত নিরাপত্তা ও কর্ম নিরীক্ষা রিপোর্ট তৈরি করুন |
| `/checkpoint` | ওয়ার্কস্পেসের বর্তমান অবস্থার একটি অপরিবর্তনীয় চেকপয়েন্ট সংরক্ষণ করুন |
| `/checkpoints` | সংরক্ষিত সমস্ত ওয়ার্কস্পেস চেকপয়েন্টের তালিকা প্রদর্শন করুন |
| `/rollback` | রিপোজিটরি ও ফাইলগুলিকে পূর্বের সংরক্ষিত চেকপয়েন্টে ফিরিয়ে নিন |
| `/status` | ইঞ্জিন এবং সিস্টেম হার্ডওয়্যারের রিয়েল-টাইম স্বাস্থ্য যাচাই করুন |
| `/doctor` | সিস্টেমের সামগ্রিক ডায়াগনস্টিকস এবং স্বয়ংক্রিয় মেরামতের টুল চালান |
| `/pair` | ইন্টারেক্টিভ পেয়ার-প্রোগ্রামিং মোড চালু করুন |
| `/perm <level>` | স্যান্ডবক্স অনুমতির স্তর সমন্বয় করুন (`strict`, `ask`, `full`) |
| `/agent` | সমান্তরাল কাজের জন্য স্বায়ত্তশাসিত সাব-এজেন্ট তৈরি ও পরিচালনা করুন |
| `/orchestrate` | একাধিক এজেন্টের সমন্বিত কাজের প্রক্রিয়া পরিচালনা করুন |

---

## পণ্য দর্শন (Product Philosophy)

1. **বাস্তব উপযোগিতা সর্বাগ্রে**: ফাইল প্যাচিং, AST যাচাইকরণ এবং সুরক্ষিত স্যান্ডবক্সিং।
2. **সততা ও স্বচ্ছতা**: কোনো ট্র্যাকিং বা টেলিমেট্রি নেই, কোনো গোপন চার্জ নেই।
3. **খাঁটি লোকাল-ফার্স্ট**: সমস্ত মডেল, ওজন এবং কোড সর্বদা আপনার নিজস্ব ডিভাইসে সুরক্ষিত।
4. **স্বচ্ছ আর্কিটেকচার**: অতিরিক্ত বোঝা ছাড়া খাঁটি পাইথনে নির্মিত অবকাঠামো।

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
