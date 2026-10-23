<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>ابنِ باستخدام النماذج. أطلق باستخدام الوكلاء.</strong><br>
  <em>نظام تشغيل الذكاء الاصطناعي المحلي المبني بلغة بايثون من قبل المؤسس راج سينغ (MarkanM)</em>
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
[![العربية](https://img.shields.io/badge/Language-العربية-059669?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">الموقع الرسمي</a> ·
  <a href="#system-architecture">بنية النظام</a> ·
  <a href="#deep-technical-capabilities">القدرات الأساسية</a> ·
  <a href="#quick-start">البدء السريع</a> ·
  <a href="#architecture-setup-wizard-lmms-install">معالج التثبيت</a> ·
  <a href="#enterprise-infrastructure--super-host">المؤسسات</a> ·
  <a href="#core-command-reference">مرجع الأوامر</a> ·
  <a href="#cli-slash-commands">أوامر سلاش</a> ·
  <a href="#license">الترخيص</a>
</p>

---

## ما هو نظام LMMs OS؟

LMMs هي طبقة تشغيل ذكاء اصطناعي أصلية بلغة بايثون لتشغيل النماذج محلياً وعن بُعد. تم تصميمها بواسطة راج سينغ (MarkanM)، وتجمع بين واجهة رسومية حقيقية لسطح المكتب، وواجهة سطر أوامر ذكية، ومحرك تشغيل ناضج لتشغيل النماذج الكبيرة متعددة الوسائط بدون أي تتبع أو قيود سحابية.

* **محرك ثنائي النواة أصلي**: استدلال كمي عالي السرعة بصيغة GGUF عبر llama.cpp وتشغيل نماذج safetensors عبر PyTorch.
* **توسع غير محدود عبر AirEngine**: تفريغ الموترات ديناميكياً بين كرت الشاشة والمعالج والقرص لتشغيل نماذج 70B+ حتى على الحواسيب المحمولة العادية.
* **استوديو سطح المكتب (GUI)**: محرر أكواد Monaco، ومقارنة بصرية للتعديلات diff، وتكامل مع Git وإدارة الأدوات البرمجية.
* **استوديو الطرفية (CLI)**: صدفة تفاعلية مع أكثر من 30 أمر سلاش، والبرمجة الثنائية، وتنسيق الوكلاء الفرعيين، وبيئة معزولة آمنة.
* **جاهز لبيئات المؤسسات**: بنية عميل-خادم موزعة عبر الشبكات الخاصة LAN/VPC مع اكتشاف تلقائي للمضيف المركزي.

---

## بنية النظام (System Architecture)

يوضح المخطط التالي البنية الشاملة لنظام LMMs OS عبر الأنظمة الفرعية للواجهات والخدمات الخلفية والاستدلال والوكلاء:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **واجهات المستخدم**: `GUI workspace [main_window.py]` (بيئة Monaco لمراجعة الأكواد) و `CLI [commands.py]` (الطرفية التفاعلية للمطورين).
2. **واجهة البرمجة والطبقة الخلفية**: `HTTP API [server.py]` (خادم FastAPI على المنفذ 11435)، و `Backend session [main.py]` (منسق الجلسات)، و `Backend services [manager.py]`.
3. **نظام الاستدلال للنماذج**: `Runtime selection [manager.py]`، و `AirEngine [runtime.py]` (تفريغ الموترات للذاكرة والقرص)، و `Model registry [registry.py]`، و `محرك llama.cpp` و `محرك PyTorch`.
4. **نظام قدرات الوكلاء**: `Request orchestration [pipeline.py]`، و `Vector retrieval [rag.py]`، و `Agent routing [manager.py]`، و `Tool execution [executor.py]`، و `Session memory [core_memory.py]`، و `Web research [engine.py]`، و `Workspace & Git [manager.py]`.

---

## القدرات التقنية العميقة (Deep Technical Capabilities)

### 1. محرك الرؤية متعدد الوسائط (`/vision` أو `/image`)
يتضمن LMMs معالجة بصرية متعددة الوسائط داخل المحرك المحلي مباشرة:
* **تحليل الواجهات والتخطيط**: فحص لقطات الشاشة لواجهات الويب أو سطح المكتب لاكتشاف الأخطاء البصرية وعيوب تنسيق CSS.
* **استخراج المخططات وهندسة النظم**: تحليل المخططات الانسيابية ومخططات العلاقات ER وتسلسلات UML وتحويلها مباشرة إلى كود Mermaid.
* **التعرف الضوئي على النصوص (OCR)**: استخراج النصوص والجداول بدقة من الصور ومستندات PDF محلياً دون إرسال البيانات خارج جهازك.

### 2. الصوت والأوامر الصوتية بدون إنترنت (`/mic`)
* **تحويل الكلام إلى نص محلياً**: نسخ صوتي فائق السرعة عبر نماذج Whisper المكممة التي تعمل بدون إنترنت.
* **التوجيه بالصوت**: تسجيل التوجيهات البرمجية مباشرة إلى موجه الأوامر النشط بزمن استجابة صفري.

### 3. محرك Git وعزل شجرة العمل Worktree (`/git` أو `/scope`)
* **حماية القراءة فقط**: تقييد عمليات الوكيل تلقائياً إلى أوامر القراءة الآمنة (`cat`, `git diff`, `grep`) ما لم يُصرح بغير ذلك.
* **أشجار عمل Git مؤقتة**: تنفيذ تعديلات الأكواد في بيئات عمل معزولة، ولا تُدمج التغييرات إلا بعد نجاح كافة الاختبارات البرمجية.
* **معاينة الفروقات الملونة**: توليد مراجعة موحدة للفروقات قبل كتابة أي تغيير على القرص.

### 4. نقاط الحفظ الحتمية والاسترجاع الفوري (`/checkpoint` أو `/rollback` أو `/undo`)
* **نسخ احتياطية لكل خطوة**: إنشاء لقطة غير قابلة للتغيير للملفات المعدلة قبل كل إجراء برمجي.
* **استرجاع في أجزاء من الثانية**: إذا تسبب التعديل في خطأ برمجي، يقوم أمر `/rollback` أو `/undo` بإعادة المستودع إلى حالته الأصلية فوراً.

### 5. الوكلاء الفرعيون المستقلون وإدارة الفرق المتعددة (`/agent` أو `/orchestrate`)
* **مهام خلفية مستقلة**: تشغيل وكلاء فرعيين بميزانية رموز محددة وصلاحيات وصول معزولة للملفات.
* **تنسيق هرمي**: يقوم الوكيل الأساسي بتفويض مهام محددة (اختبارات، توثيق) للوكلاء الفرعيين ودمج النتائج المعتمدة.

### 6. البحث المحلي والذاكرة الشعاعية RAG (`/research`)
* **فهرسة دلالية للأكواد**: فهرسة ملفات المشروع داخل مخزن شعاعي محلي للبحث الدلالي السريع عن الدوال والفئات.
* **بحث وثائقي دقيق**: جلب وقراءة الوثائق البرمجية محلياً وعبر الويب لضمان انعدام الهلوسة في الإجابات.

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

## معالج تثبيت بنية النظام (`lmms install`)

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

### [1] إعدادات محطة العمل الفردية

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

### [2] بنية المؤسسات والخادم المركزي الخارق

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **حوسبة مركزية فائقة**: يعمل الخادم المركزي على خوادم بطاقات الرسوميات (`0.0.0.0:11435`) لخدمة نماذج الشركة وتدريبها.
* **استوديوهات العملاء عن بُعد**: يتصل الموظفون من حواسيبهم المحمولة باكتشاف تلقائي عبر الشبكة الداخلية LAN/VPC.
* **خصوصية تامة للبيانات**: لا تخرج الأكواد أو التوجيهات إطلاقاً خارج نطاق شبكة المؤسسة المحمية.
* **محرك AirEngine بلا قيود للذاكرة**: تدفق ديناميكي لأوزان النماذج الضخمة عبر VRAM والذاكرة والقرص السريع NVMe.

---

### Pip & Installer Command Matrix

| الأمر | الغرض | المكون المستهدف |
|---|---|---|
| `lmms install` | تشغيل المعالج التفاعلي لاختيار بنية النظام | قائمة التكوين التفاعلية |
| `lmms install --all` | تثبيت النظام البيئي الكامل | استوديو الواجهة، الطرفية، الصوت، والمحرك الخارق |
| `lmms install --gui` | تثبيت استوديو سطح المكتب (GUI) | واجهة PyQt6 ومحرر Monaco وعميل المحرك |
| `lmms install --cli` | تثبيت استوديو الطرفية (CLI) | الصدفة التفاعلية وأدوات المطور وعميل المحرك |
| `lmms install --engine` | تثبيت المحرك الخارق Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | تثبيت المحرك الخفيف | llama.cpp + AirEngine (خاص بنماذج GGUF) |
| `lmms install --engine2` | تثبيت محرك PyTorch الأصلي | PyTorch + Transformers + AirEngine |
| `lmms install --host` | تثبيت خادم الاستضافة المركزي للمؤسسات | خادم مركزي يستمع على المنفذ 0.0.0.0:11435 |
| `lmms install --client-gui` | تثبيت واجهة العميل الرسومية للمؤسسات | واجهة مهيأة للاتصال بالمضيف البعيد عبر LAN |
| `lmms install --client-cli` | تثبيت واجهة العميل الطرفية للمؤسسات | طرفية مهيأة للاتصال بالمضيف البعيد عبر LAN |
| `lmms update` | سحب وتحديث الشيفرة المصدرية للنسخة الحالية | تحديث الفرع النشط حالياً |
| `lmms update --all` | تحديث شامل وقسري لجميع الفروع | مزامنة كاملة وشاملة مع GitHub |
| `lmms -check` | تشخيص العتاد والتحقق من متطلبات النظام | قياسات المعالج وكرت الشاشة والذاكرة والقرص |
| `lmms-uninstall -all` | إلغاء تثبيت الشيفرة المصدرية بأمان | حذف الكود مع الإبقاء على حزم pip والنماذج |
| `lmms-uninstall -all --purge` | استعادة ضبط المصنع الكامل والمسح الشامل | مسح كامل وشامل لكافة الإعدادات والنماذج والبيانات |

---

## مرجع الأوامر الأساسية

### LMMs Core Launcher Commands

| الأمر | الوصف |
|---|---|
| `lmms` | تشغيل الواجهة الافتراضية المحددة في النظام |
| `lmms --gui` | تشغيل استوديو الواجهة الرسومية مباشرة |
| `lmms --cli` | تشغيل صدفة سطر الأوامر التفاعلية مباشرة |
| `lmms --engine` | تشغيل خادم محرك الاستدلال مباشرة |
| `lmms set --gui` | تعيين استوديو الواجهة الرسومية كوضع تشغيل افتراضي |
| `lmms set --cli` | تعيين استوديو سطر الأوامر كوضع تشغيل افتراضي |
| `lmms set --engine` | تعيين خادم المحرك كوضع تشغيل افتراضي |
| `lmms stop` | إيقاف محرك LMMs الذي يعمل في الخلفية بأمان |
| `lmms -check` | التحقق من ملف مواصفات العتاد والمتطلبات الأساسية |
| `lmms update` | تحديث ذكي انطلاقاً من الفرع الحالي |
| `lmms update --all` | فرض التحديث والمزامنة الكاملة من GitHub |
| `lmms --help` | عرض دليل المساعدة الشامل للمشغل |

---

### Engine Runtime & Air Engine

| الأمر | الوصف |
|---|---|
| `lmms run <model>` | تشغيل النموذج في محادثة تفاعلية أو توجيه فردي |
| `lmms list` | عرض قائمة النماذج المحملة محلياً على الجهاز |
| `lmms ps` | عرض النماذج النشطة قيد التشغيل واستهلاك VRAM |
| `lmms pull <model>` | تنزيل نموذج من Hugging Face أو المستودع الرسمي |
| `lmms info <model>` | فحص البيانات الوصفية وحجم السياق ومستوى التكميم |
| `lmms search <query>` | البحث في مستودعات النماذج المتاحة للتنزيل |
| `lmms benchmark <model>` | قياس سرعة توليد الرموز (token/s) وزمن الاستجابة |
| `lmms doctor` | فحص سلامة المحرك وتشخيص برامج تشغيل CUDA |
| `lmms create <model> -f <file>` | تسجيل نموذج مخصص من ملفات GGUF أو Safetensors |
| `lmms -air run <model> [prompt]` | تشغيل نماذج ضخمة جداً بنظام التفريغ الديناميكي Air |
| `lmms --air run <m1> <m2>` | تشغيل نماذج متعددة في وقت واحد عبر مجدول Air |
| `lmms air ps` | مراقبة جلسات Air وتوزيع طبقات النموذج على المعالج والكرت |
| `lmms air stats` | عرض إحصائيات تفريغ الموترات والسرعة في الوقت الفعلي |
| `lmms air cache` | معاينة حجم واستخدام ذاكرة التخزين المؤقت على القرص |
| `lmms air unload` | إلغاء تحميل كافة نماذج Air وإفراغ كاش كرت الشاشة فوراً |
| `lmms air benchmark <model>` | قياس أداء الإنتاجية وسرعة المعالجة تحت مجدول Air |

---

### Server / Daemon

| الأمر | الوصف |
|---|---|
| `lmms server` | بدء تشغيل خادم الواجهة البرمجية API والويب |
| `lmms server status` | التحقق من حالة الخادم والمنفذ وزمن العمل والجاهزية |
| `lmms engine status` | عرض وضع المحرك النشط وإحصائيات استخدام الذاكرة |
| `lmms engine unload [model]` | تفريغ النماذج النشطة من الذاكرة وإتاحة VRAM |
| `lmms server start [--port 11435]` | بدء تشغيل خادم FastAPI الخلفي على المنفذ المحدد |
| `lmms server stop` | إيقاف خادم الخلفية قيد التشغيل |

---

## أوامر سلاش التفاعلية في الطرفية CLI

| الأمر | الوصف |
|---|---|
| `/fast` | التحويل لوضع FAST للاستجابات السريعة والأدوات الخفيفة |
| `/deep` | التحويل لوضع DEEP للتفكير العميق المتعدد والوصول لكافة الأدوات |
| `/model <name>` | تغيير النموذج المستخدم في جلسة المحادثة الحالية |
| `/ml -l` | عرض قائمة بكافة النماذج المحلية المحملة داخل المحادثة |
| `/ml -s <name>` | التبديل الفوري للنموذج مع الحفاظ على سياق وتاريخ الحوار |
| `/folder <path>` | ربط مجلد عمل محدد بالسياق الإدراكي للوكيل |
| `/code` | الدخول في وضع توليد وتحرير الأكواد الموجه والمكثف |
| `/chat` | عرض واستعراض سجل جلسات المحادثة السابقة |
| `/newchat` | بدء جلسة محادثة جديدة وفارغة |
| `/chat -r <id> <name>` | إعادة تسمية جلسة محادثة محددة |
| `/chat -d <id>` | حذف جلسة محادثة محددة نهائياً |
| `/undo` | التراجع الآمن عن آخر تعديل برمجي أو باتش أجراه الذكاء الاصطناعي |
| `/redo` | إعادة تطبيق آخر إجراء تم التراجع عنه |
| `/exit` | الخروج من جلسة الطرفية التفاعلية |
| `/reboot` | إعادة تشغيل محرك النظام الخلفي وإعادة الاتصال بالجلسة |
| `/mic` | تسجيل الصوت من الميكروفون والنسخ الفوري إلى نص الموجه |
| `/vision أو /image` | التحويل إلى وضع الرؤية البصرية لتحليل الصور وتصميم الواجهات |
| `/research` | التحويل إلى وضع البحث التقني واستكشاف الويب والتوثيق |
| `/read <file>` | قراءة ملف محدد من بيئة العمل ودمجه في سياق الجلسة |
| `/task` | إدارة المهام الذاتية الخلفية وأهداف الوكلاء الفرعيين |
| `/git` | تنفيذ عمليات Git آمنة وموثقة وقابلة للتدقيق عبر الوكيل |
| `/scope` | فحص وضبط نطاق وصلاحيات تشغيل الأدوات البرمجية |
| `/tools list` | عرض قائمة بكافة الأدوات الأصلية وخوادم بروتوكول MCP النشطة |
| `/report` | توليد تقرير تدقيق أمني وإجرائي موقع رقمياً ومشفر |
| `/checkpoint` | إنشاء نقطة استعادة غير قابلة للتغيير لحالة بيئة العمل الحالية |
| `/checkpoints` | عرض قائمة بكافة نقاط الاستعادة المحفوظة للمشروع |
| `/rollback` | استرجاع المستودع والملفات البرمجية إلى نقطة حفظ سابقة |
| `/status` | التحقق من صحة وجاهزية المحرك والعتاد في الوقت الفعلي |
| `/doctor` | تشغيل فحص تشخيصي شامل للنظام واختبارات المعالجة التلقائية |
| `/pair` | بدء وضع البرمجة الثنائية التفاعلية مع الوكيل |
| `/perm <level>` | تعديل مستوى صلاحيات بيئة التشغيل المعزولة (`strict`, `ask`, `full`) |
| `/agent` | إنشاء وإدارة وكلاء فرعيين مستقلين للتنفيذ البرمجي المتوازي |
| `/orchestrate` | إدارة تدفقات العمل المنسقة والمعقدة بين عدة وكلاء |

---

## فلسفة المنتج

1. **الأولوية للفائدة الفعلية**: تعديل حقيقي للملفات، وتحقق صارم من بنية AST، وتنفيذ في بيئات معزولة.
2. **الصدق والشفافية التامة**: انعدام تتبع البيانات، وبدون اشتراكات إجبارية أو دفعات مخفية.
3. **المحلي أولاً وأخيراً**: تبقى نماذجك وأوزانك وشيفراتك بالكامل على أجهزتك الشخصية.
4. **حزمة برمجية نقية**: بنية برمجية نقية بلغة بايثون خالية من التبعيات غير الضرورية.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
