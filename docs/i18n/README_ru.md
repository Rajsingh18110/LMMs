<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Создавайте с моделями. Запускайте с агентами.</strong><br>
  <em>Нативная операционная система ИИ на Python от основателя Раджа Сингха (MarkanM)</em>
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
[![Русский](https://img.shields.io/badge/Language-Русский-dc2626?style=flat-square)](#)
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
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">Веб-сайт</a> ·
  <a href="#system-architecture">Архитектура</a> ·
  <a href="#deep-technical-capabilities">Возможности</a> ·
  <a href="#quick-start">Быстрый старт</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Мастер установки</a> ·
  <a href="#enterprise-infrastructure--super-host">Предприятие</a> ·
  <a href="#core-command-reference">Команды</a> ·
  <a href="#cli-slash-commands">Слэш-команды</a> ·
  <a href="#license">Лицензия</a>
</p>

---

## Что такое LMMs OS?

LMMs — это нативный уровень операционной системы искусственного интеллекта на Python для локального и удаленного выполнения моделей. Созданный Раджем Сингхом (MarkanM), он объединяет полноценную графическую студию, интеллектуальный CLI разработчика и зрелый движок выполнения.

* **Двойное ядро движка**: квантованный инференс GGUF на базе llama.cpp и нативное выполнение safetensors в PyTorch.
* **Бесконечное масштабирование с AirEngine**: динамическая послойная выгрузка тензоров на GPU, CPU и диск позволяет запускать модели 70B+ даже на стандартных ноутбуках.
* **Десктопная студия (GUI)**: редактор кода Monaco, визуальное сравнение diff, интеграция с Git и управление инструментами.
* **Терминальная студия (CLI)**: интерактивная оболочка с более чем 30 слэш-командами, парным программированием и безопасной песочницей.
* **Корпоративная готовность**: распределенная клиент-серверная инфраструктура в частных сетях LAN/VPC с автообнаружением хоста.

---

## Архитектура системы

На следующей диаграмме показана сквозная архитектура LMMs OS в подсистемах пользовательского интерфейса, бэкенда, инференса и агентов:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Пользовательские интерфейсы**: `GUI workspace [main_window.py]` (Monaco IDE и просмотр diff) и `CLI [commands.py]` (интерактивный терминал разработчика).
2. **API и уровень бэкенда**: `HTTP API [server.py]` (демон FastAPI на порту 11435), `Backend session [main.py]` (координатор сессий), и `Backend services [manager.py]`.
3. **Подсистема инференса моделей**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (выгрузка тензоров GPU/CPU/Disk), `Model registry [registry.py]`, `llama.cpp runtime`, и `PyTorch runtime`.
4. **Подсистема возможностей агента**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]`, и `Workspace & Git [manager.py]`.

---

## Глубокие технические возможности (Deep Technical Capabilities)

### 1. Мультимодальный движок Vision (`/vision`, `/image`)
LMMs включает нативную мультимодальную обработку непосредственно в локальном движке:
* **Анализ UI и макетов**: проверяет скриншоты веб-интерфейсов или настольных приложений для обнаружения визуальных ошибок и сбоев CSS.
* **Извлечение архитектурных диаграмм**: анализирует блок-схемы, ER-диаграммы и последовательности UML, преобразуя их в структуры Mermaid или код.
* **OCR документов**: локально извлекает чистый текст и таблицы из изображений и PDF без отправки в облако.

### 2. Автономный голосовой ввод и аудио (`/mic`)
* **Локальное распознавание речи**: высокоскоростная оффлайн-транскрипция на базе квантованных моделей Whisper.
* **Голосовое управление**: запись инструкций разработчика прямо в активную сессию CLI с нулевой задержкой сети.

### 3. Git-движок и изоляция Worktree (`/git`, `/scope`)
* **Защита чтения/записи**: автоматически ограничивает операции агента безопасными командами (`cat`, `git diff`, `grep`), если не дано явного разрешения.
* **Изолированные Git Worktree**: изменяющие код правки выполняются в изолированных клонах worktree и сливаются в ветку только после успешных тестов.
* **Унифицированный предпросмотр Diff**: каждое изменение файла создает цветной diff перед записью на диск.

### 4. Детерминированные чекпоинты и безопасность отката (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Пошаговые чекпоинты**: неизменяемый снимок измененных файлов создается перед каждым действием агента.
* **Мгновенный откат**: если сгенерированный патч не проходит тесты, `/rollback` или `/undo` возвращает репозиторий в исходное состояние за миллисекунды.

### 5. Автономные субагенты и мультиагентная оркестрация (`/agent`, `/orchestrate`)
* **Фоновые задачи**: запуск независимых субагентов с выделенными бюджетами токенов и ограниченными правами.
* **Иерархическая координация**: главный оркестратор делегирует специализированные задачи субагентам и возвращает проверенные результаты.

### 6. Локальные исследования и векторная память RAG (`/research`)
* **Семантическая индексация кода**: индексация файлов рабочей области в локальном векторном хранилище для мгновенного поиска функций и классов.
* **Приватный веб-поиск**: получение актуальной документации без галлюцинаций.

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

## Мастер настройки архитектуры (`lmms install`)

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

### [1] Конфигурации индивидуальной рабочей станции

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

### [2] Корпоративная инфраструктура и супер-хост

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Централизованные вычисления**: серверный демон слушает на `0.0.0.0:11435`. Компания может запускать и обучать свои модели на GPU-кластерах.
* **Удаленные клиентские студии**: сотрудники подключаются со своих ноутбуков через LAN/VPC с автоматическим обнаружением.
* **Полная конфиденциальность**: данные компании и код никогда не покидают закрытую сеть.
* **AirEngine**: отсутствие ограничений по памяти — запуск моделей любого размера.

---

### Pip & Installer Command Matrix

| Команда | Назначение | Целевой компонент |
|---|---|---|
| `lmms install` | Интерактивный мастер архитектуры | Интерактивное меню |
| `lmms install --all` | Установка всей экосистемы | Desktop Studio, CLI, Voice, Super Engine |
| `lmms install --gui` | Установка Desktop Studio | PyQt6 GUI, Monaco Editor, Engine клиент |
| `lmms install --cli` | Установка Terminal Studio | Интерактивный шелл, инструменты, Engine клиент |
| `lmms install --engine` | Установка Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Установка облегченного движка | llama.cpp + AirEngine (GGUF раннер) |
| `lmms install --engine2` | Установка движка PyTorch | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Установка корпоративного хост-демона | Центральный сервер-демон на 0.0.0.0:11435 |
| `lmms install --client-gui` | Установка корпоративного GUI-клиента | GUI, настроенный для удаленного хоста LAN/VPC |
| `lmms install --client-cli` | Установка корпоративного CLI-клиента | CLI, настроенный для удаленного хоста LAN/VPC |
| `lmms update` | Обновление до свежего кода | Обновление текущей ветки |
| `lmms update --all` | Полное обновление всех веток | Синхронизация с GitHub |
| `lmms -check` | Диагностика оборудования | Телеметрия CPU, GPU, VRAM, AVX, диска |
| `lmms-uninstall -all` | Безопасное удаление | Удаляет код, сохраняет pip и пользовательские кэши |
| `lmms-uninstall -all --purge` | Сброс к заводским настройкам | Полное удаление конфигурации, моделей и данных |

---

## Справочник основных команд

### LMMs Core Launcher Commands

| Команда | Описание |
|---|---|
| `lmms` | Запуск настроенного интерфейса по умолчанию |
| `lmms --gui` | Запуск десктопной студии GUI |
| `lmms --cli` | Запуск терминальной студии разработчика CLI |
| `lmms --engine` | Прямой запуск движка инференса |
| `lmms set --gui` | Установить Desktop Studio режимом по умолчанию |
| `lmms set --cli` | Установить Terminal Studio режимом по умолчанию |
| `lmms set --engine` | Установить Engine Daemon режимом по умолчанию |
| `lmms stop` | Корректная остановка активного фонового движка |
| `lmms -check` | Проверка аппаратного профиля и зависимостей |
| `lmms update` | Умное обновление из текущей ветки |
| `lmms update --all` | Принудительное обновление из GitHub |
| `lmms --help` | Показать подробную справку по лаунчеру |

---

### Engine Runtime & Air Engine

| Команда | Описание |
|---|---|
| `lmms run <model>` | Запуск модели в интерактивном чате или одиночной оценке |
| `lmms list` | Список локально загруженных моделей |
| `lmms ps` | Показать активные запущенные модели и состояние VRAM |
| `lmms pull <model>` | Загрузка модели из Hugging Face / Model Hub |
| `lmms info <model>` | Просмотр метаданных модели, контекста и квантования |
| `lmms search <query>` | Поиск по доступным репозиториям моделей |
| `lmms benchmark <model>` | Тестирование скорости генерации (токен/с) и задержки |
| `lmms doctor` | Диагностика состояния движка и драйверов CUDA |
| `lmms create <model> -f <file>` | Создание записи модели из GGUF, Safetensors или манифеста |
| `lmms -air run <model> [prompt]` | Запуск сверхбольших моделей с гибридной выгрузкой Air GPU/CPU/Disk |
| `lmms --air run <m1> <m2>` | Параллельный запуск нескольких моделей через планировщик Air |
| `lmms air ps` | Отображение сессий Air и распределения слоев GPU/CPU |
| `lmms air stats` | Аппаратная телеметрия в реальном времени и статистика Air |
| `lmms air cache` | Просмотр размера и использования дискового кэша Air |
| `lmms air unload` | Выгрузка всех моделей Air и немедленная очистка VRAM/RAM |
| `lmms air benchmark <model>` | Тестирование пропускной способности под планировщиком Air |

---

### Server / Daemon

| Команда | Описание |
|---|---|
| `lmms server` | Запуск API/веб-серверного демона |
| `lmms server status` | Проверка статуса демона, порта, времени работы и здоровья |
| `lmms engine status` | Просмотр активного режима движка и статистики памяти |
| `lmms engine unload [model]` | Выгрузка активных моделей из памяти и очистка VRAM |
| `lmms server start [--port 11435]` | Запуск фонового демона FastAPI на указанном порту |
| `lmms server stop` | Остановка работающего фонового сервера |

---

## Интерактивные слэш-команды CLI

| Команда | Описание |
|---|---|
| `/fast` | Переключение в режим FAST с быстрыми ответами и легкими инструментами |
| `/deep` | Переключение в режим DEEP с полным пошаговым рассуждением и доступом к инструментам |
| `/model <name>` | Переключение на другую модель для текущей беседы |
| `/ml -l` | Список всех скачанных локальных моделей |
| `/ml -s <name>` | Горячее переключение модели с сохранением истории беседы |
| `/folder <path>` | Подключение каталога к рабочему контексту агента |
| `/code` | Переход в сфокусированный режим генерации и редактирования кода |
| `/chat` | Список и просмотр прошлых сессий чата |
| `/newchat` | Начало новой чистой сессии чата |
| `/chat -r <id> <name>` | Переименование сессии чата |
| `/chat -d <id>` | Удаление сессии чата |
| `/undo` | Безопасная отмена последнего изменения файла или патча |
| `/redo` | Повтор последнего отмененного действия с файлом |
| `/exit` | Выход из интерактивной сессии CLI |
| `/reboot` | Перезагрузка движка и перезапуск сессии |
| `/mic` | Запись голоса и прямая транскрипция в текст запроса |
| `/vision или /image` | Переключение в мультимодальный режим для анализа изображений и UI |
| `/research` | Переключение в режим исследований для поиска в веб и документации |
| `/read <file>` | Чтение любого файла рабочей области прямо в контекст сессии |
| `/task` | Управление фоновыми автономными задачами и целями субагентов |
| `/git` | Выполнение безопасных, проверяемых операций Git через агента |
| `/scope` | Просмотр и управление границами выполнения инструментов |
| `/tools list` | Список всех обнаруженных нативных инструментов и точек MCP |
| `/report` | Генерация криптографического отчета безопасности и действий |
| `/checkpoint` | Создание неизменяемого чекпоинта текущего состояния проекта |
| `/checkpoints` | Список всех сохраненных чекпоинтов рабочей области |
| `/rollback` | Откат репозитория и файлов к предыдущему чекпоинту |
| `/status` | Проверка состояния движка и аппаратного обеспечения в реальном времени |
| `/doctor` | Запуск полной диагностики системы и процедур восстановления |
| `/pair` | Вход в режим интерактивного парного программирования |
| `/perm <level>` | Настройка уровня разрешений песочницы (`strict`, `ask`, `full`) |
| `/agent` | Создание и управление автономными субагентами для параллельного выполнения |
| `/orchestrate` | Управление мультиагентными рабочими процессами и передачей задач |

---

## Философия продукта

1. **Практическая польза**: реальное исправление файлов, валидация AST и задачи в песочнице.
2. **Честность**: ноль телеметрии, никаких скрытых подписок.
3. **Локальность**: ваши модели, веса и токены остаются на ваших машинах.
4. **Минималистичный стек**: архитектура на чистом Python без лишних зависимостей.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
