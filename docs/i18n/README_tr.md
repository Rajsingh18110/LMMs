<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Modellerle inşa edin. Ajanlarla yayınlayın.</strong><br>
  <em>Kurucu Raj Singh (MarkanM) tarafından geliştirilen Python tabanlı yerel yapay zeka işletim katmanı</em>
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
[![Türkçe](https://img.shields.io/badge/Language-Türkçe-e11d48?style=flat-square)](#)
[![Tiếng Việt](https://img.shields.io/badge/Language-Tiếng_Việt-d97706?style=flat-square)](README_vi.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-be123c?style=flat-square)](README_id.md)
[![বাংলা](https://img.shields.io/badge/Language-বাংলা-047857?style=flat-square)](README_bn.md)
[![ਪੰਜਾਬੀ](https://img.shields.io/badge/Language-ਪੰਜਾਬੀ-c2410c?style=flat-square)](README_pa.md)
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](README_mr.md)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">Resmi Web Sitesi</a> ·
  <a href="#system-architecture">Sistem Mimarisi</a> ·
  <a href="#deep-technical-capabilities">Temel Yetenekler</a> ·
  <a href="#quick-start">Hızlı Başlangıç</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Kurulum Sihirbazı</a> ·
  <a href="#enterprise-infrastructure--super-host">Kurumsal Altyapı</a> ·
  <a href="#core-command-reference">Komut Kılavuzu</a> ·
  <a href="#cli-slash-commands">Slash Komutları</a> ·
  <a href="#license">Lisans</a>
</p>

---

## LMMs OS Nedir?

LMMs, yerel ve uzak model yürütme için Python tabanlı yerel bir yapay zeka işletim katmanıdır. Kurucu Raj Singh (MarkanM) tarafından geliştirilen bu sistem; gerçek bir masaüstü GUI stüdyosunu, akıllı bir geliştirici CLI'sini ve olgun bir motor çalışma zamanını bir araya getirerek geliştiricilerin ve kurumların telemetri ve bulut bağımlılığı olmadan büyük çok modlu modelleri çalıştırmasını sağlar.

* **Yerel Çift Çekirdekli Motor**: llama.cpp ile yüksek verimli kuantize GGUF çıkarımı ve PyTorch ile yerel safetensors çalıştırma.
* **AirEngine ile Sınırsız Ölçeklendirme**: GPU, CPU ve disk arasında dinamik tensör aktarımı sayesinde sıradan dizüstü bilgisayarlarda bile 70B+ modeller çalıştırılabilir.
* **Masaüstü Stüdyosu (GUI)**: Monaco kod düzenleyici, görsel diff incelemesi, Git entegrasyonu ve entegre araç yöneticisi.
* **Terminal Stüdyosu (CLI)**: 30'dan fazla slash komutu, eşli programlama, alt ajan orkestrasyonu ve güvenli yalıtılmış alan.
* **Kurumsal Kullanıma Hazır**: Özel LAN/VPC ağlarında merkezi ana bilgisayar ve otomatik istemci keşfi içeren dağıtık mimari.

---

## Sistem Mimarisi

Aşağıdaki şema, LMMs OS'un Kullanıcı Arayüzü, Arka Uç Servisleri, Model Çıkarımı ve Ajan Yetenekleri alt sistemlerini kapsayan mimarisini göstermektedir:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Kullanıcı Arayüzleri**: `GUI workspace [main_window.py]` (Monaco IDE ve diff inceleme) ve `CLI [commands.py]` (etkileşimli terminal geliştirici kabuğu).
2. **API ve Arka Uç Katmanı**: `HTTP API [server.py]` (11435 portunda dinleyen FastAPI arka plan hizmeti), `Backend session [main.py]` (oturum koordinatörü), ve `Backend services [manager.py]`.
3. **Model Çıkarım Alt Sistemi**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (GPU/CPU/Disk tensör aktarımı), `Model registry [registry.py]`, `llama.cpp motoru` ve `PyTorch motoru`.
4. **Ajan Yetenekleri Alt Sistemi**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` ve `Workspace & Git [manager.py]`.

---

## Derin Teknik Yetenekler (Deep Technical Capabilities)

### 1. Çok Modlu Görsel Motoru (`/vision`, `/image`)
LMMs yerel motorunda doğrudan çok modlu görsel işleme kabiliyetine sahiptir:
* **Arayüz ve Düzen Analizi**: Web veya masaüstü ekran görüntülerini inceleyerek görsel hataları ve CSS sorunlarını otomatik olarak tespit eder.
* **Mimari ve Diyagram Çıkarma**: Akış şemalarını, ER diyagramlarını ve UML dizilimlerini analiz ederek doğrudan geçerli Mermaid koduna dönüştürür.
* **Yerel Belge OCR**: Görsellerden ve PDF'lerden metin ve tabloları dış sunuculara göndermeden doğrudan cihazınızda ayrıştırır.

### 2. Çevrimdışı Ses ve Konuşma Tanıma (`/mic`)
* **Yerel Konuşmadan Metne**: Yerel kuantize Whisper modelleriyle sıfır ağ gecikmeli hızlı çevrimdışı ses dökümü.
* **Eller Serbest Geliştirme**: Sesli talimatları doğrudan aktif CLI oturumuna gerçek zamanlı olarak yazdırın.

### 3. Git Farkındalığı ve Worktree Yalıtımı (`/git`, `/scope`)
* **Salt Okunur Güvenlik Kilidi**: Açık onay verilmedikçe ajan eylemlerini güvenli okuma komutlarıyla (`cat`, `git diff`, `grep`) sınırlar.
* **Geçici Git Worktree Alanları**: Kod değişiklikleri izole worktree kopyalarında test edilir ve yalnızca testler başarıyla geçtiğinde ana dala birleştirilir.
* **Renkli Diff Önizlemesi**: Diske kaydedilmeden önce her dosya değişikliği için renkli birleştirilmiş fark görünümü oluşturulur.

### 4. Deterministik Denetim Noktaları ve Anında Geri Alma (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Adım Başına Yedekleme**: Her kod değişikliğinden önce değiştirilecek dosyaların anlık kopyası kaydedilir.
* **Milisaniyelik Geri Alma**: Üretilen yama testleri geçemezse, `/rollback` veya `/undo` depoyu saniyeler içinde tam önceki durumuna döndürür.

### 5. Otonom Alt Ajanlar ve Çoklu Ajan Koordinasyonu (`/agent`, `/orchestrate`)
* **Arka Plan Görevleri**: Belirli token bütçelerine ve izole izinlere sahip bağımsız alt ajanları arka planda çalıştırır.
* **Hiyerarşik İş Bölümü**: Ana orkestratör test, dokümantasyon ve refaktör görevlerini alt ajanlara delege eder ve sonuçları birleştirir.

### 6. Yerel Araştırma ve Vektör RAG (`/research`)
* **Anlamsal Kod Tabanı İndeksleme**: Projeyi yerel bir vektör veri tabanında indeksleyerek fonksiyonları ve sınıfları semantik olarak arar.
* **Halüsinasyonsuz Teknik Dokümantasyon**: Yerel ve web API belgelerini tarayarak uydurma cevapları tamamen ortadan kaldırır.

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

## Mimari Kurulum Sihirbazı (`lmms install`)

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

### [1] Bireysel İş İstasyonu Yapılandırmaları

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

### [2] Kurumsal Altyapı ve Süper Sunucu

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Merkezi Güçlü Hesaplama**: Sunucu arka plan hizmeti GPU sunucularında (`0.0.0.0:11435`) çalışarak şirket modellerine ev sahipliği yapar.
* **Uzak İstemci Stüdyoları**: Çalışanlar kendi dizüstü bilgisayarlarından LAN/VPC ağı üzerinden otomatik keşifle bağlanır.
* **Tam Veri Gizliliği**: Hiçbir kod veya prompt şirket içi yerel ağın dışına çıkmaz.
* **AirEngine ile Bellek Sınırı Yok**: VRAM, RAM ve NVMe üzerinde dinamik model ağırlığı akışı sayesinde devasa modeller çalıştırılır.

---

### Pip & Installer Command Matrix

| Komut | Amaç | Hedef Bileşen |
|---|---|---|
| `lmms install` | Etkileşimli mimari seçim sihirbazını başlat | Etkileşimli yapılandırma menüsü |
| `lmms install --all` | Tüm ekosistemi eksiksiz yükle | Masaüstü Stüdyo, CLI, Ses, Süper Motor |
| `lmms install --gui` | Masaüstü Stüdyosunu (GUI) yükle | PyQt6 Arayüzü, Monaco Editör, Motor istemcisi |
| `lmms install --cli` | Terminal Stüdyosunu (CLI) yükle | Etkileşimli kabuk, geliştirici araçları, İstemci |
| `lmms install --engine` | Süper Motor (Super Engine) çalışma zamanını yükle | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Hafif sıklet motoru yükle | llama.cpp + AirEngine (yalnızca GGUF) |
| `lmms install --engine2` | PyTorch yerel motorunu yükle | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Kurumsal merkezi sunucu arka plan hizmetini kur | 0.0.0.0:11435 adresinde dinleyen merkezi daemon |
| `lmms install --client-gui` | Kurumsal uzak masaüstü istemcisini kur | LAN/VPC uzak ana bilgisayara bağlanan GUI |
| `lmms install --client-cli` | Kurumsal uzak terminal istemcisini kur | LAN/VPC uzak ana bilgisayara bağlanan CLI |
| `lmms update` | Kaynak kodun en son sürümünü indir ve güncelle | Aktif Git dalının güncellenmesi |
| `lmms update --all` | Tüm dallarda zorunlu ve eksiksiz güncelleme | GitHub ile tam ve eşzamanlı senkronizasyon |
| `lmms -check` | Donanım teşhisi ve önkoşul kontrolü gerçekleştir | CPU, GPU, VRAM, AVX ve disk telemetrisi |
| `lmms-uninstall -all` | Kaynak kodları güvenli biçimde kaldır | Kodu siler, pip paketlerini ve modelleri korur |
| `lmms-uninstall -all --purge` | Fabrika ayarlarına sıfırla ve tamamen temizle | Tüm ayar, model ve verilerin kalıcı olarak silinmesi |

---

## Temel Komut Kılavuzu

### LMMs Core Launcher Commands

| Komut | Açıklama |
|---|---|
| `lmms` | Yapılandırılmış varsayılan arayüzü başlat |
| `lmms --gui` | Masaüstü GUI stüdyosunu doğrudan başlat |
| `lmms --cli` | Geliştirici CLI terminal kabuğunu doğrudan başlat |
| `lmms --engine` | Çıkarım motoru arka plan hizmetini doğrudan başlat |
| `lmms set --gui` | Masaüstü Stüdyosunu varsayılan başlatma modu yap |
| `lmms set --cli` | Terminal Stüdyosunu varsayılan başlatma modu yap |
| `lmms set --engine` | Motor Daemon'ını varsayılan başlatma modu yap |
| `lmms stop` | Arka planda çalışan LMMs motoru arka plan hizmetini güvenle durdur |
| `lmms --help` | Kapsamlı başlatıcı yardım kılavuzunu görüntüle |

---

### Motor Çalışma Zamanı ve Model Yönetimi

| Komut | Açıklama |
|---|---|
| `lmms run <model>` | Modeli etkileşimli sohbette veya tekli istemde çalıştır |
| `lmms stop <model>` | Çalışan aktif bir model örneğini durdur |
| `lmms list` | Yerel olarak indirilmiş modelleri listele |
| `lmms ps` | Çalışan modelleri, bellek dağılımını ve VRAM durumunu göster |
| `lmms pull <model>` | Hugging Face veya resmi Model Hub'dan model indir |
| `lmms info <model>` | Model meta verilerini, bağlam penceresini ve kuantizasyonu incele |
| `lmms rm <model>` | Yerel olarak depolanan bir modeli sil |
| `lmms search <query>` | İndirilebilir açık kaynaklı model depolarında arama yap |
| `lmms benchmark <model>` | Belirteç üretim hızını (token/s) ve yanıt gecikmesini ölç |
| `lmms doctor [--fix]` | Sağlık denetimi, küçük sorunları otomatik onarma ve CUDA/sürücü doğrulama |
| `lmms create <model> -f <file>` | GGUF veya Safetensors dosyasından özel model kaydı oluştur |

---

### Air Engine (Akıllı RAM/VRAM Takası)

Dinamik katmanlı hibrit GPU/CPU/Disk tensör aktarımı kullanarak fiziksel VRAM'i aşan dev modelleri çalıştırın.

| Komut | Açıklama |
|---|---|
| `lmms -air run <model> [prompt]` | Air hibrit bellek aktarımıyla devasa modelleri çalıştır |
| `lmms --air run <m1> <m2>` | Air zamanlayıcı ile birden fazla modeli aynı anda çalıştır |
| `lmms air ps` | Aktif Air oturumlarını ve GPU/CPU katman dağılımını izle |
| `lmms air stats` | Gerçek zamanlı donanım telemetrisi ve aktarım hızını incele |
| `lmms air cache` | Air disk önbellek boyutunu ve depolama kullanımını kontrol et |
| `lmms air unload` | Tüm Air modellerini bellekten kaldır ve VRAM önbelleğini hemen boşalt |
| `lmms air benchmark <model>` | Air dinamik zamanlayıcı altında üretim hızını test et |

---

### Server / Daemon

| Komut | Açıklama |
|---|---|
| `lmms server` | API / Web sunucu arka plan hizmetini başlat |
| `lmms server status` | Sunucu durumunu, bağlantı noktasını, çalışma süresini ve sağlığı denetle |
| `lmms engine status` | Aktif motor modunu ve bellek istatistiklerini görüntüle |
| `lmms engine unload [model]` | Aktif modelleri bellekten kaldır ve VRAM'i serbest bırak |
| `lmms server start [--port 11435]` | Belirtilen port üzerinde FastAPI arka plan hizmetini başlat |
| `lmms server stop` | Çalışan arka plan sunucu hizmetini durdur |

---

## Etkileşimli CLI Slash Komutları

| Komut | Açıklama |
|---|---|
| `/fast` | Hızlı yanıtlar ve hafif araçlar için FAST moduna geç |
| `/deep` | Çok adımlı derin mantık yürütme ve tam araç yetkisi için DEEP moduna geç |
| `/model <name>` | Geçerli konuşma oturumunda kullanılan modeli değiştir |
| `/ml -l` | İndirilmiş tüm yerel modelleri sohbet penceresinde listele |
| `/ml -s <name>` | Sohbet geçmişini koruyarak modeli anında değiştir |
| `/folder <path>` | Ajanın çalışma bağlamına belirli bir dizini iliştir |
| `/code` | Kod üretimi ve otomatik yama uygulamaya odaklanmış moda geç |
| `/chat` | Geçmiş sohbet oturumlarını listele ve incele |
| `/newchat` | Yeni ve temiz bir sohbet oturumu başlat |
| `/chat -r <id> <name>` | Belirtilen sohbet oturumunun adını değiştir |
| `/chat -d <id>` | Belirtilen sohbet oturumu geçmişini kalıcı olarak sil |
| `/undo` | Yapay zekanın yaptığı son dosya değişikliğini veya yamayı güvenle geri al |
| `/redo` | Geri alınan son dosya işlemini tekrar uygula |
| `/exit` | Etkileşimli CLI oturumundan güvenli bir şekilde çık |
| `/reboot` | Arka uç motorunu yeniden başlat ve oturumu tekrar bağla |
| `/mic` | Mikrofondan sesi kaydet ve doğrudan istem alanına dök |
| `/vision veya /image` | Görüntü ve arayüz analizi için çok modlu görme moduna geç |
| `/research` | Web ve teknik dokümanlarda derin araştırma moduna geç |
| `/read <file>` | Çalışma alanındaki bir dosyayı doğrudan sohbet bağlamına yükle |
| `/task` | Arka planda çalışan otonom alt görevleri ve hedefleri yönet |
| `/git` | Ajan aracılığıyla denetimli ve güvenli Git işlemleri yürüt |
| `/scope` | Araç çalıştırma yetkilerinin sınırlarını görüntüle ve düzenle |
| `/tools list` | Tüm yerel araçları ve aktif MCP sunucu uç noktalarını listele |
| `/report` | Kriptografik olarak imzalanmış güvenlik ve eylem denetim raporu üret |
| `/checkpoint` | Çalışma alanının mevcut durumuna ait sabit bir kontrol noktası kaydet |
| `/checkpoints` | Kaydedilmiş tüm proje kontrol noktalarını listele |
| `/rollback` | Depoyu ve dosyaları önceki bir kontrol noktasına geri döndür |
| `/status` | Motorun ve sistem donanımının anlık durumunu denetle |
| `/doctor` | Kapsamlı sistem teşhisi ve otomatik onarım testlerini çalıştır |
| `/pair` | Etkileşimli eşli programlama (pair programming) modunu başlat |
| `/perm <level>` | Yalıtılmış alan çalıştırma izin seviyesini ayarla (`strict`, `ask`, `full`) |
| `/agent` | Paralel görevler için otonom alt ajanlar oluştur ve yönet |
| `/orchestrate` | Birden çok ajan arasındaki koordineli iş akışlarını yönet |

---

## Ürün Felsefesi

1. **Gerçek Kullanışlılık Önceliklidir**: Dosya yamalama, AST doğrulama ve yalıtılmış terminal görevleri.
2. **Dürüstlük ve Şeffaflık**: Sıfır telemetri, gizli abonelik veya ödeme duvarı yok.
3. **Özünde Yerel (Local-First)**: Modelleriniz, ağırlıklarınız ve kodlarınız her zaman kendi cihazınızda kalır.
4. **Yalın Mimari**: Gereksiz yüklerden arındırılmış saf Python altyapısı.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
