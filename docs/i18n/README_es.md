<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Construye con modelos. Despliega con agentes.</strong><br>
  <em>El sistema operativo de IA local nativo en Python por el fundador Raj Singh (MarkanM)</em>
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
[![Español](https://img.shields.io/badge/Language-Español-ca8a04?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">Sitio Web</a> ·
  <a href="#system-architecture">Arquitectura</a> ·
  <a href="#deep-technical-capabilities">Capacidades Clave</a> ·
  <a href="#quick-start">Inicio Rápido</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Asistente de Instalación</a> ·
  <a href="#enterprise-infrastructure--super-host">Empresarial</a> ·
  <a href="#core-command-reference">Referencia de Comandos</a> ·
  <a href="#cli-slash-commands">Comandos Slash</a> ·
  <a href="#license">Licencia</a>
</p>

---

## ¿Qué es LMMs OS?

LMMs es una capa operativa de IA nativa en Python para la ejecución local y remota de modelos. Creado por el fundador Raj Singh (MarkanM), combina un estudio GUI de escritorio real, una CLI inteligente para desarrolladores y un motor de ejecución maduro para que profesionales y empresas ejecuten grandes modelos multimodales sin telemetría ni dependencia de la nube.

* **Núcleo de motor dual nativo**: Inferencia GGUF cuantizada de alto rendimiento con llama.cpp y ejecución nativa safetensors en PyTorch.
* **Escalado infinito con AirEngine**: La descarga dinámica de tensores entre GPU, CPU y disco permite ejecutar modelos de más de 70B incluso en portátiles estándar.
* **Estudio de escritorio (GUI)**: Editor de código Monaco, comparativas visuales diff, integración con Git y gestor de herramientas integrado.
* **Estudio de terminal (CLI)**: Shell interactiva con más de 30 comandos slash, programación en parejas, orquestación de subagentes y entorno seguro.
* **Preparado para empresas**: Arquitectura cliente-servidor distribuida en redes privadas LAN/VPC con descubrimiento automático del host central.

---

## Arquitectura del Sistema

El siguiente diagrama ilustra la arquitectura integral de LMMs OS a través de sus cuatro subsistemas principales:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Interfaces de Usuario**: `GUI workspace [main_window.py]` (IDE Monaco y revisión diff) y `CLI [commands.py]` (terminal interactiva de desarrollo).
2. **API y Capa Backend**: `HTTP API [server.py]` (demonio FastAPI en el puerto 11435), `Backend session [main.py]` (coordinador de sesión), y `Backend services [manager.py]`.
3. **Subsistema de Inferencia**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (descarga de tensores GPU/CPU/Disco), `Model registry [registry.py]`, `motor llama.cpp` y `motor PyTorch`.
4. **Subsistema de Capacidades de Agente**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` y `Workspace & Git [manager.py]`.

---

## Capacidades Técnicas Profundas (Deep Technical Capabilities)

### 1. Motor de Visión Multimodal (`/vision`, `/image`)
LMMs integra procesamiento multimodal nativo directamente en su motor local:
* **Análisis de interfaz y maquetación**: Inspecciona capturas de pantalla de aplicaciones web o de escritorio para detectar fallos visuales y errores de renderizado CSS.
* **Extracción de diagramas y arquitectura**: Analiza diagramas de flujo, diagramas ER y secuencias UML, convirtiéndolos directamente en código Mermaid o estructuras de datos.
* **OCR y extracción de documentos**: Extrae de forma limpia texto y tablas de imágenes y archivos PDF locales sin enviar datos a servidores externos.

### 2. Audio y Voz Fuera de Línea (`/mic`)
* **Reconocimiento de voz local**: Transcripción rápida y sin conexión mediante modelos Whisper cuantizados ejecutados localmente.
* **Instrucciones por voz**: Grabe instrucciones de desarrollo directamente en la sesión CLI activa con cero latencia de red.

### 3. Motor Git Contextual y Aislamiento por Worktree (`/git`, `/scope`)
* **Protección de solo lectura**: Restringe automáticamente las acciones del agente a comandos seguros (`cat`, `git diff`, `grep`) salvo autorización expresa.
* **Worktrees temporales aislados**: Las modificaciones de código se ejecutan en clones worktree independientes y solo se fusionan tras superar los tests automatizados.
* **Previsualización de Diff**: Cada cambio genera una comparativa de color unificada antes de guardarse en el disco.

### 4. Puntos de Control Deterministas y Reversión Instantánea (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Instantáneas por turno**: Se realiza una copia de seguridad inmutable de los archivos modificados antes de cada operación destructiva.
* **Restauración en milisegundos**: Si un parche genera errores o rompe las pruebas, `/rollback` o `/undo` restablece el repositorio al estado exacto anterior.

### 5. Subagentes Autónomos y Orquestación Multiagente (`/agent`, `/orchestrate`)
* **Tareas en segundo plano**: Despliega subagentes independientes con presupuestos de tokens dedicados y permisos restringidos.
* **Coordinación jerárquica**: El orquestador principal delega tareas especializadas (pruebas, documentación, refactorización) y consolida los resultados comprobados.

### 6. Investigación Local y RAG Vectorial (`/research`)
* **Indexación semántica del código**: Indexa el proyecto en una base vectorial local para buscar funciones, clases y tipos con rapidez semántica.
* **Búsqueda documental sin alucinaciones**: Consulta y procesa documentación técnica local y web eliminando alucinaciones del modelo.

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

## Asistente de Instalación de Arquitectura (`lmms install`)

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

### [1] Configuración de Estación de Trabajo Individual

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

### [2] Infraestructura Empresarial y Super Host

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Cómputo centralizado**: El demonio central se ejecuta en servidores GPU corporativos (`0.0.0.0:11435`) para servir y entrenar modelos propios.
* **Estudios cliente remotos**: Los miembros del equipo se conectan desde sus equipos mediante autodescubrimiento en la red LAN/VPC.
* **Privacidad integral**: El código fuente y las peticiones nunca salen de la infraestructura privada de la empresa.
* **AirEngine sin barreras de RAM**: Transmisión fluida de pesos de modelo a través de VRAM, RAM y almacenamiento NVMe.

---

### Pip & Installer Command Matrix

| Comando | Propósito | Componente Objetivo |
|---|---|---|
| `lmms install` | Iniciar el asistente interactivo de arquitectura | Menú de configuración interactivo |
| `lmms install --all` | Instalar el ecosistema completo | Estudio GUI, CLI, Voz, Super Engine |
| `lmms install --gui` | Instalar el Estudio de Escritorio (GUI) | Interfaz PyQt6, Editor Monaco, Cliente de motor |
| `lmms install --cli` | Instalar el Estudio de Terminal (CLI) | Shell interactiva, herramientas dev, Cliente de motor |
| `lmms install --engine` | Instalar el runtime Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Instalar el motor ligero | llama.cpp + AirEngine (exclusivo GGUF) |
| `lmms install --engine2` | Instalar el motor PyTorch | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Instalar el demonio servidor central de empresa | Servidor central escuchando en 0.0.0.0:11435 |
| `lmms install --client-gui` | Instalar cliente GUI para empresas | GUI configurada para conectar al host remoto en LAN |
| `lmms install --client-cli` | Instalar cliente CLI para empresas | CLI configurada para conectar al host remoto en LAN |
| `lmms update` | Descargar y aplicar actualizaciones de código | Actualización de la rama activa |
| `lmms update --all` | Actualización forzada en todas las ramas | Sincronización integral con GitHub |
| `lmms -check` | Diagnóstico integral de hardware y requisitos | Telemetría de CPU, GPU, VRAM, AVX y disco |
| `lmms-uninstall -all` | Desinstalación limpia del código fuente | Elimina el código, preserva paquetes pip y modelos |
| `lmms-uninstall -all --purge` | Restablecimiento de fábrica completo | Eliminación total de configuraciones, modelos y datos |

---

## Referencia de Comandos Principales

### LMMs Core Launcher Commands

| Comando | Descripción |
|---|---|
| `lmms` | Iniciar la interfaz predeterminada configurada |
| `lmms --gui` | Iniciar directamente el estudio de escritorio GUI |
| `lmms --cli` | Iniciar directamente la shell interactiva CLI |
| `lmms --engine` | Iniciar directamente el demonio del motor de inferencia |
| `lmms set --gui` | Establecer Desktop Studio como modo de inicio por defecto |
| `lmms set --cli` | Establecer Terminal Studio como modo de inicio por defecto |
| `lmms set --engine` | Establecer Engine Daemon como modo de inicio por defecto |
| `lmms stop` | Detener de forma segura el demonio del motor LMMs en segundo plano |
| `lmms --help` | Mostrar la ayuda completa del lanzador |

---

### Runtime del Motor y Gestión de Modelos

| Comando | Descripción |
|---|---|
| `lmms run <model>` | Ejecutar modelo en chat interactivo o evaluación directa |
| `lmms stop <model>` | Detener una instancia activa del modelo en ejecución |
| `lmms list` | Listar los modelos descargados localmente |
| `lmms ps` | Mostrar modelos en ejecución, asignación y estado de VRAM |
| `lmms pull <model>` | Descargar modelo desde Hugging Face o el Model Hub oficial |
| `lmms info <model>` | Inspeccionar metadatos del modelo, ventana de contexto y cuantización |
| `lmms rm <model>` | Eliminar un modelo almacenado localmente |
| `lmms search <query>` | Buscar en los repositorios de modelos disponibles |
| `lmms benchmark <model>` | Medir velocidad de generación (tokens/s) y latencia |
| `lmms doctor [--fix]` | Diagnóstico de salud, autorreparación de fallos menores y verificación de CUDA |
| `lmms create <model> -f <file>` | Registrar modelo personalizado desde GGUF, Safetensors o manifiesto |

---

### Air Engine (Intercambio Inteligente de RAM/VRAM)

Ejecute modelos masivos que superan la VRAM física mediante descarga dinámica híbrida de GPU/CPU/Disco.

| Comando | Descripción |
|---|---|
| `lmms -air run <model> [prompt]` | Ejecutar modelos gigantes mediante descarga dinámica AirEngine |
| `lmms --air run <m1> <m2>` | Ejecutar varios modelos simultáneamente con el planificador Air |
| `lmms air ps` | Ver sesiones Air activas y distribución de capas en GPU/CPU |
| `lmms air stats` | Consultar telemetría de hardware en tiempo real y estadísticas Air |
| `lmms air cache` | Ver tamaño y utilización de la memoria caché en disco de Air |
| `lmms air unload` | Descargar todos los modelos Air y vaciar inmediatamente la caché de VRAM |
| `lmms air benchmark <model>` | Evaluar rendimiento de procesamiento bajo el planificador Air |

---

### Server / Daemon

| Comando | Descripción |
|---|---|
| `lmms server` | Iniciar demonio del servidor API / Web |
| `lmms server status` | Comprobar estado del servidor, puerto, tiempo activo y salud |
| `lmms engine status` | Ver modo activo del motor y estadísticas de memoria |
| `lmms engine unload [model]` | Liberar modelos activos de memoria y limpiar VRAM |
| `lmms server start [--port 11435]` | Iniciar demonio FastAPI en segundo plano en el puerto indicado |
| `lmms server stop` | Detener el demonio del servidor en segundo plano |

---

## Comandos Interactivos Slash CLI

| Comando | Descripción |
|---|---|
| `/fast` | Cambiar a modo FAST con respuestas veloces y herramientas ligeras |
| `/deep` | Cambiar a modo DEEP con razonamiento exhaustivo y acceso total a herramientas |
| `/model <name>` | Cambiar de modelo para la conversación activa |
| `/ml -l` | Listar todos los modelos descargados localmente dentro del chat |
| `/ml -s <name>` | Cambiar de modelo en caliente preservando el historial de conversación |
| `/folder <path>` | Vincular una carpeta al contexto de trabajo del agente |
| `/code` | Entrar en el modo enfocado a generación y edición de código |
| `/chat` | Listar y revisar el historial de sesiones de conversación |
| `/newchat` | Iniciar una nueva sesión de chat limpia |
| `/chat -r <id> <name>` | Renombrar una sesión de conversación específica |
| `/chat -d <id>` | Eliminar permanentemente una sesión de chat |
| `/undo` | Deshacer de forma segura la última modificación de archivo de la IA |
| `/redo` | Rehacer la última acción de archivo deshecha |
| `/exit` | Salir de la sesión interactiva del terminal |
| `/reboot` | Reiniciar el motor backend y restablecer la conexión |
| `/mic` | Grabar audio con el micrófono y transcribir en tiempo real al prompt |
| `/vision o /image` | Activar modo de visión multimodal para análisis de imágenes e interfaces |
| `/research` | Activar modo de investigación para explorar la web y la documentación técnica |
| `/read <file>` | Cargar un archivo del proyecto directamente en el contexto de la sesión |
| `/task` | Gestionar tareas autónomas y objetivos secundarios en segundo plano |
| `/git` | Ejecutar operaciones seguras y auditadas de Git a través del agente |
| `/scope` | Inspeccionar y ajustar los límites de ejecución de herramientas |
| `/tools list` | Listar todas las herramientas nativas y puntos finales MCP activos |
| `/report` | Generar informe de auditoría criptográfico de acciones y seguridad |
| `/checkpoint` | Crear punto de control inmutable del estado del espacio de trabajo |
| `/checkpoints` | Listar todos los puntos de control del proyecto guardados |
| `/rollback` | Restaurar el repositorio y los archivos a un punto de control previo |
| `/status` | Comprobar la salud en tiempo real del motor y del hardware |
| `/doctor` | Ejecutar diagnósticos completos del sistema y pruebas de autorreparación |
| `/pair` | Activar el modo interactivo de programación en parejas |
| `/perm <level>` | Ajustar nivel de permisos del entorno de pruebas (`strict`, `ask`, `full`) |
| `/agent` | Generar y gestionar subagentes autónomos para ejecución paralela |
| `/orchestrate` | Supervisar flujos de trabajo coordinados entre múltiples agentes |

---

## Filosofía del Producto

1. **Utilidad Real en Primer Lugar**: Parches de código precisos, validación AST y tareas seguras en sandbox.
2. **Honestidad y Confianza**: Cero telemetría, sin suscripciones forzadas ni pagos ocultos.
3. **Local-First Absoluto**: Todos tus modelos, pesos y datos permanecen en tu propia máquina.
4. **Stack Limpio y Minimalista**: Arquitectura escrita en Python puro sin dependencias innecesarias.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
