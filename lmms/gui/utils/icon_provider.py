import os
from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QFileInfo

class CustomIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.icon_cache = {}
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

    def icon(self, icon_type_or_info):
        if isinstance(icon_type_or_info, QFileInfo):
            info = icon_type_or_info
            if info.isDir():
                return self.get_icon_from_svg("folder_closed.svg")
            else:
                ext = info.suffix().lower()
                if ext == "py":
                    return self.get_icon_from_svg("file_python.svg")
                elif ext == "md":
                    return self.get_icon_from_svg("file_markdown.svg")
                elif ext == "json":
                    return self.get_icon_from_svg("file_json.svg")
                else:
                    return self.get_icon_from_svg("file_default.svg")
        return super().icon(icon_type_or_info)

    def get_icon_from_svg(self, svg_name):
        if svg_name in self.icon_cache:
            return self.icon_cache[svg_name]
        
        path = os.path.join(self.assets_dir, svg_name).replace("\\", "/")
        if os.path.exists(path):
            icon = QIcon(path)
        else:
            icon = QIcon() # empty fallback
            
        self.icon_cache[svg_name] = icon
        return icon
