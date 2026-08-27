import os
import psutil
import subprocess
import requests
import time
import markdown
import datetime
import os
import psutil
import subprocess
import requests
import time
import markdown
import datetime
import json
import re

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle,
    QLabel, QPushButton, QComboBox, QLineEdit, QFrame,
    QProgressBar, QTextBrowser, QSizePolicy, QScrollArea, QDialog, QFormLayout, QDockWidget, QGridLayout, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QObject, QUrl, QRect, QSize, QTimer,
    pyqtSignal, QPropertyAnimation, QEasingCurve, QThread, QEvent
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QPixmap, QColor, QBrush,
    QPen, QFont, QIcon, QCursor, QDesktopServices
)
from PyQt6.QtNetwork import (
    QNetworkAccessManager, QNetworkRequest, QNetworkReply
)

from lmms.backend.services.model_cache import ModelCache
from lmms.backend.services.model_registry import ModelRegistry

def get_provider_details(model_id: str):
    low = model_id.lower()
    verified = False
    if "meta" in low or "llama" in low: return "meta-llama", "#0668E1", "M", True
    if "google" in low or "gemma" in low: return "google", "#EA4335", "G", True
    if "qwen" in low or "alibaba" in low: return "Qwen", "#7C3AED", "Q", True
    if "mistral" in low or "mixtral" in low: return "mistralai", "#F97316", "M", True
    if "microsoft" in low or "phi" in low: return "microsoft", "#00A4EF", "M", True
    if "ollama" in low: return "Ollama", "#222222", "O", True
    
    author = model_id.split('/')[0] if '/' in model_id else model_id
    initial = author[0].upper() if author else "M"
    colors = ["#D97706", "#059669", "#2563EB", "#7C3AED", "#DB2777", "#DC2626"]
    color = colors[hash(author) % len(colors)]
    return author, color, initial, False

def parse_model_tags(repo_id: str, tags: list):
    params_str = ""
    context_len = ""
    arch = ""
    formats = set()
    capabilities = []

    for tag in tags:
        tagL = tag.lower()
        if "b" in tagL and len(tagL) < 5 and tagL[0].isdigit(): params_str = tag.upper()
        if tagL in ["gguf", "safetensors", "gptq", "awq", "onnx"]: formats.add(tag.upper())
        if "32k" in tagL or "128k" in tagL or "64k" in tagL: context_len = tag.upper()
        if tagL in ["llama", "gemma", "qwen2", "mistral"]: arch = tag.capitalize()
        
        if "vision" in tagL or "image" in tagL: capabilities.append("👁 Vision")
        if "reasoning" in tagL: capabilities.append("🧠 Reasoning")
        if "tool" in tagL or "function" in tagL: capabilities.append("🔧 Tool Use")

    if not params_str:
        import re
        m = re.search(r'(\d+(?:\.\d+)?[bBmM])', repo_id)
        if m:
            params_str = m.group(1).upper()
        else:
            m2 = re.search(r'(\d+(?:\.\d+)?[bBmM])', repo_id)
            if m2:
                params_str = m2.group(1).upper()

    format_str = ", ".join(formats) if formats else "GGUF/Safetensors"
    return params_str, arch, context_len, format_str, capabilities

def estimate_hardware(params_str: str, format_str: str):
    params = 7
    if "B" in params_str.upper():
        try:
            params = float(params_str.upper().split("B")[0].split()[-1].replace("X", "").strip("M"))
        except: pass
    
    is_quant = "GGUF" in format_str.upper() or "AWQ" in format_str.upper() or "GPTQ" in format_str.upper()
    multiplier = 0.65 if is_quant else 2.2
    
    vram_gb = (params * multiplier) * 1.2
    
    sys_vram = 0
    try:
        res = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader'], capture_output=True, text=True)
        if res.stdout.strip():
            sys_vram = int(res.stdout.strip().split()[0]) / 1024
    except: pass
    
    if sys_vram == 0:
        return f"Estimated VRAM: {vram_gb:.1f} GB | Mac/CPU Detected"
    
    status = "Likely Compatible" if sys_vram >= vram_gb else "Requires more VRAM"
    return f"Estimated VRAM: {vram_gb:.1f} GB | Detected GPU: {sys_vram:.1f} GB | Status: {status}"

def format_relative_time(iso_date: str):
    if not iso_date: return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt
        days = diff.days
        if days == 0: return "today"
        if days == 1: return "1 day ago"
        return f"{days} days ago"
    except:
        return ""

def format_size(bytes_size):
    if bytes_size == 0: return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

class HFApiClient(QObject):
    models_ready = pyqtSignal(list)
    files_ready = pyqtSignal(str, list)
    readme_ready = pyqtSignal(str, str)
    config_ready = pyqtSignal(str, dict)
    info_ready = pyqtSignal(str, dict)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._cache = {}
        self._pending_readmes = {}

    def _create_request(self, url_str):
        req = QNetworkRequest(QUrl(url_str))
        req.setAttribute(QNetworkRequest.Attribute.Http2AllowedAttribute, False)
        req.setRawHeader(b"User-Agent", b"LMMsBrowser/1.0")
        return req

    def fetch_models(self, sort="downloads", limit=30, filter_tag="gguf", search_query="", type_filter=""):
        params = f"limit={limit}&sort={sort}&filter={filter_tag}"
        if search_query:
            params += f"&search={QUrl.toPercentEncoding(search_query).data().decode()}"
        if type_filter and type_filter != "all" and type_filter != "Installed / Remote":
            if type_filter == "Text": params += "&pipeline_tag=text-generation"
            elif type_filter == "Vision": params += "&pipeline_tag=image-to-text"
            elif type_filter == "Reasoning": params += "&tags=reasoning"
            elif type_filter == "Coding": params += "&tags=code"
            elif type_filter == "Audio": params += "&pipeline_tag=text-to-audio"
            
        url_str = f"https://huggingface.co/api/models?{params}"

        if url_str in self._cache:
            self.models_ready.emit(self._cache[url_str])
            return

        req = self._create_request(url_str)
        req.setRawHeader(b"Accept", b"application/json")
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._handle_models(reply, url_str))

    def _handle_models(self, reply, cache_key):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.error.emit(f"Failed to fetch models: {reply.errorString()}")
            reply.deleteLater()
            return
        try:
            data = json.loads(bytes(reply.readAll()))
        except Exception as e:
            self.error.emit(f"JSON parse error: {e}")
            reply.deleteLater()
            return
        self._cache[cache_key] = data
        self.models_ready.emit(data)
        reply.deleteLater()

    def fetch_config(self, fetch_id: str, emit_id: str = None):
        if not emit_id: emit_id = fetch_id
        url_str = f"https://huggingface.co/{fetch_id}/resolve/main/config.json"
        req = self._create_request(url_str)
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._on_config_finished(reply, emit_id))

    def _on_config_finished(self, reply, emit_id):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(reply.readAll().data())
                self.config_ready.emit(emit_id, data)
            except:
                self.config_ready.emit(emit_id, {})
        else:
            self.config_ready.emit(emit_id, {})
        reply.deleteLater()

    def fetch_model_info(self, model_id: str):
        url_str = f"https://huggingface.co/api/models/{model_id}"
        req = self._create_request(url_str)
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._handle_info(reply, model_id))

    def _handle_info(self, reply, model_id):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(reply.readAll().data())
                self.info_ready.emit(model_id, data)
            except:
                self.info_ready.emit(model_id, {})
        else:
            self.info_ready.emit(model_id, {})
        reply.deleteLater()

    def fetch_files(self, model_id: str):
        url_str = f"https://huggingface.co/api/models/{model_id}/tree/main"
        req = self._create_request(url_str)
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._handle_files(reply, model_id))

    def _handle_files(self, reply, model_id):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(reply.readAll().data())
                self.files_ready.emit(model_id, data)
            except:
                self.files_ready.emit(model_id, [])
        else:
            self.files_ready.emit(model_id, [])
        reply.deleteLater()

    def fetch_readme(self, model_id: str):
        if model_id in self._pending_readmes:
            old = self._pending_readmes.pop(model_id)
            old.abort()

        url_str = f"https://huggingface.co/{model_id}/raw/main/README.md"
        if url_str in self._cache:
            self.readme_ready.emit(model_id, self._cache[url_str])
            return
        req = self._create_request(url_str)
        reply = self._nam.get(req)
        self._pending_readmes[model_id] = reply
        reply.finished.connect(lambda: self._handle_readme(reply, model_id, url_str))

    def _handle_readme(self, reply, model_id, cache_key):
        self._pending_readmes.pop(model_id, None)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.readme_ready.emit(model_id, "")
            reply.deleteLater()
            return
        text = bytes(reply.readAll()).decode("utf-8", errors="replace")
        self._cache[cache_key] = text
        self.readme_ready.emit(model_id, text)
        reply.deleteLater()

    def clear_cache(self):
        self._cache.clear()

class ModelDownloaderThread(QThread):
    progress_updated = pyqtSignal(int, str, str)
    download_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, repo_id, filename, save_path):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename
        self.save_path = save_path

    def run(self):
        try:
            url = f"https://huggingface.co/{self.repo_id}/resolve/main/{self.filename}"
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            downloaded_size = 0
            start_time = time.time()
            last_time = start_time
            last_size = 0
            
            with open(self.save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk: break
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    now = time.time()
                    if now - last_time > 0.5:
                        speed = (downloaded_size - last_size) / (now - last_time)
                        speed_mb = speed / (1024*1024)
                        eta_sec = (total_size - downloaded_size) / speed if speed > 0 else 0
                        eta_str = f"{int(eta_sec//60)}m {int(eta_sec%60)}s"
                        progress = int(downloaded_size * 100 / total_size) if total_size > 0 else 0
                        self.progress_updated.emit(progress, f"{speed_mb:.1f} MB/s", eta_str)
                        last_time = now
                        last_size = downloaded_size
            self.download_complete.emit(self.save_path)
        except Exception as e:
            self.error_occurred.emit(str(e))

class LogoLoader(QObject):
    logo_ready = pyqtSignal(str, QPixmap)

    LOGO_SIZE = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._cache = {}
        self._in_flight = {}

    def load(self, org: str):
        if org in self._cache:
            self.logo_ready.emit(org, self._cache[org])
            return
        if org in self._in_flight:
            return

        urls = [
            f"https://huggingface.co/{org}/resolve/main/logo.png",
            f"https://huggingface.co/api/organizations/{org}/avatar",
            f"https://huggingface.co/api/users/{org}/avatar",
        ]
        self._try_url(org, urls, 0)

    def _try_url(self, org, urls, idx):
        if idx >= len(urls):
            pixmap = self._make_initials(org)
            self._cache[org] = pixmap
            self.logo_ready.emit(org, pixmap)
            return
        req = QNetworkRequest(QUrl(urls[idx]))
        req.setAttribute(QNetworkRequest.Attribute.Http2AllowedAttribute, False)
        req.setRawHeader(b"User-Agent", b"LMMsBrowser/1.0")
        reply = self._nam.get(req)
        self._in_flight[org] = reply
        reply.finished.connect(lambda: self._on_logo_reply(reply, org, urls, idx))

    def _on_logo_reply(self, reply, org, urls, idx):
        self._in_flight.pop(org, None)
        ok = (reply.error() == QNetworkReply.NetworkError.NoError)
        if ok:
            data = bytes(reply.readAll())
            
            # Check if Hugging Face returned JSON containing the avatarUrl
            if data.startswith(b"{"):
                try:
                    import json
                    json_data = json.loads(data.decode('utf-8'))
                    if "avatarUrl" in json_data:
                        urls.insert(idx + 1, json_data["avatarUrl"])
                        self._try_url(org, urls, idx + 1)
                        reply.deleteLater()
                        return
                except:
                    pass
                    
            pixmap = QPixmap()
            ok = pixmap.loadFromData(data)
            if not ok and len(data) > 0:
                try:
                    import io
                    from PIL import Image
                    img = Image.open(io.BytesIO(data))
                    out = io.BytesIO()
                    img.save(out, format="PNG")
                    ok = pixmap.loadFromData(out.getvalue())
                except:
                    pass
            ok = ok and not pixmap.isNull()
        if ok:
            pixmap = self._round_pixmap(pixmap, self.LOGO_SIZE)
            self._cache[org] = pixmap
            self.logo_ready.emit(org, pixmap)
        else:
            self._try_url(org, urls, idx + 1)
        reply.deleteLater()

    @staticmethod
    def _round_pixmap(src: QPixmap, size: int) -> QPixmap:
        result = QPixmap(size, size)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, size, size,
            src.scaled(size, size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation))
        painter.end()
        return result

    @staticmethod
    def _org_color(org: str) -> QColor:
        PALETTE = [
            "#534AB7","#185FA5","#0F6E56","#854F0B",
            "#993556","#3B6D11","#A32D2D","#5F5E5A",
        ]
        return QColor(PALETTE[hash(org) % len(PALETTE)])

    def _make_initials(self, org: str) -> QPixmap:
        name, color_hex, initial, verified = get_provider_details(org)
        
        s = self.LOGO_SIZE
        pixmap = QPixmap(s, s)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, s, s)
        painter.setPen(QPen(Qt.GlobalColor.white))
        
        font_size = s // 2 if len(initial) == 1 else s // 3
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, initial)
        painter.end()
        return pixmap

class ModelItemDelegate(QStyledItemDelegate):
    COMPAT_COLORS = {
        "ok":   "#1D9E75",
        "warn": "#BA7517",
        "err":  "#E24B4A",
    }

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor("#1e1e2e"))
            painter.fillRect(rect.x(), rect.y(), 3, rect.height(), QColor("#7F77DD"))

        m      = index.data(Qt.ItemDataRole.UserRole)
        logo   = index.data(Qt.ItemDataRole.UserRole + 1)
        avatar_key = index.data(Qt.ItemDataRole.UserRole + 2) or ""

        mid    = m.get("modelId", m.get("id", "Unknown"))
        name   = mid.split("/")[-1] if "/" in mid else mid
        dl     = m.get("downloads", 0)
        tags   = m.get("tags", [])
        caps   = m.get("capabilities", {})
        if isinstance(caps, list): # fallback for old HF records
            pass 
        else:
            if caps.get("vision"): tags.append("Vision")
            if caps.get("thinking"): tags.append("Thinking")
            if caps.get("tools"): tags.append("Tools")
            
        updated = format_relative_time(m.get("lastModified", ""))

        params  = next((t for t in tags if t.endswith("B") and t[:-1].replace(".","").isdigit()), "?B")
        if params == "?B" and m.get("title"):
            params_match = re.search(r'(\d+(?:\.\d+)?B)', m["title"])
            if params_match: params = params_match.group(1)

        quant   = next((t for t in tags if t in ("Q4_K_M","Q8_0","IQ4_NL","Q5_K_M","Q2_K")), "GGUF")
        
        cap_strings = []
        if "Vision" in tags or "👁 Vision" in tags: cap_strings.append("👁 Vision")
        if "Thinking" in tags or "🧠 Reasoning" in tags: cap_strings.append("🧠 Thinking")
        if "Tools" in tags or "🔧 Tool Use" in tags: cap_strings.append("🔧 Tools")
        
        extras = "  ·  ".join(cap_strings)
        if extras: extras = "  ·  " + extras
        
        if dl == "Local":
            compat = "ok"
            dl_str = "Local"
        else:
            compat  = "warn" if dl < 1000 else "ok"
            dl_str = (f"{dl/1e6:.1f}M" if dl >= 1_000_000 else f"{dl//1000}K" if dl >= 1000 else str(dl))

        x, y   = rect.x() + 10, rect.y()
        cy     = y + rect.height() // 2

        if logo and not logo.isNull():
            painter.drawPixmap(x, cy - 16, 32, 32, logo)
        else:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            _, color_hex, initial, _ = get_provider_details(mid)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x, cy - 16, 32, 32)
            
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(QRect(x, cy - 16, 32, 32), Qt.AlignmentFlag.AlignCenter, initial)

        tx = x + 40

        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#ffffff"))
        name_rect = QRect(tx, y + 8, rect.width() - tx - 70, 18)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        painter.setFont(QFont("Arial", 10))
        painter.setPen(QColor("#8b949e"))
        dot_color = self.COMPAT_COLORS.get(compat, "#888")
        painter.setBrush(QBrush(QColor(dot_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawEllipse(tx, cy + 8, 6, 6)
        painter.setPen(QColor("#8b949e"))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(tx + 12, y + rect.height() - 10, f"{params}  ·  {quant}{extras}")

        right_x = rect.right() - 65
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QColor("#8b949e"))
        
        if dl == "Local":
            painter.drawText(QRect(right_x - 70, y + 8, 60, 18), Qt.AlignmentFlag.AlignRight, dl_str)
            
            btn_rect = QRect(rect.right() - 65, rect.y() + (rect.height() - 24) // 2, 56, 24)
            painter.setBrush(QBrush(QColor("#21262d")))
            painter.setPen(QPen(QColor("#30363d"), 1))
            painter.drawRoundedRect(btn_rect, 4, 4)
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.setPen(QColor("#8b949e"))
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "Delete")
        else:
            painter.drawText(QRect(right_x, y + 8, 60, 18), Qt.AlignmentFlag.AlignRight, f"↓ {dl_str}")
        if updated:
            painter.drawText(QRect(right_x - 20, y + rect.height() - 22, 80, 18), Qt.AlignmentFlag.AlignRight, updated)
        
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(0, 54)

class ModelBrowser(QDockWidget):
    model_selected = pyqtSignal(dict) 

    def __init__(self, parent=None):
        super().__init__("Models", parent)
        self.setObjectName("ModelDock")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        self.api_client = HFApiClient(self)
        self.api_client.models_ready.connect(self._populate_list)
        self.api_client.error.connect(self.on_fetch_error)
        
        self._logo_loader = LogoLoader(self)
        self._logo_loader.logo_ready.connect(self._on_logo_loaded)
        
        self.init_title_bar()
        self.init_ui()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            for lst in [self.model_list, self.downloads_list]:
                if obj == lst.viewport():
                    pos = event.pos()
                    item = lst.itemAt(pos)
                    if item:
                        m = item.data(Qt.ItemDataRole.UserRole)
                        dl = m.get("downloads", 0)
                        if dl == "Local":
                            rect = lst.visualItemRect(item)
                            btn_rect = QRect(rect.right() - 65, rect.y() + (rect.height() - 24) // 2, 56, 24)
                            if btn_rect.contains(pos):
                                mid = m.get("id")
                                self.prompt_delete_model(mid)
                                return True
        return super().eventFilter(obj, event)

    def init_title_bar(self):
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(10, 5, 5, 5)
        title_layout.setSpacing(15)

        self.btn_discover = QPushButton("Models")
        self.btn_discover.setStyleSheet("background: transparent; color: #c9d1d9; font-weight: bold; font-size: 13px; border: none;")
        self.btn_discover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discover.clicked.connect(lambda: self.switch_tab(0))

        self.btn_downloads = QPushButton("Downloads")
        self.btn_downloads.setStyleSheet("background: transparent; color: #8b949e; font-size: 13px; border: none;")
        self.btn_downloads.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_downloads.clicked.connect(lambda: self.switch_tab(1))

        title_layout.addWidget(self.btn_discover)
        title_layout.addWidget(self.btn_downloads)
        title_layout.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("QPushButton { background: transparent; border: none; color: #8b949e; font-size: 14px; } QPushButton:hover { background: #f85149; color: white; border-radius: 4px; }")
        self.btn_close.clicked.connect(self.hide)

        title_layout.addWidget(self.btn_close)
        self.setTitleBarWidget(title_widget)

    def switch_tab(self, index):
        if index == 0:
            self.btn_discover.setStyleSheet("background: transparent; color: #c9d1d9; font-weight: bold; font-size: 13px; border: none;")
            self.btn_downloads.setStyleSheet("background: transparent; color: #8b949e; font-size: 13px; border: none;")
            if hasattr(self, 'stacked_widget'):
                self.stacked_widget.setCurrentIndex(0)
                self.load_models()
        else:
            self.btn_discover.setStyleSheet("background: transparent; color: #8b949e; font-size: 13px; border: none;")
            self.btn_downloads.setStyleSheet("background: transparent; color: #c9d1d9; font-weight: bold; font-size: 13px; border: none;")
            if hasattr(self, 'stacked_widget'):
                self.stacked_widget.setCurrentIndex(1)
                self.load_downloaded_models()


    def init_ui(self):
        container = QWidget()
        container.setStyleSheet("background-color: #0d1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        from PyQt6.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        
        self.discover_tab = QWidget()
        discover_layout = QVBoxLayout(self.discover_tab)
        discover_layout.setContentsMargins(0, 0, 0, 0)
        
        self.downloads_tab = QWidget()
        downloads_layout = QVBoxLayout(self.downloads_tab)
        downloads_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget.addWidget(self.discover_tab)
        self.stacked_widget.addWidget(self.downloads_tab)
        
        layout.addWidget(self.stacked_widget)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models by name...")
        self.search_input.setStyleSheet('''
            QLineEdit { background-color: #0e1116; color: #c9d1d9; border: 1px solid #30363d; padding: 8px 12px; border-radius: 6px; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #58a6ff; }
        ''')
        self.search_input.returnPressed.connect(self.load_models)
        search_layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "Text", "Vision", "Reasoning", "Coding", "Audio"])
        self.category_combo.setStyleSheet('''
            QComboBox { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 10px; border-radius: 6px; }
        ''')
        self.category_combo.currentTextChanged.connect(self.load_models)
        search_layout.addWidget(self.category_combo)

        # Clear button
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.setStyleSheet('''
            QPushButton { background: transparent; border: none; color: #888; font-size: 13px; }
            QPushButton:hover { color: #e0e0e0; }
        ''')
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self._collapse_search)
        search_layout.addWidget(self.clear_btn)

        discover_layout.addLayout(search_layout)

        QTimer.singleShot(0, self._store_combo_width)
        original_focus_in = self.search_input.focusInEvent
        def _search_focus_in(event):
            original_focus_in(event)
            self._expand_search()
        self.search_input.focusInEvent = _search_focus_in
        
        original_focus_out = self.search_input.focusOutEvent
        def _search_focus_out(event):
            original_focus_out(event)
            if not self.search_input.text():
                self._collapse_search()
        self.search_input.focusOutEvent = _search_focus_out
        
        # Escape key handling (from Missing Features fix)
        original_key_press = self.search_input.keyPressEvent
        def _search_key_press(event):
            if event.key() == Qt.Key.Key_Escape:
                self._collapse_search()
            else:
                original_key_press(event)
        self.search_input.keyPressEvent = _search_key_press

        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("color: #8b949e;")
        discover_layout.addWidget(self.status_label)

        self.model_list = QListWidget()
        self.model_list.setSpacing(1)
        self.model_list.setItemDelegate(ModelItemDelegate(self.model_list))
        self.model_list.itemClicked.connect(self._on_item_clicked)
        self.model_list.setStyleSheet("QListWidget { background-color: transparent; border: none; }")
        self.model_list.viewport().installEventFilter(self)

        discover_layout.addWidget(self.model_list)
        
        self.downloads_list = QListWidget()
        self.downloads_list.setSpacing(1)
        self.downloads_list.setItemDelegate(ModelItemDelegate(self.downloads_list))
        self.downloads_list.itemClicked.connect(self._on_item_clicked)
        self.downloads_list.setStyleSheet("QListWidget { background-color: transparent; border: none; }")
        self.downloads_list.viewport().installEventFilter(self)
        downloads_layout.addWidget(self.downloads_list)

        self.setWidget(container)
        self.load_models()
        self.load_downloaded_models()

    def _store_combo_width(self):
        self._combo_natural_width = self.category_combo.width()

    def _expand_search(self):
        if getattr(self, "_search_expanded", False): return
        self._search_expanded = True
        self.clear_btn.setVisible(True)

        self._anim_combo = QPropertyAnimation(self.category_combo, b"maximumWidth")
        self._anim_combo.setDuration(220)
        self._anim_combo.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_combo.setStartValue(self._combo_natural_width)
        self._anim_combo.setEndValue(0)
        self._anim_combo.start()

        self._anim_search = QPropertyAnimation(self.search_input, b"minimumWidth")
        self._anim_search.setDuration(220)
        self._anim_search.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_search.setStartValue(self.search_input.width())
        self._anim_search.setEndValue(self.search_input.width() + self._combo_natural_width)
        self._anim_search.start()

    def _collapse_search(self):
        if not getattr(self, "_search_expanded", False): return
        self._search_expanded = False
        self.search_input.clear()
        self.clear_btn.setVisible(False)
        self.search_input.clearFocus()

        self._anim_combo_back = QPropertyAnimation(self.category_combo, b"maximumWidth")
        self._anim_combo_back.setDuration(220)
        self._anim_combo_back.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_combo_back.setStartValue(0)
        self._anim_combo_back.setEndValue(self._combo_natural_width)
        self._anim_combo_back.start()

        self._anim_search_back = QPropertyAnimation(self.search_input, b"minimumWidth")
        self._anim_search_back.setDuration(220)
        self._anim_search_back.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_search_back.setStartValue(self.search_input.width())
        self._anim_search_back.setEndValue(self.search_input.width() - self._combo_natural_width)
        self._anim_search_back.start()

        self.load_models()

    def load_models(self):
        cat = self.category_combo.currentText()
        query = self.search_input.text()
        self.status_label.setText("Searching Hugging Face API..." if query else f"Loading {cat} models...")
        self.status_label.show()

        self.model_list.clear()
        self.api_client.fetch_models(search_query=query, type_filter=cat)
        
    def load_downloaded_models(self):
        self.downloads_list.clear()

        from lmms.backend.core.registry.model_registry import ModelRegistry
        models_list = ModelRegistry.list()

        models = []
        seen_paths = set()

        for m in models_list:
            # Support BOTH old-format (top-level source/path) and
            # new-format (nested metadata.source/metadata.path)
            meta = m.get("metadata", {}) or {}

            # Path: try top-level first, then metadata
            path = m.get("path") or meta.get("path", "")
            source = m.get("source") or meta.get("source", "")
            provider_name = m.get("provider", "")
            fmt = m.get("format") or meta.get("format", "")
            provider_id = m.get("provider_id", "")
            model_id = m.get("id", "") or m.get("model_id", "")

            # Determine if this is a local/offline model
            is_local = (
                source in ["Local", "lmms", "Imported (HF Cache)"]
                or provider_name in ["LMMs", "Ollama", "llama_cpp"]
                or fmt in ["GGUF", "gguf"]
                or (path and os.path.isabs(path))
                or provider_id.startswith("local_native")
                or model_id.startswith("local_native::")
            )

            if not is_local:
                continue

            # Deduplicate by file path
            if path:
                if path in seen_paths:
                    continue
                seen_paths.add(path)

            # Build display name — strip :: prefix artifacts
            display = m.get("display_name") or m.get("model_id") or model_id
            if "::" in display:
                display = display.split("::")[-1]

            # File size label
            size_bytes = m.get("size", 0) or meta.get("size", 0)
            if size_bytes:
                size_gb = size_bytes / (1024 ** 3)
                size_str = f"{size_gb:.2f} GB"
            else:
                size_str = ""

            tag_list = [fmt] if fmt else ["GGUF"]

            models.append({
                "id": model_id,
                "modelId": model_id,
                "title": display,
                "downloads": "Local",
                "tags": tag_list,
                "lastModified": m.get("updated_at", "") or m.get("last_used", ""),
                "capabilities": m.get("capabilities", {}),
                "state": "Downloaded",
                "size_str": size_str,
                "path": path,
            })

        # Sort by most recently used / updated
        models.sort(key=lambda x: str(x.get("lastModified", "")), reverse=True)

        if not models:
            # Show a helpful empty state label
            empty = QListWidgetItem("No downloaded models found.")
            empty.setForeground(QColor("#8b949e"))
            self.downloads_list.addItem(empty)
            return

        for m in models:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, m)
            org = m.get("id", "Unknown").split("/")[0]
            item.setData(Qt.ItemDataRole.UserRole + 2, org)
            item.setSizeHint(QSize(0, 54))
            self.downloads_list.addItem(item)
            self._logo_loader.load(org)

    def prompt_delete_model(self, mid):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {mid}?\nThis will permanently delete the model file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_local_model(mid)

    def _delete_local_model(self, mid):
        from lmms.backend.core.registry.model_registry import ModelRegistry
        info = ModelRegistry.get(mid)
        if info:
            path = info.get("path")
            source = info.get("source")
            if path and os.path.exists(path) and source in ["Local", "lmms"]:
                try:
                    os.remove(path)
                except Exception as e:
                    import lmms.gui.core.ui
                    lmms.gui.core.ui.show_error(f"Could not delete file:\n{e}")
                    return
            ModelRegistry.delete(mid)
            self.load_downloaded_models()
            self.load_models() # Refresh Discover tab too

    def _populate_list(self, models: list):
        self.status_label.hide()
        self.model_list.clear()
        
        from lmms.backend.core.registry.model_registry import ModelRegistry
        registry = ModelRegistry.list()
        
        for m in models:
            mid = m.get("id", "Unknown")
            is_local = any(m.get("internal_id") == mid for m in registry)
            if is_local:
                m["downloads"] = "Local"
                
            brand, _, _, is_verified = get_provider_details(mid)
            avatar_key = brand if is_verified else mid.split("/")[0]

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, m)
            item.setData(Qt.ItemDataRole.UserRole + 2, avatar_key)
            item.setSizeHint(QSize(0, 54))
            self.model_list.addItem(item)
            
            self._logo_loader.load(avatar_key)

        if not models:
            self.status_label.setText("No models found.")
            self.status_label.show()

    def _on_logo_loaded(self, org: str, pixmap: QPixmap):
        for lst in [self.model_list, getattr(self, "downloads_list", None)]:
            if lst is None: continue
            for i in range(lst.count()):
                item = lst.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole + 2) == org:
                    item.setData(Qt.ItemDataRole.UserRole + 1, pixmap)
            lst.viewport().update()

    def _on_item_clicked(self, item):
        if not item: return
        m = item.data(Qt.ItemDataRole.UserRole)
        if m:
            self.model_selected.emit(m)

    def on_fetch_error(self, err_msg):
        self.status_label.setText(f"Error: {err_msg}")
        self.status_label.setStyleSheet("color: #da3633;")
        self.status_label.show()

    def cleanup(self):
        self.api_client.clear_cache()


class ModelDetailsTab(QWidget):
    def __init__(self, model_info, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.repo_id = model_info.get("modelId", model_info.get("id", ""))
        self.local_status = ModelRegistry.get(self.repo_id)
        self.downloader = None
        self.api_client = HFApiClient(self)
        self.api_client.files_ready.connect(self.on_files_loaded)
        self.api_client.readme_ready.connect(self._render_readme)
        self.api_client.config_ready.connect(self._on_config_loaded)
        self.api_client.info_ready.connect(self._on_info_loaded)
        self.init_ui()
        self.load_metadata()

    def _fmt(self, val):
        if val == "Local": return "Local"
        if isinstance(val, int) or isinstance(val, float):
            if val >= 1_000_000: return f"{val/1e6:.1f}M"
            if val >= 1000: return f"{val//1000}K"
        return str(val)

    def _build_stats_strip(self, downloads, stars, params, ctx, updated):
        frame = QFrame()
        frame.setStyleSheet('''
            QFrame { border: 1px solid #30363d; border-radius: 8px; background: transparent; }
        ''')
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        stats = [
            ("DOWNLOADS", self._fmt(downloads)),
            ("STARS",     str(stars)),
            ("PARAMS",    params),
            ("CONTEXT",   ctx),
            ("UPDATED",   updated),
        ]
        for i, (lbl, val) in enumerate(stats):
            col_w = QWidget()
            col = QVBoxLayout(col_w)
            col.setContentsMargins(8, 12, 8, 12)
            col.setSpacing(4)
            v = QLabel(val)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet("font-size:16px; font-weight:bold; color:#e6edf3; border: none;")
            k = QLabel(lbl)
            k.setAlignment(Qt.AlignmentFlag.AlignCenter)
            k.setStyleSheet("font-size:10px; color:#8b949e; font-weight:600; border: none;")
            col.addWidget(v)
            col.addWidget(k)
            row.addWidget(col_w)
            if i < len(stats) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#30363d; background:#30363d; border: none;")
                sep.setFixedWidth(1)
                row.addWidget(sep)
        return frame

    def _make_badge(self, text: str, parent=None) -> QLabel:
        BADGE_STYLES = {
            "Vision":    ("👁 Vision", "#e8f0fe", "#1967d2", "#1967d2"),
            "Tool Use":  ("🔧 Tool Use", "#e6f4ea", "#137333", "#137333"),
            "Reasoning": ("🧠 Reasoning", "#fef7e0", "#b08d00", "#b08d00"),
            "GGUF":      ("📄 GGUF", "#ffffff", "#202124", "#dadce0"),
            "Compatible":("✓ Likely compatible", "#e6f4ea", "#137333", "#137333"),
            "llm":       ("💬 llm", "#e6f4ea", "#137333", "#137333")
        }
        bg, fg, border = BADGE_STYLES.get(text, [f"⚙ {text}", "#f3e8fd", "#7b1fa2", "#7b1fa2"])[1:]
        lbl_text = BADGE_STYLES.get(text, [f"⚙ {text}"])[0]
        lbl = QLabel(lbl_text, parent)
        lbl.setStyleSheet(f'''
            QLabel {{
                background: {bg}; color: {fg}; border: 1px solid {border};
                border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: bold;
            }}
        ''')
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return lbl

    def init_ui(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")
        
        self.container = QWidget()
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # Header: Title & Copy Icon
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        title_icon = QLabel("🤖")
        title_icon.setStyleSheet("font-size: 20px; color: #8b949e;")
        header_layout.addWidget(title_icon)
        
        self.title_lbl = QLabel(self.repo_id)
        self.title_lbl.setStyleSheet("color: #e6edf3; font-size: 22px; font-weight: bold; font-family: 'Segoe UI', sans-serif;")
        self.title_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(self.title_lbl)
        
        copy_btn = QPushButton("❐")
        copy_btn.setFixedSize(24, 24)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("QPushButton { border: none; background: transparent; color: #8b949e; font-size: 14px; } QPushButton:hover { color: #ffffff; }")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.repo_id))
        header_layout.addWidget(copy_btn)
        
        main_layout.addLayout(header_layout)

        # Subheader: Stats & Staff Pick
        stats_layout = QHBoxLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        stats_layout.setSpacing(20)
        
        self.stats_lbl = QLabel(f"↓ {self._fmt(self.model_info.get('downloads', 0))}   ☆ {self.model_info.get('likes', 0)}   Last updated: {format_relative_time(self.model_info.get('lastModified', ''))}")
        self.stats_lbl.setStyleSheet("color: #8b949e; font-size: 13px; font-weight: 500;")
        stats_layout.addWidget(self.stats_lbl)
        stats_layout.addStretch()
        
        staff_pick = QPushButton("👾 Staff Pick ↗")
        staff_pick.setFixedSize(110, 26)
        staff_pick.setStyleSheet("QPushButton { background-color: #3b3542; color: #d0a8ff; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid #483d53; }")
        stats_layout.addWidget(staff_pick)
        main_layout.addLayout(stats_layout)

        # Description Box
        desc_box = QFrame()
        desc_box.setStyleSheet("QFrame { background-color: #26243d; border-radius: 8px; border: 1px solid #332d4b; }")
        desc_layout = QVBoxLayout(desc_box)
        desc_layout.setContentsMargins(15, 15, 15, 15)
        
        desc_text = self.model_info.get("title", self.repo_id.split('/')[-1])
        # Use description if available, otherwise fallback to title
        desc_lbl = QLabel(desc_text)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #e0e0e0; font-size: 14px; line-height: 1.4;")
        desc_layout.addWidget(desc_lbl)
        main_layout.addWidget(desc_box)

        # Specs and Tags
        specs_layout = QHBoxLayout()
        specs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        specs_layout.setSpacing(10)
        
        tags = self.model_info.get("tags", [])
        params, arch, ctx, fmt, caps = parse_model_tags(self.repo_id, tags)
        
        # Inject capabilities from dict for local/custom models
        model_caps = self.model_info.get("capabilities", {})
        if isinstance(model_caps, dict):
            if model_caps.get("vision") and "👁 Vision" not in caps: caps.append("👁 Vision")
            if model_caps.get("thinking") and "🧠 Reasoning" not in caps: caps.append("🧠 Reasoning")
            if model_caps.get("tools") and "🔧 Tool Use" not in caps: caps.append("🔧 Tool Use")
            
        if not params or params == "?B":
            params_match = re.search(r'(\d+(?:\.\d+)?B)', desc_text)
            if params_match: params = params_match.group(1)

        def make_spec_badge(key, val):
            frm = QFrame()
            frm.setStyleSheet("QFrame { background: transparent; }")
            lyt = QHBoxLayout(frm)
            lyt.setContentsMargins(0,0,0,0)
            lyt.setSpacing(4)
            kl = QLabel(key)
            kl.setStyleSheet("color: #8b949e; font-size: 12px;")
            vl = QLabel(val)
            vl.setObjectName(key)
            vl.setStyleSheet("color: #c9d1d9; font-size: 12px; font-weight: bold; background-color: #2b2d31; padding: 2px 6px; border-radius: 4px; border: 1px solid #30363d;")
            lyt.addWidget(kl)
            lyt.addWidget(vl)
            return frm

        specs_layout.addWidget(make_spec_badge("Params", params))
        specs_layout.addWidget(make_spec_badge("Arch", arch if arch else "Unknown"))
        specs_layout.addWidget(make_spec_badge("Domain", "llm"))
        specs_layout.addWidget(make_spec_badge("Format", fmt))
        main_layout.addLayout(specs_layout)

        # Capabilities
        caps_layout = QHBoxLayout()
        caps_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        caps_layout.setSpacing(10)
        caps_layout.setContentsMargins(0, 10, 0, 15)
        
        caps_lbl = QLabel("Capabilities:")
        caps_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        caps_layout.addWidget(caps_lbl)
        
        for cap in caps:
            caps_layout.addWidget(self._make_badge(cap))
            
        main_layout.addLayout(caps_layout)

        # Download Options Box
        self.download_box = QFrame()
        self.download_box.setStyleSheet("QFrame { background-color: #1e1e1e; border: 1px solid #30363d; border-radius: 8px; }")
        dl_layout = QVBoxLayout(self.download_box)
        dl_layout.setContentsMargins(15, 15, 15, 15)
        
        dl_header = QLabel("📦 Download Options")
        dl_header.setStyleSheet("color: #c9d1d9; font-size: 13px; font-weight: bold;")
        dl_layout.addWidget(dl_header)
        
        dl_layout.addSpacing(10)
        
        # Files container
        self.file_card_container = QVBoxLayout()
        self.file_card_container.setSpacing(8)
        dl_layout.addLayout(self.file_card_container)
        
        main_layout.addWidget(self.download_box)

        # README Box
        self.readme_box = QFrame()
        self.readme_box.setStyleSheet("QFrame { background-color: #212121; border-radius: 8px; border: 1px solid #30363d; margin-top: 15px; }")
        rc_lyt = QVBoxLayout(self.readme_box)
        rc_lyt.setContentsMargins(20, 20, 20, 20)
        
        rm_hdr = QLabel("📄 README")
        rm_hdr.setStyleSheet("color: #c9d1d9; font-size: 13px; font-weight: bold; margin-bottom: 10px;")
        rc_lyt.addWidget(rm_hdr)
        
        self.readme_view = QTextBrowser()
        self.readme_view.setOpenExternalLinks(False)
        self.readme_view.setOpenLinks(False)
        self.readme_view.anchorClicked.connect(self._handle_anchor)
        self.readme_view.setMinimumHeight(500)
        self.readme_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.readme_view.setStyleSheet("QTextBrowser { background-color: transparent; border: none; }")
        rc_lyt.addWidget(self.readme_view)
        
        main_layout.addWidget(self.readme_box)
        
        main_layout.addStretch()
        self.scroll.setWidget(self.container)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.scroll)
        
        self.specs_card = self.container  # For _on_config_loaded fallback

    def _on_config_loaded(self, model_id, config_data):
        if model_id != self.repo_id or not config_data: return
        
        archs = config_data.get("architectures", [])
        if archs:
            for c in self.specs_card.findChildren(QLabel):
                if c.objectName() == "Arch":
                    c.setText(archs[0])

    def update_action_visibility(self):
        pass

    def _handle_anchor(self, url):
        if url.scheme() == "copy":
            import base64
            from PyQt6.QtGui import QGuiApplication
            try:
                code_text = base64.b64decode(url.toString().replace("copy:", "")).decode('utf-8')
                QGuiApplication.clipboard().setText(code_text)
            except:
                pass
        else:
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)

    def load_metadata(self):
        self._show_readme_loading()
        self.api_client.fetch_readme(self.repo_id)
        self.api_client.fetch_files(self.repo_id)
        self.api_client.fetch_model_info(self.repo_id)

    def _on_info_loaded(self, model_id, info):
        if model_id != self.repo_id or not info: return
        card_data = info.get("cardData", {})
        
        base_model = card_data.get("base_model", model_id)
        if isinstance(base_model, list) and len(base_model) > 0:
            base_model = base_model[0]
        self.api_client.fetch_config(base_model, emit_id=model_id)

    def _show_readme_loading(self):
        loading_html = '''
        <html><body style='font-family:sans-serif;padding:12px'>
        <p style='color:#555;font-size:13px;animation:pulse 1s infinite'>
        ⏳ Loading README...</p>
        </body></html>
        '''
        self.readme_view.setHtml(loading_html)

    def _render_readme(self, model_id: str, raw_md: str):
        if not raw_md.strip():
            self.readme_view.setHtml(
                "<p style='color:#666;font-size:13px;font-family:sans-serif;padding:12px'>"
                "No README available for this model.</p>")
            return

        raw_md = re.sub(r'^---.*?---\s*', '', raw_md, flags=re.DOTALL)

        def repl_img(m):
            alt, link = m.group(1), m.group(2)
            if not link.startswith("http") and not link.startswith("data:"):
                link = f"https://huggingface.co/{model_id}/resolve/main/{link}"
            return f"![{alt}]({link})"
        raw_md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl_img, raw_md)

        def repl_html_img(m):
            src = m.group(1)
            if not src.startswith("http") and not src.startswith("data:"):
                src = f"https://huggingface.co/{model_id}/resolve/main/{src}"
            return f'<img src="{src}"'
        raw_md = re.sub(r'<img[^>]+src=["\']([^"\']+)["\']', repl_html_img, raw_md)

        html_body = markdown.markdown(raw_md, extensions=["fenced_code", "tables", "nl2br", "toc"])

        import base64
        import html
        def add_copy_button(match):
            code_content = match.group(1)
            clean_code = code_content.strip()
            raw_code = html.unescape(re.sub(r'<[^>]+>', '', clean_code))
            encoded = base64.b64encode(raw_code.encode('utf-8')).decode('utf-8')
            return f'<div class="code-header"><a href="copy:{encoded}">📋 Copy Code</a></div><pre><code>{code_content}</code></pre>'
            
        html_body = re.sub(r'<pre><code[^>]*>(.*?)</code></pre>', add_copy_button, html_body, flags=re.DOTALL)

        full_html = f'''
        <!DOCTYPE html>
        <html><head><style>
        body {{ font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.75; color: #d0d0d0; padding: 4px 2px; margin: 0; }}
        h1 {{ font-size: 17px; font-weight: 500; color: #f0f0f0; border-bottom: 0.5px solid #333; padding-bottom: 6px; margin: 16px 0 10px; }}
        h2 {{ font-size: 14px; font-weight: 500; color: #e8e8e8; margin: 14px 0 8px; }}
        h3 {{ font-size: 13px; font-weight: 500; color: #e0e0e0; margin: 12px 0 6px; }}
        p   {{ margin: 6px 0; }}
        a   {{ color: #7F77DD; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ background: #2a2a2a; border: 0.5px solid #3a3a3a; border-radius: 4px; padding: 1px 5px; font-family: 'JetBrains Mono','Fira Code',monospace; font-size: 12px; color: #ce9178; }}
        pre {{ background: #1a1a1a; border: 0.5px solid #333; border-radius: 7px; padding: 12px 14px; overflow-x: auto; margin: 10px 0; }}
        pre code {{ background: transparent; border: none; padding: 0; color: #d4d4d4; font-size: 12px; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin: 10px 0; }}
        th {{ background: #252525; font-weight: 500; color: #e0e0e0; padding: 6px 10px; border: 0.5px solid #3a3a3a; text-align: left; }}
        td {{ padding: 5px 10px; border: 0.5px solid #2e2e2e; color: #c0c0c0; }}
        tr:nth-child(even) td {{ background: #1c1c1c; }}
        blockquote {{ border-left: 3px solid #7F77DD; margin: 8px 0; padding: 6px 12px; color: #888; background: #1e1e2e; border-radius: 0 6px 6px 0; }}
        ul, ol {{ padding-left: 20px; margin: 6px 0; }}
        li  {{ margin: 3px 0; }}
        img {{ max-width: 100%; border-radius: 6px; margin: 8px 0; }}
        hr  {{ border: none; border-top: 0.5px solid #333; margin: 14px 0; }}
        </style></head>
        <body>{html_body}</body></html>
        '''
        self.readme_view.setHtml(full_html)
        self.readme_view.setOpenExternalLinks(True)

    def on_files_loaded(self, model_id, files):
        if model_id != self.repo_id: return
        
        while self.file_card_container.count():
            item = self.file_card_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        gguf_files = [f for f in files if f.get("path", "").endswith(".gguf") or f.get("path", "").endswith(".safetensors")]
        if not gguf_files: return
        
        f = gguf_files[0] 
        filename = f["path"]
        size_gb = f.get("size", 0) / (1024**3)
        size_str = f"{size_gb:.1f} GB"
        
        # update size in specs card if it exists
        if hasattr(self, 'specs_card'):
            for c in self.specs_card.findChildren(QLabel):
                if c.objectName() == "FILE_SIZE":
                    c.setText(size_str)

        quant = next((t for t in self.model_info.get("tags", []) if t in ("Q4_K_M","Q8_0","IQ4_NL","Q5_K_M","Q2_K")), "GGUF")
        license_tag = next((t for t in self.model_info.get("tags", []) if t.startswith("license:")), "license:unknown").split(":")[1].capitalize()
        
        fc = QFrame()
        fc.setStyleSheet("QFrame { background-color: #212121; border-radius: 12px; }")
        fc_lyt = QVBoxLayout(fc)
        fc_lyt.setContentsMargins(20, 20, 20, 20)
        
        top_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setStyleSheet("background-color: #e6edf3; border-radius: 8px;")
        top_row.addWidget(icon_lbl)
        
        det_vbox = QVBoxLayout()
        det_vbox.setSpacing(4)
        fname_lbl = QLabel(filename)
        fname_lbl.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; border: none;")
        det_vbox.addWidget(fname_lbl)
        
        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        
        for tg in [size_str, quant, "GGUF", license_tag]:
            t_lbl = QLabel(tg)
            t_lbl.setStyleSheet("background-color: #30363d; color: #8b949e; border-radius: 4px; padding: 4px 8px; font-size: 12px; border: none;")
            tags_row.addWidget(t_lbl)
        tags_row.addStretch()
        det_vbox.addLayout(tags_row)
        top_row.addLayout(det_vbox)
        
        local_path = os.path.join(os.getcwd(), "models", self.repo_id.replace("/", "_"), filename)
        if os.path.exists(local_path):
            btn = QPushButton("✓ Downloaded")
            btn.setStyleSheet("background-color: #21262d; color: #3fb950; border: 1px solid #30363d; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 14px;")
            btn.setEnabled(False)
            top_row.addWidget(btn)
        else:
            btn = QPushButton("↓ Download")
            btn.setStyleSheet("background-color: #238636; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 14px;")
            btn.clicked.connect(lambda checked, fn=filename, b=btn: self.start_download(fn, b))
            top_row.addWidget(btn)
            
        fc_lyt.addLayout(top_row)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #30363d; margin-top: 15px; margin-bottom: 15px; border: none;")
        fc_lyt.addWidget(sep)
        
        params, arch, ctx, fmt, caps = parse_model_tags(self.repo_id, self.model_info.get("tags", []))
        if not params: params = "12B"
        
        try:
            import subprocess
            out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader"], stderr=subprocess.DEVNULL).decode("utf-8")
            sys_vram = int(out.split()[0]) / 1024.0
        except Exception:
            sys_vram = 8.0

        vram_est = size_gb * 1.2 
        
        pct = min(100, int((vram_est / sys_vram) * 100))
        color = ("#1D9E75" if pct < 70 else "#f0883e" if pct < 90 else "#E24B4A")
        status = ("Likely compatible" if pct < 70 else "Needs more VRAM" if pct < 90 else "Incompatible")

        vram_top = QHBoxLayout()
        v_l1 = QLabel("Estimated VRAM usage")
        v_l1.setStyleSheet("color: #8b949e; font-size: 12px; border: none;")
        v_r1 = QLabel(f"{vram_est:.1f} GB / {sys_vram:.0f} GB detected")
        v_r1.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; border: none;")
        vram_top.addWidget(v_l1)
        vram_top.addStretch()
        vram_top.addWidget(v_r1)
        fc_lyt.addLayout(vram_top)
        
        vbar = QProgressBar()
        vbar.setRange(0, 100)
        vbar.setValue(pct)
        vbar.setTextVisible(False)
        vbar.setFixedHeight(6)
        vbar.setStyleSheet(f'''
            QProgressBar {{ background: #30363d; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}
        ''')
        fc_lyt.addWidget(vbar)
        
        vram_bot = QHBoxLayout()
        v_l2 = QLabel(f"{pct}% of GPU VRAM")
        v_l2.setStyleSheet("color: #8b949e; font-size: 12px; border: none;")
        v_r2 = QLabel(status)
        v_r2.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
        vram_bot.addWidget(v_l2)
        vram_bot.addStretch()
        vram_bot.addWidget(v_r2)
        fc_lyt.addLayout(vram_bot)

        self.file_card_container.addWidget(fc)


    def start_download(self, filename, btn):
        btn.setEnabled(False)
        btn.setText("Downloading...")
        save_path = os.path.join(os.getcwd(), "models", self.repo_id.replace("/", "_"), filename)
        
        if self.downloader is not None and self.downloader.isRunning():
            self.downloader.quit()
            self.downloader.wait()
            
        self.downloader = ModelDownloaderThread(self.repo_id, filename, save_path)
        self.downloader.progress_updated.connect(lambda p, s, e: btn.setText(f"{p}% | {s}"))
        self.downloader.download_complete.connect(lambda path: self.on_download_complete(path, btn))
        self.downloader.error_occurred.connect(lambda err: btn.setText("Failed"))
        self.downloader.start()

    def on_fetch_error(self, err_msg):
        self.status_label.setText(f"Error: {err_msg}")
        self.status_label.setStyleSheet("color: #da3633;")
        self.status_label.show()

    def cleanup(self):
        if self.downloader is not None and self.downloader.isRunning():
            self.downloader.quit()
            self.downloader.wait()
            self.downloader = None

    def on_download_complete(self, path, btn):
        btn.setText("✓ Downloaded")
        btn.setStyleSheet("background-color: #21262d; color: #3fb950; border: 1px solid #30363d; padding: 4px 12px; border-radius: 4px;")
        ModelRegistry.register(model_id=self.repo_id, provider_id="ollama" if path.endswith(".gguf") else "huggingface", display_name=self.repo_id.split("/")[-1], modality="text", capabilities={"thinking": False, "vision": False, "tools": False}, path=path, format="GGUF" if path.endswith(".gguf") else "Safetensors")
        self.local_status = ModelRegistry.get(self.repo_id)
        self.update_action_visibility()

