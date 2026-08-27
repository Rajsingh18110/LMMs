import psutil
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

class PortsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.toolbar.addWidget(self.refresh_btn)
        self.toolbar.addStretch()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Port", "Process", "PID"])
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #1e1e1e; color: #c9d1d9; border: none; font-size: 12px; }
            QHeaderView::section { background-color: #161b22; color: #8b949e; border: none; border-bottom: 1px solid #30363d; padding: 4px; }
        """)
        
        self.layout.addLayout(self.toolbar)
        self.layout.addWidget(self.tree)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_ports)
        self.timer.start(5000) # Auto refresh every 5 seconds
        
        self.refresh_ports()
        
    def refresh_ports(self):
        self.tree.clear()
        
        current_pid = os.getpid()
        try:
            current_proc = psutil.Process(current_pid)
            children = current_proc.children(recursive=True)
            procs_to_check = [current_proc] + children
            
            for p in procs_to_check:
                try:
                    conns = p.connections(kind='inet')
                    for c in conns:
                        if c.status == 'LISTEN':
                            port = c.laddr.port
                            name = p.name()
                            pid = p.pid
                            
                            item = QTreeWidgetItem([str(port), name, str(pid)])
                            self.tree.addTopLevelItem(item)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
