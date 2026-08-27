import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSlot, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from lmms.gui.utils.diagnostic_manager import DiagnosticManager

class ProblemsTab(QWidget):
    # Emitted when a diagnostic is double-clicked: file_path, line (0-indexed), column (0-indexed)
    diagnostic_clicked = pyqtSignal(str, int, int)
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 0)
        self.layout.setSpacing(5)
        
        # Toolbar
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt6.QtWidgets import QLineEdit, QPushButton
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter (e.g. text, **/*.ts, !**/node...)")
        self.filter_input.setStyleSheet("QLineEdit { background: #181818; color: #e5e7eb; border: 1px solid #30363d; border-radius: 2px; padding: 2px 6px; }")
        
        self.btn_group = QPushButton("≡")
        self.btn_copy = QPushButton("📋")
        self.btn_maximize = QPushButton("↑")
        self.btn_close = QPushButton("✕")
        
        for btn in [self.btn_group, self.btn_copy, self.btn_maximize, self.btn_close]:
            btn.setFixedSize(24, 24)
            btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #8b949e; } QPushButton:hover { color: #e5e7eb; background: #21262d; border-radius: 2px; }")
            
        self.toolbar_layout.addWidget(self.filter_input)
        self.toolbar_layout.addWidget(self.btn_group)
        self.toolbar_layout.addWidget(self.btn_copy)
        self.toolbar_layout.addWidget(self.btn_maximize)
        self.toolbar_layout.addWidget(self.btn_close)
        
        self.layout.addLayout(self.toolbar_layout)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #1e1e1e; color: #c9d1d9; border: none; font-size: 12px; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #21262d; }
        """)
        
        self.layout.addWidget(self.tree)
        
        # Connect signals
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.diag_mgr = DiagnosticManager.get_instance()
        self.diag_mgr.diagnostics_updated.connect(self.refresh)
        
        self.refresh("")
        
    @pyqtSlot(str)
    def refresh(self, _path: str):
        self.tree.clear()
        
        all_diags = self.diag_mgr.get_diagnostics()
        
        for file_path, diags in all_diags.items():
            if not diags:
                continue
                
            file_name = os.path.basename(file_path)
            file_item = QTreeWidgetItem(self.tree, [f"{file_name}  {file_path}"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": file_path})
            file_item.setExpanded(True)
            
            for d in diags:
                severity = d.get("severity", 1)
                message = d.get("message", "").split("\n")[0]
                line = d.get("range", {}).get("start", {}).get("line", 0) + 1
                col = d.get("range", {}).get("start", {}).get("character", 0) + 1
                source = d.get("source", "")
                
                # Determine icon/prefix based on severity
                if severity == 1:
                    prefix = "❌"
                elif severity == 2:
                    prefix = "⚠️"
                else:
                    prefix = "ℹ️"
                    
                text = f"{prefix} {message} [{line}, {col}]"
                if source:
                    text += f" ({source})"
                    
                diag_item = QTreeWidgetItem(file_item, [text])
                diag_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "diagnostic",
                    "path": file_path,
                    "line": line - 1,
                    "col": col - 1
                })

    @pyqtSlot(QTreeWidgetItem, int)
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        if data["type"] == "diagnostic":
            self.diagnostic_clicked.emit(data["path"], data["line"], data["col"])
        elif data["type"] == "file":
            self.diagnostic_clicked.emit(data["path"], 0, 0)
