# LMMs Unified Architecture
```text
==================================================
       ██╗     ███╗   ███╗███╗   ███╗███████╗
       ██║     ████╗ ████║████╗ ████║██╔════╝
       ██║     ██╔████╔██║██╔████╔██║███████╗
       ██║     ██║╚██╔╝██║██║╚██╔╝██║╚════██║
       ███████╗██║ ╚═╝ ██║██║ ╚═╝ ██║███████║
       ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝
==================================================
```

LMMs is an advanced, multi-component agentic AI ecosystem natively designed to integrate directly with OS-level capabilities and automated browser testing. This repository serves as the master monorepo for all LMMs components, fully decoupling the source code into optimized standalone binaries.

## 📦 Architecture Components
This repository compiles into **4 distinct applications** dynamically based on your needs:
- **LMMs-All-in-One (`LMMs`)**: The core application merging Engine, Backend, CLI, and GUI together.
- **LMMs-Engine**: The AI execution layer utilizing PyTorch and LLaMA integrations.
- **LMMs-Backend**: The brain of the AI agent which interprets user commands and manages OS tools.
- **LMMs-GUI**: The frontend PyQt6 graphical user interface.

---

## 🛠️ Installation

LMMs now uses a unified pip-based package manager. You don't need to manually clone this repository or compile any code. The **LMMs-builder** will automatically download the correct pre-compiled standalone binary for your OS (Windows, Mac, or Linux).

```bash
# 1. Install the official LMMs Builder package
pip install LMMs-builder

# 2. Check compatibility
LMMs-builder -check

# 3. Install LMMs
LMMs-builder install --all
```

---

## 💻 Commands Reference

### 1) Builder / Installer Commands
The standalone `LMMs-builder` application controls your entire installation securely.

* `LMMs-builder -check` : Automatically detects OS, hardware compatibility, and installed LMMs components.
* `LMMs-builder install --<component>` : Downloads and installs a specific standalone component (`--engine`, `--backend`, `--gui`).
* `LMMs-builder install --all` : Downloads and installs the entire merged LMMs ecosystem.

### 2) Repair & Rebuild
These commands help you manage corruption without losing precious data.
* `LMMs-repair LMMs -<component>` : Repairs a corrupted component seamlessly without deleting your saved data (chats, persona, models, db).
* `LMMs-rebuild LMMs` : **Factory Reset**. Completely deletes the LMMs project and ALL your saved user data, then installs a fresh copy.
* `LMMs-rebuild LMMs -ds` : **Data-Safe Reset**. Rebuilds the code structure and standalone apps but keeps your saved user data, downloaded models, and persona files intact.

### 3) Uninstall
* `LMMs-uninstall --<component>` : Deletes a specific component from your system.
* `LMMs-uninstall -all --purge` : Completely removes all LMMs binaries, code, and user data from your PC. **Use with caution!**

### 4) LMMs Core Launcher Commands
Once installed, the `LMMs` standalone app routes traffic to the engine, CLI, or GUI depending on your preference.

* `LMMs -set --gui` | `--cli` | `--engine` : Sets the default component that starts when you simply type `LMMs`.
* `LMMs --gui` | `--cli` | `--engine` : Directly runs the specified component for this session (overriding the default).
* `LMMs` : Runs your configured default component.
* `LMMs-cl` : Shows the complete command list.

---

## 🚀 Automated CI/CD (GitHub Actions)
Every push to the `main` branch triggers our powerful GitHub Actions pipeline. The CI/CD automatically:
1. Compiles the python code into **4 distinct `.exe` (Windows), Linux, and macOS binaries** using PyInstaller.
2. Uploads the 12 artifacts directly to the **Releases** page.
3. Your local `LMMs-builder` syncs with these releases to download updates instantly without Git.

## 📄 License
This project is licensed under the **Apache License 2.0**. See the `LICENSE` file for details.
