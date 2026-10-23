<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Construa com modelos. Entregue com agentes.</strong><br>
  <em>O sistema operacional de IA local nativo em Python pelo fundador Raj Singh (MarkanM)</em>
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
[![Português](https://img.shields.io/badge/Language-Português-15803d?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">Site Oficial</a> ·
  <a href="#system-architecture">Arquitetura</a> ·
  <a href="#deep-technical-capabilities">Recursos Principais</a> ·
  <a href="#quick-start">Início Rápido</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Assistente de Instalação</a> ·
  <a href="#enterprise-infrastructure--super-host">Empresarial</a> ·
  <a href="#core-command-reference">Referência de Comandos</a> ·
  <a href="#cli-slash-commands">Comandos Slash</a> ·
  <a href="#license">Licença</a>
</p>

---

## O que é o LMMs OS?

O LMMs é uma camada operacional de IA nativa em Python para execução local e remota de modelos. Criado pelo fundador Raj Singh (MarkanM), ele combina um estúdio GUI de desktop completo, uma CLI inteligente para desenvolvedores e um mecanismo de execução robusto para que desenvolvedores e empresas executem modelos multimodais com zero telemetria e sem dependência da nuvem.

* **Núcleo de motor duplo nativo**: Inferência quantizada GGUF de alto desempenho com llama.cpp e execução nativa safetensors em PyTorch.
* **Escala infinita com AirEngine**: O descarregamento dinâmico de tensores entre GPU, CPU e disco permite rodar modelos de 70B+ até mesmo em notebooks comuns.
* **Estúdio de Desktop (GUI)**: Editor de código Monaco, comparações visuais diff, integração Git e gerenciador de ferramentas embutido.
* **Estúdio de Terminal (CLI)**: Shell interativa com mais de 30 comandos slash, programação em par, orquestração de subagentes e sandbox segura.
* **Pronto para Empresas**: Infraestrutura cliente-servidor distribuída em redes privadas LAN/VPC com descoberta automática do host central.

---

## Arquitetura do Sistema

O diagrama a seguir ilustra a arquitetura completa do LMMs OS nos subsistemas de Interface, Backend, Inferência e Agentes:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Interfaces de Usuário**: `GUI workspace [main_window.py]` (IDE Monaco e revisão diff) e `CLI [commands.py]` (terminal interativo para desenvolvedores).
2. **API e Camada de Backend**: `HTTP API [server.py]` (daemon FastAPI na porta 11435), `Backend session [main.py]` (coordenador de sessão), e `Backend services [manager.py]`.
3. **Subsistema de Inferência**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (descarregamento GPU/CPU/Disco), `Model registry [registry.py]`, `runtime llama.cpp` e `runtime PyTorch`.
4. **Subsistema de Recursos de Agente**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` e `Workspace & Git [manager.py]`.

---

## Recursos Técnicos Avançados (Deep Technical Capabilities)

### 1. Motor de Visão Multimodal (`/vision`, `/image`)
O LMMs integra processamento multimodal diretamente no motor local:
* **Análise de UI e Layout**: Examina capturas de tela de aplicações web e desktop para detectar erros visuais, desalinhamentos e bugs CSS.
* **Extração de Diagramas e Arquitetura**: Analisa fluxogramas, diagramas ER e sequências UML, transcrevendo-os em código Mermaid ou estruturas de dados.
* **OCR Local de Documentos**: Extrai texto limpo e tabelas de imagens e PDFs sem enviar dados para a nuvem.

### 2. Áudio e Voz Offline (`/mic`)
* **Reconhecimento de Voz Local**: Transcrição rápida e offline alimentada por modelos Whisper quantizados locais.
* **Comandos por Voz**: Grave instruções e notas diretamente na sessão CLI ativa com latência zero.

### 3. Consciência Git e Isolamento por Worktree (`/git`, `/scope`)
* **Proteção de Leitura**: Restringe operações a comandos seguros (`cat`, `git diff`, `grep`), exceto quando explicitamente autorizado.
* **Worktrees Git Temporárias**: Alterações de código são executadas em clones de worktree isolados e só são mescladas após validação dos testes.
* **Pré-visualização Diff**: Toda alteração gera uma visualização colorida antes de ser gravada em disco.

### 4. Checkpoints Determinísticos e Reversão Instantânea (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Instantâneos por Turno**: Backup imutável dos arquivos é salvo antes de qualquer alteração destrutiva.
* **Reversão em Milissegundos**: Se um patch falhar nos testes, `/rollback` ou `/undo` restaura o projeto ao estado exato anterior.

### 5. Subagentes Autônomos e Orquestração Multiagente (`/agent`, `/orchestrate`)
* **Tarefas em Segundo Plano**: Inicia subagentes independentes com limites de tokens e permissões restritas.
* **Coordenação Hierárquica**: O orquestrador principal delega tarefas especializadas (testes, documentação, refatoração) e consolida os resultados.

### 6. Pesquisa Local e RAG Vetorial (`/research`)
* **Indexação Semântica**: Indexa o repositório em um banco vetorial local para busca rápida de classes e métodos.
* **Pesquisa Sem Alucinações**: Consulta documentação técnica local e da web eliminando respostas inventadas.

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

## Assistente de Instalação de Arquitetura (`lmms install`)

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

### [1] Configuração para Estação de Trabalho Individual

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

### [2] Infraestrutura Corporativa e Super Host

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Computação Centralizada**: O daemon roda em servidores GPU dedicados (`0.0.0.0:11435`) para servir modelos da empresa.
* **Clientes Remotos**: Funcionários conectam-se de seus notebooks com descoberta automática em rede LAN/VPC.
* **Privacidade Total**: Todo o código e comandos permanecem na rede interna da empresa.
* **AirEngine sem Limitações**: Streaming dinâmico de pesos de modelos em VRAM, RAM e NVMe.

---

### Pip & Installer Command Matrix

| Comando | Objetivo | Componente Alvo |
|---|---|---|
| `lmms install` | Iniciar o assistente interativo de arquitetura | Menu de configuração interativo |
| `lmms install --all` | Instalar todo o ecossistema | Estúdio Desktop, CLI, Voz, Super Engine |
| `lmms install --gui` | Instalar o Estúdio Desktop (GUI) | Interface PyQt6, Editor Monaco, Cliente do motor |
| `lmms install --cli` | Instalar o Estúdio Terminal (CLI) | Shell interativo, ferramentas dev, Cliente do motor |
| `lmms install --engine` | Instalar o runtime Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Instalar motor leve | llama.cpp + AirEngine (exclusivo GGUF) |
| `lmms install --engine2` | Instalar motor PyTorch | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Instalar daemon do servidor corporativo | Servidor central escutando em 0.0.0.0:11435 |
| `lmms install --client-gui` | Instalar cliente GUI corporativo | GUI configurada para conectar a host remoto na LAN |
| `lmms install --client-cli` | Instalar cliente CLI corporativo | CLI configurada para conectar a host remoto na LAN |
| `lmms update` | Atualizar código-fonte da aplicação | Atualização da branch ativa atual |
| `lmms update --all` | Atualização forçada em todas as branches | Sincronização integral com o GitHub |
| `lmms -check` | Diagnóstico de hardware e requisitos | Telemetria de CPU, GPU, VRAM, AVX e disco |
| `lmms-uninstall -all` | Remoção segura do código-fonte | Remove o código, mantém pacotes pip e modelos |
| `lmms-uninstall -all --purge` | Restauração de fábrica completa | Eliminação total de configurações, modelos e dados |

---

## Referência de Comandos Principais

### LMMs Core Launcher Commands

| Comando | Descrição |
|---|---|
| `lmms` | Iniciar a interface padrão configurada |
| `lmms --gui` | Iniciar diretamente o estúdio desktop GUI |
| `lmms --cli` | Iniciar diretamente a shell interativa CLI |
| `lmms --engine` | Iniciar diretamente o daemon do motor de inferência |
| `lmms set --gui` | Definir o Desktop Studio como modo padrão de inicialização |
| `lmms set --cli` | Definir o Terminal Studio como modo padrão de inicialização |
| `lmms set --engine` | Definir o Engine Daemon como modo padrão de inicialização |
| `lmms stop` | Encerrar de forma segura o daemon do motor LMMs em segundo plano |
| `lmms --help` | Exibir ajuda abrangente do inicializador |

---

### Runtime do Motor e Gerenciamento de Modelos

| Comando | Descrição |
|---|---|
| `lmms run <model>` | Executar modelo em chat interativo ou prompt único |
| `lmms stop <model>` | Parar uma instância ativa de modelo em execução |
| `lmms list` | Listar modelos baixados localmente |
| `lmms ps` | Exibir modelos em execução, alocação e estado da VRAM |
| `lmms pull <model>` | Baixar modelo do Hugging Face ou Hub oficial |
| `lmms info <model>` | Inspecionar metadados, janela de contexto e quantização |
| `lmms rm <model>` | Excluir um modelo armazenado localmente |
| `lmms search <query>` | Pesquisar nos repositórios de modelos disponíveis |
| `lmms benchmark <model>` | Medir velocidade de geração (tokens/s) e latência |
| `lmms doctor [--fix]` | Diagnóstico de saúde, correção automática de falhas e teste de CUDA |
| `lmms create <model> -f <file>` | Registrar modelo personalizado a partir de GGUF ou Safetensors |

---

### Air Engine (Troca Inteligente de RAM/VRAM)

Execute modelos gigantescos que excedem a VRAM física usando descarregamento dinâmico híbrido GPU/CPU/Disco.

| Comando | Descrição |
|---|---|
| `lmms -air run <model> [prompt]` | Executar modelos gigantes via descarregamento dinâmico AirEngine |
| `lmms --air run <m1> <m2>` | Executar múltiplos modelos concorrentes com o escalonador Air |
| `lmms air ps` | Visualizar sessões Air ativas e divisão de camadas em GPU/CPU |
| `lmms air stats` | Acompanhar telemetria de hardware e estatísticas de offload |
| `lmms air cache` | Verificar tamanho e uso do cache de disco do Air |
| `lmms air unload` | Descarregar modelos Air e liberar cache de VRAM imediatamente |
| `lmms air benchmark <model>` | Avaliar taxa de transferência sob o escalonador Air |

---

### Server / Daemon

| Comando | Descrição |
|---|---|
| `lmms server` | Iniciar daemon do servidor API / Web |
| `lmms server status` | Verificar status do servidor, porta, uptime e saúde |
| `lmms engine status` | Verificar modo ativo do motor e dados de memória |
| `lmms engine unload [model]` | Liberar modelos ativos da memória e limpar VRAM |
| `lmms server start [--port 11435]` | Iniciar daemon FastAPI em segundo plano na porta especificada |
| `lmms server stop` | Parar daemon do servidor em segundo plano |

---

## Comandos Interactivos Slash CLI

| Comando | Descrição |
|---|---|
| `/fast` | Mudar para modo FAST com respostas rápidas e ferramentas leves |
| `/deep` | Mudar para modo DEEP com raciocínio profundo e acesso a ferramentas |
| `/model <name>` | Trocar o modelo usado na conversa atual |
| `/ml -l` | Listar todos os modelos baixados localmente dentro do chat |
| `/ml -s <name>` | Trocar modelo a quente mantendo o histórico de mensagens |
| `/folder <path>` | Vincular um diretório ao contexto de trabalho do agente |
| `/code` | Entrar no modo focado em geração e edição de código |
| `/chat` | Listar e revisar histórico de sessões anteriores |
| `/newchat` | Iniciar uma nova sessão de conversa limpa |
| `/chat -r <id> <name>` | Renomear uma sessão de conversa específica |
| `/chat -d <id>` | Excluir permanentemente uma sessão de conversa |
| `/undo` | Desfazer com segurança a última alteração de arquivo feita pela IA |
| `/redo` | Refazer a última ação de arquivo desfeita |
| `/exit` | Sair da sessão interativa do terminal |
| `/reboot` | Reiniciar o motor backend e reconectar a sessão |
| `/mic` | Gravar voz no microfone e transcrever direto no prompt |
| `/vision ou /image` | Ativar modo de visão multimodal para inspeção de imagens e telas |
| `/research` | Ativar modo de pesquisa para busca na web e documentação |
| `/read <file>` | Carregar arquivo do projeto diretamente no contexto da sessão |
| `/task` | Gerenciar tarefas autônomas e objetivos em segundo plano |
| `/git` | Executar operações seguras e auditadas de Git pelo agente |
| `/scope` | Inspecionar e ajustar limites de permissão das ferramentas |
| `/tools list` | Listar todas as ferramentas nativas e servidores MCP ativos |
| `/report` | Gerar relatório criptográfico de auditoria e segurança |
| `/checkpoint` | Criar ponto de restauração imutável do espaço de trabalho |
| `/checkpoints` | Listar todos os pontos de restauração salvos |
| `/rollback` | Restaurar repositório e arquivos para um ponto anterior |
| `/status` | Verificar saúde em tempo real do motor e do hardware |
| `/doctor` | Executar diagnóstico do sistema e rotinas de autorrecuperação |
| `/pair` | Ativar modo de programação em par interativo |
| `/perm <level>` | Ajustar nível de permissões da sandbox (`strict`, `ask`, `full`) |
| `/agent` | Criar e gerenciar subagentes para tarefas paralelas |
| `/orchestrate` | Supervisionar fluxos coordenados de múltiplos agentes |

---

## Filosofia do Produto

1. **Utilidade Real em Primeiro Lugar**: Aplicação direta de código, validação AST e execução em sandbox.
2. **Honestidade e Transparência**: Zero telemetria, sem cobranças ocultas ou assinaturas forçadas.
3. **Local-First Genuíno**: Todos os seus modelos e dados permanecem sob seu controle local.
4. **Arquitetura Limpa**: Desenvolvido em Python puro sem dependências desnecessárias.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
