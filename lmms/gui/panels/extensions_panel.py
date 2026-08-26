import os
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar, QStackedWidget,
    QScrollArea, QFrame, QSizePolicy, QApplication, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor, QPalette
import base64


# ─── Thread: search Open VSX ─────────────────────────────────────────────────

class ExtensionSearchThread(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            url = f"https://open-vsx.org/api/-/search?query={self.query}&size=20&sortBy=relevance"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.results_ready.emit(data.get("extensions", []))
        except Exception as e:
            self.error_occurred.emit(str(e))


# ─── Thread: fetch extension details ─────────────────────────────────────────

class ExtensionDetailThread(QThread):
    detail_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, namespace, name):
        super().__init__()
        self.namespace = namespace
        self.name = name

    def run(self):
        try:
            url = f"https://open-vsx.org/api/{self.namespace}/{self.name}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            self.detail_ready.emit(resp.json())
        except Exception as e:
            self.error_occurred.emit(str(e))


# ─── Thread: fetch extension icon ────────────────────────────────────────────

class IconThread(QThread):
    icon_ready = pyqtSignal(bytes)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=8)
            if resp.status_code == 200:
                self.icon_ready.emit(resp.content)
        except Exception:
            pass


# ─── Extension Detail View ────────────────────────────────────────────────────

class ExtensionDetailView(QScrollArea):
    install_requested = pyqtSignal(str, str)  # ext_id, download_url

    STYLE = """
        QScrollArea { background: #1e1e1e; border: none; }
        QWidget#detailBg { background: #1e1e1e; }
        QLabel { color: #cccccc; background: transparent; }
        QFrame#divider { color: #3d3d3d; }
        QPushButton#installBtn {
            background-color: #0e639c; color: white; border-radius: 3px;
            padding: 5px 14px; font-weight: bold; font-size: 12px;
        }
        QPushButton#installBtn:hover { background-color: #1177bb; }
        QPushButton#disableBtn {
            background-color: #3c3c3c; color: #cccccc; border-radius: 3px;
            padding: 5px 14px; font-size: 12px; border: 1px solid #555;
        }
        QPushButton#disableBtn:hover { background-color: #505050; }
        QLabel#tagLabel {
            background: #2d3139; color: #adb5c0; border-radius: 3px;
            padding: 2px 6px; font-size: 10px;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(self.STYLE)

        self._ext_data = None
        self._icon_thread = None
        self._detail_thread = None

        bg = QWidget()
        bg.setObjectName("detailBg")
        self._layout = QVBoxLayout(bg)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(0)
        self.setWidget(bg)

        self._show_placeholder()

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        self._clear()
        lbl = QLabel("Select an extension to view details")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #555; font-size: 13px; margin-top: 60px;")
        self._layout.addWidget(lbl)
        self._layout.addStretch()

    def load_extension(self, ext: dict):
        """Load summary data immediately, then fetch full detail in background."""
        self._ext_data = ext
        self._build_summary(ext)

        ns = ext.get("namespace", "")
        name = ext.get("name", "")
        if ns and name:
            self._detail_thread = ExtensionDetailThread(ns, name)
            self._detail_thread.detail_ready.connect(self._build_full)
            self._detail_thread.error_occurred.connect(lambda e: None)
            self._detail_thread.start()

    def _build_summary(self, ext: dict):
        self._clear()
        v_layout = self._layout

        # ── Header row ───────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(14)

        # Icon placeholder
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(64, 64)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(
            "background:#2d2d2d; border-radius:6px; color:#555; font-size:24px;"
        )
        self._icon_lbl.setText("⬛")
        header.addWidget(self._icon_lbl)

        # Fetch icon
        icon_url = ext.get("files", {}).get("icon", "")
        if icon_url:
            self._icon_thread = IconThread(icon_url)
            self._icon_thread.icon_ready.connect(self._set_icon)
            self._icon_thread.start()

        # Title block
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        name_lbl = QLabel(ext.get("displayName") or ext.get("name", ""))
        name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #e6edf3;")
        title_col.addWidget(name_lbl)

        pub_lbl = QLabel(ext.get("namespace", ""))
        pub_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        title_col.addWidget(pub_lbl)

        # Stars + downloads row
        stars = ext.get("averageRating", 0)
        downloads = ext.get("downloadCount", 0)
        star_str = "★" * round(stars) + "☆" * (5 - round(stars))
        meta_lbl = QLabel(f"{star_str}  ({round(stars, 1)})  ·  ⬇ {downloads:,}")
        meta_lbl.setStyleSheet("color: #f0b429; font-size: 11px;")
        title_col.addWidget(meta_lbl)

        desc_short = ext.get("description", "")
        if desc_short:
            dl = QLabel(desc_short)
            dl.setStyleSheet("color: #aab0b8; font-size: 12px; margin-top: 4px;")
            dl.setWordWrap(True)
            title_col.addWidget(dl)

        header.addLayout(title_col, 1)
        v_layout.addLayout(header)
        self._add_divider(12)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        download_url = ext.get("files", {}).get("download", "")
        ext_id = f"{ext.get('namespace', '')}.{ext.get('name', '')}"

        self._install_btn = QPushButton("Install")
        self._install_btn.setObjectName("installBtn")
        self._install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._install_btn.clicked.connect(
            lambda: self.install_requested.emit(ext_id, download_url)
        )
        btn_row.addWidget(self._install_btn)

        self._disable_btn = QPushButton("Disable")
        self._disable_btn.setObjectName("disableBtn")
        self._disable_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row.addWidget(self._disable_btn)

        btn_row.addStretch()
        v_layout.addLayout(btn_row)
        self._add_divider(12)

        # ── Metadata sidebar ──────────────────────────────────────────────────
        info_grid = QWidget()
        grid = QVBoxLayout(info_grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        version = ext.get("version", "—")
        timestamp = ext.get("timestamp", "")
        date_str = timestamp[:10] if timestamp else "—"

        self._add_meta_row(grid, "Identifier", ext_id)
        self._add_meta_row(grid, "Version", version)
        self._add_meta_row(grid, "Last Updated", date_str)
        v_layout.addWidget(info_grid)
        self._add_divider(12)

        # ── Description (placeholder until full detail loads) ─────────────────
        self._desc_lbl = QLabel("Loading full description…")
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet("color: #aab0b8; font-size: 12px; line-height: 160%;")
        self._desc_lbl.setTextFormat(Qt.TextFormat.RichText)
        v_layout.addWidget(self._desc_lbl)

        v_layout.addStretch()

    def _build_full(self, detail: dict):
        """Supplement with full detail from the Open VSX API response."""
        # Update description with README / long description
        readme = detail.get("files", {}).get("readme", "")
        if readme:
            # Fetch README
            t = _ReadmeThread(readme)
            t.ready.connect(self._set_readme)
            t.start()
            self._readme_thread = t

        # Update categories as tags
        cats = detail.get("categories", []) or detail.get("tags", [])
        if cats and hasattr(self, '_tag_container'):
            return
        if cats:
            tag_row = QHBoxLayout()
            tag_row.setSpacing(4)
            for cat in cats[:6]:
                t = QLabel(cat)
                t.setObjectName("tagLabel")
                tag_row.addWidget(t)
            tag_row.addStretch()
            # Insert before stretch (last item)
            self._layout.insertLayout(self._layout.count() - 1, tag_row)

    def _set_readme(self, html: str):
        # Strip markdown slightly for display
        self._desc_lbl.setText(html[:3000])  # cap length

    def _set_icon(self, data: bytes):
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            px = px.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            self._icon_lbl.setPixmap(px)
            self._icon_lbl.setText("")

    def _add_divider(self, margin=8):
        f = QFrame()
        f.setObjectName("divider")
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet(f"color:#3d3d3d; margin-top:{margin}px; margin-bottom:{margin}px;")
        self._layout.addWidget(f)

    def _add_meta_row(self, parent_layout, key, value):
        row = QHBoxLayout()
        k = QLabel(key)
        k.setStyleSheet("color:#8b949e; font-size:11px;")
        k.setFixedWidth(100)
        v = QLabel(value)
        v.setStyleSheet("color:#cccccc; font-size:11px;")
        v.setWordWrap(True)
        row.addWidget(k)
        row.addWidget(v, 1)
        parent_layout.addLayout(row)


class _ReadmeThread(QThread):
    ready = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=8)
            if resp.status_code == 200:
                text = resp.text
                # Convert minimal Markdown to HTML for display
                import re
                text = re.sub(r'^# (.+)$', r'<b style="font-size:16px">\1</b><br>', text, flags=re.MULTILINE)
                text = re.sub(r'^## (.+)$', r'<b style="font-size:14px">\1</b><br>', text, flags=re.MULTILINE)
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'`(.+?)`', r'<code style="background:#2d2d2d;padding:1px 4px">\1</code>', text)
                text = text.replace('\n', '<br>')
                self.ready.emit(text)
        except Exception:
            self.ready.emit("Could not load README.")


# ─── Main Extensions Panel ─────────────────────────────────────────────────────

class ExtensionsPanel(QDockWidget):
    STYLE = """
        QDockWidget { background: #1e1e1e; }
        QWidget { background: #1e1e1e; color: #cccccc; }
        QLineEdit {
            background: #3c3c3c; color: #cccccc; border: 1px solid #555;
            border-radius: 3px; padding: 5px 8px; font-size: 12px;
        }
        QListWidget { background: #252526; border: none; outline: none; }
        QListWidget::item { border-bottom: 1px solid #2d2d2d; }
        QListWidget::item:hover { background: #2a2d2e; }
        QListWidget::item:selected { background: #094771; border: none; }
        QProgressBar {
            background: #3c3c3c; border: none; height: 2px;
        }
        QProgressBar::chunk { background: #007acc; }
        QSplitter::handle { background: #3d3d3d; width: 1px; }
    """

    def __init__(self, parent=None):
        super().__init__("Extensions", parent)
        self.setObjectName("ExtensionsDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._search_thread = None
        self._ext_map = {}   # list index -> ext dict
        self.init_ui()

    def init_ui(self):
        root = QWidget()
        root.setStyleSheet(self.STYLE)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top search bar ────────────────────────────────────────────────────
        top = QWidget()
        top.setStyleSheet("background:#252526; border-bottom: 1px solid #3d3d3d;")
        top_l = QVBoxLayout(top)
        top_l.setContentsMargins(8, 8, 8, 8)
        top_l.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Extensions in Marketplace")
        self.search_input.returnPressed.connect(self.do_search)
        top_l.addWidget(self.search_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.hide()
        top_l.addWidget(self.progress_bar)

        root_layout.addWidget(top)

        # ── Splitter: list (left) + detail (right) ───────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        # List
        list_container = QWidget()
        list_container.setStyleSheet("background:#252526;")
        list_l = QVBoxLayout(list_container)
        list_l.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        list_l.addWidget(self.list_widget)

        # Detail
        self.detail_view = ExtensionDetailView()
        self.detail_view.install_requested.connect(self.install_extension)

        self.splitter.addWidget(list_container)
        self.splitter.addWidget(self.detail_view)
        self.splitter.setSizes([280, 500])

        root_layout.addWidget(self.splitter, 1)
        self.setWidget(root)

        # Default search
        self.search_input.setText("python")
        self.do_search()

    # ─── Search ───────────────────────────────────────────────────────────────

    def do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.list_widget.clear()
        self._ext_map.clear()
        self.progress_bar.show()

        self._search_thread = ExtensionSearchThread(query)
        self._search_thread.results_ready.connect(self.on_results)
        self._search_thread.error_occurred.connect(self.on_error)
        self._search_thread.start()

    # ─── Results ──────────────────────────────────────────────────────────────

    def on_results(self, extensions):
        self.progress_bar.hide()
        self.list_widget.clear()
        self._ext_map.clear()

        for idx, ext in enumerate(extensions):
            self._ext_map[idx] = ext

            name = ext.get("displayName") or ext.get("name", "")
            publisher = ext.get("namespace", "")
            description = ext.get("description", "")
            version = ext.get("version", "")
            downloads = ext.get("downloadCount", 0)

            # Item widget
            item_w = QWidget()
            item_w.setStyleSheet("background: transparent;")
            item_l = QVBoxLayout(item_w)
            item_l.setContentsMargins(10, 8, 10, 8)
            item_l.setSpacing(2)

            # Header: name + Install button
            row = QHBoxLayout()
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setStyleSheet("color: #e6edf3; font-size: 12px; background: transparent;")
            row.addWidget(name_lbl, 1)

            btn = QPushButton("Install")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            btn.setStyleSheet("""
                QPushButton { background:#0e639c; color:white; border-radius:3px;
                              padding:2px 10px; font-size:11px; }
                QPushButton:hover { background:#1177bb; }
            """)
            dl_url = ext.get("files", {}).get("download", "")
            ext_id = f"{publisher}.{ext.get('name', '')}"
            btn.clicked.connect(
                lambda _, eid=ext_id, url=dl_url: self.install_extension(eid, url)
            )
            row.addWidget(btn)
            item_l.addLayout(row)

            # Description
            desc_lbl = QLabel(description[:80] + ("…" if len(description) > 80 else ""))
            desc_lbl.setStyleSheet("color:#8b949e; font-size:11px; background:transparent;")
            desc_lbl.setWordWrap(True)
            item_l.addWidget(desc_lbl)

            # Publisher + version
            pub_lbl = QLabel(f"{publisher}  ·  v{version}  ·  ⬇ {downloads:,}")
            pub_lbl.setStyleSheet("color:#555; font-size:10px; background:transparent;")
            item_l.addWidget(pub_lbl)

            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_w.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_w)

    # ─── Click handler ────────────────────────────────────────────────────────

    def _on_item_clicked(self, item):
        row = self.list_widget.row(item)
        self._load_detail(row)

    def _on_row_changed(self, row):
        if row >= 0:
            self._load_detail(row)

    def _load_detail(self, row):
        ext = self._ext_map.get(row)
        if ext:
            self.detail_view.load_extension(ext)

    # ─── Error / Install ──────────────────────────────────────────────────────

    def on_error(self, error):
        self.progress_bar.hide()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Search Error", f"Failed to fetch extensions:\n{error}")

    def install_extension(self, extension_id, download_url):
        from PyQt6.QtWidgets import QMessageBox
        if not download_url:
            QMessageBox.information(self, "Install", f"No download URL for {extension_id}")
            return
        QMessageBox.information(
            self, "Install Extension",
            f"Installing: {extension_id}\n\nThis will be handled by the Monaco Extension Host."
        )
        print(f"[Extensions] Install requested: {extension_id} → {download_url}")
