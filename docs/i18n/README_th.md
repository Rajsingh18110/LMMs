<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>สร้างด้วยโมเดล ส่งมอบด้วยเอเจนต์</strong><br>
  <em>ระบบปฏิบัติการ AI ภายในเครื่องที่พัฒนาด้วย Python โดยผู้ก่อตั้ง Raj Singh (MarkanM)</em>
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
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](#)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">เว็บไซต์ทางการ</a> ·
  <a href="#system-architecture">สถาปัตยกรรมระบบ</a> ·
  <a href="#deep-technical-capabilities">ขีดความสามารถหลัก</a> ·
  <a href="#quick-start">เริ่มต้นใช้งาน</a> ·
  <a href="#architecture-setup-wizard-lmms-install">ตัวช่วยติดตั้ง</a> ·
  <a href="#enterprise-infrastructure--super-host">สำหรับองค์กร</a> ·
  <a href="#core-command-reference">คู่มือคำสั่ง</a> ·
  <a href="#cli-slash-commands">คำสั่ง Slash</a> ·
  <a href="#license">สัญญาอนุญาต</a>
</p>

---

## LMMs OS คืออะไร?

LMMs คือระบบปฏิบัติการ AI แบบเนทีฟบน Python สำหรับการรันโมเดลภาษาและโมเดลมัลติโมดอลทั้งในเครื่องและระยะไกล พัฒนาโดย Raj Singh (MarkanM) รวมเอาเดสก์ท็อปสตูดิโอแบบ GUI, CLI อัจฉริยะสำหรับนักพัฒนา และรันไทม์การประมวลผลที่เสถียรเข้าด้วยกัน ช่วยให้สามารถรันโมเดลขนาดใหญ่ได้โดยปราศจากการเก็บข้อมูล Telemetry และไม่ต้องพึ่งพาระบบคลาวด์

* **แกนประมวลผลคู่แบบเนทีฟ**: การอนุมานโมเดล GGUF ควอนไทซ์ประสิทธิภาพสูงด้วย llama.cpp พร้อมการรันโมเดล safetensors ดั้งเดิมบน PyTorch
* **ขยายสเกลไร้ขีดจำกัดด้วย AirEngine**: ถ่ายโอนเทนเซอร์แบบไดนามิกระหว่าง GPU, CPU และดิสก์ ช่วยให้รันโมเดลขนาด 70B+ ได้อย่างลื่นไหลแม้บนแล็ปท็อปทั่วไป
* **เดสก์ท็อปสตูดิโอ (GUI)**: โปรแกรมแก้ไขโค้ด Monaco, การเปรียบเทียบความแตกต่าง (diff) ด้วยภาพ, การเชื่อมต่อ Git และตัวจัดการเครื่องมือในตัว
* **เทอร์มินัลสตูดิโอ (CLI)**: เชลล์แบบโต้ตอบพร้อมคำสั่ง Slash มากกว่า 30 คำสั่ง, การเขียนโปรแกรมคู่, การควบคุมเอเจนต์ย่อย และแซนด์บ็อกซ์ที่ปลอดภัย
* **พร้อมใช้งานในระดับองค์กร**: สถาปัตยกรรมแบบไคลเอนต์-เซิร์ฟเวอร์บนเครือข่ายส่วนตัว LAN/VPC พร้อมการค้นหาเซิร์ฟเวอร์โฮสต์ส่วนกลางอัตโนมัติ

---

## สถาปัตยกรรมระบบ (System Architecture)

แผนภาพต่อไปนี้แสดงโครงสร้างสถาปัตยกรรมแบบครบวงจรของ LMMs OS ครอบคลุมระบบส่วนต่อประสานผู้ใช้, บริการแบ็กเอนด์, เครื่องมือประมวลผลโมเดล และระบบขีดความสามารถของเอเจนต์:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **ส่วนต่อประสานผู้ใช้**: `GUI workspace [main_window.py]` (IDE บน Monaco และตัวตรวจทาน diff) และ `CLI [commands.py]` (เทอร์มินัลเชลล์แบบโต้ตอบสำหรับนักพัฒนา)
2. **API และเลเยอร์แบ็กเอนด์**: `HTTP API [server.py]` (FastAPI เดมอนบนพอร์ต 11435), `Backend session [main.py]` (ตัวประสานเซสชัน), และ `Backend services [manager.py]`
3. **ระบบย่อยการอนุมานโมเดล**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (การกระจายเทนเซอร์ GPU/CPU/Disk), `Model registry [registry.py]`, `llama.cpp runtime` และ `PyTorch runtime`
4. **ระบบย่อยขีดความสามารถของเอเจนต์**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` และ `Workspace & Git [manager.py]`

---

## ขีดความสามารถทางเทคนิคขั้นสูง (Deep Technical Capabilities)

### 1. เครื่องมือวิทัศน์มัลติโมดอล (`/vision`, `/image`)
LMMs รวมการประมวลผลมัลติโมดอลไว้ภายในเครื่องโดยตรง:
* **การวิเคราะห์ UI และโครงสร้างหน้าเว็บ**: ตรวจสอบภาพหน้าจอของเว็บหรือแอปพลิเคชันเพื่อตรวจหาจุดบกพร่องทางภาพและข้อผิดพลาดในการแสดงผล CSS
* **การสกัดแผนภาพและสถาปัตยกรรม**: วิเคราะห์โฟลว์ชาร์ต, ไดอะแกรม ER และลำดับ UML พร้อมแปลงเป็นโค้ด Mermaid หรือโครงสร้างข้อมูลได้ทันที
* **การสแกน OCR เอกสารภายในเครื่อง**: ดึงข้อความและตารางจากรูปภาพและไฟล์ PDF ได้อย่างปลอดภัยโดยไม่มีการส่งข้อมูลออกนอกเครื่อง

### 2. ระบบเสียงและการแปลงเสียงพูดออฟไลน์ (`/mic`)
* **การถอดเสียงพูดเป็นข้อความภายในเครื่อง**: ถอดเสียงออฟไลน์ความเร็วสูงด้วยโมเดล Whisper แบบควอนไทซ์ที่ทำงานบนเครื่อง
* **การป้อนคำสั่งแบบแฮนด์ฟรี**: บันทึกคำสั่งและบันทึกช่วยจำของนักพัฒนาลงในเซสชัน CLI ได้โดยตรงโดยไม่มีความล่าช้าของเครือข่าย

### 3. ระบบรองรับ Git และการแยก Worktree อย่างปลอดภัย (`/git`, `/scope`)
* **ระบบป้องกันสิทธิ์อ่านอย่างเดียว**: จำกัดการทำงานของเอเจนต์ให้ใช้เฉพาะคำสั่งอ่านข้อมูลที่ปลอดภัย (`cat`, `git diff`, `grep`) เว้นแต่จะได้รับอนุญาตอย่างชัดเจน
* **Git Worktree ชั่วคราว**: การแก้ไขโค้ดจะดำเนินการในโคลน worktree ที่แยกต่างหาก และจะผสานเข้ากับกิ่งหลักหลังจากผ่านการทดสอบอัตโนมัติทั้งหมดแล้วเท่านั้น
* **การแสดงตัวอย่าง Diff แบบมีสี**: ทุกการแก้ไขไฟล์จะแสดงภาพเปรียบเทียบความแตกต่างก่อนที่จะถูกเขียนลงดิสก์จริง

### 4. จุดตรวจที่กำหนดได้และการย้อนกลับทันที (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **สแน็ปช็อตสำรองตามขั้นตอน**: บันทึกข้อมูลสำรองที่ไม่สามารถแก้ไขได้ของไฟล์ก่อนเริ่มดำเนินการแก้ไขโค้ดทุกครั้ง
* **การย้อนคืนในระดับมิลลิวินาที**: หากโค้ดแพตช์ทำให้การทดสอบล้มเหลวหรือเกิดข้อผิดพลาดทางไวยากรณ์ คำสั่ง `/rollback` หรือ `/undo` จะกู้คืนสภาพเดิมให้ทันที

### 5. เอเจนต์ย่อยอัตโนมัติและการควบคุมหลายเอเจนต์ (`/agent`, `/orchestrate`)
* **งานเบื้องหลังอิสระ**: สร้างเอเจนต์ย่อยที่ทำงานเบื้องหลังพร้อมงบประมาณโทเค็นและสิทธิ์การเข้าถึงไฟล์ที่แยกเป็นอิสระ
* **การประสานงานตามลำดับชั้น**: ออร์เคสตราเตอร์หลักจะมอบหมายงานเฉพาะทาง (การทดสอบ, การจัดทำเอกสาร) ให้กับเอเจนต์ย่อยและรวบรวมผลลัพธ์ที่ผ่านการตรวจสอบแล้ว

### 6. การวิจัยภายในเครื่องและ RAG แบบเวกเตอร์ (`/research`)
* **การทำดัชนีโค้ดเชิงความหมาย**: สร้างดัชนีพื้นที่ทำงานลงในที่เก็บเวกเตอร์ในเครื่องเพื่อค้นหาฟังก์ชันและคลาสได้อย่างรวดเร็ว
* **การค้นหาเอกสารโดยปราศจากภาพหลอน**: ดึงและอ้างอิงเอกสาร API ภายในเครื่องและเว็บเพื่อป้องกันไม่ให้โมเดลสร้างข้อมูลเท็จ

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

## ตัวช่วยติดตั้งสถาปัตยกรรมระบบ (`lmms install`)

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

### [1] การกำหนดค่าสำหรับเวิร์กสเตชันเดี่ยว

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

### [2] โครงสร้างพื้นฐานระดับองค์กรและซูเปอร์โฮสต์

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **ศูนย์กลางการประมวลผลประสิทธิภาพสูง**: เดมอนเซิร์ฟเวอร์ทำงานบนเครื่อง GPU ระดับสูง (`0.0.0.0:11435`) เพื่อรองรับและฝึกฝนโมเดลส่วนตัวขององค์กร
* **สตูดิโอไคลเอนต์ระยะไกล**: สมาชิกในทีมสามารถเชื่อมต่อจากแล็ปท็อปของตนผ่านการค้นหาอัตโนมัติบนเครือข่าย LAN/VPC
* **ความเป็นส่วนตัวของข้อมูลสมบูรณ์แบบ**: โค้ดและพรอมต์ทั้งหมดจะถูกเก็บรักษาไว้ภายในเครือข่ายส่วนตัวขององค์กรเท่านั้น
* **AirEngine ปลดล็อกขีดจำกัดหน่วยความจำ**: สตรีมค่าน้ำหนักโมเดลขนาดใหญ่แบบไดนามิกผ่าน VRAM, RAM และ NVMe

---

### Pip & Installer Command Matrix

| คำสั่ง | วัตถุประสงค์ | ส่วนประกอบเป้าหมาย |
|---|---|---|
| `lmms install` | เปิดตัวช่วยตั้งค่าสถาปัตยกรรมระบบแบบโต้ตอบ | เมนูการตั้งค่าแบบโต้ตอบ |
| `lmms install --all` | ติดตั้งระบบนิเวศทั้งหมดอย่างสมบูรณ์ | เดสก์ท็อปสตูดิโอ, CLI, โมดูลเสียง, ซูเปอร์เอนจิน |
| `lmms install --gui` | ติดตั้งเดสก์ท็อปสตูดิโอ (GUI) | PyQt6 GUI, ตัวแก้ไข Monaco, ไคลเอนต์เอนจิน |
| `lmms install --cli` | ติดตั้งเทอร์มินัลสตูดิโอ (CLI) | เชลล์แบบโต้ตอบ, เครื่องมือนักพัฒนา, ไคลเอนต์ |
| `lmms install --engine` | ติดตั้งรันไทม์ Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | ติดตั้งเครื่องมือประมวลผลขนาดเบา | llama.cpp + AirEngine (สำหรับ GGUF เท่านั้น) |
| `lmms install --engine2` | ติดตั้งเครื่องมือประมวลผล PyTorch ดั้งเดิม | PyTorch + Transformers + AirEngine |
| `lmms install --host` | ติดตั้งเดมอนเซิร์ฟเวอร์โฮสต์ระดับองค์กร | เซิร์ฟเวอร์กลางที่รอรับการเชื่อมต่อที่ 0.0.0.0:11435 |
| `lmms install --client-gui` | ติดตั้งไคลเอนต์ GUI ระดับองค์กร | GUI ที่กำหนดค่าให้เชื่อมต่อกับโฮสต์ระยะไกล |
| `lmms install --client-cli` | ติดตั้งไคลเอนต์ CLI ระดับองค์กร | CLI ที่กำหนดค่าให้เชื่อมต่อกับโฮสต์ระยะไกล |
| `lmms update` | ดึงซอร์สโค้ดล่าสุดและอัปเดตระบบ | อัปเดตกิ่ง Git ที่กำลังใช้งานอยู่ |
| `lmms update --all` | บังคับอัปเดตและซิงค์ครบทุกกิ่ง | ซิงโครไนซ์สมบูรณ์แบบกับ GitHub |
| `lmms -check` | วินิจฉัยฮาร์ดแวร์และข้อกำหนดเบื้องต้น | การตรวจสอบ CPU, GPU, VRAM, AVX และดิสก์ |
| `lmms-uninstall -all` | ถอนการติดตั้งซอร์สโค้ดอย่างปลอดภัย | ลบโค้ดออกโดยคงแพ็กเกจ pip และแคชโมเดลไว้ |
| `lmms-uninstall -all --purge` | รีเซ็ตเป็นค่าเริ่มต้นจากโรงงานทั้งหมด | ลบการตั้งค่า โมเดล และข้อมูลทั้งหมดอย่างถาวร |

---

## คู่มือคำสั่งหลัก (Core Command Reference)

### LMMs Core Launcher Commands

| คำสั่ง | คำอธิบาย |
|---|---|
| `lmms` | เปิดใช้อินเทอร์เฟซเริ่มต้นที่กำหนดค่าไว้ |
| `lmms --gui` | เปิดเดสก์ท็อป GUI สตูดิโอโดยตรง |
| `lmms --cli` | เปิดเทอร์มินัล CLI เชลล์สำหรับนักพัฒนาโดยตรง |
| `lmms --engine` | เปิดเดมอนเครื่องมือประมวลผลโมเดลโดยตรง |
| `lmms set --gui` | ตั้งค่าให้เปิด Desktop Studio เป็นโหมดเริ่มต้น |
| `lmms set --cli` | ตั้งค่าให้เปิด Terminal Studio เป็นโหมดเริ่มต้น |
| `lmms set --engine` | ตั้งค่าให้เปิด Engine Daemon เป็นโหมดเริ่มต้น |
| `lmms stop` | หยุดการทำงานของเอนจิน LMMs ที่ทำงานอยู่เบื้องหลัง |
| `lmms -check` | ตรวจสอบโปรไฟล์ฮาร์ดแวร์และสิ่งที่จำเป็นต้องใช้ |
| `lmms update` | อัปเดตอัจฉริยะจากกิ่ง Git ปัจจุบัน |
| `lmms update --all` | บังคับอัปเดตและซิงค์ใหม่ทั้งหมดจาก GitHub |
| `lmms --help` | แสดงคู่มือช่วยเหลือของตัวเรียกใช้ทั้งหมด |

---

### Engine Runtime & Air Engine

| คำสั่ง | คำอธิบาย |
|---|---|
| `lmms run <model>` | รันโมเดลในการสนทนาแบบโต้ตอบหรือการประเมินรอบเดียว |
| `lmms list` | แสดงรายการโมเดลที่ดาวน์โหลดไว้ในเครื่องทั้งหมด |
| `lmms ps` | แสดงโมเดลที่กำลังทำงานอยู่และสถานะการใช้ VRAM |
| `lmms pull <model>` | ดาวน์โหลดโมเดลจาก Hugging Face หรือ Hub ทางการ |
| `lmms info <model>` | ตรวจสอบข้อมูลเมทาดาทา, หน้าต่างบริบท และการควอนไทซ์ |
| `lmms search <query>` | ค้นหาคลังโมเดลโอเพนซอร์สที่พร้อมให้ดาวน์โหลด |
| `lmms benchmark <model>` | วัดความเร็วในการสร้างโทเค็น (t/s) และความหน่วง |
| `lmms doctor` | ตรวจสอบความสมบูรณ์ของเอนจินและไดรเวอร์ CUDA/GPU |
| `lmms create <model> -f <file>` | ลงทะเบียนโมเดลที่กำหนดเองจากไฟล์ GGUF หรือ Safetensors |
| `lmms -air run <model> [prompt]` | รันโมเดลขนาดมหึมาด้วยเทคโนโลยี Air dynamic hybrid offloading |
| `lmms --air run <m1> <m2>` | รันโมเดลหลายตัวพร้อมกันผ่านตัวจัดตารางเวลาของ Air |
| `lmms air ps` | แสดงเซสชัน Air ที่กำลังทำงานและการกระจายเลเยอร์บน GPU/CPU |
| `lmms air stats` | ดูข้อมูลฮาร์ดแวร์แบบเรียลไทม์และสถิติการสลับข้อมูล |
| `lmms air cache` | ตรวจสอบขนาดของแคชดิสก์ Air และพื้นที่จัดเก็บที่ใช้ไป |
| `lmms air unload` | ยกเลิกการโหลดโมเดล Air ทั้งหมดและล้างแคช VRAM ทันที |
| `lmms air benchmark <model>` | ทดสอบประสิทธิภาพการประมวลผลภายใต้ตัวจัดตารางเวลาของ Air |

---

### Server / Daemon

| คำสั่ง | คำอธิบาย |
|---|---|
| `lmms server` | เริ่มการทำงานของเดมอนเซิร์ฟเวอร์ API / เว็บ |
| `lmms server status` | ตรวจสอบสถานะเซิร์ฟเวอร์, พอร์ต, เวลาทำงาน และความสมบูรณ์ |
| `lmms engine status` | ดูโหมดเอนจินที่ใช้งานอยู่และสถิติการใช้หน่วยความจำ |
| `lmms engine unload [model]` | ล้างโมเดลที่ใช้งานอยู่ออกจากหน่วยความจำและคืน VRAM |
| `lmms server start [--port 11435]` | เริ่มรัน FastAPI ในพื้นหลังตามพอร์ตที่กำหนด |
| `lmms server stop` | หยุดการทำงานของเซิร์ฟเวอร์ที่ทำงานอยู่เบื้องหลัง |

---

## คำสั่งโต้ตอบ Slash CLI (CLI Slash Commands)

| คำสั่ง | คำอธิบาย |
|---|---|
| `/fast` | สลับไปยังโหมด FAST สำหรับการตอบกลับที่รวดเร็วและใช้เครื่องมือขนาดเบา |
| `/deep` | สลับไปยังโหมด DEEP สำหรับการคิดวิเคราะห์หลายขั้นตอนและการใช้เครื่องมือเต็มรูปแบบ |
| `/model <name>` | เปลี่ยนโมเดลที่จะใช้สำหรับเซสชันการสนทนาปัจจุบัน |
| `/ml -l` | แสดงรายการโมเดลในเครื่องทั้งหมดภายในหน้าต่างแชท |
| `/ml -s <name>` | สลับเปลี่ยนโมเดลทันทีโดยยังคงรักษาประวัติการสนทนาไว้ |
| `/folder <path>` | แนบโฟลเดอร์โครงการเข้ากับบริบทการทำงานของเอเจนต์ |
| `/code` | เข้าสู่โหมดที่เน้นการสร้างและแก้ไขโค้ดโดยเฉพาะ |
| `/chat` | แสดงรายการและตรวจทานประวัติเซสชันการแชทก่อนหน้า |
| `/newchat` | เริ่มเซสชันการสนทนาใหม่ที่ว่างเปล่า |
| `/chat -r <id> <name>` | เปลี่ยนชื่อเซสชันการแชทที่ระบุ |
| `/chat -d <id>` | ลบประวัติเซสชันการแชทที่ระบุอย่างถาวร |
| `/undo` | ยกเลิกการแก้ไขไฟล์หรือโค้ดแพตช์ล่าสุดของ AI อย่างปลอดภัย |
| `/redo` | ทำซ้ำการดำเนินการกับไฟล์ที่เพิ่งยกเลิกไป |
| `/exit` | ออกจากเซสชันเทอร์มินัลแบบโต้ตอบ |
| `/reboot` | รีบูตเอนจินแบ็กเอนด์และเชื่อมต่อเซสชันใหม่อีกครั้ง |
| `/mic` | บันทึกเสียงจากไมโครโฟนและถอดเสียงลงในกล่องข้อความทันที |
| `/vision หรือ /image` | สลับไปยังโหมดการมองเห็นเพื่อวิเคราะห์รูปภาพและหน้าตาโปรแกรม |
| `/research` | สลับไปยังโหมดการวิจัยเพื่อค้นหาข้อมูลบนเว็บและเอกสารทางเทคนิค |
| `/read <file>` | อ่านไฟล์ในพื้นที่ทำงานเข้าสู่บริบทของการสนทนาโดยตรง |
| `/task` | จัดการงานเบื้องหลังอัตโนมัติและเป้าหมายของเอเจนต์ย่อย |
| `/git` | ดำเนินการคำสั่ง Git ที่ปลอดภัยและมีบันทึกตรวจสอบผ่านเอเจนต์ |
| `/scope` | ตรวจสอบและปรับขอบเขตการเข้าถึงเครื่องมือ |
| `/tools list` | แสดงรายการเครื่องมือภายในและเซิร์ฟเวอร์ MCP ที่ใช้งานได้ทั้งหมด |
| `/report` | สร้างรายงานการตรวจสอบความปลอดภัยและการกระทำที่มีลายเซ็นดิจิทัล |
| `/checkpoint` | บันทึกจุดตรวจสอบ (checkpoint) ที่ไม่สามารถแก้ไขได้ของพื้นที่ทำงาน |
| `/checkpoints` | แสดงรายการจุดตรวจสอบทั้งหมดที่บันทึกไว้ |
| `/rollback` | ย้อนคืนที่เก็บโค้ดและไฟล์กลับไปยังจุดตรวจสอบก่อนหน้า |
| `/status` | ตรวจสอบสถานะสุขภาพของเอนจินและฮาร์ดแวร์แบบเรียลไทม์ |
| `/doctor` | รันการวินิจฉัยระบบอย่างละเอียดและการทดสอบการซ่อมแซมอัตโนมัติ |
| `/pair` | เปิดใช้งานโหมดการเขียนโปรแกรมคู่แบบโต้ตอบ |
| `/perm <level>` | ปรับระดับสิทธิ์ของแซนด์บ็อกซ์ (`strict`, `ask`, `full`) |
| `/agent` | สร้างและจัดการเอเจนต์ย่อยสำหรับการประมวลผลงานคู่ขนาน |
| `/orchestrate` | จัดการเวิร์กโฟลว์การทำงานร่วมกันระหว่างหลายเอเจนต์ |

---

## ปรัชญาของผลิตภัณฑ์

1. **เน้นประโยชน์ใช้งานจริงเป็นอันดับแรก**: การแพตช์ไฟล์จริง, การตรวจสอบโครงสร้าง AST และการประมวลผลในแซนด์บ็อกซ์
2. **ความโปร่งใสและตรงไปตรงมา**: ไม่มีการดักจับข้อมูลการใช้งาน (Zero-Telemetry) ไม่มีค่าบริการแอบแฝง
3. **เน้นการทำงานในเครื่องอย่างแท้จริง**: ข้อมูล โมเดล และค่าน้ำหนักทั้งหมดจะอยู่บนเครื่องของคุณเท่านั้น
4. **โครงสร้างที่กระชับและสะอาด**: พัฒนาด้วย Python ล้วนโดยไม่มีส่วนประกอบที่ไม่จำเป็น

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
