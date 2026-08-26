import os
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

class ExtensionSearchThread(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            url = f"https://open-vsx.org/api/-/search?query={self.query}&size=20"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.results_ready.emit(data.get("extensions", []))
        except Exception as e:
            self.error_occurred.emit(str(e))


class ExtensionsPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Extensions", parent)
        self.setObjectName("ExtensionsDock")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Extensions in Marketplace")
        self.search_input.returnPressed.connect(self.do_search)
        layout.addWidget(self.search_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #30363d; }
            QListWidget::item:selected { background-color: #2a2d2e; }
        """)
        layout.addWidget(self.list_widget)

        self.setWidget(container)
        
        # Load recommended by default
        self.do_search("python")

    def do_search(self, query=None):
        if not query:
            query = self.search_input.text().strip()
        if not query:
            return
            
        self.list_widget.clear()
        self.progress_bar.show()
        
        self.thread = ExtensionSearchThread(query)
        self.thread.results_ready.connect(self.on_results)
        self.thread.error_occurred.connect(self.on_error)
        self.thread.start()

    def on_results(self, extensions):
        self.progress_bar.hide()
        self.list_widget.clear()
        
        for ext in extensions:
            name = ext.get("displayName") or ext.get("name")
            publisher = ext.get("namespace")
            description = ext.get("description", "")[:60] + "..."
            download_url = ext.get("files", {}).get("download")
            version = ext.get("version")
            
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            header_layout = QHBoxLayout()
            title = QLabel(f"<b>{name}</b>")
            title.setStyleSheet("color: #e6edf3; font-size: 13px;")
            
            btn_install = QPushButton("Install")
            btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_install.setStyleSheet("""
                QPushButton { background-color: #0e639c; color: white; border-radius: 3px; padding: 4px 10px; font-weight: bold; }
                QPushButton:hover { background-color: #1177bb; }
            """)
            btn_install.clicked.connect(lambda checked, url=download_url, pid=f"{publisher}.{ext.get('name')}": self.install_extension(pid, url))
            
            header_layout.addWidget(title)
            header_layout.addStretch()
            header_layout.addWidget(btn_install)
            
            desc = QLabel(description)
            desc.setStyleSheet("color: #8b949e; font-size: 11px;")
            desc.setWordWrap(True)
            
            pub = QLabel(f"{publisher} • v{version}")
            pub.setStyleSheet("color: #8b949e; font-size: 10px;")
            
            item_layout.addLayout(header_layout)
            item_layout.addWidget(desc)
            item_layout.addWidget(pub)
            
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

    def on_error(self, error):
        self.progress_bar.hide()
        QMessageBox.warning(self, "Search Error", f"Failed to fetch extensions:\n{error}")

    def install_extension(self, extension_id, download_url):
        # We will send a QWebChannel message to the JS frontend
        # The JS frontend will use the `extensions-service-override` to install it.
        # For now, we print and notify.
        print(f"Installing {extension_id} from {download_url}")
        
        # We need a reference to the main window's bridge.
        main_win = self.parent().parent() # QDockWidget -> QMainWindow -> MainWindow(maybe?)
        if hasattr(main_win, 'editor_manager'):
            # This logic will be wired during Task 3 when the bridge is extended
            pass
