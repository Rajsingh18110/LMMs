import os
from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QFileInfo

class CustomIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.icon_cache = {}

    def icon(self, icon_type_or_info):
        if isinstance(icon_type_or_info, QFileInfo):
            info = icon_type_or_info
            if info.isDir():
                return self.get_or_create_icon("folder", "#dcb67a") # Yellow-ish folder
            else:
                ext = info.suffix().lower()
                if ext == "py":
                    return self.get_or_create_icon("py", "#3572A5") # Python blue
                elif ext == "md":
                    return self.get_or_create_icon("md", "#ffffff") # Markdown white
                elif ext == "json":
                    return self.get_or_create_icon("{}", "#cb9053") # JSON orange
                elif ext in ["js", "jsx", "ts", "tsx"]:
                    return self.get_or_create_icon("js", "#f1e05a") # JS yellow
                elif ext in ["html", "htm"]:
                    return self.get_or_create_icon("<>", "#e34c26") # HTML orange
                elif ext == "css":
                    return self.get_or_create_icon("#", "#563d7c") # CSS purple
                else:
                    return self.get_or_create_icon("txt", "#8b949e") # Default text color
        return super().icon(icon_type_or_info)

    def get_or_create_icon(self, text, color_hex):
        key = f"{text}_{color_hex}"
        if key in self.icon_cache:
            return self.icon_cache[key]
        
        # Generate an icon dynamically
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if text == "folder":
            # Draw a simple folder
            painter.setBrush(QColor(color_hex))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 8, 28, 20, 2, 2)
            painter.drawRoundedRect(2, 4, 12, 6, 2, 2)
        else:
            # Draw text-based icon for files
            painter.setPen(QColor(color_hex))
            font = QFont("Consolas", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            
        painter.end()
        
        icon = QIcon(pixmap)
        self.icon_cache[key] = icon
        return icon
