<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>모델로 빌드하고, 에이전트로 배포하라.</strong><br>
  <em>창립자 Raj Singh (MarkanM)이 구축한 Python 네이티브 로컬 AI 운영체제</em>
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
[![한국어](https://img.shields.io/badge/Language-한국어-16a34a?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">공식 웹사이트</a> ·
  <a href="#system-architecture">시스템 아키텍처</a> ·
  <a href="#deep-technical-capabilities">핵심 기능</a> ·
  <a href="#quick-start">빠른 시작</a> ·
  <a href="#architecture-setup-wizard-lmms-install">설치 마법사</a> ·
  <a href="#enterprise-infrastructure--super-host">엔터프라이즈</a> ·
  <a href="#core-command-reference">명령어 레퍼런스</a> ·
  <a href="#cli-slash-commands">슬래시 명령어</a> ·
  <a href="#license">라이선스</a>
</p>

---

## LMMs OS란 무엇인가요?

LMMs는 로컬 및 원격 모델 실행을 위한 Python 네이티브 AI 운영 레이어입니다. 창립자 Raj Singh (MarkanM)이 설계한 이 시스템은 실제 데스크톱 GUI 스튜디오, 스마트한 CLI, 성숙한 백엔드 엔진을 통합하여 텔레메트리와 클라우드 종속 없이 안전하게 대규모 모델을 실행할 수 있습니다.

* **네이티브 듀얼 엔진 코어**: llama.cpp 기반의 고속 양자화 GGUF 추론과 PyTorch safetensors 네이티브 런타임 제공.
* **AirEngine을 통한 무한 확장**: GPU, CPU, 디스크 간의 동적 텐서 오프로딩을 통해 일반 노트북에서도 70B 이상의 대규모 모델 구동.
* **데스크톱 스튜디오 (GUI)**: Monaco 코드 에디터, 시각적 diff 비교, Git 연동 및 도구 관리자 내장.
* **터미널 스튜디오 (CLI)**: 30개 이상의 대화형 슬래시 명령, 페어 프로그래밍, 서브에이전트 오케스트레이션 및 안전한 샌드박스.
* **엔터프라이즈 클러스터 지원**: 사설 LAN/VPC 네트워크에서 중앙 호스트 서버와 자동 검색 클라이언트 연동.

---

## 시스템 아키텍처

다음 다이어그램은 UI, 백엔드 서비스, 모델 추론 및 에이전트 능력 서브시스템에 걸친 LMMs OS의 엔드투엔드 아키텍처를 보여줍니다:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **사용자 인터페이스**: `GUI workspace [main_window.py]` (Monaco 기반 에디터 및 diff 뷰어) 및 `CLI [commands.py]` (대화형 개발자 터미널 셸).
2. **API 및 백엔드 계층**: `HTTP API [server.py]` (포트 11435에서 대기하는 FastAPI 데몬), `Backend session [main.py]` (세션 조율자), `Backend services [manager.py]`.
3. **모델 추론 서브시스템**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (GPU/CPU/디스크 오프로드), `Model registry [registry.py]`, `llama.cpp 런타임`, `PyTorch 런타임`.
4. **에이전트 기능 서브시스템**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]`, `Workspace & Git [manager.py]`.

---

## 심층 기술 역량 (Deep Technical Capabilities)

### 1. 멀티모달 비전 엔진 (`/vision`, `/image`)
LMMs는 로컬 엔진 내부에 네이티브 비전 처리 파이프라인을 탑재하고 있습니다:
* **UI 및 레이아웃 파싱**: 웹 또는 데스크톱 UI 스크린샷을 분석하여 시각적 버그, 정렬 오류 및 CSS 렌더링 결함을 자동 감지합니다.
* **아키텍처 및 다이어그램 추출**: 플로우차트, ER 다이어그램, UML 시퀀스를 분석하여 유효한 Mermaid 코드 및 데이터 구조로 직접 변환합니다.
* **로컬 문서 OCR**: 외부 클라우드로 이미지 데이터를 전송하지 않고 로컬 이미지 및 PDF에서 텍스트와 표를 안전하게 추출합니다.

### 2. 오프라인 음성 인식 및 오디오 인터페이스 (`/mic`)
* **로컬 음성-텍스트 변환**: 양자화된 로컬 Whisper 모델을 통해 지연 없는 오프라인 음성 전사를 제공합니다.
* **핸즈프리 프롬프팅**: 개발 지시 및 음성 메모를 활성 CLI 세션에 직접 마이크로 입력할 수 있습니다.

### 3. 저장소 인식 Git 엔진 및 Worktree 격리 (`/git`, `/scope`)
* **읽기 전용 보호 가드**: 명시적 승인이 없는 한 에이전트의 작업을 읽기 전용 명령(`cat`, `git diff`, `grep`)으로 자동 제한합니다.
* **격리된 임시 Git Worktree**: 코드 수정 작업은 격리된 worktree 복제본에서 실행되며, 자동화된 테스트가 통과된 후에만 작업 브랜치로 병합됩니다.
* **통합 Diff 미리보기**: 디스크에 쓰기 전에 변경 사항을 컬러 diff로 시각적으로 사전 검토합니다.

### 4. 결정론적 체크포인트 및 롤백 안전성 (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **턴 기반 안전 스냅샷**: 파일 수정 작업 직전에 변경 대상 파일의 불변 백업 스냅샷을 생성합니다.
* **밀리초 단위 롤백**: 생성된 패치가 테스트에 실패하거나 문법 오류를 일으킬 경우, `/rollback` 또는 `/undo`를 통해 즉시 이전 상태로 복구합니다.

### 5. 자율 서브에이전트 및 멀티에이전트 오케스트레이션 (`/agent`, `/orchestrate`)
* **백그라운드 독립 태스크**: 전용 토큰 예산과 파일 권한이 격리된 서브에이전트를 백그라운드에서 실행합니다.
* **계층적 업무 위임**: 주 오케스트레이터가 테스트, 문서화, 린팅 작업을 서브에이전트에 위임하고 검증된 결과를 통합합니다.

### 6. 로컬 연구 및 벡터 메모리 RAG (`/research`)
* **시맨틱 코드베이스 인덱싱**: 워크스페이스 코드를 로컬 벡터 스토어에 인덱싱하여 함수와 클래스를 빠르게 시맨틱 검색합니다.
* **무할루시네이션 기술 문서 검색**: 로컬 API 문서를 캐싱 및 참조하여 모델의 허위 생성을 근본적으로 차단합니다.

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

## 아키텍처 설치 마법사 (`lmms install`)

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

### [1] 개인 워크스테이션 배포 옵션

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

### [2] 엔터프라이즈 인프라 및 슈퍼 호스트

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **중앙 집중식 고성능 연산**: 사내 고사양 GPU 서버에서 `0.0.0.0:11435`로 호스트 데몬을 실행하여 자체 모델 서빙 및 학습 지원.
* **원격 클라이언트 스튜디오**: 팀원들이 개인 노트북에서 LAN 자동 검색으로 즉시 호스트에 연결.
* **완벽한 데이터 주권**: 기업의 소스코드와 프롬프트가 사내 사설망 밖으로 유출되지 않음.
* **AirEngine 기반 무제한 모델 서빙**: VRAM 한계를 뛰어넘어 초대형 모델을 유연하게 처리.

---

### Pip & Installer Command Matrix

| 명령어 | 목적 | 대상 컴포넌트 |
|---|---|---|
| `lmms install` | 대화형 아키텍처 설치 마법사 실행 | 대화형 설정 메뉴 |
| `lmms install --all` | 전체 에코시스템 설치 | Desktop Studio, CLI, Voice, Super Engine |
| `lmms install --gui` | Desktop Studio (GUI) 설치 | PyQt6 GUI, Monaco Editor, Engine 클라이언트 |
| `lmms install --cli` | Terminal Studio (CLI) 설치 | 대화형 셸, 개발 도구, Engine 클라이언트 |
| `lmms install --engine` | Super Engine 통합 런타임 설치 | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | 경량 추론 엔진 설치 | llama.cpp + AirEngine (GGUF 전용) |
| `lmms install --engine2` | PyTorch 딥러닝 엔진 설치 | PyTorch + Transformers + AirEngine |
| `lmms install --host` | 엔터프라이즈 호스트 데몬 설치 | 중앙 서버 데몬 (0.0.0.0:11435) |
| `lmms install --client-gui` | 엔터프라이즈 원격 GUI 클라이언트 설치 | LAN/VPC 원격 호스트 연결용 GUI |
| `lmms install --client-cli` | 엔터프라이즈 원격 CLI 클라이언트 설치 | LAN/VPC 원격 호스트 연결용 CLI |
| `lmms update` | 최신 코드 동기화 및 업데이트 | 현재 활성 브랜치 업데이트 |
| `lmms update --all` | 모든 컴포넌트 완전 업데이트 | GitHub 원격 저장소와 전체 동기화 |
| `lmms -check` | 하드웨어 및 환경 종합 진단 | CPU, GPU, VRAM, AVX, 디스크 텔레메트리 |
| `lmms-uninstall -all` | 소스코드 안전 제거 | 코드만 삭제, pip 패키지 및 사용자 모델 캐시 유지 |
| `lmms-uninstall -all --purge` | 공장 초기화 (완전 삭제) | 모든 설정, 모델 및 세션 데이터 완전 영구 삭제 |

---

## 핵심 명령어 레퍼런스

### LMMs Core Launcher Commands

| 명령어 | 설명 |
|---|---|
| `lmms` | 설정된 기본 인터페이스 시작 |
| `lmms --gui` | Desktop Studio (GUI) 직접 시작 |
| `lmms --cli` | 개발자 CLI 셸 직접 시작 |
| `lmms --engine` | 추론 엔진 데몬 직접 시작 |
| `lmms set --gui` | Desktop Studio를 기본 실행 모드로 설정 |
| `lmms set --cli` | Terminal Studio를 기본 실행 모드로 설정 |
| `lmms set --engine` | Engine Daemon을 기본 실행 모드로 설정 |
| `lmms stop` | 백그라운드에서 실행 중인 엔진 안전하게 종료 |
| `lmms -check` | 하드웨어 프로필 및 사전 요구사항 검증 |
| `lmms update` | 현재 브랜치에서 스마트 업데이트 |
| `lmms update --all` | GitHub에서 전체 강제 업데이트 |
| `lmms --help` | 상세 실행 도움말 표시 |

---

### Engine Runtime & Air Engine

| 명령어 | 설명 |
|---|---|
| `lmms run <model>` | 대화형 채팅 또는 단일 프롬프트로 모델 실행 |
| `lmms list` | 로컬에 다운로드된 모델 목록 표시 |
| `lmms ps` | 현재 실행 중인 모델 및 VRAM 할당 상태 확인 |
| `lmms pull <model>` | Hugging Face 또는 공식 허브에서 모델 다운로드 |
| `lmms info <model>` | 모델 메타데이터, 컨텍스트 길이, 양자화 사양 검사 |
| `lmms search <query>` | 다운로드 가능한 오픈소스 모델 저장소 검색 |
| `lmms benchmark <model>` | 토큰 생성 속도(t/s) 및 초기 응답 지연 시간 벤치마크 |
| `lmms doctor` | 엔진 상태 및 CUDA/GPU 드라이버 무결성 진단 |
| `lmms create <model> -f <file>` | GGUF 또는 매니페스트로부터 커스텀 모델 등록 |
| `lmms -air run <model> [prompt]` | AirEngine 메모리 계층화를 통한 초대형 모델 실행 |
| `lmms --air run <m1> <m2>` | Air 스케줄러를 통한 다중 모델 병렬 실행 |
| `lmms air ps` | Air 세션의 모델 레이어 배치 및 GPU/CPU 할당 모니터링 |
| `lmms air stats` | 실시간 하드웨어 텐서 오프로드 처리량 및 메모리 통계 |
| `lmms air cache` | Air 디스크 캐시 용량 및 스토리지 사용률 확인 |
| `lmms air unload` | 모든 Air 모델 언로드 및 VRAM 캐시 즉시 비우기 |
| `lmms air benchmark <model>` | Air 동적 스케줄링 환경에서의 실행 처리량 벤치마크 |

---

### Server / Daemon

| 명령어 | 설명 |
|---|---|
| `lmms server` | API / 웹 서버 데몬 시작 |
| `lmms server status` | 서버 데몬 상태, 포트, 가동 시간 및 헬스체크 확인 |
| `lmms engine status` | 현재 엔진 실행 모드 및 활성 메모리 점유율 확인 |
| `lmms engine unload [model]` | 활성 모델을 메모리에서 해제하고 VRAM 반환 |
| `lmms server start [--port 11435]` | 지정된 포트에서 FastAPI 백그라운드 데몬 시작 |
| `lmms server stop` | 실행 중인 백그라운드 서버 데몬 종료 |

---

## CLI 대화형 슬래시 명령어

| 명령어 | 설명 |
|---|---|
| `/fast` | 빠른 응답과 가벼운 도구 호출을 우선하는 FAST 모드로 전환 |
| `/deep` | 다단계 심층 추론과 전체 도구 권한을 갖는 DEEP 모드로 전환 |
| `/model <name>` | 현재 대화 세션에 사용할 다른 로컬 모델로 전환 |
| `/ml -l` | 채팅 세션 내에서 다운로드된 모든 모델 목록 표시 |
| `/ml -s <name>` | 대화 문맥을 유지한 채 실행 모델 핫 스왑 |
| `/folder <path>` | 지정된 디렉터리를 에이전트 작업 컨텍스트에 연결 |
| `/code` | 코드 생성 및 자동 패치 적용 전용 모드로 진입 |
| `/chat` | 과거 대화 세션 기록 목록 확인 및 검토 |
| `/newchat` | 새로운 빈 대화 세션 시작 |
| `/chat -r <id> <name>` | 특정 세션 이름 바꾸기 |
| `/chat -d <id>` | 특정 세션 기록 영구 삭제 |
| `/undo` | 에이전트가 수행한 최근 파일 편집이나 패치 안전하게 취소 |
| `/redo` | 방금 취소된 파일 작업 다시 실행 |
| `/exit` | 대화형 CLI 세션 안전하게 종료 |
| `/reboot` | 백엔드 엔진을 재부팅하고 세션 재연결 |
| `/mic` | 마이크 입력을 녹음하여 프롬프트로 실시간 음성 전사 |
| `/vision 또는 /image` | 이미지 분석 및 UI 검사를 위한 멀티모달 비전 모드로 전환 |
| `/research` | 기술 문서 및 웹 정보를 탐색하는 리서치 모드로 전환 |
| `/read <file>` | 지정된 로컬 파일을 대화 컨텍스트에 직접 로드 |
| `/task` | 백그라운드에서 동작하는 자율 서브태스크 및 목표 관리 |
| `/git` | 에이전트를 통해 검증 및 감사된 안전한 Git 작업 실행 |
| `/scope` | 현재 도구 실행 권한의 범위 확인 및 변경 |
| `/tools list` | 사용 가능한 모든 네이티브 도구 및 MCP 엔드포인트 목록 표시 |
| `/report` | 암호화 서명된 보안 및 작업 감사 보고서 생성 |
| `/checkpoint` | 현재 워크스페이스 상태의 불변 체크포인트 생성 |
| `/checkpoints` | 저장된 모든 워크스페이스 체크포인트 목록 표시 |
| `/rollback` | 저장소와 파일을 이전 체크포인트 상태로 복원 |
| `/status` | 엔진 및 시스템 하드웨어의 실시간 상태 확인 |
| `/doctor` | 종합 시스템 진단 및 자동 복구 도구 실행 |
| `/pair` | 대화형 페어 프로그래밍 모드 시작 |
| `/perm <level>` | 샌드박스 도구 실행 권한 수준 조정 (`strict`, `ask`, `full`) |
| `/agent` | 동시 하위 작업을 수행하는 자율 서브에이전트 생성 및 관리 |
| `/orchestrate` | 다중 에이전트 간의 협업 워크플로 및 작업 인계 관리 |

---

## 제품 철학

1. **실용성 우선**: 코드 패치, AST 검증, 안전한 샌드박스 태스크 중심.
2. **투명한 신뢰**: 제로 텔레메트리 및 숨겨진 비용 없음.
3. **로컬 퍼스트**: 사용자의 모든 데이터와 모델 가중치는 로컬에 안전하게 보관.
4. **간결한 스택**: 불필요한 의존성을 배제한 순수 Python 아키텍처.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
