<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Mit Modellen bauen. Mit Agenten ausliefern.</strong><br>
  <em>Das native Python-basierte lokale KI-Betriebssystem von Gründer Raj Singh (MarkanM)</em>
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
[![Deutsch](https://img.shields.io/badge/Language-Deutsch-475569?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">Offizielle Website</a> ·
  <a href="#system-architecture">Systemarchitektur</a> ·
  <a href="#deep-technical-capabilities">Kernfunktionen</a> ·
  <a href="#quick-start">Schnellstart</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Installationsassistent</a> ·
  <a href="#enterprise-infrastructure--super-host">Enterprise</a> ·
  <a href="#core-command-reference">Befehlsreferenz</a> ·
  <a href="#cli-slash-commands">Slash-Befehle</a> ·
  <a href="#license">Lizenz</a>
</p>

---

## Was ist LMMs OS?

LMMs ist eine native Python-KI-Betriebsschicht für die lokale und dezentrale Ausführung von Sprach- und Multimodalmodellen. Entwickelt von Gründer Raj Singh (MarkanM), vereint es ein vollwertiges Desktop-GUI-Studio, eine intelligente Entwickler-CLI und eine ausgereifte Engine-Laufzeit, damit Entwickler und Unternehmen ohne Telemetrie und Cloud-Zwang arbeiten können.

* **Nativer Dual-Engine-Kern**: Quantisierte GGUF-Inferenz mit hohem Durchsatz via llama.cpp sowie native safetensors-Ausführung in PyTorch.
* **Grenzenlose Skalierung mit AirEngine**: Dynamisches GPU-, CPU- und Festplatten-Tensor-Offloading erlaubt den Betrieb von 70B+-Modellen selbst auf normalen Laptops.
* **Desktop Studio (GUI)**: Monaco-Code-Editor, visuelle Diff-Vergleiche, Git-Integration und integrierte Werkzeugverwaltung.
* **Terminal Studio (CLI)**: Interaktive KI-Shell mit über 30 Slash-Befehlen, Pair-Programming, Subagenten-Orchestrierung und sicherer Sandbox.
* **Enterprise-tauglich**: Client-Server-Clustering in privaten LAN/VPC-Netzwerken mit automatischer Erkennung des zentralen Host-Servers.

---

## Systemarchitektur

Das folgende Diagramm veranschaulicht die End-to-End-Architektur von LMMs OS über Benutzeroberfläche, Backend-Dienste, Modellinferenz und Agentenfähigkeiten:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Benutzeroberflächen**: `GUI workspace [main_window.py]` (Monaco IDE und Diff-Prüfung) und `CLI [commands.py]` (interaktive Entwickler-Shell).
2. **API- und Backend-Ebene**: `HTTP API [server.py]` (FastAPI-Daemon auf Port 11435), `Backend session [main.py]` (Sitzungskoordinator), und `Backend services [manager.py]`.
3. **Modell-Inferenzsystem**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (GPU/CPU/Disk-Offloading), `Model registry [registry.py]`, `llama.cpp Laufzeit` und `PyTorch Laufzeit`.
4. **Agenten-Fähigkeitssystem**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` und `Workspace & Git [manager.py]`.

---

## Tiefgehende Technische Fähigkeiten (Deep Technical Capabilities)

### 1. Multimodale Vision-Engine (`/vision`, `/image`)
LMMs bietet native Bild- und Oberflächenverarbeitung direkt im lokalen System:
* **UI- und Layout-Analyse**: Untersucht Screenshots von Web- und Desktop-Oberflächen, um Darstellungsfehler, Ausrichtungsungenauigkeiten und CSS-Probleme zu erkennen.
* **Diagramm- und Architektur-Extraktion**: Erfasst Flussdiagramme, ER-Diagramme und UML-Sequenzen und übersetzt sie direkt in Mermaid-Code oder Datenstrukturen.
* **Lokale Dokumenten-OCR**: Extrahiert Text und Tabellen aus lokalen Bildern und PDFs, ohne Daten an externe Cloud-Server zu übermitteln.

### 2. Lokale Sprach- und Audioverarbeitung (`/mic`)
* **Offline-Spracherkennung**: Extrem schnelle Transkription dank lokal quantisierter Whisper-Modelle.
* **Freihändiges Prompting**: Sprechen Sie Entwicklungsanweisungen und Notizen direkt mit null Netzwerklatenz in die aktive CLI-Sitzung ein.

### 3. Git-Verständnis und Worktree-Isolation (`/git`, `/scope`)
* **Schreibschutz-Wächter**: Beschränkt Agentenaktionen standardmäßig auf lesende Befehle (`cat`, `git diff`, `grep`), sofern keine Freigabe vorliegt.
* **Flüchtige Git-Worktrees**: Codeänderungen werden in isolierten Klon-Worktrees durchgeführt und erst nach erfolgreichen Tests in den Hauptarbeitszweig übernommen.
* **Farbige Diff-Vorschau**: Jede Dateiänderung erzeugt vor dem Schreiben auf die Festplatte eine einheitliche Diff-Vorschau.

### 4. Deterministische Checkpoints und sofortiger Rollback (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Schrittweise Schnappschüsse**: Vor jeder Dateiänderung wird ein unveränderlicher Backup-Zustand erfasst.
* **Millisekundenschneller Rollback**: Scheitern Tests oder treten Syntaxfehler auf, setzt `/rollback` oder `/undo` das Projekt sofort in den Ursprungszustand zurück.

### 5. Autonome Subagenten und Multi-Agenten-Orchestrierung (`/agent`, `/orchestrate`)
* **Hintergrundaufgaben**: Startet eigenständige Subagenten mit getrennten Token-Budgets und beschränkten Zugriffsrechten.
* **Hierarchische Koordination**: Der Hauptorchestrierer delegiert Spezialaufgaben (Testing, Dokumentation, Refactoring) und führt die Resultate zusammen.

### 6. Lokale Recherche und Vektor-RAG (`/research`)
* **Semantische Code-Indizierung**: Erfasst das Projekt in einer lokalen Vektordatenbank zur schnellen semantischen Suche nach Klassen und Funktionen.
* **Präzise Dokumentenanalyse**: Durchsucht lokale und Web-API-Dokumentation zur Vermeidung von Modell-Halluzinationen.

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

## Architektur-Installationsassistent (`lmms install`)

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

### [1] Konfiguration für Einzelarbeitsplätze

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

### [2] Enterprise-Infrastruktur & Super-Host

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Zentralisierte Rechenleistung**: Der Host-Daemon läuft auf internen GPU-Servern (`0.0.0.0:11435`), um eigene Unternehmensmodelle bereitzustellen.
* **Entfernte Client-Studios**: Teammitglieder verbinden sich von ihren Laptops via automatischer LAN/VPC-Erkennung mit dem Server.
* **Vollständige Datensouveränität**: Kein Quellcode und keine Prompts verlassen das Firmennetzwerk.
* **AirEngine ohne Speichergrenzen**: Nahtloses Streaming riesiger Modellgewichte über VRAM, RAM und NVMe-Speicher.

---

### Pip & Installer Command Matrix

| Befehl | Zweck | Zielkomponente |
|---|---|---|
| `lmms install` | Interaktiven Architektur-Assistenten starten | Interaktives Menü |
| `lmms install --all` | Komplettes Ökosystem installieren | Desktop Studio, CLI, Sprachmodul, Super Engine |
| `lmms install --gui` | Desktop Studio (GUI) installieren | PyQt6 GUI, Monaco Editor, Engine-Client |
| `lmms install --cli` | Terminal Studio (CLI) installieren | Interaktive Shell, Dev-Tools, Engine-Client |
| `lmms install --engine` | Super Engine Laufzeit installieren | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Leichtgewichtige Engine installieren | llama.cpp + AirEngine (nur GGUF) |
| `lmms install --engine2` | PyTorch Engine installieren | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Enterprise Host-Daemon installieren | Zentraler Server-Daemon auf 0.0.0.0:11435 |
| `lmms install --client-gui` | Enterprise Desktop-Client installieren | GUI vorkonfiguriert für LAN/VPC-Host |
| `lmms install --client-cli` | Enterprise Terminal-Client installieren | CLI vorkonfiguriert für LAN/VPC-Host |
| `lmms update` | Neuesten Quellcode abrufen und aktualisieren | Aktualisierung des aktuellen Git-Zweigs |
| `lmms update --all` | Vollständiges Update über alle Zweige | Vollständige Synchronisation mit GitHub |
| `lmms -check` | Hardware- und Voraussetzungsdiagnose | Telemetrie von CPU, GPU, VRAM, AVX und Festplatte |
| `lmms-uninstall -all` | Saubere Deinstallation des Quellcodes | Entfernt Code, behält pip-Pakete und Modelle |
| `lmms-uninstall -all --purge` | Vollständiger Werksreset | Vollständiges Löschen aller Konfigurationen und Modelle |

---

## Befehlsreferenz

### LMMs Core Launcher Commands

| Befehl | Beschreibung |
|---|---|
| `lmms` | Standardmäßig konfiguriertes Interface starten |
| `lmms --gui` | Desktop Studio (GUI) direkt starten |
| `lmms --cli` | Entwickler-CLI direkt im Terminal starten |
| `lmms --engine` | Inferenz-Engine-Daemon direkt starten |
| `lmms set --gui` | Desktop Studio als Standard-Startmodus festlegen |
| `lmms set --cli` | Terminal Studio als Standard-Startmodus festlegen |
| `lmms set --engine` | Engine Daemon als Standard-Startmodus festlegen |
| `lmms stop` | Laufende LMMs-Hintergrund-Engine sauber stoppen |
| `lmms -check` | Hardwareprofil und Systemvoraussetzungen prüfen |
| `lmms update` | Intelligente Aktualisierung aus aktuellem Zweig |
| `lmms update --all` | Vollständiges Update von GitHub erzwingen |
| `lmms --help` | Ausführliche Hilfe des Launchers anzeigen |

---

### Engine Runtime & Air Engine

| Befehl | Beschreibung |
|---|---|
| `lmms run <model>` | Modell im Chat oder für Einzelanfragen ausführen |
| `lmms list` | Lokal heruntergeladene Modelle auflisten |
| `lmms ps` | Aktive Modelle, Speicherbelegung und VRAM anzeigen |
| `lmms pull <model>` | Modell von Hugging Face oder dem Modell-Hub laden |
| `lmms info <model>` | Metadaten, Kontextfenster und Quantisierung prüfen |
| `lmms search <query>` | Verfügbare Modell-Repositories durchsuchen |
| `lmms benchmark <model>` | Generierungsgeschwindigkeit (t/s) und Latenz messen |
| `lmms doctor` | Engine-Zustand prüfen und CUDA/Treiberprobleme diagnostizieren |
| `lmms create <model> -f <file>` | Eigenes Modell aus GGUF, Safetensors oder Manifest registrieren |
| `lmms -air run <model> [prompt]` | Riesige Modelle mit dynamischem AirEngine-Offloading ausführen |
| `lmms --air run <m1> <m2>` | Mehrere Modelle gleichzeitig über den Air-Scheduler betreiben |
| `lmms air ps` | Aktive Air-Modelle und Schichtenverteilung anzeigen |
| `lmms air stats` | Echtzeit-Hardwaretelemetrie und Offloading-Werte abrufen |
| `lmms air cache` | Größe und Belegung des Air-Festplatten-Caches einsehen |
| `lmms air unload` | Alle Air-Modelle entladen und VRAM-Cache sofort leeren |
| `lmms air benchmark <model>` | Durchsatz unter dem Air-Offload-Scheduler messen |

---

### Server / Daemon

| Befehl | Beschreibung |
|---|---|
| `lmms server` | API- und Webserver-Daemon starten |
| `lmms server status` | Serverstatus, Port, Betriebszeit und Zustand prüfen |
| `lmms engine status` | Aktiven Engine-Modus und Speicherwerte anzeigen |
| `lmms engine unload [model]` | Modelle aus dem Arbeitsspeicher entfernen und VRAM freigeben |
| `lmms server start [--port 11435]` | FastAPI-Daemon im Hintergrund auf Port starten |
| `lmms server stop` | Laufenden Hintergrund-Server stoppen |

---

## Interaktive CLI Slash-Befehle

| Befehl | Beschreibung |
|---|---|
| `/fast` | In den FAST-Modus für schnelle Antworten und schlanke Tools wechseln |
| `/deep` | In den DEEP-Modus mit mehrstufigem Denken und vollen Toolrechten wechseln |
| `/model <name>` | Modell für die aktuelle Unterhaltung wechseln |
| `/ml -l` | Alle lokal heruntergeladenen Modelle direkt im Chat auflisten |
| `/ml -s <name>` | Modell bei Beibehaltung des Chat-Verlaufs im laufenden Betrieb wechseln |
| `/folder <path>` | Verzeichnis an den Arbeitskontext des Agenten anhängen |
| `/code` | In den fokussierten Code-Generierungs- und Bearbeitungsmodus wechseln |
| `/chat` | Bisherige Chat-Sitzungen auflisten und überprüfen |
| `/newchat` | Eine neue, leere Chat-Sitzung beginnen |
| `/chat -r <id> <name>` | Bestimmte Chat-Sitzung umbenennen |
| `/chat -d <id>` | Bestimmte Chat-Sitzung dauerhaft löschen |
| `/undo` | Letzte Dateiänderung oder Patch der KI sicher rückgängig machen |
| `/redo` | Zuletzt rückgängig gemachte Dateiaktion wiederherstellen |
| `/exit` | Interaktive CLI-Sitzung beenden |
| `/reboot` | Backend-Engine neu starten und Verbindung wiederherstellen |
| `/mic` | Spracheingabe aufnehmen und direkt in den Prompt transkribieren |
| `/vision oder /image` | In den multimodalen Bildanalyse- und UI-Modus wechseln |
| `/research` | In den Recherche-Modus für Web- und Dokumentationssuche wechseln |
| `/read <file>` | Beliebige Arbeitsdatei direkt in den Kontext einlesen |
| `/task` | Autonome Hintergrundaufgaben und Unterziele verwalten |
| `/git` | Sichere, auditierte Git-Aktionen über den Agenten ausführen |
| `/scope` | Gültigkeitsbereich der Werkzeugberechtigungen einsehen und anpassen |
| `/tools list` | Alle nativen Werkzeuge und aktiven MCP-Endpunkte auflisten |
| `/report` | Kryptografisch signierten Sicherheits- und Aktionsprüfbericht erstellen |
| `/checkpoint` | Unveränderlichen Prüfpunkt des Arbeitsbereichszustands sichern |
| `/checkpoints` | Alle gespeicherten Prüfpunkte des Projekts auflisten |
| `/rollback` | Projekt und Dateien auf einen früheren Prüfpunkt zurücksetzen |
| `/status` | Echtzeitzustand von Engine und Hardware überprüfen |
| `/doctor` | Umfassende Systemdiagnose und Selbstreparaturtests ausführen |
| `/pair` | Interaktiven Pair-Programming-Modus aktivieren |
| `/perm <level>` | Berechtigungsstufe der Sandbox anpassen (`strict`, `ask`, `full`) |
| `/agent` | Autonome Subagenten für parallele Ausführung erzeugen und steuern |
| `/orchestrate` | Koordinierte Arbeitsabläufe mehrerer Agenten verwalten |

---

## Produktphilosophie

1. **Echter Nutzen an erster Stelle**: Präzise Code-Patches, AST-Prüfung und sichere Sandbox-Ausführung.
2. **Transparenz und Ehrlichkeit**: Keine Telemetrie, keine versteckten Abos oder Bezahlschranken.
3. **Kompromisslos lokal**: Alle Modelle, Gewichte und Daten bleiben auf Ihrer Hardware.
4. **Minimalistischer Stack**: Reine Python-Architektur ohne überflüssigen Ballast.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
