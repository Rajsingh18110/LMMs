"""
Extensions Panel — sidebar list + click opens a VS Code-style detail tab
in the main editor area via editor_manager.open_custom_tab().
"""
import os
import requests

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar, QApplication,
    QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QUrl


# ─── Background threads ───────────────────────────────────────────────────────

class ExtensionSearchThread(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            url = (f"https://open-vsx.org/api/-/search"
                   f"?query={self.query}&size=20&sortBy=relevance")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            self.results_ready.emit(resp.json().get("extensions", []))
        except Exception as e:
            self.error_occurred.emit(str(e))


class ExtensionDetailThread(QThread):
    """Fetches full Open VSX detail JSON for one extension."""
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


class ReadmeThread(QThread):
    """Downloads the README for an extension."""
    ready = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=8)
            if resp.ok:
                self.ready.emit(resp.text)
        except Exception:
            self.ready.emit("")


# ─── Extension Detail Tab (opens in main editor area) ────────────────────────

class ExtensionDetailTab(QWebEngineView):
    """
    A QWebEngineView that renders a VS Code-style extension detail page.
    It starts with the search-result summary, then enriches itself with
    the full Open VSX detail JSON once fetched.
    """

    LOADING_HTML = """
    <html><body style="background:#1e1e1e;color:#ccc;font-family:sans-serif;
                        display:flex;align-items:center;justify-content:center;
                        height:100vh;margin:0;">
      <div style="text-align:center">
        <div style="font-size:32px;margin-bottom:12px">⏳</div>
        <p style="color:#888">Loading extension details…</p>
      </div>
    </body></html>
    """

    def __init__(self, ext: dict, parent=None):
        super().__init__(parent)
        self._ext = ext
        self._detail = {}
        self._readme_html = ""
        self.setHtml(self.LOADING_HTML)
        self.setProperty("is_custom", True)
        ns = ext.get("namespace", "")
        name = ext.get("name", "")
        identifier = f"ext:{ns}.{name}"
        self.setProperty("identifier", identifier)

        # Fetch detail + README in background
        self._detail_thread = ExtensionDetailThread(ns, name)
        self._detail_thread.detail_ready.connect(self._on_detail)
        self._detail_thread.error_occurred.connect(lambda _: self._render())
        self._detail_thread.start()

    # ── Data handlers ─────────────────────────────────────────────────────────

    def _on_detail(self, detail: dict):
        self._detail = detail
        # Kick off README fetch if available
        readme_url = detail.get("files", {}).get("readme", "")
        if readme_url:
            self._readme_thread = ReadmeThread(readme_url)
            self._readme_thread.ready.connect(self._on_readme)
            self._readme_thread.start()
        else:
            self._render()

    def _on_readme(self, raw: str):
        self._readme_html = self._md_to_html(raw)
        self._render()

    # ── Markdown → HTML (minimal) ─────────────────────────────────────────────

    @staticmethod
    def _md_to_html(md: str) -> str:
        import re
        # Headings
        md = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', md, flags=re.M)
        md = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', md, flags=re.M)
        md = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', md, flags=re.M)
        md = re.sub(r'^# (.+)$',    r'<h1>\1</h1>', md, flags=re.M)
        # Bold / italic
        md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)
        md = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', md)
        # Inline code
        md = re.sub(r'`([^`]+)`', r'<code>\1</code>', md)
        # Links  [text](url)
        md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                    r'<a href="\2" style="color:#4db2ff">\1</a>', md)
        # Images  ![alt](url)
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                    r'<img src="\2" alt="\1" style="max-width:100%;border-radius:4px">', md)
        # Paragraphs / newlines
        md = re.sub(r'\n{2,}', '</p><p>', md)
        md = md.replace('\n', '<br>')
        return f"<p>{md}</p>"

    # ── Render ─────────────────────────────────────────────────────────────────

    def _render(self):
        ext = {**self._ext, **self._detail}  # merge; detail wins on conflicts

        name        = ext.get("displayName") or ext.get("name", "")
        namespace   = ext.get("namespace", "")
        description = ext.get("description", "")
        version     = ext.get("version", "—")
        stars       = float(ext.get("averageRating", 0) or 0)
        downloads   = int(ext.get("downloadCount", 0) or 0)
        timestamp   = (ext.get("timestamp", "") or "")[:10]
        categories  = ext.get("categories", []) or []
        tags        = ext.get("tags", []) or []
        icon_url    = (ext.get("files", {}) or {}).get("icon", "")
        ext_id      = f"{namespace}.{ext.get('name', '')}"
        published   = ext.get("publishedDate", "")
        size        = ext.get("packageSizes", {}).get("download", 0)
        size_str    = f"{size/1024:.1f} KB" if size else "—"

        star_full  = "★" * round(stars)
        star_empty = "☆" * (5 - round(stars))

        # Category/tag pills
        all_tags  = list(dict.fromkeys(categories + tags))[:8]
        pills_html = " ".join(
            f'<span style="background:#2d3139;border-radius:3px;'
            f'padding:2px 8px;font-size:11px;color:#aab0b8">{t}</span>'
            for t in all_tags
        )

        # Icon or placeholder
        icon_tag = (
            f'<img src="{icon_url}" width="80" height="80" '
            f'style="border-radius:8px;object-fit:contain" onerror="this.style.display=\'none\'">'
            if icon_url else
            '<div style="width:80px;height:80px;background:#2d2d2d;border-radius:8px;'
            'display:flex;align-items:center;justify-content:center;font-size:36px">⬛</div>'
        )

        readme_section = (
            f'<div class="readme">{self._readme_html}</div>'
            if self._readme_html else
            '<p style="color:#666">No README available for this extension.</p>'
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #1e1e1e; color: #cccccc;
    font-family: -apple-system, 'Segoe UI', sans-serif;
    font-size: 13px; line-height: 1.6;
    padding: 0; overflow-x: hidden;
  }}

  /* ── Top hero ── */
  .hero {{
    background: #252526;
    padding: 24px 28px 18px;
    border-bottom: 1px solid #3d3d3d;
    display: flex; gap: 20px; align-items: flex-start;
  }}
  .hero .icon-wrap {{ flex-shrink: 0; }}
  .hero .info {{ flex: 1; }}
  .hero h1 {{ font-size: 22px; color: #e6edf3; margin-bottom: 2px; }}
  .hero .pub {{ color: #4db2ff; font-size: 12px; margin-bottom: 6px; cursor: pointer; }}
  .hero .meta {{
    color: #f0b429; font-size: 12px; margin-bottom: 6px;
  }}
  .hero .desc {{ color: #9aa0a6; font-size: 12px; margin-bottom: 12px; }}
  .hero .btns {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}

  /* ── Buttons ── */
  .btn-install {{
    background: #0e639c; color: white; border: none; border-radius: 3px;
    padding: 6px 16px; font-size: 12px; font-weight: 600; cursor: pointer;
  }}
  .btn-install:hover {{ background: #1177bb; }}
  .btn-disable {{
    background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px;
    padding: 6px 14px; font-size: 12px; cursor: pointer;
  }}
  .btn-disable:hover {{ background: #505050; }}
  .btn-prerelease {{
    background: #4d2600; color: #f0a500; border: 1px solid #704000; border-radius: 3px;
    padding: 6px 14px; font-size: 12px; cursor: pointer;
  }}

  /* ── Nav tabs ── */
  .nav {{
    background: #252526; border-bottom: 1px solid #3d3d3d;
    display: flex; padding: 0 28px;
  }}
  .nav a {{
    color: #8b949e; text-decoration: none; font-size: 12px; font-weight: 500;
    padding: 10px 14px; display: inline-block; border-bottom: 2px solid transparent;
  }}
  .nav a.active {{
    color: #e6edf3; border-bottom: 2px solid #4db2ff;
  }}
  .nav a:hover {{ color: #ccc; }}

  /* ── Two-column layout ── */
  .body-wrap {{
    display: flex; gap: 0;
  }}
  .main-col {{
    flex: 1; padding: 24px 28px; min-width: 0; overflow-wrap: break-word;
  }}
  .side-col {{
    width: 240px; flex-shrink: 0; padding: 24px 20px;
    border-left: 1px solid #3d3d3d;
  }}

  /* ── README ── */
  .readme h1, .readme h2, .readme h3, .readme h4 {{
    color: #e6edf3; margin: 18px 0 8px;
  }}
  .readme h1 {{ font-size: 20px; border-bottom: 1px solid #3d3d3d; padding-bottom: 6px; }}
  .readme h2 {{ font-size: 17px; }}
  .readme h3 {{ font-size: 15px; }}
  .readme p  {{ margin-bottom: 12px; color: #bcc4ce; }}
  .readme code {{
    background: #2d2d2d; border-radius: 3px; padding: 1px 5px;
    font-family: 'Fira Code', monospace; font-size: 12px; color: #e6edf3;
  }}
  .readme a {{ color: #4db2ff; }}
  .readme img {{ max-width: 100%; border-radius: 6px; margin: 8px 0; }}
  .readme ul, .readme ol {{ padding-left: 20px; margin-bottom: 12px; color: #bcc4ce; }}

  /* ── Sidebar sections ── */
  .side-section {{ margin-bottom: 22px; }}
  .side-section h3 {{
    font-size: 11px; font-weight: 700; color: #8b949e;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;
  }}
  .meta-row {{ display: flex; margin-bottom: 5px; font-size: 11px; }}
  .meta-row .key {{ color: #8b949e; width: 90px; flex-shrink: 0; }}
  .meta-row .val {{ color: #cccccc; word-break: break-all; }}
  .pills {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  .pill {{
    background: #2d3139; border-radius: 3px; padding: 2px 8px;
    font-size: 10px; color: #aab0b8;
  }}
  .resource-link {{
    display: block; color: #4db2ff; font-size: 11px;
    text-decoration: none; margin-bottom: 4px;
  }}
  .resource-link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>

<!-- ── Hero ── -->
<div class="hero">
  <div class="icon-wrap">{icon_tag}</div>
  <div class="info">
    <h1>{name}</h1>
    <div class="pub">{namespace}</div>
    <div class="meta">
      <span style="color:#f0b429">{star_full}{star_empty}</span>
      &nbsp;({round(stars,1)})&nbsp;&nbsp;
      <span style="color:#8b949e">⬇ {downloads:,}</span>
    </div>
    <div class="desc">{description}</div>
    <div class="btns">
      <button class="btn-install">Install</button>
      <button class="btn-disable">Disable</button>
      <button class="btn-prerelease">Switch to Pre-Release Version</button>
    </div>
  </div>
</div>

<!-- ── Nav ── -->
<div class="nav">
  <a href="#" class="active">DETAILS</a>
  <a href="#">FEATURES</a>
  <a href="#">CHANGELOG</a>
  <a href="#">DEPENDENCIES</a>
</div>

<!-- ── Body: main + sidebar ── -->
<div class="body-wrap">

  <!-- README -->
  <div class="main-col">
    {readme_section}
  </div>

  <!-- Sidebar -->
  <div class="side-col">

    <div class="side-section">
      <h3>Installation</h3>
      <div class="meta-row"><span class="key">Identifier</span><span class="val">{ext_id}</span></div>
      <div class="meta-row"><span class="key">Version</span><span class="val">{version}</span></div>
      <div class="meta-row"><span class="key">Last Updated</span><span class="val">{timestamp}</span></div>
      <div class="meta-row"><span class="key">Size</span><span class="val">{size_str}</span></div>
    </div>

    <div class="side-section">
      <h3>Marketplace</h3>
      <div class="meta-row"><span class="key">Published</span><span class="val">{published[:10] if published else '—'}</span></div>
      <div class="meta-row"><span class="key">Last Released</span><span class="val">{timestamp}</span></div>
    </div>

    {"<div class='side-section'><h3>Categories</h3><div class='pills'>" + pills_html + "</div></div>" if pills_html else ""}

    <div class="side-section">
      <h3>Resources</h3>
      <a class="resource-link" href="https://open-vsx.org/extension/{namespace}/{ext.get('name','')}">🌐 Marketplace</a>
      <a class="resource-link" href="#">📄 License</a>
      <a class="resource-link" href="#">📦 Repository</a>
    </div>

  </div>
</div>

</body>
</html>"""
        self.setHtml(html)


# ─── Extensions Panel (sidebar dock) ─────────────────────────────────────────

class ExtensionsPanel(QDockWidget):
    # Emitted when user clicks an extension; MainWindow connects this to
    # open the detail tab in editor_manager.
    open_detail_requested = pyqtSignal(object)   # payload: ext dict

    STYLE = """
        QDockWidget { background: #1e1e1e; }
        QWidget      { background: #1e1e1e; color: #cccccc; }
        QLineEdit {
            background: #3c3c3c; color: #cccccc; border: 1px solid #555;
            border-radius: 3px; padding: 5px 8px; font-size: 12px;
        }
        QListWidget  { background: #252526; border: none; outline: none; }
        QListWidget::item { border-bottom: 1px solid #2d2d2d; }
        QListWidget::item:hover    { background: #2a2d2e; }
        QListWidget::item:selected { background: #094771; border: none; }
        QProgressBar { background: #3c3c3c; border: none; height: 2px; }
        QProgressBar::chunk { background: #007acc; }
    """

    def __init__(self, parent=None):
        super().__init__("Extensions", parent)
        self.setObjectName("ExtensionsDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._search_thread = None
        self._ext_map: dict[int, dict] = {}
        self.init_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def init_ui(self):
        root = QWidget()
        root.setStyleSheet(self.STYLE)
        root_l = QVBoxLayout(root)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)

        # Search bar
        top = QWidget()
        top.setStyleSheet("background:#252526; border-bottom:1px solid #3d3d3d;")
        top_l = QVBoxLayout(top)
        top_l.setContentsMargins(8, 8, 8, 6)
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

        root_l.addWidget(top)

        # Results list
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        root_l.addWidget(self.list_widget, 1)

        self.setWidget(root)

        # Default search
        self.search_input.setText("python")
        self.do_search()

    # ── Search ────────────────────────────────────────────────────────────────

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

    # ── Results ───────────────────────────────────────────────────────────────

    def on_results(self, extensions: list):
        self.progress_bar.hide()
        self.list_widget.clear()
        self._ext_map.clear()

        for idx, ext in enumerate(extensions):
            self._ext_map[idx] = ext

            name        = ext.get("displayName") or ext.get("name", "")
            publisher   = ext.get("namespace", "")
            description = ext.get("description", "")
            version     = ext.get("version", "")
            downloads   = int(ext.get("downloadCount", 0) or 0)

            # Row widget
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_l = QVBoxLayout(row_w)
            row_l.setContentsMargins(10, 8, 10, 8)
            row_l.setSpacing(2)

            # Name + install btn
            hr = QHBoxLayout()
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setStyleSheet("color:#e6edf3;font-size:12px;background:transparent;")
            hr.addWidget(name_lbl, 1)

            dl_url  = (ext.get("files") or {}).get("download", "")
            ext_id  = f"{publisher}.{ext.get('name', '')}"
            btn = QPushButton("Install")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            btn.setStyleSheet("""
                QPushButton { background:#0e639c; color:white; border-radius:3px;
                              padding:2px 10px; font-size:11px; }
                QPushButton:hover { background:#1177bb; }
            """)
            btn.clicked.connect(
                lambda _, eid=ext_id, url=dl_url: self.install_extension(eid, url)
            )
            hr.addWidget(btn)
            row_l.addLayout(hr)

            # Description
            desc_lbl = QLabel(description[:80] + ("…" if len(description) > 80 else ""))
            desc_lbl.setStyleSheet("color:#8b949e;font-size:11px;background:transparent;")
            desc_lbl.setWordWrap(True)
            row_l.addWidget(desc_lbl)

            # Publisher · version · downloads
            pub_lbl = QLabel(f"{publisher}  ·  v{version}  ·  ⬇ {downloads:,}")
            pub_lbl.setStyleSheet("color:#555;font-size:10px;background:transparent;")
            row_l.addWidget(pub_lbl)

            li = QListWidgetItem(self.list_widget)
            li.setSizeHint(row_w.sizeHint())
            self.list_widget.addItem(li)
            self.list_widget.setItemWidget(li, row_w)

    # ── Click → open detail tab ───────────────────────────────────────────────

    def _on_item_clicked(self, item):
        row = self.list_widget.row(item)
        ext = self._ext_map.get(row)
        if ext:
            self.open_detail_requested.emit(ext)

    # ── Error / Install ───────────────────────────────────────────────────────

    def on_error(self, error: str):
        self.progress_bar.hide()
        QMessageBox.warning(self, "Search Error", f"Failed to fetch extensions:\n{error}")

    def install_extension(self, ext_id: str, download_url: str):
        QMessageBox.information(
            self, "Install Extension",
            f"Installing: {ext_id}\n\nThis will be handled by the Monaco Extension Host."
        )
        print(f"[Extensions] Install: {ext_id} → {download_url}")
