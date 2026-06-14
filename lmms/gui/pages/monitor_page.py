from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Monitor Page")
        layout.addWidget(label)
