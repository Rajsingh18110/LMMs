<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Construisez avec des modèles. Déployez avec des agents.</strong><br>
  <em>Le système d'exploitation IA local natif en Python par le fondateur Raj Singh (MarkanM)</em>
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
[![Français](https://img.shields.io/badge/Language-Français-2563eb?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">Site Officiel</a> ·
  <a href="#system-architecture">Architecture Système</a> ·
  <a href="#deep-technical-capabilities">Capacités Clés</a> ·
  <a href="#quick-start">Démarrage Rapide</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Assistant d'Installation</a> ·
  <a href="#enterprise-infrastructure--super-host">Entreprise</a> ·
  <a href="#core-command-reference">Répertoire des Commandes</a> ·
  <a href="#cli-slash-commands">Commandes Slash</a> ·
  <a href="#license">Licence</a>
</p>

---

## Qu'est-ce que LMMs OS ?

LMMs est une couche d'exploitation IA native en Python pour l'exécution locale et distante de modèles. Conçu par le fondateur Raj Singh (MarkanM), il combine un véritable studio graphique de bureau, une CLI intelligente et un moteur d'exécution éprouvé afin que développeurs et entreprises puissent exécuter de grands modèles multimodaux sans aucune télémétrie ni dépendance cloud.

* **Noyau à double moteur natif** : Inférence GGUF quantifiée haute performance via llama.cpp et exécution native safetensors en PyTorch.
* **Mise à l'échelle infinie avec AirEngine** : Le déchargement dynamique des tenseurs entre GPU, CPU et disque permet d'exécuter des modèles de 70B+ même sur des ordinateurs portables ordinaires.
* **Studio de bureau (GUI)** : Éditeur de code Monaco, comparaisons visuelles diff, intégration Git et gestionnaire d'outils intégré.
* **Studio de terminal (CLI)** : Shell IA interactif avec plus de 30 commandes slash, programmation en binôme, orchestration de sous-agents et bac à sable sécurisé.
* **Prêt pour l'entreprise** : Déploiement en cluster client-serveur sur réseau privé LAN/VPC avec détection automatique de l'hôte central.

---

## Architecture du Système

Le schéma suivant illustre l'architecture de bout en bout de LMMs OS à travers ses quatre sous-systèmes principaux :

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Interfaces Utilisateur** : `GUI workspace [main_window.py]` (IDE Monaco et révision diff) et `CLI [commands.py]` (terminal interactif pour développeur).
2. **API et Couche Backend** : `HTTP API [server.py]` (démon FastAPI sur le port 11435), `Backend session [main.py]` (coordinateur de session), et `Backend services [manager.py]`.
3. **Sous-système d'Inférence** : `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (déchargement de tenseurs GPU/CPU/Disque), `Model registry [registry.py]`, `moteur llama.cpp` et `moteur PyTorch`.
4. **Sous-système de Capacités d'Agent** : `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` et `Workspace & Git [manager.py]`.

---

## Capacités Techniques Avancées (Deep Technical Capabilities)

### 1. Moteur de Vision Multimodale (`/vision`, `/image`)
LMMs intègre un traitement multimodal natif directement dans son moteur local :
* **Analyse d'interface utilisateur et de mise en page** : Inspecte les captures d'écran web ou desktop pour identifier les bugs visuels, défauts d'alignement et anomalies CSS.
* **Extraction de diagrammes et d'architectures** : Analyse les organigrammes, diagrammes ER et diagrammes de séquence UML pour les transcrire directement en structures Mermaid ou en code.
* **OCR de documents et extraction** : Extrait proprement le texte et les tableaux depuis des images et PDF locaux sans envoyer le moindre octet dans le cloud.

### 2. Audio et Voix Hors-Ligne (`/mic`)
* **Reconnaissance vocale locale** : Transcription hors-ligne ultra-rapide alimentée par des modèles Whisper quantifiés exécutés en local.
* **Invites mains-libres** : Enregistrez directement vos instructions de code et notes vocales dans la session CLI active avec une latence réseau nulle.

### 3. Moteur Git Contextuel et Isolation par Worktree (`/git`, `/scope`)
* **Garde de sécurité Lecture Seule** : Restreint automatiquement les opérations de l'agent aux commandes de lecture (`cat`, `git diff`, `grep`) sauf autorisation explicite.
* **Worktrees Git Éphémères** : Les modifications de code sont appliquées dans des clones worktree isolés ; elles ne sont fusionnées dans la branche active qu'après validation complète des tests.
* **Aperçu visuel Diff** : Chaque modification génère une comparaison unifiée en couleur avant toute écriture sur le disque.

### 4. Points de Contrôle Déterministes et Restauration Immédiate (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Snapshots par tour d'action** : Un instantané immuable des fichiers modifiés est sauvegardé avant chaque opération altérant le code.
* **Restauration en quelques millisecondes** : Si un patch généré échoue aux tests ou crée une erreur de syntaxe, `/rollback` ou `/undo` rétablit le dépôt dans son état d'origine exact.

### 5. Sous-Agents Autonomes et Orchestration Multi-Agents (`/agent`, `/orchestrate`)
* **Tâches en arrière-plan** : Déclenche des sous-agents autonomes avec budgets de tokens dédiés et permissions restreintes.
* **Coordination hiérarchique** : L'orchestrateur principal délègue des tâches spécialisées (tests, documentation, linting) aux sous-agents et consolide les résultats validés.

### 6. Recherche Locale et RAG Vectoriel (`/research`)
* **Indexation sémantique du code** : Indexe le projet dans un magasin vectoriel local pour retrouver instantanément fonctions, classes et types.
* **Recherche documentaire ciblée** : Analyse la documentation technique locale et web pour éliminer les hallucinations de code.

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

## Assistant d'Installation d'Architecture (`lmms install`)

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

### [1] Configuration pour Station de Travail Individuelle

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

### [2] Infrastructure Entreprise et Hôte Central

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Calcul intensif centralisé** : Le démon hôte s'exécute sur le serveur GPU central (`0.0.0.0:11435`) pour héberger et entraîner les modèles internes.
* **Postes clients distants** : Les collaborateurs s'y connectent depuis leurs ordinateurs portables via détection automatique sur réseau LAN/VPC.
* **Confidentialité totale des données** : Aucun code source ni prompt ne quitte le réseau privé de l'entreprise.
* **AirEngine sans contrainte mémoire** : Diffusion dynamique des poids de modèle sur VRAM, RAM et NVMe.

---

### Pip & Installer Command Matrix

| Commande | Objectif | Composant Cible |
|---|---|---|
| `lmms install` | Lancer l'assistant interactif d'architecture | Menu de configuration interactif |
| `lmms install --all` | Installer l'écosystème complet | Studio GUI, CLI, Audio, Super Engine |
| `lmms install --gui` | Installer le Studio de Bureau (GUI) | Interface PyQt6, Éditeur Monaco, Client moteur |
| `lmms install --cli` | Installer le Studio Terminal (CLI) | Shell interactif, outils dev, Client moteur |
| `lmms install --engine` | Installer le runtime Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Installer le moteur léger | llama.cpp + AirEngine (dédié GGUF) |
| `lmms install --engine2` | Installer le moteur PyTorch | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Installer le démon hôte d'entreprise | Serveur central écoutant sur 0.0.0.0:11435 |
| `lmms install --client-gui` | Installer le client GUI d'entreprise | GUI configurée pour se connecter à l'hôte distant |
| `lmms install --client-cli` | Installer le client CLI d'entreprise | CLI configurée pour se connecter à l'hôte distant |
| `lmms update` | Mettre à jour le code source | Mise à jour de la branche active |
| `lmms update --all` | Mise à jour complète multi-branches | Synchronisation intégrale avec GitHub |
| `lmms -check` | Diagnostics matériels et dépendances | Télémétrie CPU, GPU, VRAM, AVX et disque |
| `lmms-uninstall -all` | Désinstallation sécurisée du code | Supprime le code, préserve pip et les modèles |
| `lmms-uninstall -all --purge` | Réinitialisation d'usine totale | Suppression définitive de toutes les configurations et modèles |

---

## Répertoire des Commandes Principales

### LMMs Core Launcher Commands

| Commande | Description |
|---|---|
| `lmms` | Lancer l'interface par défaut configurée |
| `lmms --gui` | Lancer directement le studio de bureau GUI |
| `lmms --cli` | Lancer directement le shell CLI interactif |
| `lmms --engine` | Lancer directement le démon du moteur d'inférence |
| `lmms set --gui` | Définir le studio GUI comme mode de démarrage par défaut |
| `lmms set --cli` | Définir le studio CLI comme mode de démarrage par défaut |
| `lmms set --engine` | Définir le démon Engine comme mode de démarrage par défaut |
| `lmms stop` | Arrêter proprement le moteur LMMs en arrière-plan |
| `lmms -check` | Vérifier le profil matériel et les prérequis système |
| `lmms update` | Mise à jour intelligente depuis la branche actuelle |
| `lmms update --all` | Forcer la mise à jour complète depuis GitHub |
| `lmms --help` | Afficher l'aide complète du lanceur |

---

### Engine Runtime & Air Engine

| Commande | Description |
|---|---|
| `lmms run <model>` | Exécuter un modèle en mode interactif ou invite unique |
| `lmms list` | Lister les modèles téléchargés localement |
| `lmms ps` | Afficher les modèles actifs, l'allocation et l'usage VRAM |
| `lmms pull <model>` | Télécharger un modèle depuis Hugging Face ou le Hub officiel |
| `lmms info <model>` | Inspecter les métadonnées, la fenêtre de contexte et la quantification |
| `lmms search <query>` | Rechercher parmi les dépôts de modèles disponibles |
| `lmms benchmark <model>` | Mesurer la vitesse de génération (tokens/s) et la latence |
| `lmms doctor` | Vérifier l'état du moteur et diagnostiquer les pilotes CUDA/GPU |
| `lmms create <model> -f <file>` | Enregistrer un modèle personnalisé depuis GGUF ou Safetensors |
| `lmms -air run <model> [prompt]` | Exécuter des modèles géants via le déchargement dynamique AirEngine |
| `lmms --air run <m1> <m2>` | Exécuter plusieurs modèles simultanément via le planificateur Air |
| `lmms air ps` | Afficher les modèles Air actifs et la répartition des couches GPU/CPU |
| `lmms air stats` | Consulter la télémétrie matérielle et les statistiques de déchargement |
| `lmms air cache` | Vérifier la taille et l'utilisation du cache disque Air |
| `lmms air unload` | Décharger tous les modèles Air et vider immédiatement le cache VRAM |
| `lmms air benchmark <model>` | Évaluer le débit de génération sous le planificateur Air |

---

### Server / Daemon

| Commande | Description |
|---|---|
| `lmms server` | Démarrer le démon serveur API / Web |
| `lmms server status` | Vérifier le statut du serveur, port d'écoute, uptime et santé |
| `lmms engine status` | Consulter le mode actif du moteur et l'utilisation mémoire |
| `lmms engine unload [model]` | Décharger les modèles de la mémoire et libérer la VRAM |
| `lmms server start [--port 11435]` | Lancer le démon FastAPI en arrière-plan sur le port indiqué |
| `lmms server stop` | Arrêter le démon serveur en arrière-plan |

---

## Commandes Interactives Slash CLI

| Commande | Description |
|---|---|
| `/fast` | Passer en mode FAST pour des réponses rapides et des outils légers |
| `/deep` | Passer en mode DEEP avec raisonnement multi-étapes et accès complet aux outils |
| `/model <name>` | Changer de modèle pour la conversation active |
| `/ml -l` | Lister tous les modèles téléchargés localement dans le chat |
| `/ml -s <name>` | Basculer de modèle à chaud tout en conservant l'historique de discussion |
| `/folder <path>` | Attacher un dossier au contexte de travail de l'agent |
| `/code` | Entrer dans le mode dédié à la génération et l'édition de code |
| `/chat` | Lister et examiner l'historique des sessions de discussion |
| `/newchat` | Démarrer une nouvelle session de chat vide |
| `/chat -r <id> <name>` | Renommer une session de discussion existante |
| `/chat -d <id>` | Supprimer définitivement une session de discussion |
| `/undo` | Annuler en toute sécurité la dernière modification de fichier effectuée par l'IA |
| `/redo` | Rétablir la dernière action de fichier annulée |
| `/exit` | Quitter la session interactive du terminal |
| `/reboot` | Redémarrer le moteur backend et rétablir la connexion |
| `/mic` | Enregistrer la voix au micro et transcrire en direct dans l'invite |
| `/vision ou /image` | Activer le mode vision multimodale pour l'analyse d'images et d'UI |
| `/research` | Activer le mode recherche pour explorer le web et la documentation |
| `/read <file>` | Charger un fichier du projet directement dans le contexte de session |
| `/task` | Gérer les tâches autonomes et sous-objectifs en arrière-plan |
| `/git` | Exécuter des commandes Git sécurisées et auditées via l'agent |
| `/scope` | Inspecter et ajuster les limites d'accès des outils |
| `/tools list` | Lister l'ensemble des outils natifs et serveurs MCP disponibles |
| `/report` | Générer un rapport d'audit cryptographique des actions et de sécurité |
| `/checkpoint` | Créer un point de contrôle immuable de l'état actuel de l'espace de travail |
| `/checkpoints` | Lister l'ensemble des points de contrôle sauvegardés |
| `/rollback` | Restaurer le dépôt et les fichiers à un point de contrôle antérieur |
| `/status` | Vérifier la santé en temps réel du moteur et du matériel |
| `/doctor` | Lancer un diagnostic complet du système et des tests d'autoréparation |
| `/pair` | Activer le mode de programmation en binôme interactif |
| `/perm <level>` | Régler le niveau de permission du bac à sable (`strict`, `ask`, `full`) |
| `/agent` | Créer et gérer des sous-agents autonomes pour l'exécution parallèle |
| `/orchestrate` | Superviser les flux de travail coordonnés multi-agents |

---

## Philosophie du Produit

1. **Privilégier l'Utilité Réelle** : Application de correctifs de code, validation AST et tâches sécurisées en sandbox.
2. **Transparence Totale** : Zéro télémétrie, aucun abonnement caché.
3. **Local-First Intégral** : Tous vos modèles, poids et jetons restent sur vos propres machines.
4. **Architecture Épurée** : Une conception en Python pur sans couches superflues.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
