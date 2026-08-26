"""
Extensions Panel — VS Code-accurate sidebar + full detail tab.

Sidebar list: icon · name · description · publisher · downloads · Install btn
Detail tab:   QWebEngineView rendering a full VS Code-style extension page
"""
import os
import requests

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar, QSizePolicy,
    QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt6.QtGui import QPixmap, QFont, QColor


# ══════════════════════════════════════════════════════════════════════════════
# Background threads
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionSearchThread(QThread):
    results_ready  = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            url = (f"https://open-vsx.org/api/-/search"
                   f"?query={self.query}&size=25&sortBy=relevance")
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            self.results_ready.emit(r.json().get("extensions", []))
        except Exception as e:
            self.error_occurred.emit(str(e))


class IconThread(QThread):
    """Downloads one icon; payload = (row_index, bytes)."""
    icon_ready = pyqtSignal(int, bytes)

    def __init__(self, row: int, url: str):
        super().__init__()
        self.row = row
        self.url = url

    def run(self):
        try:
            r = requests.get(self.url, timeout=6)
            if r.ok:
                self.icon_ready.emit(self.row, r.content)
        except Exception:
            pass


class ExtensionDetailThread(QThread):
    detail_ready   = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, namespace, name):
        super().__init__()
        self.namespace = namespace
        self.name = name

    def run(self):
        try:
            r = requests.get(
                f"https://open-vsx.org/api/{self.namespace}/{self.name}",
                timeout=10
            )
            r.raise_for_status()
            self.detail_ready.emit(r.json())
        except Exception as e:
            self.error_occurred.emit(str(e))


class ReadmeThread(QThread):
    ready = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            r = requests.get(self.url, timeout=10)
            self.ready.emit(r.text if r.ok else "")
        except Exception:
            self.ready.emit("")


# ══════════════════════════════════════════════════════════════════════════════
# Extension card widget (one row in the sidebar list)
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionCard(QWidget):
    """
    VS Code-style extension list card:
    ┌────┬──────────────────────────────┬──────┐
    │icon│ Name (bold)         ⬇ 56.4M  │Instal│
    │    │ Description truncated…       │      │
    │    │ publisher  v1.0.0            │      │
    └────┴──────────────────────────────┴──────┘
    """
    ICON_SIZE = 40

    def __init__(self, ext: dict, row: int, parent=None):
        super().__init__(parent)
        self._ext = ext
        self.row  = row
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()

    def _build(self):
        ext = self._ext
        name        = ext.get("displayName") or ext.get("name", "")
        publisher   = ext.get("namespace", "")
        description = ext.get("description", "")
        version     = ext.get("version", "")
        downloads   = int(ext.get("downloadCount", 0) or 0)
        dl_str      = self._fmt_dl(downloads)
        icon_url    = (ext.get("files") or {}).get("icon", "")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 8, 8, 8)
        outer.setSpacing(10)

        # ── Icon ──────────────────────────────────────────────────────────────
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(
            "background:#2d2d2d; border-radius:4px; color:#555; font-size:18px;"
        )
        self.icon_lbl.setText("⬜")
        outer.addWidget(self.icon_lbl)

        # ── Text block ────────────────────────────────────────────────────────
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        # Row 1: name + downloads
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        name_lbl = QLabel(name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(9)
        name_lbl.setFont(name_font)
        name_lbl.setStyleSheet("color:#e6edf3; background:transparent;")
        row1.addWidget(name_lbl, 1)

        dl_lbl = QLabel(f"⬇ {dl_str}")
        dl_lbl.setStyleSheet("color:#8b949e; font-size:10px; background:transparent;")
        dl_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(dl_lbl)
        text_col.addLayout(row1)

        # Row 2: description
        short_desc = description[:72] + ("…" if len(description) > 72 else "")
        desc_lbl = QLabel(short_desc)
        desc_lbl.setStyleSheet("color:#9e9e9e; font-size:11px; background:transparent;")
        desc_lbl.setWordWrap(False)
        text_col.addWidget(desc_lbl)

        # Row 3: publisher · version
        pub_lbl = QLabel(f"{publisher}  v{version}")
        pub_lbl.setStyleSheet("color:#6e7681; font-size:10px; background:transparent;")
        text_col.addWidget(pub_lbl)

        outer.addLayout(text_col, 1)

        # ── Install button ─────────────────────────────────────────────────────
        self.btn_install = QPushButton("Install")
        self.btn_install.setFixedSize(60, 22)
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setStyleSheet("""
            QPushButton {
                background: #0e639c; color: white; border: none;
                border-radius: 2px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #1177bb; }
            QPushButton:pressed { background: #0a4f7e; }
        """)
        outer.addWidget(self.btn_install, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_icon(self, data: bytes):
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            px = px.scaled(
                self.ICON_SIZE, self.ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.icon_lbl.setPixmap(px)
            self.icon_lbl.setText("")

    @staticmethod
    def _fmt_dl(n: int) -> str:
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n)


# ══════════════════════════════════════════════════════════════════════════════
# Extension Detail Tab  (QWebEngineView opened in main editor)
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionDetailTab(QWebEngineView):
    """Full VS Code-style extension detail page rendered in a WebEngine tab."""

    def __init__(self, ext: dict, parent=None):
        super().__init__(parent)
        self._ext   = ext
        self._detail = {}
        self._readme = ""
        self.setProperty("is_custom", True)
        ns   = ext.get("namespace", "")
        name = ext.get("name", "")
        self.setProperty("identifier", f"ext:{ns}.{name}")
        # Show skeleton immediately
        self.setHtml(self._skeleton_html())
        # Fetch detail
        self._dt = ExtensionDetailThread(ns, name)
        self._dt.detail_ready.connect(self._on_detail)
        self._dt.error_occurred.connect(lambda _: self._render())
        self._dt.start()

    # ── data ──────────────────────────────────────────────────────────────────

    def _on_detail(self, detail: dict):
        self._detail = detail
        readme_url = (detail.get("files") or {}).get("readme", "")
        if readme_url:
            self._rt = ReadmeThread(readme_url)
            self._rt.ready.connect(self._on_readme)
            self._rt.start()
        else:
            self._render()

    def _on_readme(self, text: str):
        self._readme = text
        self._render()

    # ── markdown → html ───────────────────────────────────────────────────────

    @staticmethod
    def _md(md: str) -> str:
        import re
        # fenced code blocks
        md = re.sub(r'```[a-z]*\n?(.*?)```', lambda m:
            f'<pre><code>{m.group(1).strip()}</code></pre>', md, flags=re.S)
        # headings
        for i in range(4, 0, -1):
            md = re.sub(r'^#{%d} (.+)$' % i, r'<h%d>\1</h%d>' % (i, i), md, flags=re.M)
        # bold / italic
        md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)
        md = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         md)
        # inline code
        md = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', md)
        # images before links (order matters)
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                    r'<img src="\2" alt="\1" style="max-width:100%;border-radius:4px;margin:6px 0">', md)
        # links
        md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                    r'<a href="\2">\1</a>', md)
        # horizontal rule
        md = re.sub(r'^---+$', r'<hr>', md, flags=re.M)
        # unordered lists
        md = re.sub(r'^[ \t]*[-*] (.+)$', r'<li>\1</li>', md, flags=re.M)
        md = re.sub(r'(<li>.*?</li>)+', lambda m: f'<ul>{m.group(0)}</ul>', md, flags=re.S)
        # paragraphs
        paragraphs = re.split(r'\n{2,}', md)
        out = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith(('<h', '<ul', '<pre', '<hr', '<img')):
                out.append(p)
            else:
                out.append(f'<p>{p.replace(chr(10), " ")}</p>')
        return '\n'.join(out)

    # ── skeleton while loading ────────────────────────────────────────────────

    def _skeleton_html(self) -> str:
        ext  = self._ext
        name = ext.get("displayName") or ext.get("name", "")
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
          body{{background:#1e1e1e;color:#ccc;font-family:'Segoe UI',sans-serif;margin:0;padding:28px}}
          .pulse{{animation:pulse 1.4s ease-in-out infinite}}
          @keyframes pulse{{0%,100%{{opacity:.6}}50%{{opacity:1}}}}
          .bar{{background:#2d2d2d;border-radius:3px;height:14px;margin:6px 0}}
        </style></head><body>
        <h2 style="color:#e6edf3">{name}</h2>
        <div class="bar pulse" style="width:60%"></div>
        <div class="bar pulse" style="width:80%"></div>
        <div class="bar pulse" style="width:45%"></div>
        <p style="color:#555;margin-top:24px">Loading extension details…</p>
        </body></html>"""

    # ── full render ───────────────────────────────────────────────────────────

    def _render(self):
        ext = {**self._ext, **self._detail}

        name        = ext.get("displayName") or ext.get("name", "")
        namespace   = ext.get("namespace", "")
        ext_name    = ext.get("name", "")
        description = ext.get("description", "")
        version     = ext.get("version", "—")
        stars       = float(ext.get("averageRating") or 0)
        review_cnt  = int(ext.get("reviewCount") or 0)
        downloads   = int(ext.get("downloadCount") or 0)
        timestamp   = (ext.get("timestamp") or "")[:10]
        published   = (ext.get("publishedDate") or "")[:10]
        categories  = list(ext.get("categories") or [])
        tags        = list(ext.get("tags") or [])
        icon_url    = (ext.get("files") or {}).get("icon", "")
        ext_id      = f"{namespace}.{ext_name}"
        size_bytes  = (ext.get("packageSizes") or {}).get("download", 0)
        size_str    = f"{size_bytes/1_000_000:.2f}MB" if size_bytes else "—"

        # stars
        full  = round(stars)
        s_str = "★" * full + "☆" * (5 - full)

        # downloads formatted
        def fmt(n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000:     return f"{n/1_000:.0f}K"
            return str(n)

        # icon
        icon_html = (
            f'<img id="extIcon" src="{icon_url}" width="120" height="120"'
            f' style="border-radius:8px;object-fit:contain"'
            f' onerror="this.style.display=\'none\';document.getElementById(\'iconFallback\').style.display=\'flex\'">'
            f'<div id="iconFallback" style="display:none;width:120px;height:120px;'
            f'background:#2d2d2d;border-radius:8px;align-items:center;'
            f'justify-content:center;font-size:48px">⬛</div>'
            if icon_url else
            '<div style="width:120px;height:120px;background:#2d2d2d;border-radius:8px;'
            'display:flex;align-items:center;justify-content:center;font-size:48px">⬛</div>'
        )

        # pills
        all_tags = list(dict.fromkeys(categories + tags))[:8]
        pills = "".join(
            f'<span style="background:transparent;border:1px solid #555;'
            f'border-radius:2px;padding:1px 6px;font-size:11px;color:#aab0b8;'
            f'margin:2px 2px 0 0;display:inline-block">{t}</span>'
            for t in all_tags
        )

        readme_html = self._md(self._readme) if self._readme else \
            '<p style="color:#666">No README available for this extension.</p>'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
:root {{
  --bg:       #1e1e1e;
  --bg2:      #252526;
  --border:   #3c3c3c;
  --text:     #cccccc;
  --dim:      #8b949e;
  --accent:   #4db2ff;
  --yellow:   #cca700;
  --green:    #0e639c;
  --green-h:  #1177bb;
}}
* {{ box-sizing: border-box; margin:0; padding:0; }}
html, body {{
  background: var(--bg); color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 13px; line-height: 1.5;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── Hero ── */
.hero {{
  background: var(--bg2);
  padding: 20px 24px 16px;
  display: flex; gap: 18px; align-items: flex-start;
  border-bottom: 1px solid var(--border);
}}
.hero-icon {{ flex-shrink: 0; line-height:0; }}
.hero-body {{ flex: 1; min-width: 0; }}
.hero-name  {{ font-size:20px; font-weight:700; color:#e6edf3; line-height:1.2; margin-bottom:2px; }}
.hero-pub   {{ font-size:12px; color:var(--accent); margin-bottom:5px; cursor:pointer; }}
.hero-meta  {{ font-size:12px; color:var(--dim); margin-bottom:6px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
.hero-stars {{ color:var(--yellow); letter-spacing:1px; }}
.hero-desc  {{ font-size:13px; color:#9e9e9e; margin-bottom:14px; }}

/* ── Action buttons ── */
.actions {{ display:flex; gap:6px; align-items:center; flex-wrap:wrap; }}
.btn {{
  border:none; border-radius:2px; padding:5px 14px;
  font-size:12px; font-weight:600; cursor:pointer; line-height:1.4;
}}
.btn-primary  {{ background:var(--green); color:#fff; }}
.btn-primary:hover  {{ background:var(--green-h); }}
.btn-secondary {{ background:#3c3c3c; color:var(--text); border:1px solid #555; font-weight:400; }}
.btn-secondary:hover {{ background:#505050; }}
.btn-prerelease {{ background:#4b3800; color:#e8a12d; border:1px solid #6b5100; font-weight:400; }}
.btn-prerelease:hover {{ background:#5a4500; }}
.autoupdate {{ display:flex; align-items:center; gap:4px; font-size:12px; color:var(--dim); cursor:pointer; }}
.autoupdate input {{ accent-color: var(--accent); cursor:pointer; }}

/* ── Nav tabs ── */
.nav {{
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  display: flex; padding: 0 24px; overflow-x:auto;
}}
.nav-tab {{
  color: var(--dim); font-size: 11px; font-weight: 500;
  padding: 10px 16px; cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid transparent; text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.nav-tab.active {{ color: #e6edf3; border-bottom-color: var(--accent); }}
.nav-tab:hover:not(.active) {{ color: var(--text); }}

/* ── Page layout ── */
.page {{ display:flex; min-height:100%; }}
.content {{ flex:1; padding:24px; min-width:0; overflow-x:hidden; }}
.sidebar {{
  width:220px; flex-shrink:0; padding:20px 16px;
  border-left: 1px solid var(--border); font-size:12px;
}}

/* ── README ── */
.content h1 {{ font-size:18px; color:#e6edf3; margin:20px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--border); }}
.content h2 {{ font-size:15px; color:#e6edf3; margin:18px 0 8px; }}
.content h3 {{ font-size:13px; color:#e6edf3; margin:14px 0 6px; }}
.content h4 {{ font-size:12px; color:#e6edf3; margin:12px 0 4px; }}
.content p  {{ color:#bcc4ce; margin-bottom:10px; word-break:break-word; }}
.content ul, .content ol {{ padding-left:20px; color:#bcc4ce; margin-bottom:10px; }}
.content li {{ margin-bottom:3px; }}
.content code {{
  background:#2d2d2d; border-radius:3px; padding:1px 5px;
  font-family:'Fira Code','Cascadia Code',monospace; font-size:11.5px; color:#e6edf3;
}}
.content pre {{
  background:#2d2d2d; border-radius:4px; padding:12px 14px;
  margin:10px 0; overflow-x:auto; font-size:11.5px; line-height:1.6;
  font-family:'Fira Code','Cascadia Code',monospace; color:#e6edf3;
}}
.content pre code {{ background:none; padding:0; }}
.content a {{ color:var(--accent); }}
.content img {{ max-width:100%; border-radius:4px; margin:8px 0; }}
.content hr {{ border:none; border-top:1px solid var(--border); margin:16px 0; }}

/* ── Sidebar ── */
.sidebar-section {{ margin-bottom:20px; }}
.sidebar-section h3 {{
  font-size:10px; font-weight:700; color:var(--dim);
  text-transform:uppercase; letter-spacing:0.08em;
  margin-bottom:8px;
}}
.meta-row {{ display:flex; gap:8px; margin-bottom:5px; }}
.meta-key {{ color:var(--dim); width:88px; flex-shrink:0; }}
.meta-val {{ color:var(--text); flex:1; word-break:break-all; }}
.meta-val a {{ color:var(--accent); }}
.resource {{ display:flex; align-items:center; gap:6px; color:var(--accent); margin-bottom:5px; text-decoration:none; font-size:12px; }}
.resource:hover {{ text-decoration:underline; }}
</style>
</head>
<body>

<!-- ══ Hero ══ -->
<div class="hero">
  <div class="hero-icon">{icon_html}</div>
  <div class="hero-body">
    <div class="hero-name">{name}</div>
    <div class="hero-pub">{namespace}</div>
    <div class="hero-meta">
      <span class="hero-stars">{s_str}</span>
      <span>({review_cnt})</span>
      <span>|</span>
      <span>⬇ {fmt(downloads)}</span>
    </div>
    <div class="hero-desc">{description}</div>
    <div class="actions">
      <button class="btn btn-primary">Install</button>
      <button class="btn btn-secondary">Disable ▾</button>
      <button class="btn btn-secondary">Uninstall ▾</button>
      <button class="btn btn-prerelease">Switch to Pre-Release Version</button>
      <label class="autoupdate">
        <input type="checkbox" checked> Auto Update
      </label>
    </div>
  </div>
</div>

<!-- ══ Nav ══ -->
<div class="nav">
  <div class="nav-tab active">Details</div>
  <div class="nav-tab">Features</div>
  <div class="nav-tab">Changelog</div>
  <div class="nav-tab">Dependencies</div>
</div>

<!-- ══ Page body ══ -->
<div class="page">

  <!-- README -->
  <div class="content">
    {readme_html}
  </div>

  <!-- Sidebar -->
  <div class="sidebar">

    <div class="sidebar-section">
      <h3>Installation</h3>
      <div class="meta-row">
        <span class="meta-key">Identifier</span>
        <span class="meta-val">{ext_id}</span>
      </div>
      <div class="meta-row">
        <span class="meta-key">Version</span>
        <span class="meta-val">{version}</span>
      </div>
      <div class="meta-row">
        <span class="meta-key">Last Updated</span>
        <span class="meta-val">{timestamp}</span>
      </div>
      <div class="meta-row">
        <span class="meta-key">Size</span>
        <span class="meta-val"><a href="#">{size_str}</a></span>
      </div>
    </div>

    <div class="sidebar-section">
      <h3>Marketplace</h3>
      <div class="meta-row">
        <span class="meta-key">Published</span>
        <span class="meta-val">{published or '—'}</span>
      </div>
      <div class="meta-row">
        <span class="meta-key">Last Released</span>
        <span class="meta-val">{timestamp or '—'}</span>
      </div>
    </div>

    {"<div class='sidebar-section'><h3>Categories</h3>" + pills + "</div>" if pills else ""}

    <div class="sidebar-section">
      <h3>Resources</h3>
      <a class="resource" href="https://open-vsx.org/extension/{namespace}/{ext_name}">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="#4db2ff">
          <path d="M2 2h5v1.5H3.5v9h9V9H14v5H2V2z"/>
          <path d="M9.5 2H14v4.5h-1.5V4.56L7.28 9.78 6.22 8.72l5.22-5.22H9.5V2z"/>
        </svg>
        Repository
      </a>
      <a class="resource" href="#">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="#4db2ff">
          <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 12.5a5.5 5.5 0 110-11 5.5 5.5 0 010 11z"/>
          <path d="M7 6h2v5H7zm0-2h2v1.5H7z"/>
        </svg>
        License
      </a>
      <a class="resource" href="#">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="#4db2ff">
          <path d="M2 2h5v1.5H3.5v9h9V9H14v5H2V2z"/>
        </svg>
        Marketplace
      </a>
    </div>

  </div>
</div>

<script>
// Tab switching
document.querySelectorAll('.nav-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
  }});
}});
</script>
</body>
</html>"""
        self.setHtml(html)


# ══════════════════════════════════════════════════════════════════════════════
# Main Extensions Panel  (QDockWidget)
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionsPanel(QDockWidget):
    open_detail_requested = pyqtSignal(object)   # ext dict

    PANEL_STYLE = """
    QDockWidget       { background: #252526; }
    QWidget#panelRoot { background: #252526; }
    QLineEdit {
        background: #3c3c3c; color: #cccccc; border: 1px solid #3c3c3c;
        border-radius: 2px; padding: 4px 8px; font-size: 12px;
    }
    QLineEdit:focus { border-color: #007acc; }
    QListWidget {
        background: #252526; border: none; outline: none;
    }
    QListWidget::item { border: none; padding: 0px; }
    QListWidget::item:hover    { background: #2a2d2e; }
    QListWidget::item:selected { background: #04395e; }
    QProgressBar { background: #3c3c3c; border: none; max-height: 2px; }
    QProgressBar::chunk { background: #007acc; }
    QScrollBar:vertical {
        background: #252526; width: 10px; border: none;
    }
    QScrollBar::handle:vertical {
        background: #424242; border-radius: 5px; min-height: 20px;
    }
    QScrollBar::handle:vertical:hover { background: #555; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    def __init__(self, parent=None):
        super().__init__("Extensions", parent)
        self.setObjectName("ExtensionsDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._search_thread = None
        self._icon_threads: list = []
        self._ext_map:  dict[int, dict]           = {}
        self._cards:    dict[int, ExtensionCard]  = {}
        self._init_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QWidget()
        root.setObjectName("panelRoot")
        root.setStyleSheet(self.PANEL_STYLE)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background:#252526; border-bottom:1px solid #1e1e1e;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(8, 8, 8, 6)
        h_layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Extensions in Marketplace")
        self.search_input.returnPressed.connect(self.do_search)
        h_layout.addWidget(self.search_input)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(2)
        self.progress.hide()
        h_layout.addWidget(self.progress)

        layout.addWidget(header)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_clicked)
        layout.addWidget(self.list_widget, 1)

        self.setWidget(root)

        # Default search
        self.search_input.setText("python")
        QTimer.singleShot(200, self.do_search)

    # ── Search ────────────────────────────────────────────────────────────────

    def do_search(self):
        q = self.search_input.text().strip()
        if not q:
            return
        self.list_widget.clear()
        self._ext_map.clear()
        self._cards.clear()
        self.progress.show()

        self._search_thread = ExtensionSearchThread(q)
        self._search_thread.results_ready.connect(self._on_results)
        self._search_thread.error_occurred.connect(self._on_error)
        self._search_thread.start()

    # ── Results ───────────────────────────────────────────────────────────────

    def _on_results(self, extensions: list):
        self.progress.hide()
        self.list_widget.clear()
        self._ext_map.clear()
        self._cards.clear()
        self._icon_threads.clear()

        for idx, ext in enumerate(extensions):
            self._ext_map[idx] = ext

            card = ExtensionCard(ext, idx)
            # Wire Install button
            dl_url = (ext.get("files") or {}).get("download", "")
            ext_id = f"{ext.get('namespace','')}.{ext.get('name','')}"
            card.btn_install.clicked.connect(
                lambda _, eid=ext_id, url=dl_url: self._install(eid, url)
            )
            self._cards[idx] = card

            li = QListWidgetItem(self.list_widget)
            li.setSizeHint(QSize(self.list_widget.width(), 72))
            self.list_widget.addItem(li)
            self.list_widget.setItemWidget(li, card)

            # Async icon fetch
            icon_url = (ext.get("files") or {}).get("icon", "")
            if icon_url:
                t = IconThread(idx, icon_url)
                t.icon_ready.connect(self._on_icon)
                t.start()
                self._icon_threads.append(t)

    def _on_icon(self, row: int, data: bytes):
        card = self._cards.get(row)
        if card:
            card.set_icon(data)

    # ── Click → open detail tab ───────────────────────────────────────────────

    def _on_clicked(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        ext = self._ext_map.get(row)
        if ext:
            self.open_detail_requested.emit(ext)

    # ── Install / Error ───────────────────────────────────────────────────────

    def _install(self, ext_id: str, download_url: str):
        QMessageBox.information(
            self, "Install Extension",
            f"Installing: {ext_id}\nHandled by Monaco Extension Host."
        )
        print(f"[Extensions] Install: {ext_id} → {download_url}")

    def _on_error(self, err: str):
        self.progress.hide()
        QMessageBox.warning(self, "Search Error", f"Failed to search:\n{err}")
