from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSlot
from lmms.gui.utils.diagnostic_manager import DiagnosticManager
from lmms.gui.utils.git_manager import GitManager

class CustomStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.setStyleSheet("""
            QWidget {
                background-color: #181818; /* statusbar_bg */
                color: #e5e7eb; /* text_primary */
                font-size: 11px;
                border-top: 1px solid #30363d; /* border_color */
            }
            QLabel { padding: 0 6px; }
            QPushButton {
                background: transparent;
                border: none;
                color: #e5e7eb;
                padding: 0 6px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(2)
        
        # --- Left Side ---
        # Git Status
        self.git_btn = QPushButton("🌿 main")
        self.git_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Diagnostic Counts
        self.diag_btn = QPushButton("❌ 0  ⚠️ 0")
        self.diag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.layout.addWidget(self.git_btn)
        self.layout.addWidget(self.diag_btn)
        
        self.layout.addStretch()
        
        # --- Right Side ---
        self.cursor_pos = QLabel("Ln 1, Col 1")
        self.indentation = QLabel("Spaces: 4")
        self.encoding = QLabel("UTF-8")
        self.line_endings = QLabel("LF")
        
        self.language_btn = QPushButton("{} Plain Text")
        self.language_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.layout.addWidget(self.cursor_pos)
        self.layout.addWidget(self.indentation)
        self.layout.addWidget(self.encoding)
        self.layout.addWidget(self.line_endings)
        self.layout.addWidget(self.language_btn)
        
        # Wire up diagnostics
        self.diag_mgr = DiagnosticManager.get_instance()
        self.diag_mgr.diagnostics_updated.connect(self.update_diagnostics)
        self.git_mgr = None
        
    def set_git_manager(self, git_mgr):
        self.git_mgr = git_mgr
        if self.git_mgr:
            self.git_mgr.repo_changed.connect(self.update_git_status)
            self.update_git_status()
            
    @pyqtSlot()
    def update_git_status(self):
        if not self.git_mgr or not self.git_mgr.is_valid():
            self.git_btn.setText("🌿 No Git")
            return
            
        branch = self.git_mgr.get_current_branch()
        status = self.git_mgr.get_status()
        changes = len(status.get("modified", [])) + len(status.get("untracked", []))
        
        if changes > 0:
            self.git_btn.setText(f"🌿 {branch}*")
        else:
            self.git_btn.setText(f"🌿 {branch}")
        
    @pyqtSlot()
    def update_diagnostics(self):
        all_diags = self.diag_mgr.get_diagnostics()
        errors = 0
        warnings = 0
        for diags in all_diags.values():
            for d in diags:
                sev = d.get("severity", 1)
                if sev == 1:
                    errors += 1
                elif sev == 2:
                    warnings += 1
        self.diag_btn.setText(f"❌ {errors}  ⚠️ {warnings}")

    @pyqtSlot(int, int)
    def update_cursor_position(self, line: int, col: int):
        self.cursor_pos.setText(f"Ln {line}, Col {col}")
        
    @pyqtSlot(str, int, str, str)
    def update_file_context(self, language: str, indent: int, encoding: str, eol: str):
        if not language:
            language = "Plain Text"
        self.language_btn.setText(f"{{}} {language}")
        self.indentation.setText(f"Spaces: {indent}")
        self.encoding.setText(encoding.upper())
        self.line_endings.setText(eol)
