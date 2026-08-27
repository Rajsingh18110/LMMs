from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPlainTextEdit, QLabel
from PyQt6.QtCore import pyqtSlot
from lmms.gui.utils.output_channel import OutputChannelRegistry

class OutputTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Toolbar
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(0, 0, 0, 5)
        
        self.channel_combo = QComboBox()
        self.channel_combo.setMinimumWidth(150)
        self.channel_combo.currentIndexChanged.connect(self.on_channel_changed)
        
        self.toolbar.addWidget(QLabel("Tasks")) # VS Code style label
        self.toolbar.addStretch()
        self.toolbar.addWidget(self.channel_combo)
        
        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background-color: #1e1e1e; color: #c9d1d9; border: none; font-family: monospace;")
        
        self.layout.addLayout(self.toolbar)
        self.layout.addWidget(self.text_area)
        
        # Initial wireup
        self.registry = OutputChannelRegistry.get_instance()
        self.registry.message_appended.connect(self.on_message_appended)
        
        self._populate_combo()
        
    def _populate_combo(self):
        current_text = self.channel_combo.currentText()
        self.channel_combo.clear()
        channels = self.registry.get_channels()
        for ch in channels:
            self.channel_combo.addItem(ch)
        
        if current_text in channels:
            self.channel_combo.setCurrentText(current_text)
        elif channels:
            self.channel_combo.setCurrentIndex(0)
            
    @pyqtSlot(str, str)
    def on_message_appended(self, channel_name: str, message: str):
        # If new channel appeared, repopulate combo
        if self.channel_combo.findText(channel_name) == -1:
            self.channel_combo.addItem(channel_name)
            if self.channel_combo.count() == 1:
                self.channel_combo.setCurrentIndex(0)
                
        # If this is the currently selected channel, append to text area
        if self.channel_combo.currentText() == channel_name:
            self.text_area.appendPlainText(message)
            
    @pyqtSlot(int)
    def on_channel_changed(self, index: int):
        if index >= 0:
            channel_name = self.channel_combo.itemText(index)
            content = self.registry.get_channel_content(channel_name)
            self.text_area.setPlainText(content)
            # Scroll to bottom
            scrollbar = self.text_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
