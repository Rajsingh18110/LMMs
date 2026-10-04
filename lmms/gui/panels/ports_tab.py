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
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.toolbar.addWidget(self.refresh_btn)
        self.toolbar.addStretch()
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Port", "Process", "PID"])
        
        self.layout.addLayout(self.toolbar)
        self.layout.addWidget(self.tree)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_ports)
        self.timer.start(5000) # Auto refresh every 5 seconds
        
        self.refresh_ports()
        
    def refresh_ports(self):
        self.tree.clear()
        
        try:
            conns = psutil.net_connections(kind='inet')
            seen_ports = set()
            for c in conns:
                if c.status == 'LISTEN' and c.pid:
                    port = c.laddr.port
                    if port in seen_ports:
                        continue
                    seen_ports.add(port)
                    try:
                        p = psutil.Process(c.pid)
                        name = p.name()
                        item = QTreeWidgetItem([str(port), name, str(c.pid)])
                        self.tree.addTopLevelItem(item)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception:
            pass
