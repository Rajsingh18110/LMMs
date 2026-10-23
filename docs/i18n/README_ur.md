<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>ماڈلز کے ساتھ تعمیر کریں۔ ایجنٹس کے ساتھ لانچ کریں۔</strong><br>
  <em>بانی راج سنگھ (MarkanM) کا تیار کردہ ازخود پائتھن پر مبنی مقامی AI آپریٹنگ سسٹم</em>
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
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](README_mr.md)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](#)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">سرکاری ویب سائٹ</a> ·
  <a href="#system-architecture">سسٹم کا ڈھانچہ</a> ·
  <a href="#deep-technical-capabilities">بنیادی صلاحیتیں</a> ·
  <a href="#quick-start">فوری آغاز</a> ·
  <a href="#architecture-setup-wizard-lmms-install">تنصیب کا رہنما</a> ·
  <a href="#enterprise-infrastructure--super-host">انٹرپرائز</a> ·
  <a href="#core-command-reference">کمانڈز کی فہرست</a> ·
  <a href="#cli-slash-commands">سلیش کمانڈز</a> ·
  <a href="#license">لائسنس</a>
</p>

---

## LMMs OS کیا ہے؟

LMMs مقامی اور ریموٹ ماڈل پروسیسنگ کے لیے پائتھن پر مبنی ایک مقامی AI آپریٹنگ لیئر ہے۔ بانی راج سنگھ (MarkanM) کا ڈیزائن کردہ یہ سسٹم ایک مکمل ڈیسک ٹاپ GUI سٹوڈیو، سمارٹ ڈویلپر CLI، اور بالغ ترین انجن رن ٹائم کو یکجا کرتا ہے تاکہ ڈویلپرز بغیر کسی کلاؤڈ انحصار اور بغیر کسی ٹیلی میٹری کے بڑے ملٹی ماڈل ماڈلز چلا سکیں۔

* **مقامی ڈوئل انجن کور**: llama.cpp کے ذریعے تیز رفتار کوانٹائزڈ GGUF انفرنس اور PyTorch کے ذریعے حقیقی safetensors پروسیسنگ۔
* **AirEngine کے ساتھ لامحدود وسعت**: GPU، CPU اور ڈسک کے درمیان متحرک ٹینسر آف لوڈنگ عام لیپ ٹاپس پر بھی 70B+ ماڈلز چلانے کی صلاحیت دیتی ہے۔
* **ڈیسک ٹاپ سٹوڈیو (GUI)**: موناكو کوڈ ایڈیٹر، بصری diff تقابل، Git انٹیگریشن اور بلٹ ان ٹول مینیجر۔
* **ٹرمینل سٹوڈیو (CLI)**: 30 سے زیادہ سلیش کمانڈز، جوڑی دار پروگرامنگ، ذیلی ایجنٹس کی ہم آہنگی اور محفوظ سینڈ باکس۔
* **انٹرپرائز ریڈی**: نجی LAN/VPC نیٹ ورکس پر مرکزی میزبان اور خودکار تلاش کے ساتھ تقسیم شدہ کلسٹر۔

---

## سسٹم کا ڈھانچہ (System Architecture)

درج ذیل خاکہ LMMs OS کے یوزر انٹرفیس، بیک اینڈ سروسز، ماڈل انفرنس اور ایجنٹ صلاحیتوں کے جامع نظام کو واضح کرتا ہے:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **صارف کے انٹرفیس**: `GUI workspace [main_window.py]` (موناكو ایڈیٹر اور کوڈ جائزہ) اور `CLI [commands.py]` (انٹرایکٹو ڈویلپر ٹرمینل)۔
2. **API اور بیک اینڈ کی سطح**: `HTTP API [server.py]` (پورٹ 11435 پر FastAPI سرور)، `Backend session [main.py]` (سیشن کوآرڈینیٹر)، اور `Backend services [manager.py]`۔
3. **ماڈل انفرنس سب سسٹم**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (ٹینسر آف لوڈنگ)، `Model registry [registry.py]`, `llama.cpp انجن` اور `PyTorch انجن`۔
4. **ایجنٹ صلاحیتوں کا سب سسٹم**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` اور `Workspace & Git [manager.py]`۔

---

## گہری تکنیکی صلاحیتیں (Deep Technical Capabilities)

### 1. ملٹی ماڈل ویژن انجن (`/vision` یا `/image`)
LMMs میں مقامی انجن کے اندر براہ راست بصری پروسیسنگ کی صلاحیت موجود ہے:
* **UI اور لے آؤٹ کا تجزیہ**: بصری نقائص اور CSS رینڈرنگ کی غلطیوں کو پکڑنے کے لیے ویب یا ڈیسک ٹاپ سکرین شاٹس کی جانچ۔
* **ڈھانچے اور خاکوں کا اخراج**: فلو چارٹس، ER خاکوں اور UML تسلسل کا تجزیہ کر کے براہ راست کارآمد Mermaid کوڈ میں تبدیلی۔
* **مقامی دستاویزات کا OCR**: بغیر کسی بیرونی سرور پر تصویر بھیجے براہ راست ڈیوائس سے متن اور جدول کا محفوظ اخراج۔

### 2. آف لائن آواز اور آڈیو ان پٹ (`/mic`)
* **مقامی آواز سے متن کی تبدیلی**: کوانٹائزڈ مقامی Whisper ماڈلز کے ذریعے بغیر انٹرنیٹ کے انتہائی تیز آواز کی تحریر۔
* **ہینڈز فری ہدایات**: بغیر کسی نیٹ ورک تاخیر کے براہ راست فعال CLI سیشن میں اپنی آواز کے ذریعے کوڈنگ ہدایات ریکارڈ کریں۔

### 3. Git آگاہی اور Worktree تنہائی (`/git` یا `/scope`)
* **صرف پڑھنے کی حفاظت کا ضامن**: واضح اجازت کے بغیر ایجنٹ کی کارروائیوں کو صرف محفوظ کمانڈز (`cat`, `git diff`, `grep`) تک محدود رکھتا ہے۔
* **عارضی Git Worktrees**: کوڈ کی تبدیلیاں الگ کلون میں انجام پاتی ہیں اور تمام خودکار ٹیسٹ پاس ہونے کے بعد ہی اصل برانچ میں شامل ہوتی ہیں۔
* **رنگین Diff پیش منظر**: ڈسک پر فائل محفوظ کرنے سے پہلے رنگین اور واضح فرق پیش کرتا ہے۔

### 4. حتمی بحالی پوائنٹس اور فوری واپسی (`/checkpoint` یا `/rollback` یا `/undo`)
* **قدم بہ قدم بیک اپ**: فائل میں تبدیلی سے قبل فائلز کا ایک مستقل بیک اپ محفوظ کر لیا جاتا ہے۔
* **ملی سیکنڈز میں بحالی**: اگر کوئی کوڈ پیچ خرابی پیدا کرے تو `/rollback` یا `/undo` کے ذریعے کوڈ فوراً اپنی سابقہ محفوظ حالت میں آ جاتا ہے۔

### 5. خود مختار ذیلی ایجنٹس اور کثیر ایجنٹ نظام (`/agent` یا `/orchestrate`)
* **پس منظر کے خود مختار کام**: مخصوص ٹوکن بجٹ اور فائل اجازتوں کے ساتھ الگ ذیلی ایجنٹس کو متوازی کام کے لیے چلانا۔
* **مربوط انتظام**: مرکزی آرکیسٹریٹر مخصوص کام (ٹیسٹنگ، دستاویزات) ذیلی ایجنٹس کو سونپتا ہے اور نتائج کو یکجا کرتا ہے۔

### 6. مقامی تحقیق اور ویکٹر میموری RAG (`/research`)
* **کوڈ بیس کی ویکٹر انڈیکسنگ**: فنکشنز اور کلاسز کی تیز ترین تلاش کے لیے پروجیکٹ کی فائلوں کو مقامی ویکٹر ڈیٹا بیس میں محفوظ کرنا۔
* **بے بنیاد معلومات سے پاک دستاویزات**: غلط معلومات سے بچنے کے لیے مقامی اور ویب API دستاویزات کا براہ راست مطالعہ۔

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

## سسٹم تنصیب کا رہنما (`lmms install`)

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

### [1] انفرادی ورک سٹیشن کی تشکیل

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

### [2] انٹرپرائز انفراسٹرکچر اور سپر ہوسٹ

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **مرکزی طاقتور کمپیوٹنگ**: ہوسٹ سرور کمپنی کے مرکزی GPU سرور (`0.0.0.0:11435`) پر چلتا ہے جو نجی ماڈلز کی تربیت اور سروس فراہم کرتا ہے۔
* **ریموٹ کلائنٹ سٹوڈیوز**: ٹیم کے اراکین اپنے ذاتی لیپ ٹاپس سے LAN/VPC کے ذریعے خودکار تلاش سے جڑ جاتے ہیں۔
* **مکمل ڈیٹا پرائیویسی**: کوئی بھی کوڈ یا ہدایت کمپنی کے داخلی محفوظ نیٹ ورک سے باہر نہیں جاتی۔
* **AirEngine لامحدود میموری**: VRAM، RAM اور تیز ترین NVMe سٹوریج کے ذریعے انتہائی بڑے ماڈلز روانی سے چلتے ہیں۔

---

### Pip & Installer Command Matrix

| کمانڈ | مقصد | ہدف جزو |
|---|---|---|
| `lmms install` | انٹرایکٹو سسٹم آرکیٹیکچر سیٹ اپ وزرڈ چلائیں | انٹرایکٹو کنفیگریشن مینو |
| `lmms install --all` | مکمل ایکو سسٹم انسٹال کریں | ڈیسک ٹاپ سٹوڈیو، CLI، آواز، سپر انجن |
| `lmms install --gui` | ڈیسک ٹاپ سٹوڈیو (GUI) انسٹال کریں | PyQt6 انٹرفیس، موناكو ایڈیٹر، کلائنٹ |
| `lmms install --cli` | ٹرمینل سٹوڈیو (CLI) انسٹال کریں | انٹرایکٹو شیل، ڈویلپر ٹولز، کلائنٹ |
| `lmms install --engine` | سپر انجن رن ٹائم انسٹال کریں | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | ہلکا پھلکا انجن انسٹال کریں | llama.cpp + AirEngine (صرف GGUF کے لیے) |
| `lmms install --engine2` | PyTorch نیٹو انجن انسٹال کریں | PyTorch + Transformers + AirEngine |
| `lmms install --host` | انٹرپرائز مرکزی ہوسٹ سرور انسٹال کریں | مرکزی سرور 0.0.0.0:11435 پر فعال |
| `lmms install --client-gui` | انٹرپرائز ڈیسک ٹاپ کلائنٹ انسٹال کریں | ریموٹ ہوسٹ سے جڑنے والا GUI |
| `lmms install --client-cli` | انٹرپرائز ٹرمینل کلائنٹ انسٹال کریں | ریموٹ ہوسٹ سے جڑنے والا CLI |
| `lmms update` | تازہ ترین کوڈ ڈاؤن لوڈ اور اپ ڈیٹ کریں | موجودہ برانچ کی اپ ڈیٹ |
| `lmms update --all` | تمام برانچز پر مکمل اور لازمی اپ ڈیٹ | GitHub سے مکمل ہم آہنگی |
| `lmms -check` | ہارڈ ویئر کی تشخیص اور ضروریات کی جانچ | CPU، GPU، VRAM، AVX اور ڈسک کی صورتحال |
| `lmms-uninstall -all` | سورورس کوڈ کو محفوظ طریقے سے حذف کریں | کوڈ ہٹاتا ہے، pip پیکجز اور ماڈلز محفوظ رکھتا ہے |
| `lmms-uninstall -all --purge` | مکمل فیکٹری ری سیٹ اور صفائی | تمام سیٹنگز، ماڈلز اور ڈیٹا کو مستقل طور پر مٹائیں |

---

## بنیادی کمانڈز کا رہنما (Core Command Reference)

### LMMs Core Launcher Commands

| کمانڈ | تفصیل |
|---|---|
| `lmms` | طے شدہ ڈیفالٹ انٹرفیس شروع کریں |
| `lmms --gui` | ڈیسک ٹاپ GUI سٹوڈیو براہ راست شروع کریں |
| `lmms --cli` | ڈویلپر CLI شیل براہ راست شروع کریں |
| `lmms --engine` | انفرنس انجن سرور براہ راست شروع کریں |
| `lmms set --gui` | ڈیسک ٹاپ سٹوڈیو کو ڈیفالٹ موڈ بنائیں |
| `lmms set --cli` | ٹرمینل سٹوڈیو کو ڈیفالٹ موڈ بنائیں |
| `lmms set --engine` | انجن سرور کو ڈیفالٹ موڈ بنائیں |
| `lmms stop` | پس منظر میں چلتے ہوئے LMMs انجن کو محفوظ طریقے سے روکیں |
| `lmms -check` | ہارڈ ویئر پروفائل اور تقاضوں کی تصدیق کریں |
| `lmms update` | موجودہ برانچ سے اسمارٹ اپ ڈیٹ کریں |
| `lmms update --all` | GitHub سے تمام اجزاء کو مکمل اپ ڈیٹ کریں |
| `lmms --help` | لانچر کی مکمل امدادی گائیڈ دیکھیں |

---

### Engine Runtime & Air Engine

| کمانڈ | تفصیل |
|---|---|
| `lmms run <model>` | انٹرایکٹو چیٹ یا انفرادی پرامپٹ میں ماڈل چلائیں |
| `lmms list` | مقامی طور پر ڈاؤن لوڈ کردہ ماڈلز کی فہرست دیکھیں |
| `lmms ps` | فعال ماڈلز، میموری کی تقسیم اور VRAM کی حالت دیکھیں |
| `lmms pull <model>` | Hugging Face یا سرکاری ہب سے ماڈل ڈاؤن لوڈ کریں |
| `lmms info <model>` | ماڈل میٹا ڈیٹا، سیاق و سباق کی حد اور کوانٹائزیشن دیکھیں |
| `lmms search <query>` | دستیاب اوپن سورس ماڈل ریپوزٹریز میں تلاش کریں |
| `lmms benchmark <model>` | ٹوکن پیدا کرنے کی رفتار (t/s) اور تاخیر کی پیمائش کریں |
| `lmms doctor` | انجن کی صحت اور CUDA ڈرائیورز کی حالت جانچیں |
| `lmms create <model> -f <file>` | GGUF یا Safetensors فائل سے کسٹم ماڈل درج کریں |
| `lmms -air run <model> [prompt]` | Air میموری آف لوڈنگ کے ساتھ بہت بڑے ماڈلز چلائیں |
| `lmms --air run <m1> <m2>` | Air شیڈیولر کے ذریعے ایک ساتھ متعدد ماڈلز چلائیں |
| `lmms air ps` | فعال Air سیشنز اور GPU/CPU تہوں کی تقسیم کی نگرانی کریں |
| `lmms air stats` | ریئل ٹائم ہارڈ ویئر اور آف لوڈ کے اعداد و شمار دیکھیں |
| `lmms air cache` | Air ڈسک کیشے کے حجم اور استعمال کا جائزہ لیں |
| `lmms air unload` | تمام Air ماڈلز بند کریں اور فوراً VRAM کیشے خالی کریں |
| `lmms air benchmark <model>` | Air شیڈیولر کے تحت پروسیسنگ کی رفتار ماپیں |

---

### Server / Daemon

| کمانڈ | تفصیل |
|---|---|
| `lmms server` | API / ویب سرور ڈیمن شروع کریں |
| `lmms server status` | سرور کی حالت، پورٹ، اپ ٹائم اور صحت کی تصدیق کریں |
| `lmms engine status` | فعال انجن موڈ اور میموری کے اعداد و شمار دیکھیں |
| `lmms engine unload [model]` | میموری سے ماڈلز کو ہٹا کر VRAM آزاد کریں |
| `lmms server start [--port 11435]` | مخصوص پورٹ پر بیک گراؤنڈ FastAPI سرور چلائیں |
| `lmms server stop` | چلتے ہوئے بیک گراؤنڈ سرور کو روکیں |

---

## انٹرایکٹو CLI سلیش کمانڈز

| کمانڈ | تفصیل |
|---|---|
| `/fast` | تیز رفتار جوابات اور ہلکے ٹولز کے لیے FAST موڈ پر جائیں |
| `/deep` | گہری سوچ اور مکمل ٹول رسائی کے لیے DEEP موڈ پر جائیں |
| `/model <name>` | موجودہ گفتگو کے لیے دوسرا ماڈل منتخب کریں |
| `/ml -l` | ڈاؤن لوڈ کردہ تمام مقامی ماڈلز کی فہرست چیٹ میں دیکھیں |
| `/ml -s <name>` | گفتگو کا سیاق و سباق کھوئے بغیر فوری ماڈل تبدیل کریں |
| `/folder <path>` | ایجنٹ کے کام کے دائرہ کار کے ساتھ ایک فولڈر منسلک کریں |
| `/code` | کوڈ بنانے اور ترمیم کرنے کے مخصوص موڈ میں داخل ہوں |
| `/chat` | سابقہ چیٹ سیشنز کی فہرست دیکھیں اور جائزہ لیں |
| `/newchat` | ایک نیا اور بالکل صاف چیٹ سیشن شروع کریں |
| `/chat -r <id> <name>` | کسی مخصوص چیٹ سیشن کا نام تبدیل کریں |
| `/chat -d <id>` | کسی مخصوص چیٹ سیشن کو مستقل طور پر حذف کریں |
| `/undo` | AI کی طرف سے کی گئی آخری فائل تبدیلی کو محفوظ طور پر واپس لیں |
| `/redo` | واپس لی گئی فائل ترمیم کو دوبارہ نافذ کریں |
| `/exit` | انٹرایکٹو CLI سیشن سے محفوظ طریقے سے باہر نکلیں |
| `/reboot` | بیک اینڈ انجن کو دوبارہ شروع کریں اور سیشن بحال کریں |
| `/mic` | مائیکروفون سے آواز ریکارڈ کریں اور براہ راست متن میں تبدیل کریں |
| `/vision یا /image` | تصویری تجزیے اور انٹرفیس کی جانچ کے لیے ویژن موڈ پر جائیں |
| `/research` | ویب اور تکنیکی دستاویزات کی تحقیق کے لیے ریسرچ موڈ پر جائیں |
| `/read <file>` | پروجیکٹ کی کوئی بھی فائل براہ راست سیشن میں پڑھیں |
| `/task` | پس منظر کے خود مختار کاموں اور اہداف کا انتظام کریں |
| `/git` | ایجنٹ کے ذریعے محفوظ اور تصدیق شدہ Git آپریشنز چلائیں |
| `/scope` | ٹول چلانے کی اجازتوں کی حدود کا جائزہ لیں اور تبدیلی کریں |
| `/tools list` | تمام مقامی ٹولز اور فعال MCP سرورز کی فہرست دیکھیں |
| `/report` | سیکیورٹی اور آڈٹ کی تفصیلی رپورٹ تیار کریں |
| `/checkpoint` | موجودہ کام کا ایک ناقابل تبدیلی بحالی پوائنٹ بنائیں |
| `/checkpoints` | محفوظ شدہ تمام بحالی پوائنٹس کی فہرست دیکھیں |
| `/rollback` | کوڈ اور فائلوں کو پچھلے بحالی پوائنٹ پر واپس لے جائیں |
| `/status` | انجن اور ہارڈ ویئر کی ریئل ٹائم صحت کی جانچ کریں |
| `/doctor` | سسٹم کی مکمل جانچ اور خودکار مرمت کے ٹیسٹ چلائیں |
| `/pair` | انٹرایکٹو جوڑی دار پروگرامنگ موڈ فعال کریں |
| `/perm <level>` | سینڈ باکس اجازت کی سطح سیٹ کریں (`strict`, `ask`, `full`) |
| `/agent` | متوازی کاموں کے لیے خود مختار ذیلی ایجنٹس بنائیں اور چلائیں |
| `/orchestrate` | متعدد ایجنٹس کے درمیان مربوط ورک فلو کا انتظام کریں |

---

## پروڈکٹ کا فلسفہ (Product Philosophy)

1. **حقیقی افادیت سب سے پہلے**: حقیقی فائل پیچنگ، AST کی تصدیق اور محفوظ سینڈ باکس۔
2. **دیانت داری اور مکمل شفافیت**: کوئی ٹریکنگ یا ٹیلی میٹری نہیں، کوئی پوشیدہ فیس نہیں۔
3. **خالصتاً مقامی اولیت**: آپ کے تمام ماڈلز، وزن اور کوڈ ہمیشہ آپ کے ذاتی آلات پر محفوظ رہتے ہیں۔
4. **صاف اور شفاف فن تعمیر**: اضافی بوجھ کے بغیر خالص پائتھن پر مبنی ڈھانچہ۔

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
