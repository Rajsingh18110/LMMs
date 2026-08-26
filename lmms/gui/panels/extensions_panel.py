"""
Extensions Panel — VS Code-accurate sidebar + full detail tab.

Sidebar: search · sort dropdown · icon cards · "Load More" pagination
Detail tab: QWebEngineView with real tab switching (Details/Features/Changelog/Dependencies)
            Each tab fetches its own URL from Open VSX and renders actual content.
"""
import os
import json
import requests

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QProgressBar,
    QMessageBox, QComboBox, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt6.QtGui import QPixmap, QFont


PAGE_SIZE = 25   # results per page


# ══════════════════════════════════════════════════════════════════════════════
# Background threads
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionSearchThread(QThread):
    results_ready  = pyqtSignal(list, int)   # extensions, totalSize
    error_occurred = pyqtSignal(str)

    # Valid Open VSX sortBy values: relevance | timestamp | rating | downloadCount
    SORT_MAP = {
        "Relevance":  "relevance",
        "Downloads":  "downloadCount",
        "Rating":     "rating",
        "Updated":    "timestamp",
    }

    def __init__(self, query, offset=0, sort_by="relevance"):
        super().__init__()
        self.query   = query
        self.offset  = offset
        self.sort_by = sort_by

    def run(self):
        try:
            q_enc = requests.utils.quote(self.query)
            url = (
                f"https://open-vsx.org/api/-/search"
                f"?query={q_enc}"
                f"&size={PAGE_SIZE}"
                f"&offset={self.offset}"
                f"&sortBy={self.sort_by}"
                f"&sortOrder=desc"
            )
            r = requests.get(url, timeout=12)
            r.raise_for_status()
            data       = r.json()
            extensions = data.get("extensions", [])
            total      = int(data.get("totalSize", 0))

            # --- Exact-match boost (first page only) -------------------------
            # If the top result isn't an obvious match, try fetching the exact
            # extension by namespace/name (e.g. query = "ms-python.python" or
            # just "codex" → try open-vsx.org/api/-/search?query=codex exactly)
            if self.offset == 0 and extensions:
                exact = self._try_exact_lookup(self.query)
                if exact:
                    # Remove duplicate from list, then prepend exact match
                    ns_name = f"{exact.get('namespace','')}.{exact.get('name','')}"
                    extensions = [e for e in extensions
                                  if f"{e.get('namespace','')}.{e.get('name','')}" != ns_name]
                    extensions.insert(0, exact)
            # -----------------------------------------------------------------

            self.results_ready.emit(extensions, total)
        except Exception as e:
            self.error_occurred.emit(str(e))

    @staticmethod
    def _try_exact_lookup(query: str) -> dict | None:
        """If query looks like 'namespace.name', fetch it directly."""
        if '.' not in query:
            return None
        parts = query.strip().split('.', 1)
        if len(parts) != 2:
            return None
        ns, name = parts[0], parts[1]
        try:
            r = requests.get(
                f"https://open-vsx.org/api/{ns}/{name}",
                timeout=6
            )
            if r.ok:
                return r.json()
        except Exception:
            pass
        return None


class IconThread(QThread):
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
        self.name      = name

    def run(self):
        try:
            r = requests.get(
                f"https://open-vsx.org/api/{self.namespace}/{self.name}",
                timeout=12
            )
            r.raise_for_status()
            self.detail_ready.emit(r.json())
        except Exception as e:
            self.error_occurred.emit(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# Extension card widget (one row in the sidebar list)
# ══════════════════════════════════════════════════════════════════════════════

class ExtensionCard(QWidget):
    ICON_SIZE = 40

    def __init__(self, ext: dict, row: int):
        super().__init__()
        self._ext = ext
        self.row  = row
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()

    def _build(self):
        ext         = self._ext
        name        = ext.get("displayName") or ext.get("name", "")
        publisher   = ext.get("namespace", "")
        description = ext.get("description", "")
        version     = ext.get("version", "")
        downloads   = int(ext.get("downloadCount", 0) or 0)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 8, 8, 8)
        outer.setSpacing(10)

        # Icon
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(
            "background:#37373d; border-radius:4px; color:#555; font-size:16px;"
        )
        self.icon_lbl.setText("⬜")
        outer.addWidget(self.icon_lbl)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        row1 = QHBoxLayout()
        row1.setSpacing(4)

        name_lbl = QLabel(name)
        f = QFont(); f.setBold(True); f.setPointSize(9)
        name_lbl.setFont(f)
        name_lbl.setStyleSheet("color:#e6edf3; background:transparent;")
        row1.addWidget(name_lbl, 1)

        dl_lbl = QLabel(f"⬇ {_fmt_dl(downloads)}")
        dl_lbl.setStyleSheet("color:#8b949e; font-size:10px; background:transparent;")
        dl_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(dl_lbl)
        text_col.addLayout(row1)

        short = description[:72] + ("…" if len(description) > 72 else "")
        desc_lbl = QLabel(short)
        desc_lbl.setStyleSheet("color:#9e9e9e; font-size:11px; background:transparent;")
        text_col.addWidget(desc_lbl)

        pub_lbl = QLabel(f"{publisher}  v{version}")
        pub_lbl.setStyleSheet("color:#6e7681; font-size:10px; background:transparent;")
        text_col.addWidget(pub_lbl)

        outer.addLayout(text_col, 1)

        # Install button
        self.btn_install = QPushButton("Install")
        self.btn_install.setFixedSize(58, 22)
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setStyleSheet("""
            QPushButton {
                background:#0e639c; color:white; border:none;
                border-radius:2px; font-size:11px; font-weight:600;
            }
            QPushButton:hover   { background:#1177bb; }
            QPushButton:pressed { background:#0a4f7e; }
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


def _fmt_dl(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)


# ══════════════════════════════════════════════════════════════════════════════
# Extension Detail Tab  (QWebEngineView, real tab switching)
# ══════════════════════════════════════════════════════════════════════════════

_DETAIL_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
:root {
  --bg:     #1e1e1e;
  --bg2:    #252526;
  --border: #3c3c3c;
  --text:   #cccccc;
  --dim:    #8b949e;
  --accent: #4db2ff;
  --yellow: #cca700;
  --btn-bg: #0e639c;
  --btn-h:  #1177bb;
  --pre-bg: #2d2d2d;
}
* { box-sizing:border-box; margin:0; padding:0; }
html,body {
  background:var(--bg); color:var(--text);
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  font-size:13px; line-height:1.6; overflow-x:hidden;
}
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }

/* ── Hero ────────────────────────────────── */
.hero {
  background:var(--bg2); padding:18px 22px 14px;
  display:flex; gap:16px; align-items:flex-start;
  border-bottom:1px solid var(--border); flex-wrap:wrap;
}
.hero-icon { flex-shrink:0; }
.hero-icon img, .hero-icon .icon-ph {
  width:96px; height:96px; border-radius:6px; object-fit:contain;
}
.icon-ph {
  background:#37373d; display:flex; align-items:center;
  justify-content:center; font-size:40px;
}
.hero-body { flex:1; min-width:200px; }
.hero-name  { font-size:20px; font-weight:700; color:#e6edf3; margin-bottom:2px; }
.hero-pub   { font-size:12px; color:var(--accent); margin-bottom:4px; }
.hero-meta  { font-size:12px; color:var(--dim); display:flex; flex-wrap:wrap; gap:8px; margin-bottom:6px; }
.stars      { color:var(--yellow); }
.hero-desc  { font-size:12px; color:#9e9e9e; margin-bottom:12px; }
.actions    { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
.btn        { border:none; border-radius:2px; padding:5px 12px;
              font-size:11.5px; font-weight:600; cursor:pointer; }
.btn-primary   { background:var(--btn-bg); color:#fff; }
.btn-primary:hover { background:var(--btn-h); }
.btn-secondary { background:#3c3c3c; color:var(--text); border:1px solid #555; font-weight:400; }
.btn-secondary:hover { background:#505050; }
.btn-prerel    { background:#4b3800; color:#e8a12d; border:1px solid #6b5100; font-weight:400; }
.btn-prerel:hover { background:#5a4500; }
.auto-update   { display:flex; align-items:center; gap:4px; font-size:11.5px; color:var(--dim); cursor:pointer; }
.auto-update input { accent-color:var(--accent); }

/* ── Nav tabs ─────────────────────────────── */
.nav {
  background:var(--bg2); border-bottom:1px solid var(--border);
  display:flex; padding:0 22px; overflow-x:auto;
}
.nav-tab {
  font-size:11px; font-weight:600; color:var(--dim);
  padding:9px 14px; cursor:pointer; white-space:nowrap;
  border-bottom:2px solid transparent; text-transform:uppercase;
  letter-spacing:0.05em; transition:color .15s;
}
.nav-tab.active { color:#e6edf3; border-bottom-color:var(--accent); }
.nav-tab:hover:not(.active) { color:var(--text); }

/* ── Page layout ─────────────────────────── */
.page { display:flex; min-height:calc(100vh - 165px); }
.content { flex:1; padding:20px 22px; min-width:0; overflow-wrap:break-word; }
.sidebar {
  width:210px; flex-shrink:0; padding:18px 14px;
  border-left:1px solid var(--border);
}

/* ── Content area typography ──────────────── */
.content h1 { font-size:17px; color:#e6edf3; margin:16px 0 8px; padding-bottom:5px; border-bottom:1px solid var(--border); }
.content h2 { font-size:14px; color:#e6edf3; margin:14px 0 6px; }
.content h3 { font-size:12.5px; color:#e6edf3; margin:12px 0 5px; }
.content h4 { font-size:12px; color:#e6edf3; margin:10px 0 4px; }
.content p  { color:#bcc4ce; margin-bottom:10px; }
.content ul, .content ol { padding-left:20px; color:#bcc4ce; margin-bottom:10px; }
.content li { margin-bottom:3px; }
.content code {
  background:var(--pre-bg); border-radius:3px; padding:1px 5px;
  font-family:'Cascadia Code','Fira Code',monospace; font-size:11.5px; color:#e6edf3;
}
.content pre {
  background:var(--pre-bg); border-radius:4px; padding:11px 13px;
  margin:10px 0; overflow-x:auto; font-size:11.5px;
  font-family:'Cascadia Code','Fira Code',monospace; color:#e6edf3; line-height:1.5;
}
.content pre code { background:none; padding:0; }
.content blockquote {
  border-left:3px solid #444; padding-left:12px; margin:10px 0;
  color:#8b949e; font-style:italic;
}
.content table { border-collapse:collapse; width:100%; margin:10px 0; }
.content th { background:#2d2d2d; color:#e6edf3; padding:6px 10px; text-align:left; border:1px solid var(--border); font-size:11.5px; }
.content td { padding:5px 10px; border:1px solid var(--border); color:#bcc4ce; font-size:11.5px; }
.content img { max-width:100%; border-radius:4px; margin:8px 0; }
.content hr  { border:none; border-top:1px solid var(--border); margin:14px 0; }
.content a   { color:var(--accent); }

/* ── Loading / error states ──────────────── */
.loading {
  display:flex; align-items:center; gap:10px;
  color:var(--dim); padding:20px 0;
}
.spinner {
  width:16px; height:16px; border:2px solid var(--border);
  border-top-color:var(--accent); border-radius:50%;
  animation:spin .8s linear infinite;
}
@keyframes spin { to { transform:rotate(360deg); } }
.empty { color:#555; font-size:12px; padding:20px 0; }

/* ── Features tab ────────────────────────── */
.feature-group { margin-bottom:18px; }
.feature-group h3 { font-size:12px; color:#e6edf3; font-weight:700;
  text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px; color:var(--dim); }
.feature-item { display:flex; gap:8px; margin-bottom:5px; font-size:11.5px; }
.feature-item .key { color:#e6edf3; font-weight:600; min-width:100px; }
.feature-item .val { color:#bcc4ce; }
.badge { background:#37373d; border-radius:2px; padding:1px 6px;
  font-size:10px; color:#aab0b8; display:inline-block; margin:1px 2px 0 0; }

/* ── Sidebar ─────────────────────────────── */
.side-section { margin-bottom:18px; }
.side-section h3 {
  font-size:10px; font-weight:700; color:var(--dim);
  text-transform:uppercase; letter-spacing:0.08em; margin-bottom:7px;
}
.meta-row { display:flex; gap:6px; margin-bottom:4px; font-size:11px; }
.meta-key { color:var(--dim); width:82px; flex-shrink:0; }
.meta-val { color:var(--text); flex:1; word-break:break-all; }
.meta-val a { color:var(--accent); }
.pill {
  background:transparent; border:1px solid #555; border-radius:2px;
  padding:1px 6px; font-size:10px; color:#aab0b8;
  display:inline-block; margin:2px 2px 0 0;
}
.res-link { display:flex; align-items:center; gap:5px; color:var(--accent);
  font-size:11px; text-decoration:none; margin-bottom:4px; }
.res-link:hover { text-decoration:underline; }
</style>
</head>
<body>

<!-- ══ Hero ══ -->
<div class="hero">
  <div class="hero-icon">
    __ICON_HTML__
  </div>
  <div class="hero-body">
    <div class="hero-name">__NAME__</div>
    <div class="hero-pub">__PUBLISHER__</div>
    <div class="hero-meta">
      <span class="stars">__STARS__</span>
      <span>(__REVIEW_CNT__)</span>
      <span>|</span>
      <span>⬇ __DOWNLOADS__</span>
    </div>
    <div class="hero-desc">__DESC__</div>
    <div class="actions">
      <button class="btn btn-primary">Install</button>
      <button class="btn btn-secondary">Disable ▾</button>
      <button class="btn btn-secondary">Uninstall ▾</button>
      <button class="btn btn-prerel">Switch to Pre-Release Version</button>
      <label class="auto-update"><input type="checkbox" checked> Auto Update</label>
    </div>
  </div>
</div>

<!-- ══ Nav ══ -->
<div class="nav">
  <div class="nav-tab active" data-tab="details" onclick="switchTab('details',this)">Details</div>
  <div class="nav-tab" data-tab="features" onclick="switchTab('features',this)">Features</div>
  <div class="nav-tab" data-tab="changelog" onclick="switchTab('changelog',this)">Changelog</div>
  <div class="nav-tab" data-tab="dependencies" onclick="switchTab('dependencies',this)">Dependencies</div>
</div>

<!-- ══ Body ══ -->
<div class="page">
  <div class="content" id="tabContent">
    <div class="loading"><div class="spinner"></div> Loading details…</div>
  </div>
  <div class="sidebar">
    <div class="side-section">
      <h3>Installation</h3>
      <div class="meta-row"><span class="meta-key">Identifier</span><span class="meta-val">__EXT_ID__</span></div>
      <div class="meta-row"><span class="meta-key">Version</span><span class="meta-val">__VERSION__</span></div>
      <div class="meta-row"><span class="meta-key">Last Updated</span><span class="meta-val">__UPDATED__</span></div>
      <div class="meta-row"><span class="meta-key">Size</span><span class="meta-val">__SIZE__</span></div>
    </div>
    <div class="side-section">
      <h3>Marketplace</h3>
      <div class="meta-row"><span class="meta-key">Published</span><span class="meta-val">__PUBLISHED__</span></div>
      <div class="meta-row"><span class="meta-key">Last Released</span><span class="meta-val">__RELEASED__</span></div>
    </div>
    __CATEGORIES_HTML__
    <div class="side-section">
      <h3>Resources</h3>
      <a class="res-link" href="__MKT_URL__">🌐 Marketplace</a>
      <a class="res-link" href="__LICENSE_URL__">📄 License</a>
      __REPO_LINK__
    </div>
  </div>
</div>

<script>
// ── Extension metadata injected by Python ──────────────────────────────────
const EXT = __EXT_JSON__;

// ── Markdown → HTML ────────────────────────────────────────────────────────
function mdToHtml(md) {
  if (!md) return '<p class="empty">No content available.</p>';

  // Fenced code blocks
  md = md.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${escHtml(code.trim())}</code></pre>`);

  // Tables
  md = md.replace(/^\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n)*)/gm, (_, hdr, rows) => {
    const ths = hdr.split('|').map(c => `<th>${c.trim()}</th>`).join('');
    const trs = rows.trim().split('\n').map(row => {
      const tds = row.split('|').slice(1,-1).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  });

  // Headings
  md = md.replace(/^#{6} (.+)$/gm, '<h6>$1</h6>');
  md = md.replace(/^#{5} (.+)$/gm, '<h5>$1</h5>');
  md = md.replace(/^#{4} (.+)$/gm, '<h4>$1</h4>');
  md = md.replace(/^### (.+)$/gm,  '<h3>$1</h3>');
  md = md.replace(/^## (.+)$/gm,   '<h2>$1</h2>');
  md = md.replace(/^# (.+)$/gm,    '<h1>$1</h1>');

  // Blockquote
  md = md.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // HR
  md = md.replace(/^---+$/gm, '<hr>');

  // Bold / italic
  md = md.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  md = md.replace(/\*\*(.+?)\*\*/g,    '<strong>$1</strong>');
  md = md.replace(/\*(.+?)\*/g,        '<em>$1</em>');

  // Inline code
  md = md.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // Images (before links)
  md = md.replace(/!\[([^\]]*)\]\(([^)]+)\)/g,
    '<img src="$2" alt="$1">');

  // Links
  md = md.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2">$1</a>');

  // Task lists
  md = md.replace(/^[ \t]*- \[x\] (.+)$/gm, '<li>☑ $1</li>');
  md = md.replace(/^[ \t]*- \[ \] (.+)$/gm, '<li>☐ $1</li>');

  // Unordered lists
  md = md.replace(/((?:^[ \t]*[-*] .+\n?)+)/gm, match => {
    const items = match.trim().split('\n').map(line =>
      `<li>${line.replace(/^[ \t]*[-*] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  md = md.replace(/((?:^\d+\. .+\n?)+)/gm, match => {
    const items = match.trim().split('\n').map(line =>
      `<li>${line.replace(/^\d+\. /, '')}</li>`).join('');
    return `<ol>${items}</ol>`;
  });

  // Paragraphs
  const blocks = md.split(/\n{2,}/);
  return blocks.map(b => {
    b = b.trim();
    if (!b) return '';
    if (/^<(h[1-6]|ul|ol|pre|blockquote|table|hr)/.test(b)) return b;
    return `<p>${b.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Features renderer ──────────────────────────────────────────────────────
function renderFeatures(contributes) {
  if (!contributes || !Object.keys(contributes).length)
    return '<p class="empty">No features information available.</p>';

  const LABELS = {
    languages:     'Language Support',
    grammars:      'Syntax Grammars',
    themes:        'Color Themes',
    iconThemes:    'File Icon Themes',
    commands:      'Commands',
    keybindings:   'Keybindings',
    snippets:      'Snippets',
    debuggers:     'Debuggers',
    configuration: 'Settings',
    menus:         'Menus',
    views:         'Views',
    viewsContainers: 'View Containers',
    taskDefinitions: 'Task Definitions',
    breakpoints:   'Breakpoints',
    walkthroughs:  'Walkthroughs',
  };

  let html = '';
  for (const [key, items] of Object.entries(contributes)) {
    const label = LABELS[key] || key;
    const arr   = Array.isArray(items) ? items : [items];
    html += `<div class="feature-group"><h3>${label} (${arr.length})</h3>`;

    if (key === 'commands') {
      arr.slice(0, 30).forEach(cmd => {
        html += `<div class="feature-item">
          <span class="key">${escHtml(cmd.title || cmd.command || '')}</span>
          <span class="val"><code>${escHtml(cmd.command || '')}</code></span>
        </div>`;
      });
    } else if (key === 'languages') {
      arr.forEach(lang => {
        const exts = (lang.extensions || []).join(', ');
        html += `<div class="feature-item">
          <span class="key">${escHtml(lang.id || '')}</span>
          <span class="val">${escHtml(exts)}</span>
        </div>`;
      });
    } else if (key === 'themes') {
      arr.forEach(t => {
        html += `<div class="feature-item">
          <span class="key">${escHtml(t.label || t.id || '')}</span>
          <span class="val">${escHtml(t.uiTheme || '')}</span>
        </div>`;
      });
    } else if (key === 'keybindings') {
      arr.slice(0, 20).forEach(kb => {
        html += `<div class="feature-item">
          <span class="key"><code>${escHtml(kb.key || '')}</code></span>
          <span class="val">${escHtml(kb.command || '')}</span>
        </div>`;
      });
    } else if (key === 'configuration') {
      const props = (Array.isArray(items) ? items[0] : items).properties || {};
      Object.keys(props).slice(0, 20).forEach(k => {
        html += `<div class="feature-item">
          <span class="key" style="min-width:220px">${escHtml(k)}</span>
          <span class="val">${escHtml(props[k].description || props[k].markdownDescription || '')}</span>
        </div>`;
      });
    } else {
      arr.slice(0, 10).forEach(item => {
        const display = typeof item === 'string' ? item :
          (item.id || item.title || item.label || item.command || JSON.stringify(item).slice(0, 60));
        html += `<span class="badge">${escHtml(String(display))}</span>`;
      });
    }
    html += '</div>';
  }
  return html || '<p class="empty">No features information available.</p>';
}

// ── Dependencies renderer ──────────────────────────────────────────────────
function renderDeps(deps, bundled) {
  let html = '';
  if (!deps.length && !bundled.length)
    return '<p class="empty">This extension has no declared dependencies.</p>';
  if (deps.length) {
    html += '<h2>Dependencies</h2><ul>';
    deps.forEach(d => {
      const id  = d.namespace ? `${d.namespace}.${d.extension}` : String(d);
      const url = d.url || `https://open-vsx.org/extension/${id.replace('.','/')}`;
      html += `<li><a href="${url}">${id}</a></li>`;
    });
    html += '</ul>';
  }
  if (bundled.length) {
    html += '<h2>Bundled Extensions</h2><ul>';
    bundled.forEach(d => {
      const id  = d.namespace ? `${d.namespace}.${d.extension}` : String(d);
      const url = d.url || `https://open-vsx.org/extension/${id.replace('.','/')}`;
      html += `<li><a href="${url}">${id}</a></li>`;
    });
    html += '</ul>';
  }
  return html;
}

// ── Tab switching ──────────────────────────────────────────────────────────
const _cache = {};
let _activeTab = 'details';

async function switchTab(name, el) {
  if (name === _activeTab && _cache[name]) return;
  _activeTab = name;

  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');

  const content = document.getElementById('tabContent');
  content.innerHTML = '<div class="loading"><div class="spinner"></div> Loading…</div>';

  if (_cache[name]) {
    content.innerHTML = _cache[name];
    return;
  }

  try {
    let html = '';
    if (name === 'details') {
      const url = EXT.files && EXT.files.readme;
      if (url) {
        const r = await fetch(url);
        html = mdToHtml(await r.text());
      } else {
        html = `<p>${EXT.description || 'No description available.'}</p>`;
      }
    }
    else if (name === 'changelog') {
      const url = EXT.files && EXT.files.changelog;
      if (url) {
        const r = await fetch(url);
        html = mdToHtml(await r.text());
      } else {
        html = '<p class="empty">No changelog available for this extension.</p>';
      }
    }
    else if (name === 'features') {
      const url = EXT.files && EXT.files.manifest;
      if (url) {
        const r = await fetch(url);
        const manifest = await r.json();
        html = renderFeatures(manifest.contributes || {});
      } else {
        html = '<p class="empty">No features information available.</p>';
      }
    }
    else if (name === 'dependencies') {
      html = renderDeps(EXT.bundledExtensions || [], EXT.dependencies || []);
    }

    _cache[name] = html;
    content.innerHTML = html;
  } catch (e) {
    content.innerHTML = `<p class="empty">Failed to load content: ${e.message}</p>`;
  }
}

// Auto-load details on start
switchTab('details', document.querySelector('.nav-tab.active'));
</script>
</body>
</html>
"""


class ExtensionDetailTab(QWebEngineView):
    """VS Code-style extension detail page with real per-tab content fetching."""

    def __init__(self, ext: dict, parent=None):
        super().__init__(parent)
        self._ext    = ext
        self._detail = {}
        self.setProperty("is_custom", True)
        ns   = ext.get("namespace", "")
        name = ext.get("name", "")
        self.setProperty("identifier", f"ext:{ns}.{name}")
        # Show skeleton while fetching detail
        self.setHtml(self._skeleton())
        # Fetch full detail from Open VSX
        self._dt = ExtensionDetailThread(ns, name)
        self._dt.detail_ready.connect(self._render)
        self._dt.error_occurred.connect(lambda _: self._render(ext))
        self._dt.start()

    def _skeleton(self) -> str:
        name = self._ext.get("displayName") or self._ext.get("name", "")
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
          body {{background:#1e1e1e;color:#ccc;font-family:'Segoe UI',sans-serif;margin:24px}}
          @keyframes pulse {{0%,100%{{opacity:.5}}50%{{opacity:1}}}}
          .bar {{background:#2d2d2d;border-radius:3px;height:12px;margin:8px 0;animation:pulse 1.4s infinite}}
        </style></head>
        <body>
        <h2 style="color:#e6edf3;margin-bottom:14px">{name}</h2>
        <div class="bar" style="width:55%"></div>
        <div class="bar" style="width:75%"></div>
        <div class="bar" style="width:40%"></div>
        <p style="color:#555;margin-top:20px;font-size:12px">Loading extension details…</p>
        </body></html>"""

    def _render(self, detail: dict):
        ext = {**self._ext, **detail}

        name       = ext.get("displayName") or ext.get("name", "")
        namespace  = ext.get("namespace", "")
        ext_name   = ext.get("name", "")
        desc       = ext.get("description", "")
        version    = ext.get("version", "—")
        stars      = float(ext.get("averageRating") or 0)
        reviews    = int(ext.get("reviewCount") or 0)
        downloads  = int(ext.get("downloadCount") or 0)
        timestamp  = (ext.get("timestamp") or "")[:10]
        published  = (ext.get("publishedDate") or ext.get("timestamp") or "")[:10]
        categories = list(ext.get("categories") or [])
        tags       = list(ext.get("tags") or [])
        icon_url   = (ext.get("files") or {}).get("icon", "")
        ext_id     = f"{namespace}.{ext_name}"
        size_bytes = (ext.get("packageSizes") or {}).get("download", 0)
        size_str   = f"{size_bytes/1_000_000:.2f} MB" if size_bytes else "—"
        license_url = (ext.get("files") or {}).get("license", "#")
        repo_url    = ext.get("homepage") or ext.get("repository") or ""

        # Stars string
        full  = round(stars)
        s_str = "★" * full + "☆" * (5 - full)

        # Icon HTML
        if icon_url:
            icon_html = (
                f'<img src="{icon_url}" width="96" height="96" '
                f'style="border-radius:6px;object-fit:contain" '
                f'onerror="this.style.display=\'none\'">'
            )
        else:
            icon_html = '<div class="icon-ph">⬛</div>'

        # Category pills
        all_tags = list(dict.fromkeys(categories + tags))[:8]
        if all_tags:
            pills   = "".join(f'<span class="pill">{t}</span>' for t in all_tags)
            cats_html = f'<div class="side-section"><h3>Categories</h3>{pills}</div>'
        else:
            cats_html = ""

        # Repo link
        repo_html = f'<a class="res-link" href="{repo_url}">📦 Repository</a>' if repo_url else ""

        # Build injected ext JSON (only include files + dependency fields)
        ext_json = json.dumps({
            "description": desc,
            "files": ext.get("files") or {},
            "bundledExtensions": ext.get("bundledExtensions") or [],
            "dependencies":      ext.get("dependencies") or [],
        })

        html = (_DETAIL_HTML_TEMPLATE
            .replace("__ICON_HTML__", icon_html)
            .replace("__NAME__",      name)
            .replace("__PUBLISHER__", namespace)
            .replace("__STARS__",     s_str)
            .replace("__REVIEW_CNT__", str(reviews))
            .replace("__DOWNLOADS__", _fmt_dl(downloads))
            .replace("__DESC__",      desc)
            .replace("__EXT_ID__",    ext_id)
            .replace("__VERSION__",   version)
            .replace("__UPDATED__",   timestamp or "—")
            .replace("__SIZE__",      size_str)
            .replace("__PUBLISHED__", published or "—")
            .replace("__RELEASED__",  timestamp or "—")
            .replace("__CATEGORIES_HTML__", cats_html)
            .replace("__MKT_URL__",   f"https://open-vsx.org/extension/{namespace}/{ext_name}")
            .replace("__LICENSE_URL__", license_url)
            .replace("__REPO_LINK__", repo_html)
            .replace("__EXT_JSON__",  ext_json)
        )
        self.setHtml(html)


# ══════════════════════════════════════════════════════════════════════════════
# Main Extensions Panel (QDockWidget sidebar)
# ══════════════════════════════════════════════════════════════════════════════

_PANEL_STYLE = """
QDockWidget       { background:#252526; }
QWidget#panelRoot { background:#252526; }
QLineEdit {
    background:#3c3c3c; color:#cccccc; border:1px solid #3c3c3c;
    border-radius:2px; padding:4px 8px; font-size:12px;
}
QLineEdit:focus { border-color:#007acc; }
QComboBox {
    background:#3c3c3c; color:#aaa; border:none;
    border-radius:2px; padding:2px 6px; font-size:11px;
}
QComboBox::drop-down { border:none; width:14px; }
QComboBox QAbstractItemView {
    background:#252526; color:#ccc; border:1px solid #3c3c3c; outline:none;
    selection-background-color:#094771;
}
QListWidget {
    background:#252526; border:none; outline:none;
}
QListWidget::item { padding:0px; border:none; }
QListWidget::item:hover    { background:#2a2d2e; }
QListWidget::item:selected { background:#04395e; }
QProgressBar { background:#3c3c3c; border:none; max-height:2px; }
QProgressBar::chunk { background:#007acc; }
QPushButton#loadMoreBtn {
    background:#2d2d2d; color:#4db2ff; border:none;
    padding:8px; font-size:11px; border-top:1px solid #3c3c3c;
}
QPushButton#loadMoreBtn:hover { background:#37373d; }
QScrollBar:vertical { background:#252526; width:8px; border:none; }
QScrollBar::handle:vertical { background:#424242; border-radius:4px; min-height:20px; }
QScrollBar::handle:vertical:hover { background:#555; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
"""


class ExtensionsPanel(QDockWidget):
    open_detail_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__("Extensions", parent)
        self.setObjectName("ExtensionsDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._search_thread  = None
        self._icon_threads:  list = []
        self._ext_map:  dict[int, dict]          = {}
        self._cards:    dict[int, ExtensionCard] = {}
        self._offset  = 0
        self._total   = 0
        self._query   = "python"
        self._sort_by = "relevance"
        self._init_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QWidget()
        root.setObjectName("panelRoot")
        root.setStyleSheet(_PANEL_STYLE)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header: search + sort ─────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background:#252526; border-bottom:1px solid #1e1e1e;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(8, 8, 8, 6)
        h_layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Extensions in Marketplace")
        self.search_input.returnPressed.connect(self._new_search)
        # Live search — fire 450ms after user stops typing (VS Code behaviour)
        self._live_timer = QTimer(self)
        self._live_timer.setSingleShot(True)
        self._live_timer.setInterval(450)
        self._live_timer.timeout.connect(self._new_search)
        self.search_input.textChanged.connect(self._on_text_changed)
        h_layout.addWidget(self.search_input)

        # Sort row
        sort_row = QHBoxLayout()
        sort_row.setContentsMargins(0, 0, 0, 0)
        sort_row.setSpacing(4)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setStyleSheet("color:#6e7681; font-size:11px; background:transparent;")
        sort_row.addWidget(sort_lbl)

        self.sort_combo = QComboBox()
        # Only add sort options the Open VSX API actually supports
        self.sort_combo.addItems(["Relevance", "Downloads", "Rating", "Updated"])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        self.sort_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sort_row.addWidget(self.sort_combo, 1)

        h_layout.addLayout(sort_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(2)
        self.progress.hide()
        h_layout.addWidget(self.progress)

        layout.addWidget(header)

        # ── Results list ──────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(0)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_clicked)
        layout.addWidget(self.list_widget, 1)

        # ── Load More button ──────────────────────────────────────────────────
        self.load_more_btn = QPushButton("Load More")
        self.load_more_btn.setObjectName("loadMoreBtn")
        self.load_more_btn.hide()
        self.load_more_btn.clicked.connect(self._load_more)
        layout.addWidget(self.load_more_btn)

        self.setWidget(root)

        # Initial search
        self.search_input.setText("python")
        QTimer.singleShot(300, self._new_search)

    # ── Search control ────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        """Restart the live-search debounce timer on every keystroke."""
        if len(text.strip()) >= 2:
            self._live_timer.start()   # restarts if already running
        elif text.strip() == "":
            self._live_timer.stop()

    def _new_search(self):
        """Fresh search — reset offset, clear list."""
        self._live_timer.stop()
        self._query  = self.search_input.text().strip() or "python"
        if len(self._query) < 2:
            return
        self._offset = 0
        self._ext_map.clear()
        self._cards.clear()
        self.list_widget.clear()
        self.load_more_btn.hide()
        self._fetch(append=False)

    def _load_more(self):
        self._offset += PAGE_SIZE
        self._fetch(append=True)

    def _on_sort_changed(self, label: str):
        sort_map = {
            "Relevance": "relevance",
            "Downloads": "downloadCount",
            "Rating":    "rating",       # Open VSX uses 'rating' not 'averageRating'
            "Updated":   "timestamp",
        }
        self._sort_by = sort_map.get(label, "relevance")
        self._new_search()

    def _fetch(self, append: bool):
        self.progress.show()
        self.load_more_btn.hide()
        if not append:
            self._icon_threads.clear()

        t = ExtensionSearchThread(self._query, self._offset, self._sort_by)
        t.results_ready.connect(lambda exts, tot: self._on_results(exts, tot, append))
        t.error_occurred.connect(self._on_error)
        t.start()
        self._search_thread = t

    # ── Results ───────────────────────────────────────────────────────────────

    def _on_results(self, extensions: list, total: int, append: bool):
        self.progress.hide()
        self._total = total

        base_idx = len(self._ext_map)

        for i, ext in enumerate(extensions):
            row = base_idx + i
            self._ext_map[row] = ext

            card = ExtensionCard(ext, row)
            dl_url = (ext.get("files") or {}).get("download", "")
            ext_id = f"{ext.get('namespace','')}.{ext.get('name','')}"
            card.btn_install.clicked.connect(
                lambda _, eid=ext_id, url=dl_url: self._install(eid, url)
            )
            self._cards[row] = card

            li = QListWidgetItem(self.list_widget)
            li.setSizeHint(QSize(self.list_widget.width() or 240, 80))

            self.list_widget.addItem(li)
            self.list_widget.setItemWidget(li, card)

            # Async icon
            icon_url = (ext.get("files") or {}).get("icon", "")
            if icon_url:
                t = IconThread(row, icon_url)
                t.icon_ready.connect(self._on_icon)
                t.start()
                self._icon_threads.append(t)

        # Show Load More if there are more results
        loaded = len(self._ext_map)
        if loaded < total:
            remaining = total - loaded
            self.load_more_btn.setText(
                f"Load More  ({remaining:,} remaining of {total:,})"
            )
            self.load_more_btn.show()

    def _on_icon(self, row: int, data: bytes):
        card = self._cards.get(row)
        if card:
            card.set_icon(data)

    # ── Click → detail tab ────────────────────────────────────────────────────

    def _on_clicked(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        ext = self._ext_map.get(row)
        if ext:
            self.open_detail_requested.emit(ext)

    # ── Error / Install ───────────────────────────────────────────────────────

    def _on_error(self, err: str):
        self.progress.hide()
        QMessageBox.warning(self, "Search Error", f"Failed to search:\n{err}")

    def _install(self, ext_id: str, url: str):
        QMessageBox.information(
            self, "Install Extension",
            f"Installing: {ext_id}\nHandled by Monaco Extension Host."
        )
        print(f"[Extensions] Install: {ext_id} → {url}")
