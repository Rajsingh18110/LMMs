from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSlot
from lmms.gui.utils.diagnostic_manager import DiagnosticManager

# VS Code status bar colors
_SB_BG   = "#007acc"   # classic VS Code blue
_SB_TEXT = "#ffffff"
_SB_HOVER = "rgba(255,255,255,0.12)"

_STATUS_BAR_QSS = f"""
    QWidget#CustomStatusBar {{
        background-color: {_SB_BG};
        border-top: none;
    }}
    QLabel#statusLabel {{
        background-color: transparent;
        color: {_SB_TEXT};
        font-size: 12px;
        font-family: "Segoe UI", Roboto, sans-serif;
        padding: 0 6px;
        border: none;
    }}
    QPushButton#statusBtn {{
        background-color: transparent;
        color: {_SB_TEXT};
        font-size: 12px;
        font-family: "Segoe UI", Roboto, sans-serif;
        padding: 0 8px;
        border: none;
        border-radius: 0px;
    }}
    QPushButton#statusBtn:hover {{
        background-color: {_SB_HOVER};
    }}
"""


class CustomStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomStatusBar")
        self.setFixedHeight(22)
        self.setStyleSheet(_STATUS_BAR_QSS)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)

        # ── Left side ──────────────────────────────
        self.git_btn = self._make_btn("⎇  main")
        self.diag_btn = self._make_btn("⊘ 0  △ 0")
        layout.addWidget(self.git_btn)
        layout.addWidget(self.diag_btn)

        layout.addStretch()

        # ── Right side ─────────────────────────────
        self.cursor_pos   = self._make_lbl("Ln 1, Col 1")
        self.indentation  = self._make_lbl("Spaces: 4")
        self.encoding     = self._make_lbl("UTF-8")
        self.line_endings = self._make_lbl("LF")
        self.language_btn = self._make_btn("{} Plain Text")
        self.language_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        for w in (self.cursor_pos, self.indentation,
                  self.encoding, self.line_endings, self.language_btn):
            layout.addWidget(w)

        # ── Diagnostics ────────────────────────────
        self.diag_mgr = DiagnosticManager.get_instance()
        self.diag_mgr.diagnostics_updated.connect(self.update_diagnostics)
        self.git_mgr = None

    # ── Helpers ──────────────────────────────────────────
    def _make_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("statusLabel")
        return lbl

    def _make_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("statusBtn")
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    # ── Public API ───────────────────────────────────────
    def set_git_manager(self, git_mgr):
        self.git_mgr = git_mgr
        if self.git_mgr:
            self.git_mgr.repo_changed.connect(self.update_git_status)
            self.update_git_status()

    @pyqtSlot()
    def update_git_status(self):
        if not self.git_mgr or not self.git_mgr.is_valid():
            self.git_btn.setText("⎇  No Git")
            return
        branch = self.git_mgr.get_current_branch()
        status = self.git_mgr.get_status()
        changes = len(status.get("modified", [])) + len(status.get("untracked", []))
        self.git_btn.setText(f"⎇  {branch}{'*' if changes else ''}")

    @pyqtSlot()
    def update_diagnostics(self):
        errors = warnings = 0
        for diags in self.diag_mgr.get_diagnostics().values():
            for d in diags:
                sev = d.get("severity", 1)
                if sev == 1:
                    errors += 1
                elif sev == 2:
                    warnings += 1
        self.diag_btn.setText(f"⊘ {errors}  △ {warnings}")

    @pyqtSlot(int, int)
    def update_cursor_position(self, line: int, col: int):
        self.cursor_pos.setText(f"Ln {line}, Col {col}")

    @pyqtSlot(str, int, str, str)
    def update_file_context(self, language: str, indent: int, encoding: str, eol: str):
        language = language or "Plain Text"
        self.language_btn.setText(f"{{}} {language}")
        self.indentation.setText(f"Spaces: {indent}")
        self.encoding.setText(encoding.upper())
        self.line_endings.setText(eol)
