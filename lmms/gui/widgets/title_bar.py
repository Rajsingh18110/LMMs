import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter

class CustomTitleBar(QWidget):
    def __init__(self, main_window, menu_bar=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.menu_bar = menu_bar
        self.setFixedHeight(35)
        # Apply style via objectName in dark.qss to prevent QSS cascade breakage
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("CustomTitleBar")
        self._is_dragging = False
        self._drag_start_pos = None

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(5)

        # Left: App Icon (optional) and MenuBar
        if self.menu_bar:
            layout.addWidget(self.menu_bar)

        # Center: Title
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Custom Logo
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "lmms_logo_transparent.png")
        if os.path.exists(logo_path):
            self.title_logo = QLabel()
            logo_pixmap = QPixmap(logo_path).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.title_logo.setPixmap(logo_pixmap)
            layout.addWidget(self.title_logo)
        
        self.title_label = QLabel("Large Model Machine Studio")
        font = QFont()
        font.setPixelSize(13)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Toggle Left Panel Button
        self.btn_toggle_left = QPushButton("◧")
        self.btn_toggle_left.setObjectName("toggleBtn")
        self.btn_toggle_left.setToolTip("Toggle Left Panel")
        layout.addWidget(self.btn_toggle_left)

        # Toggle Right Panel Button
        self.btn_toggle_right = QPushButton("◨")
        self.btn_toggle_right.setObjectName("toggleBtn")
        self.btn_toggle_right.setToolTip("Toggle Right Panel")
        layout.addWidget(self.btn_toggle_right)
        
        # Window Controls
        self.btn_minimize = QPushButton("—")
        self.btn_minimize.setObjectName("minimizeBtn")
        self.btn_minimize.clicked.connect(self.main_window.showMinimized)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("🗖")
        self.btn_maximize.setObjectName("maximizeBtn")
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("closeBtn")
        self.btn_close.clicked.connect(self.main_window.close)
        
        # Override right margin to 0 for window controls
        layout.setContentsMargins(10, 0, 0, 0)
        layout.addWidget(self.btn_close)

    def toggle_maximize(self):
        if self.main_window.isMaximized():
            self.main_window.showNormal()
            self.btn_maximize.setText("🗖")
        else:
            self.main_window.showMaximized()
            self.btn_maximize.setText("🗗")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.main_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.main_window.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

class ChatDockTitleBar(QWidget):
    def __init__(self, dock, chat_page, parent=None):
        super().__init__(parent)
        self.dock = dock
        self.chat_page = chat_page
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(5)
        
        self.title_label = QLabel("AI Chat")
        self.title_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 11px; text-transform: uppercase;")
        
        self.btn_new = QPushButton("+")
        self.btn_new.setToolTip("New Chat")
        self.btn_new.clicked.connect(self.chat_page.start_new_chat)
        
        self.btn_history = QPushButton("↺")
        self.btn_history.setToolTip("History")
        
        self.btn_more = QPushButton("...")
        self.btn_more.setToolTip("More Actions")
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close Panel")
        self.btn_close.clicked.connect(self.dock.close)
        
        for btn in [self.btn_new, self.btn_history, self.btn_more, self.btn_close]:
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #c9d1d9;
                    border-radius: 4px;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #30363d;
                    color: #c9d1d9;
                }
            """)
            
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_new)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_more)
        layout.addWidget(self.btn_close)
