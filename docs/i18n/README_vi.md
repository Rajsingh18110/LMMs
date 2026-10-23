<div align="center">
  <a href="https://lmms.markanm.com">
    <img src="../../assets/lmms-banner.svg" alt="LMMs OS" width="100%" />
  </a>
</div>

<p align="center">
  <strong>Xây dựng với các mô hình. Phát hành với các tác tử.</strong><br>
  <em>Hệ điều hành AI cục bộ nguyên bản bằng Python được phát triển bởi nhà sáng lập Raj Singh (MarkanM)</em>
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
[![Türkçe](https://img.shields.io/badge/Language-Türkçe-e11d48?style=flat-square)](README_tr.md)
[![Tiếng Việt](https://img.shields.io/badge/Language-Tiếng_Việt-d97706?style=flat-square)](#)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-be123c?style=flat-square)](README_id.md)
[![বাংলা](https://img.shields.io/badge/Language-বাংলা-047857?style=flat-square)](README_bn.md)
[![ਪੰਜਾਬੀ](https://img.shields.io/badge/Language-ਪੰਜਾਬੀ-c2410c?style=flat-square)](README_pa.md)
[![मराठी](https://img.shields.io/badge/Language-मराठी-1d4ed8?style=flat-square)](README_mr.md)
[![اردو](https://img.shields.io/badge/Language-اردو-065f46?style=flat-square)](README_ur.md)
[![ไทย](https://img.shields.io/badge/Language-ไทย-4338ca?style=flat-square)](README_th.md)

</div>


<p align="center">
  <a href="https://lmms.markanm.com">Trang Chủ</a> ·
  <a href="#system-architecture">Kiến Trúc</a> ·
  <a href="#deep-technical-capabilities">Khả Năng Cốt Lõi</a> ·
  <a href="#quick-start">Khởi Động Nhanh</a> ·
  <a href="#architecture-setup-wizard-lmms-install">Trình Cài Đặt</a> ·
  <a href="#enterprise-infrastructure--super-host">Doanh Nghiệp</a> ·
  <a href="#core-command-reference">Lệnh Cốt Lõi</a> ·
  <a href="#cli-slash-commands">Lệnh Slash</a> ·
  <a href="#license">Giấy Phép</a>
</p>

---

## LMMs OS Là Gì?

LMMs là tầng vận hành AI nguyên bản bằng Python phục vụ thực thi mô hình cục bộ và từ xa. Được xây dựng bởi nhà sáng lập Raj Singh (MarkanM), nó kết hợp giao diện đồ họa máy tính để bàn (GUI), giao diện dòng lệnh thông minh (CLI) và bộ động cơ suy luận hoàn thiện để giúp lập trình viên và doanh nghiệp triển khai các mô hình đa phương thức mà không cần gửi dữ liệu lên đám mây hay chịu ràng buộc dịch vụ.

* **Lõi động cơ kép nguyên bản**: Suy luận GGUF lượng tử hóa hiệu năng cao với llama.cpp cùng môi trường chạy safetensors thuần PyTorch.
* **Mở rộng không giới hạn với AirEngine**: Phân tầng và chuyển tải tensor động giữa GPU, CPU và ổ đĩa cho phép chạy các mô hình 70B+ ngay trên máy tính xách tay thông thường.
* **Desktop Studio (GUI)**: Trình biên tập mã nguồn Monaco, công cụ so sánh diff trực quan, tích hợp Git và quản lý công cụ.
* **Terminal Studio (CLI)**: Shell tương tác với hơn 30 lệnh slash, lập trình cặp đôi (pair-programming), điều phối tác tử con và hộp cát an toàn.
* **Sẵn sàng cho Doanh nghiệp**: Mô hình cụm máy khách - máy chủ phân tán trên mạng nội bộ LAN/VPC với cơ chế tự động dò tìm máy chủ trung tâm.

---

## Kiến Trúc Hệ Thống

Sơ đồ dưới đây minh họa kiến trúc toàn diện của LMMs OS qua 4 phân hệ chính: Giao diện người dùng, Tầng dịch vụ backend, Động cơ suy luận và Khả năng tác tử:

<div align="center">
  <img src="../../assets/lmms-architecture.png" alt="LMMs OS System Architecture" width="100%" />
</div>

### Architectural Subsystems:

1. **Giao diện Người dùng**: `GUI workspace [main_window.py]` (IDE Monaco và đánh giá diff) và `CLI [commands.py]` (terminal tương tác cho lập trình viên).
2. **Tầng API và Backend**: `HTTP API [server.py]` (FastAPI daemon trên cổng 11435), `Backend session [main.py]` (điều phối phiên làm việc), và `Backend services [manager.py]`.
3. **Phân hệ Suy luận Mô hình**: `Runtime selection [manager.py]`, `AirEngine [runtime.py]` (chuyển tải tensor GPU/CPU/Ổ đĩa), `Model registry [registry.py]`, `động cơ llama.cpp` và `động cơ PyTorch`.
4. **Phân hệ Năng lực Tác tử**: `Request orchestration [pipeline.py]`, `Vector retrieval [rag.py]`, `Agent routing [manager.py]`, `Tool execution [executor.py]`, `Session memory [core_memory.py]`, `Web research [engine.py]` và `Workspace & Git [manager.py]`.

---

## Năng Lực Kỹ Thuật Chuyên Sâu (Deep Technical Capabilities)

### 1. Động cơ Thị giác Đa phương thức (`/vision`, `/image`)
LMMs tích hợp sẵn đường ống xử lý thị giác máy tính trực tiếp trong động cơ cục bộ:
* **Phân tích giao diện và bố cục**: Kiểm tra ảnh chụp màn hình ứng dụng web hoặc desktop để phát hiện lỗi hiển thị, lệch căn chỉnh và sai lệch CSS.
* **Trích xuất lưu đồ và kiến trúc hệ thống**: Đọc các biểu đồ luồng, sơ đồ quan hệ ER và chuỗi UML để chuyển đổi trực tiếp thành mã Mermaid hoặc cấu trúc dữ liệu.
* **Nhận dạng ký tự quang học (OCR) nội bộ**: Trích xuất văn bản và bảng biểu từ hình ảnh và PDF mà không gửi dữ liệu ra bên ngoài.

### 2. Âm thanh và Nhận dạng Giọng nói Ngoại tuyến (`/mic`)
* **Chuyển đổi giọng nói thành văn bản cục bộ**: Phiên âm ngoại tuyến tốc độ cao nhờ mô hình Whisper lượng tử hóa chạy ngay trên máy tính của bạn.
* **Nhập lệnh rảnh tay**: Thu âm trực tiếp các chỉ dẫn lập trình vào cửa sổ dòng lệnh với độ trễ bằng không.

### 3. Tương thích Git và Cô lập Cây làm việc Worktree (`/git`, `/scope`)
* **Khóa an toàn chỉ đọc**: Tự động giới hạn hành vi tác tử ở các thao tác đọc an toàn (`cat`, `git diff`, `grep`) trừ khi được cấp quyền rõ ràng.
* **Git Worktree tạm thời**: Các chỉnh sửa mã được thực hiện trên bản sao worktree riêng biệt và chỉ được gộp vào nhánh chính sau khi vượt qua toàn bộ bài kiểm thử tự động.
* **Xem trước Diff có màu**: Mọi thay đổi tệp tin đều được hiển thị dưới dạng diff trực quan trước khi ghi xuống đĩa.

### 4. Điểm kiểm soát Xác định và Khôi phục Tức thì (`/checkpoint`, `/rollback`, `/undo`, `/redo`)
* **Sao lưu từng bước thực thi**: Ảnh chụp bất biến của các tệp bị sửa đổi được tạo trước mỗi hành động can thiệp mã nguồn.
* **Khôi phục trong vài mili giây**: Nếu bản vá gây lỗi kiểm thử hoặc cú pháp, `/rollback` hoặc `/undo` sẽ khôi phục kho mã về trạng thái ban đầu ngay lập tức.

### 5. Tác tử con Tự trị và Điều phối Đa tác tử (`/agent`, `/orchestrate`)
* **Tác vụ chạy ngầm độc lập**: Khởi tạo tác tử con với hạn mức token riêng biệt và phạm vi truy cập tệp an toàn để xử lý song song.
* **Phân cấp nhiệm vụ**: Tác tử điều phối chính bàn giao các công việc chuyên biệt (kiểm thử, tài liệu hóa, dọn dẹp mã) cho tác tử con và tổng hợp kết quả.

### 6. Nghiên cứu Nội bộ và RAG Vector (`/research`)
* **Đánh chỉ mục mã nguồn ngữ nghĩa**: Lập chỉ mục không gian làm việc vào kho lưu trữ vector cục bộ để tìm kiếm hàm, lớp và cấu trúc một cách nhanh chóng.
* **Tra cứu tài liệu không ảo giác**: Tải và đọc tài liệu API nội bộ để loại bỏ triệt để việc mô hình tạo ra mã nguồn sai lệch.

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

## Trình Hướng Dẫn Cài Đặt Kiến Trúc (`lmms install`)

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

### [1] Cấu Hình Cho Trạm Làm Việc Đơn Lẻ

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

### [2] Hạ Tầng Doanh Nghiệp Và Máy Chủ Siêu Cấp

```text
  ? Select Enterprise Infrastructure Role:

  ❯ [1] Host Server Infrastructure
        Central inference server daemon listening on 0.0.0.0:11435 for team access

    [2] Remote Client Studio
        Workstation applications connecting to host via Local->LAN->Global discovery
  ──────────────────────────────────────────────────────────────────────
```

* **Tính toán tập trung hiệu năng cao**: Máy chủ daemon chạy trên hệ thống GPU trung tâm (`0.0.0.0:11435`) để phục vụ và huấn luyện mô hình nội bộ.
* **Studio máy khách từ xa**: Nhân viên kết nối từ máy tính xách tay cá nhân qua mạng nội bộ LAN/VPC với tính năng tự động phát hiện máy chủ.
* **Bảo mật dữ liệu tuyệt đối**: Không có bất kỳ dòng mã hay câu lệnh prompt nào bị lọt ra ngoài mạng riêng của doanh nghiệp.
* **AirEngine không giới hạn phần cứng**: Tự động luân chuyển trọng số mô hình lớn qua VRAM, RAM và bộ nhớ NVMe tốc độ cao.

---

### Pip & Installer Command Matrix

| Lệnh | Mục đích | Thành phần mục tiêu |
|---|---|---|
| `lmms install` | Khởi động trình hướng dẫn cài đặt kiến trúc tương tác | Menu cấu hình tương tác |
| `lmms install --all` | Cài đặt toàn bộ hệ sinh thái | Desktop Studio, CLI, Giọng nói, Super Engine |
| `lmms install --gui` | Cài đặt Desktop Studio (GUI) | Giao diện PyQt6, Trình soạn thảo Monaco, Client |
| `lmms install --cli` | Cài đặt Terminal Studio (CLI) | Shell tương tác, bộ công cụ dev, Client |
| `lmms install --engine` | Cài đặt bộ động cơ hỗn hợp Super Engine | llama.cpp + PyTorch + AirEngine |
| `lmms install --engine1` | Cài đặt động cơ nhẹ (Lightweight) | llama.cpp + AirEngine (dành riêng GGUF) |
| `lmms install --engine2` | Cài đặt động cơ PyTorch gốc | PyTorch + Transformers + AirEngine |
| `lmms install --host` | Cài đặt máy chủ doanh nghiệp trung tâm | Daemon lắng nghe trên địa chỉ 0.0.0.0:11435 |
| `lmms install --client-gui` | Cài đặt máy khách GUI doanh nghiệp | GUI kết nối với máy chủ từ xa qua mạng LAN |
| `lmms install --client-cli` | Cài đặt máy khách CLI doanh nghiệp | CLI kết nối với máy chủ từ xa qua mạng LAN |
| `lmms update` | Cập nhật mã nguồn mới nhất của ứng dụng | Cập nhật nhánh đang hoạt động |
| `lmms update --all` | Cập nhật bắt buộc đồng bộ tất cả các nhánh | Đồng bộ hóa toàn diện từ kho GitHub |
| `lmms -check` | Chẩn đoán phần cứng và kiểm tra điều kiện hệ thống | Đo lường CPU, GPU, VRAM, AVX và ổ đĩa |
| `lmms-uninstall -all` | Gỡ bỏ mã nguồn an toàn | Xóa mã, giữ nguyên gói pip và bộ nhớ đệm mô hình |
| `lmms-uninstall -all --purge` | Khôi phục cài đặt gốc và xóa hoàn toàn | Xóa vĩnh viễn toàn bộ cấu hình, mô hình và dữ liệu |

---

## Tài Liệu Hướng Dẫn Lệnh Cốt Lõi

### LMMs Core Launcher Commands

| Lệnh | Mô tả |
|---|---|
| `lmms` | Khởi chạy giao diện mặc định đã được cấu hình |
| `lmms --gui` | Khởi chạy trực tiếp giao diện máy tính để bàn (GUI) |
| `lmms --cli` | Khởi chạy trực tiếp giao diện dòng lệnh (CLI) |
| `lmms --engine` | Khởi chạy trực tiếp dịch vụ động cơ suy luận |
| `lmms set --gui` | Thiết lập Desktop Studio làm chế độ khởi động mặc định |
| `lmms set --cli` | Thiết lập Terminal Studio làm chế độ khởi động mặc định |
| `lmms set --engine` | Thiết lập Engine Daemon làm chế độ khởi động mặc định |
| `lmms stop` | Dừng an toàn dịch vụ động cơ LMMs đang chạy ngầm |
| `lmms -check` | Kiểm tra hồ sơ phần cứng và các thư viện phụ thuộc |
| `lmms update` | Cập nhật thông minh từ nhánh Git hiện tại |
| `lmms update --all` | Bắt buộc cập nhật toàn bộ từ kho GitHub |
| `lmms --help` | Hiển thị trợ giúp chi tiết về trình khởi chạy |

---

### Engine Runtime & Air Engine

| Lệnh | Mô tả |
|---|---|
| `lmms run <model>` | Chạy mô hình trong phiên trò chuyện hoặc câu lệnh đơn |
| `lmms list` | Liệt kê danh sách các mô hình đã tải về máy |
| `lmms ps` | Xem các mô hình đang hoạt động và dung lượng VRAM chiếm dụng |
| `lmms pull <model>` | Tải mô hình từ Hugging Face hoặc Model Hub chính thức |
| `lmms info <model>` | Xem thông số siêu dữ liệu, độ dài ngữ cảnh và mức lượng tử |
| `lmms search <query>` | Tìm kiếm các kho lưu trữ mô hình mã nguồn mở |
| `lmms benchmark <model>` | Đo tốc độ tạo token (t/s) và độ trễ phản hồi |
| `lmms doctor` | Chẩn đoán tình trạng động cơ và trình điều khiển CUDA/GPU |
| `lmms create <model> -f <file>` | Đăng ký mô hình tùy chỉnh từ tệp GGUF hoặc Safetensors |
| `lmms -air run <model> [prompt]` | Chạy mô hình siêu lớn nhờ cơ chế chia tầng bộ nhớ AirEngine |
| `lmms --air run <m1> <m2>` | Chạy đồng thời nhiều mô hình qua bộ lập lịch Air |
| `lmms air ps` | Theo dõi phiên Air và sự phân bổ các tầng mô hình trên GPU/CPU |
| `lmms air stats` | Xem thống kê thời gian thực về thông lượng và tốc độ chuyển tải |
| `lmms air cache` | Kiểm tra kích thước và mức sử dụng bộ nhớ đệm ổ đĩa Air |
| `lmms air unload` | Gỡ bỏ tất cả mô hình Air và làm sạch bộ nhớ VRAM ngay lập tức |
| `lmms air benchmark <model>` | Đánh giá tốc độ xử lý dưới sự điều phối của Air |

---

### Server / Daemon

| Lệnh | Mô tả |
|---|---|
| `lmms server` | Khởi động dịch vụ máy chủ API / Web |
| `lmms server status` | Kiểm tra trạng thái máy chủ, cổng, thời gian hoạt động |
| `lmms engine status` | Xem chế độ động cơ đang hoạt động và số liệu RAM |
| `lmms engine unload [model]` | Gỡ mô hình khỏi bộ nhớ và giải phóng tài nguyên VRAM |
| `lmms server start [--port 11435]` | Chạy máy chủ FastAPI dưới nền trên cổng chỉ định |
| `lmms server stop` | Dừng máy chủ đang chạy ở chế độ nền |

---

## Lệnh Slash Tương Tác Trong CLI

| Lệnh | Mô tả |
|---|---|
| `/fast` | Chuyển sang chế độ FAST để phản hồi nhanh và dùng công cụ nhẹ |
| `/deep` | Chuyển sang chế độ DEEP với suy luận sâu nhiều bước và đủ quyền công cụ |
| `/model <name>` | Đổi sang mô hình khác cho phiên trò chuyện hiện tại |
| `/ml -l` | Xem danh sách toàn bộ mô hình cục bộ ngay trong cửa sổ chat |
| `/ml -s <name>` | Đổi mô hình ngay tức thì mà không làm mất lịch sử hội thoại |
| `/folder <path>` | Gắn một thư mục vào ngữ cảnh làm việc của tác tử |
| `/code` | Vào chế độ chuyên sâu tạo mã và áp dụng bản vá tự động |
| `/chat` | Liệt kê và xem lại lịch sử các phiên trò chuyện trước |
| `/newchat` | Bắt đầu một phiên trò chuyện mới hoàn toàn sạch |
| `/chat -r <id> <name>` | Đổi tên một phiên trò chuyện cụ thể |
| `/chat -d <id>` | Xóa vĩnh viễn một phiên trò chuyện đã chọn |
| `/undo` | Hủy bỏ an toàn thao tác chỉnh sửa tệp gần nhất của AI |
| `/redo` | Làm lại thao tác tệp vừa được hủy bỏ |
| `/exit` | Thoát khỏi phiên làm việc dòng lệnh tương tác |
| `/reboot` | Khởi động lại động cơ backend và kết nối lại phiên |
| `/mic` | Thu âm giọng nói và phiên âm trực tiếp vào câu lệnh nhắc |
| `/vision hoặc /image` | Chuyển sang chế độ thị giác đa phương thức để phân tích ảnh và UI |
| `/research` | Chuyển sang chế độ nghiên cứu tài liệu kỹ thuật và tra cứu web |
| `/read <file>` | Đọc tệp tin bất kỳ trong dự án trực tiếp vào ngữ cảnh phiên |
| `/task` | Quản lý các tác vụ tự trị ngầm và mục tiêu của tác tử con |
| `/git` | Thực thi các lệnh Git an toàn và có nhật ký kiểm toán qua tác tử |
| `/scope` | Kiểm tra và điều chỉnh phạm vi thực thi của các công cụ |
| `/tools list` | Liệt kê toàn bộ công cụ tích hợp và máy chủ MCP đang hoạt động |
| `/report` | Tạo báo cáo kiểm toán bảo mật và hành động có chữ ký số |
| `/checkpoint` | Lưu điểm kiểm soát (checkpoint) bất biến cho không gian làm việc |
| `/checkpoints` | Liệt kê tất cả các điểm kiểm soát đã lưu của dự án |
| `/rollback` | Khôi phục kho mã và tệp tin về điểm kiểm soát đã lưu trước đó |
| `/status` | Kiểm tra tình trạng sức khỏe thời gian thực của động cơ và phần cứng |
| `/doctor` | Chạy chẩn đoán toàn diện hệ thống và kiểm thử tự phục hồi |
| `/pair` | Bắt đầu chế độ lập trình đôi (pair-programming) tương tác |
| `/perm <level>` | Điều chỉnh mức quyền hạn của hộp cát sandbox (`strict`, `ask`, `full`) |
| `/agent` | Tạo và quản lý các tác tử con độc lập để xử lý song song |
| `/orchestrate` | Quản lý và điều phối các luồng công việc phức tạp giữa nhiều tác tử |

---

## Triết Lý Sản Phẩm

1. **Tính Thực Dụng Là Trên Hết**: Vá mã thực tế, kiểm tra cú pháp AST và chạy trong hộp cát.
2. **Minh Bạch Và Tin Cậy**: Hoàn toàn không thu thập dữ liệu (zero-telemetry), không phí ngầm.
3. **Ưu Tiên Cục Bộ Tuyệt Đối**: Toàn bộ mô hình, trọng số và dữ liệu luôn nằm trên máy của bạn.
4. **Kiến Trúc Tối Giản**: Xây dựng thuần Python không mang vác phụ thuộc rườm rà.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](../../LICENSE) file for complete details.

<div align="center">
  <p>Official Website: <a href="https://lmms.markanm.com">https://lmms.markanm.com</a></p>
  <p><sub>Developed with pride by <strong>Raj Singh (MarkanM)</strong> · All rights reserved.</sub></p>
</div>
