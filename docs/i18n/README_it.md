<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Costruisci con i modelli. Distribuisci con gli agenti.</strong><br>
  <em>Il sistema operativo IA locale nativo in Python del fondatore Raj Singh (MarkanM)</em>
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
  <a href="#system-architecture">Architettura</a> ·
  <a href="#deep-technical-capabilities">Funzionalità Chiave</a> ·
  <a href="#quick-start">Guida Rapida</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Procedura Guidata</a> ·
  <a href="#enterprise-infrastructure--super-host">Aziendale</a> ·
  <a href="#core-command-reference">Guida ai Comandi</a> ·
  <a href="#cli-slash-commands">Comandi Slash</a> ·
  <a href="#license">Licenza</a>
</p>

---

## Cos'è LMMs OS?

LMMs è uno strato operativo IA nativo in Python per l'esecuzione di modelli locali e remoti. Progettato dal fondatore Raj Singh (MarkanM), combina un autentico studio desktop GUI, una CLI avanzata e un motore affidabile per consentire l'esecuzione di modelli multimodali senza alcuna telemetria né vincoli cloud.

* **Doppio motore nativo**: Inferenza GGUF quantizzata ad alta velocità con llama.cpp ed esecuzione nativa safetensors in PyTorch.
* **Scalabilità infinita con AirEngine**: L'offloading dinamico dei tensori tra GPU, CPU e disco consente di eseguire modelli da 70B+ anche su normali computer portatili.
* **Studio Desktop (GUI)**: Editor di codice Monaco, comparazione visiva diff, integrazione Git e gestione strumenti integrata.
* **Studio Terminale (CLI)**: Shell interattiva con più di 30 comandi slash, programmazione in coppia, orchestrazione di sotto-agenti e sandbox protetta.
* **Pronto per l'Azienda**: Architettura distribuita client-server su reti private LAN/VPC con rilevamento automatico dell'host centrale.

---

## Architettura di Sistema

Il diagramma seguente mostra l'architettura completa di LMMs OS attraverso i quattro sottosistemi principali:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Interfacce Utente**: `GUI workspace [main_window.py]` (IDE Monaco e revisione diff) e `CLI [commands.py]` (terminale interattivo di sviluppo).
2. **API e Livello Backend**: `HTTP API [server.py]` (demone FastAPI su porta 11435), `Backend session [main.py]` (coordinatore delle sessioni), e `Backend services [manager.py]`.
3. **Sottosistema di Inferenza**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (offloading GPU/CPU/Disco), `Model registry [registry.py]`, `runtime llama.cpp` e `runtime PyTorch`.
4. **Sottosistema delle Capacità dell'Agente**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` e `Workspace & Git [manager.py]`.

---

## Capacità Tecniche Avanzate (Deep Technical Capabilities)

### 1. Motore di Visione Multimodale (`/vision`, `/image`)
LMMs integra elaborazione multimodale nativa direttamente nel motore locale:
* **Analisi di Interfaccia e Layout**: Ispeziona screenshot di app web o desktop per rilevare errori visivi, disallineamenti e bug CSS.
* **Estrazione di Schemi e Architetture**: Analizza diagrammi di flusso, schemi ER e sequenze UML, traducendoli in codice Mermaid o strutture dati.
* **OCR Locale di Documenti**: Estrae testo e tabelle da immagini e file PDF senza inviare alcun dato al cloud.

### 2. Audio e Voce Offline (`/mic`)
* **Trascrizione Vocale Locale**: Riconoscimento vocale ultraveloce e offline tramite modelli Whisper quantizzati in locale.
* **Istruzioni a Mani Libere**: Registra note e comandi di codice direttamente nella sessione CLI attiva a latenza zero.

### 3. Consapevolezza Git e Isolamento Worktree (`/git`, `/scope`)
* **Guardia di Sola Lettura**: Limita le operazioni dell'agente a comandi sicuri (`cat`, `git diff`, `grep`) salvo autorizzazione esplicita.
* **Worktree Git Temporanei**: Le modifiche al codice avvengono in cloni isolati e vengono unite al ramo principale solo dopo il superamento dei test.
* **Anteprima Diff a Colori**: Ogni modifica genera un'anteprima unificata prima del salvataggio su disco.

### 4. Punti di Ripristino Deterministici e Rollback Immediato (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Snapshot per Turno**: Viene registrato un backup immutabile dei file prima di qualsiasi modifica invasiva.
* **Ripristino Istantaneo**: Se una patch fallisce o crea errori di sintassi, `/rollback` o `/undo` riporta il codice allo stato esatto precedente.

### 5. Sotto-Agenti Autonomi e Orchestrazione Multi-Agente (`/agent`, `/orchestrate`)
* **Attività in Background**: Avvia sotto-agenti indipendenti con quote dedicate di token e permessi circoscritti.
* **Coordinamento Gerarchico**: L'orchestratore principale assegna compiti specifici (test, documentazione, linting) e ne unifica gli esiti convalidati.

### 6. Ricerca Locale e RAG Vettoriale (`/research`)
* **Indicizzazione Semantica del Codice**: Crea un indice vettoriale del progetto per rintracciare rapidamente classi e funzioni.
* **Consultazione Documentale Precisa**: Analizza documentazione tecnica locale e web eliminando le allucinazioni del modello.

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

## Installazione Guidata dell'Architettura (`lmms install`)

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

### [1] Configurazione per Singola Stazione di Lavoro

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

### [2] Infrastruttura Aziendale e Super Host

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Calcolo Centralizzato**: Il demone server opera su GPU aziendali dedicate (`0.0.0.0:11435`) per servire modelli interni.
* **Postazioni Client Remote**: I collaboratori si connettono dai portatili con rilevamento automatico su rete LAN/VPC.
* **Tutela Assoluta dei Dati**: Nessun codice sorgente né richiesta esce mai dalla rete privata dell'organizzazione.
* **AirEngine senza Vincoli di RAM**: Streaming dinamico dei pesi dei modelli su VRAM, RAM e memoria NVMe.

---

### Pip & Installer Command Matrix

| Comando | Scopo | Componente Destinazione |
|---|---|---|
| `lmms install` | Avvia la procedura guidata per la selezione dell'architettura | Menu di configurazione interattivo |
| `lmms install --all` | Installa l'intero ecosistema | Studio Desktop, CLI, Modulo Vocale, Super Engine |
| `lmms install --gui` | Installa lo Studio Desktop (GUI) | Interfaccia PyQt6, Editor Monaco, Client del motore |
| `lmms install --cli` | Installa lo Studio da Terminale (CLI) | Shell interattiva, strumenti dev, Client del motore |
| `lmms install --engine` | Installa il runtime Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Installa il motore leggero | llama.cpp + AirEngine (solo GGUF) |
| `lmms install --engine2` | Installa il motore PyTorch | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Installa il demone host aziendale | Server centrale in ascolto su 0.0.0.0:11435 |
| `lmms install --client-gui` | Installa il client GUI aziendale | GUI preconfigurata per la connessione remota su LAN |
| `lmms install --client-cli` | Installa il client CLI aziendale | CLI preconfigurata per la connessione remota su LAN |
| `lmms update` | Scarica e applica gli aggiornamenti del codice | Aggiornamento del ramo Git attivo |
| `lmms update --all` | Aggiornamento forzato su tutti i rami | Sincronizzazione completa con GitHub |
| `lmms -check` | Diagnostica hardware e prerequisiti | Telemetria di CPU, GPU, VRAM, AVX e disco |
| `lmms-uninstall -all` | Rimozione sicura del codice sorgente | Rimuove il codice, preserva librerie pip e modelli |
| `lmms-uninstall -all --purge` | Ripristino completo alle impostazioni di fabbrica | Cancellazione definitiva di configurazioni, modelli e dati |

---

## Guida ai Comandi Principali

### LMMs Core Launcher Commands

| Comando | Descrizione |
|---|---|
| `lmms` | Avvia l'interfaccia predefinita impostata |
| `lmms --gui` | Avvia direttamente lo studio desktop GUI |
| `lmms --cli` | Avvia direttamente la shell interattiva per sviluppatori |
| `lmms --engine` | Avvia direttamente il demone del motore di inferenza |
| `lmms set --gui` | Imposta Desktop Studio come modalità di avvio predefinita |
| `lmms set --cli` | Imposta Terminal Studio come modalità di avvio predefinita |
| `lmms set --engine` | Imposta Engine Daemon come modalità di avvio predefinita |
| `lmms stop` | Arresta correttamente il demone del motore LMMs in background |
| `lmms --help` | Mostra la guida completa del launcher |

---

### Runtime del Motore e Gestione dei Modelli

| Comando | Descrizione |
|---|---|
| `lmms run <model>` | Esegue il modello in chat interattiva o prompt singolo |
| `lmms stop <model>` | Arresta un'istanza del modello attualmente in esecuzione |
| `lmms list` | Elenca i modelli scaricati localmente |
| `lmms ps` | Mostra i modelli attivi, l'allocazione e la VRAM usata |
| `lmms pull <model>` | Scarica un modello da Hugging Face o dall'Hub ufficiale |
| `lmms info <model>` | Esamina i metadati, la finestra di contesto e la quantizzazione |
| `lmms rm <model>` | Elimina un modello memorizzato localmente |
| `lmms search <query>` | Cerca nei repository di modelli disponibili |
| `lmms benchmark <model>` | Misura la velocità di generazione (token/s) e la latenza |
| `lmms doctor [--fix]` | Controllo dello stato, riparazione automatica di problemi minori e verifica CUDA |
| `lmms create <model> -f <file>` | Registra un modello personalizzato da file GGUF o Safetensors |

---

### Air Engine (Scambio Intelligente di RAM/VRAM)

Esegui modelli enormi che superano la VRAM fisica tramite l'offloading ibrido dinamico GPU/CPU/Disco.

| Comando | Descrizione |
|---|---|
| `lmms -air run <model> [prompt]` | Esegue modelli giganti tramite offloading dinamico AirEngine |
| `lmms --air run <m1> <m2>` | Esegue più modelli contemporaneamente tramite lo scheduler Air |
| `lmms air ps` | Visualizza le sessioni Air attive e la distribuzione GPU/CPU |
| `lmms air stats` | Consulta telemetria hardware in tempo reale e statistiche Air |
| `lmms air cache` | Verifica dimensioni e utilizzo della cache su disco di Air |
| `lmms air unload` | Scarica tutti i modelli Air e svuota la cache della VRAM |
| `lmms air benchmark <model>` | Valuta la velocità di elaborazione sotto lo scheduler Air |

---

### Server / Daemon

| Comando | Descrizione |
|---|---|
| `lmms server` | Avvia il demone del server API / Web |
| `lmms server status` | Verifica stato del server, porta, tempo di attività e salute |
| `lmms engine status` | Controlla la modalità del motore attiva e l'uso della memoria |
| `lmms engine unload [model]` | Scarica i modelli dalla memoria e libera la VRAM |
| `lmms server start [--port 11435]` | Avvia il demone FastAPI in background sulla porta indicata |
| `lmms server stop` | Arresta il demone del server in background |

---

## Comandi Interattivi Slash CLI

| Comando | Descrizione |
|---|---|
| `/fast` | Passa alla modalità FAST con risposte rapide e strumenti leggeri |
| `/deep` | Passa alla modalità DEEP con ragionamento approfondito e pieno accesso agli strumenti |
| `/model <name>` | Cambia il modello utilizzato per la conversazione corrente |
| `/ml -l` | Elenca tutti i modelli scaricati localmente direttamente nella chat |
| `/ml -s <name>` | Cambia modello a caldo preservando la cronologia della conversazione |
| `/folder <path>` | Collega una cartella al contesto di lavoro dell'agente |
| `/code` | Entra nella modalità dedicata alla generazione e modifica di codice |
| `/chat` | Elenca e visualizza la cronologia delle sessioni di chat precedenti |
| `/newchat` | Avvia una nuova sessione di chat vuota |
| `/chat -r <id> <name>` | Rinomina una sessione di chat specifica |
| `/chat -d <id>` | Elimina definitivamente una sessione di chat |
| `/undo` | Annulla in sicurezza l'ultima modifica ai file eseguita dall'IA |
| `/redo` | Ripristina l'ultima modifica ai file annullata |
| `/exit` | Esci dalla sessione interattiva da terminale |
| `/reboot` | Riavvia il motore backend e ricollega la sessione |
| `/mic` | Registra la voce dal microfono e trascrivi direttamente nel prompt |
| `/vision o /image` | Attiva la modalità visiva multimodale per l'analisi di immagini e UI |
| `/research` | Attiva la modalità ricerca per consultare web e documentazione tecnica |
| `/read <file>` | Carica un file del workspace direttamente nel contesto della sessione |
| `/task` | Gestisci attività autonome e sotto-obiettivi in background |
| `/git` | Esegui comandi Git sicuri e verificabili tramite l'agente |
| `/scope` | Esamina e modifica i limiti operativi degli strumenti |
| `/tools list` | Mostra tutti gli strumenti nativi e i server MCP disponibili |
| `/report` | Genera un rapporto crittografico di audit per le azioni eseguite |
| `/checkpoint` | Crea un punto di controllo immutabile dello stato del progetto |
| `/checkpoints` | Elenca tutti i punti di controllo salvati |
| `/rollback` | Ripristina il repository e i file a un punto di controllo precedente |
| `/status` | Verifica lo stato di salute in tempo reale di motore e hardware |
| `/doctor` | Esegue test approfonditi di diagnosi e autoriparazione del sistema |
| `/pair` | Attiva la modalità di programmazione in coppia interattiva |
| `/perm <level>` | Imposta il livello di autorizzazioni della sandbox (`strict`, `ask`, `full`) |
| `/agent` | Crea e gestisci sotto-agenti autonomi per l'elaborazione parallela |
| `/orchestrate` | Coordina flussi di lavoro complessi tra più agenti |

---

## Filosofia del Prodotto

1. **Utilità Concreta al Primo Posto**: Patch di codice reali, verifica sintattica AST ed esecuzione protetta in sandbox.
2. **Trasparenza e Affidabilità**: Nessuna telemetria, nessun costo nascosto o abbonamento obbligatorio.
3. **Autenticamente Locale**: Tutti i tuoi modelli, pesi e file restano sui tuoi dispositivi.
4. **Architettura Pulita**: Scritto interamente in puro Python senza dipendenze superflue.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
