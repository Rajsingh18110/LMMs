from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt

class GitHubAuthDialog(QDialog):
    def __init__(self, github_manager, parent=None):
        super().__init__(parent)
        self.github_manager = github_manager
        self.setWindowTitle("GitHub Authentication")
        self.setFixedSize(400, 150)
        self.setStyleSheet("""
            QDialog { background-color: #252526; color: #cccccc; }
            QLabel { color: #cccccc; }
            QLineEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #007acc;
                padding: 4px;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 2px;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        
        layout = QVBoxLayout(self)
        
        info = QLabel("Enter your GitHub Personal Access Token (PAT):")
        layout.addWidget(info)
        
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("ghp_...")
        layout.addWidget(self.token_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #555555;")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_login = QPushButton("Login")
        self.btn_login.clicked.connect(self._on_login)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)
        
    def _on_login(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Error", "Token cannot be empty.")
            return
            
        success = self.github_manager.authenticate(token)
        if success:
            QMessageBox.information(self, "Success", f"Logged in as {self.github_manager.get_username()}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to authenticate. Check token.")
