from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from lmms.extensions.models import ExtensionRecord

class ExtensionPermissionsDialog(QDialog):
    """
    Dialog asking the user to grant permissions to an extension
    before it is activated.
    """
    def __init__(self, record: ExtensionRecord, parent=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle("Extension Permissions")
        self.setFixedSize(450, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
                color: #cccccc;
            }
            QLabel {
                font-size: 13px;
                color: #cccccc;
            }
            QCheckBox {
                font-size: 13px;
                color: #e6edf3;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton#primaryBtn {
                background-color: #0e639c;
                color: white;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1177bb;
            }
        """)
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        hdr = QLabel(f"<b>{self.record.display_name}</b> wants to activate.")
        hdr.setStyleSheet("font-size: 15px; color: #e6edf3;")
        layout.addWidget(hdr)
        
        desc = QLabel("This extension requires the following capabilities:")
        desc.setStyleSheet("color: #8b949e;")
        layout.addWidget(desc)
        
        # Permissions List
        frame = QFrame()
        frame.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 4px;")
        flayout = QVBoxLayout(frame)
        flayout.setContentsMargins(15, 15, 15, 15)
        flayout.setSpacing(10)
        
        self.chk_fs = QCheckBox("Read and write workspace files")
        self.chk_fs.setChecked(True)
        flayout.addWidget(self.chk_fs)
        
        self.chk_term = QCheckBox("Execute terminal commands")
        self.chk_term.setChecked(True)
        flayout.addWidget(self.chk_term)
        
        self.chk_net = QCheckBox("Access the network (telemetry/APIs)")
        self.chk_net.setChecked(True)
        flayout.addWidget(self.chk_net)
        
        layout.addWidget(frame)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_allow = QPushButton("Allow and Activate")
        btn_allow.setObjectName("primaryBtn")
        btn_allow.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_allow.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_allow)
        
        layout.addLayout(btn_layout)

    def get_granted_permissions(self) -> dict[str, bool]:
        """Returns a dict of granted capabilities."""
        return {
            "fs": self.chk_fs.isChecked(),
            "terminal": self.chk_term.isChecked(),
            "network": self.chk_net.isChecked()
        }
