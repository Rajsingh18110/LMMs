<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>モデルで創り、エージェントで届ける。</strong><br>
  <em>創業者 Raj Singh (MarkanM) による Python ネイティブ ローカル AI オペレーティング システム</em>
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
[![日本語](https://img.shields.io/badge/Language-日本語-0f172a?style=flat-square)](#)
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
  <a href="https://lmms.markanm.com">公式サイト</a> ·
  <a href="#system-architecture">システム構成</a> ·
  <a href="#deep-technical-capabilities">コア機能</a> ·
  <a href="#quick-start">クイックスタート</a> ·
  <a href="#architecture-setup-wizard-lmms-install">導入ウィザード</a> ·
  <a href="#enterprise-infrastructure--super-host">エンタープライズ</a> ·
  <a href="#core-command-reference">コマンド一覧</a> ·
  <a href="#cli-slash-commands">スラッシュコマンド</a> ·
  <a href="#license">ライセンス</a>
</p>

---

## LMMs OS とは？

LMMs は、ローカルおよびリモートでモデルを実行するための Python ネイティブ AI オペレーティング層です。創業者 Raj Singh (MarkanM) によって構築され、デスクトップ GUI スタジオ、スマートな開発者 CLI、高機能エンジンを統合し、完全なプライバシーとゼロ テレメトリでマルチモーダル モデルを実行できます。

* **ネイティブ デュアル エンジン コア**: llama.cpp による高速量子化 GGUF 推論と PyTorch safetensors ネイティブ実行の統合。
* **AirEngine による無限のスケーリング**: GPU、CPU、ディスク間の動的テンソル オフロードにより、一般的なノート PC でも 70B 以上の超大規模モデルを実行可能。
* **デスクトップ スタジオ (GUI)**: Monaco コード エディター、ビジュアル diff 表示、ワークスペース Git 連携、ツール管理。
* **ターミナル スタジオ (CLI)**: 30 以上のスラッシュ コマンド、ペア プログラミング、自律エージェント オーケストレーション、安全なサンドボックス。
* **エンタープライズ対応**: プライベート LAN / VPC ネットワークにおける中央ホスト サーバとクライアントの自動検出。

---

## システム アーキテクチャ

以下の図は、UI、バックエンド、モデル推論、エージェント能力の各サブシステムにわたるエンドツーエンドのトポロジを示しています:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **ユーザー インターフェース層**: `GUI workspace [main_window.py]`（Monaco エディターと差分レビュー）および `CLI [commands.py]`（対話型開発者ターミナル）。
2. **API・バックエンド層**: `HTTP API [server.py]`（ポート 11435 で待機する FastAPI デーモン）、`Backend session [main.py]`（セッション管理）、`Backend services [manager.py]`。
3. **モデル推論サブシステム**: `Runtime selection [manager.py]`、`AirEngine [runtime.py]`（GPU/CPU/ディスク オフロード）、`Model registry [registry.py]`、`llama.cpp 実行環境`、`PyTorch 実行環境`。
4. **エージェント能力サブシステム**: `Request orchestration [pipeline.py]`、`Vector retrieval [rag.py]`、`Agent routing [manager.py]`、`Tool execution [executor.py]`、`Session memory [core_memory.py]`、`Web research [engine.py]`、`Workspace & Git [manager.py]`。

---

## 詳細な技術的機能 (Deep Technical Capabilities)

### 1. マルチモーダル Vision エンジン (`/vision`, `/image`)
LMMs はローカル エンジン内で直接マルチモーダル処理を実行します:
* **UI・レイアウト解析**: Web やデスクトップ UI のスクリーンショットを検査し、視覚的バグや CSS の描画崩れを検出。
* **設計図・ダイアグラムの抽出**: フローチャート、ER 図、UML を解析し、直接 Mermaid 形式やコード構造に変換。
* **ローカル OCR**: 外部クラウドに画像データを送信することなく、画像や PDF からテキストや表構造を抽出。

### 2. オフライン音声認識・音声操作 (`/mic`)
* **ローカル音声テキスト変換**: 量子化された Whisper モデルにより、完全オフラインで高速な文字起こしを実現。
* **ハンズフリー入力**: 開発プロンプトや作業指示をマイクから直接アクティブな CLI セッションへ録音・入力可能。

### 3. Git 連動・Worktree 完全分離 (`/git`, `/scope`)
* **読み取り専用ガード**: 明示的な許可がない限り、エージェントの操作を安全なコマンド（`cat`, `git diff`, `grep`）に自動制限。
* **一時的 Git Worktree**: コード変更は隔離された Worktree 内で実行され、自動テストが通過した後にのみ作業ブランチへマージ。
* **統合 Diff プレビュー**: ディスクに変更を書き込む前に、変更差分をカラーで視覚的に事前確認。

### 4. 決定論的チェックポイントとロールバック保証 (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **ターン単位の安全スナップショット**: ファイル編集を行う直前に、変更対象ファイルの変更不可スナップショットを自動保存。
* **瞬時ロールバック**: パッチ適用でテストが失敗したり構文エラーが発生した場合、数ミリ秒で実行直前の状態へ完全復元。

### 5. 自律サブエージェントとマルチエージェント オーケストレーション (`/agent`, `/orchestrate`)
* **バックグラウンド並行タスク**: 個別のトークン枠とアクセス権限を持つサブエージェントをバックグラウンドで起動。
* **階層型タスク委任**: テスト作成、ドキュメント更新、静的解析などのタスクをサブエージェントへ委託し、検証結果を統合。

### 6. ローカル ベクトル検索 RAG (`/research`)
* **リポジトリのセマンティック インデックス**: ワークスペース内のコードをベクトル化し、関数やクラス定義を高速検索。
* **ハルシネーションの排除**: 最新のローカル ドキュメントを参照することで、AI の誤認を根本から防止。

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

## アーキテクチャ設定ウィザード (`lmms install`)

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

### [1] 個別ワークステーション構成

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

### [2] エンタープライズ インフラ & スーパー ホスト

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **集中型ハイパフォーマンス計算**: 社内 GPU サーバでホスト デーモン (`0.0.0.0:11435`) を起動し、自社モデルの運用やファインチューニングを実施。
* **軽量クライアント スタジオ**: 従業員は各自の PC から LAN 自動検出によりセキュアに接続。
* **完全なデータ主権**: 機密コードやプロンプトが社内プライベート ネットワーク外へ送信されることはありません。
* **AirEngine の無制限オフロード**: VRAM 容量に関わらず超巨大モデルを安定ストリーミング実行。

---

### Pip & Installer Command Matrix

| コマンド | 目的 | 対象コンポーネント |
|---|---|---|
| `lmms install` | 対話型のアーキテクチャ設定ウィザードを起動 | 対話型設定メニュー |
| `lmms install --all` | 全エコシステムの完全インストール | Desktop Studio, CLI, Voice, Super Engine |
| `lmms install --gui` | Desktop Studio (GUI) のインストール | PyQt6 GUI, Monaco Editor, Engine クライアント |
| `lmms install --cli` | Terminal Studio (CLI) のインストール | 対話型シェル, 開発ツール, Engine クライアント |
| `lmms install --engine` | Super Engine のインストール | llama.cpp + PyTorch + AirEngine 統合デーモン |
| `lmms install --engine1` | 軽量版エンジンのインストール | llama.cpp + AirEngine (GGUF 専用) |
| `lmms install --engine2` | PyTorch ネイティブ版エンジンのインストール | PyTorch + Transformers + AirEngine |
| `lmms install --host` | エンタープライズ用中央ホスト デーモンを設置 | 0.0.0.0:11435 で待機する推論サーバ |
| `lmms install --client-gui` | エンタープライズ用リモート GUI クライアント | LAN/VPC ホストに自動接続するデスクトップ UI |
| `lmms install --client-cli` | エンタープライズ用リモート CLI クライアント | LAN/VPC ホストに自動接続するターミナル UI |
| `lmms update` | 最新ソースコードの取得と更新 | 現在のアクティブ ブランチの更新 |
| `lmms update --all` | 全ブランチの強制同期アップデート | GitHub リモート リポジトリとの完全同期 |
| `lmms -check` | ハードウェア診断と環境検証を実行 | CPU, GPU, VRAM, AVX, ディスク診断 |
| `lmms-uninstall -all` | 安全なアンインストール | ソースコードを削除（モデルや pip は保持） |
| `lmms-uninstall -all --purge` | 完全初期化（ファクトリー リセット） | 設定、モデル、キャッシュを完全に消去 |

---

## 基本コマンド リファレンス

### LMMs Core Launcher Commands

| コマンド | 説明 |
|---|---|
| `lmms` | 設定済みのデフォルト インターフェースを起動 |
| `lmms --gui` | Desktop Studio (GUI) を直接起動 |
| `lmms --cli` | 対話型開発者 CLI シェルを直接起動 |
| `lmms --engine` | 推論エンジン デーモンを直接起動 |
| `lmms set --gui` | Desktop Studio を標準起動モードに設定 |
| `lmms set --cli` | Terminal Studio を標準起動モードに設定 |
| `lmms set --engine` | Engine デーモンを標準起動モードに設定 |
| `lmms stop` | バックグラウンドで動作中の LMMs エンジン デーモンを正常終了 |
| `lmms --help` | ランチャーのヘルプ メッセージを表示 |

---

### エンジン ランタイムとモデル管理 (Engine Runtime & Model Management)

| コマンド | 説明 |
|---|---|
| `lmms run <model>` | モデルを対話形式または単発プロンプトで実行 |
| `lmms stop <model>` | 実行中のアクティブなモデル インスタンスを停止 |
| `lmms list` | ローカルにダウンロード済みのモデル一覧を表示 |
| `lmms ps` | 実行中のアクティブ モデルと VRAM 使用状況を表示 |
| `lmms pull <model>` | Hugging Face や公式ハブからモデルを取得 |
| `lmms info <model>` | モデルのメタデータ、コンテキスト長、量子化を確認 |
| `lmms rm <model>` | ローカルに保存されているモデルを削除 |
| `lmms search <query>` | 利用可能な公開モデル リポジトリを検索 |
| `lmms benchmark <model>` | 生成速度（トークン/秒）と応答遅延を計測 |
| `lmms doctor [--fix]` | エンジンの健全性診断と軽微な問題の自動修復、CUDA/ドライバ検証 |
| `lmms create <model> -f <file>` | GGUF またはマニフェストからカスタム モデルを登録 |

---

### Air Engine (インテリジェントな RAM/VRAM スワップ機構)

GPU、CPU、ディスク間の動的多層オフロードにより、物理 VRAM を超える巨大モデルを実行。

| コマンド | 説明 |
|---|---|
| `lmms -air run <model> [prompt]` | AirEngine による多層オフロードで超巨大モデルを実行 |
| `lmms --air run <m1> <m2>` | Air スケジューラを通じて複数モデルを同時実行 |
| `lmms air ps` | Air セッション中のモデル層配置と GPU/CPU 状況を表示 |
| `lmms air stats` | リアルタイムのハードウェア負荷とオフロード速度を表示 |
| `lmms air cache` | Air ディスク キャッシュの容量と利用率を確認 |
| `lmms air unload` | 全 Air モデルを解放し VRAM キャッシュを完全消去 |
| `lmms air benchmark <model>` | Air オフロード制御下での実行スループットを測定 |

---

### Server / Daemon

| コマンド | 説明 |
|---|---|
| `lmms server` | API / Web サーバ デーモンを起動 |
| `lmms server status` | サーバの状態、ポート、稼働時間、ヘルスチェックを確認 |
| `lmms engine status` | 現在のエンジン モードとメモリ割り当てを表示 |
| `lmms engine unload [model]` | アクティブ モデルをメモリから破棄し VRAM を解放 |
| `lmms server start [--port 11435]` | 指定ポートで FastAPI バックグラウンド デーモンを起動 |
| `lmms server stop` | 動作中のバックグラウンド デーモンを停止 |

---

## 対話型 CLI スラッシュ コマンド

| コマンド | 説明 |
|---|---|
| `/fast` | レスポンス速度を最優先する FAST モードに切り替え |
| `/deep` | 多段階の深い推論とフルツール権限を持つ DEEP モードに切り替え |
| `/model <name>` | 現在の会話セッションで使用するモデルを変更 |
| `/ml -l` | ローカルに存在する全モデルをチャット内で一覧表示 |
| `/ml -s <name>` | 会話履歴を保持したままモデルをホット スイッチ |
| `/folder <path>` | 指定フォルダを作業コンテキストとしてエージェントに紐付け |
| `/code` | コード生成と自動パッチ適用に特化したモードへ移行 |
| `/chat` | 過去の会話セッション履歴を表示・確認 |
| `/newchat` | 新しいクリーンな会話セッションを開始 |
| `/chat -r <id> <name>` | 指定したセッション名をリネーム |
| `/chat -d <id>` | 指定したセッション履歴を完全削除 |
| `/undo` | 直前に行われた AI のファイル編集やパッチを安全に取り消し |
| `/redo` | 取り消されたファイル操作を再度やり直す |
| `/exit` | 対話型 CLI セッションを終了 |
| `/reboot` | バックエンド エンジンを再起動しセッションを再接続 |
| `/mic` | マイク入力を録音し、プロンプトへリアルタイム文字起こし |
| `/vision または /image` | 画像解析や UI 診断を行うマルチモーダル Vision モードへ切り替え |
| `/research` | 技術ドキュメントや Web 情報を調査するリサーチ モードへ切り替え |
| `/read <file>` | 指定ファイルを直接会話コンテキストに読み込み |
| `/task` | バックグラウンドで動作する自律サブタスクの管理 |
| `/git` | 監査ログ付きの安全な Git 操作をエージェント経由で実行 |
| `/scope` | 現在のツール実行権限の範囲を確認・変更 |
| `/tools list` | 利用可能な全ネイティブ ツールおよび MCP ツールを表示 |
| `/report` | 暗号署名付きの操作監査レポートを出力 |
| `/checkpoint` | 現在のワークスペース状態の不変チェックポイントを作成 |
| `/checkpoints` | 保存されているチェックポイント一覧を表示 |
| `/rollback` | リポジトリとファイルを過去のチェックポイントへ復元 |
| `/status` | エンジンとハードウェアのリアルタイム健全性を確認 |
| `/doctor` | 総合システム診断と自動修復テストを実行 |
| `/pair` | 対話型ペア プログラミング モードを開始 |
| `/perm <level>` | サンドボックスの実行権限レベル (`strict`, `ask`, `full`) を変更 |
| `/agent` | 並行処理を行う自律サブエージェントを生成・管理 |
| `/orchestrate` | 複数エージェントによる連携ワークフローを統合管理 |

---

## プロダクト設計思想

1. **実用性を第一に**: コード編集、AST 構文検証、サンドボックス実行に特化。
2. **透明性と誠実さ**: テレメトリ収集ゼロ、不当な課金なし。
3. **ローカル ファースト**: すべてのモデルとデータ資産はお手元に保持。
4. **クリーンな構成**: 不要な依存関係を排除した純粋な Python 設計。

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
