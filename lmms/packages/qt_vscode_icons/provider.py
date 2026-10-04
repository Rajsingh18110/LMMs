import json
import os
from pathlib import Path
try:
    from PyQt6.QtWidgets import QFileIconProvider
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import QFileInfo
except ImportError:
    try:
        from PySide6.QtWidgets import QFileIconProvider
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QFileInfo
    except ImportError:
        raise ImportError("Either PyQt6 or PySide6 must be installed to use qt-vscode-icons.")

from .downloader import get_assets_dir, download_and_extract_icons

class VscodeIconProvider(QFileIconProvider):
    def __init__(self, fallback_to_native=True):
        super().__init__()
        self.fallback_to_native = fallback_to_native
        self.assets_dir = get_assets_dir()
        self.icons_dir = self.assets_dir / "icons"
        self.json_path = self.assets_dir / "material-icons.json"
        
        # Ensure icons are downloaded
        if not self.icons_dir.exists() or not self.json_path.exists():
            print("VS Code icons not found locally. Triggering download...")
            download_and_extract_icons()
            
        self.mapping = {}
        self.file_names = {}
        self.language_ids = {}
        self.icon_cache = {}
        
        self.load_mapping()
        
    def load_mapping(self):
        if not self.json_path.exists():
            return
            
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # The VS Code icon theme JSON has:
        # fileExtensions: { "ext": "icon_name" }
        # fileNames: { "filename.ext": "icon_name" }
        # languageIds: { "lang": "icon_name" }
        # The actual SVG is usually icon_name.svg
        
        self.mapping = data.get("fileExtensions", {})
        self.file_names = data.get("fileNames", {})
        self.language_ids = data.get("languageIds", {})
        
    def icon(self, icon_type_or_info):
        # Handle QFileInfo
        if isinstance(icon_type_or_info, QFileInfo):
            file_info = icon_type_or_info
            
            if file_info.isDir():
                return self.get_icon("folder.svg")
                
            filename = file_info.fileName()
            
            # Check direct file name match first (e.g. dockerfile, package.json)
            if filename in self.file_names:
                return self.get_icon(self.file_names[filename] + ".svg")
                
            # Then extension match
            # VS Code supports multi-dot extensions (e.g. d.ts). We should check longest suffix first.
            parts = filename.split('.')
            if len(parts) > 1:
                # check full extension
                for i in range(1, len(parts)):
                    ext = ".".join(parts[i:])
                    if ext in self.mapping:
                        return self.get_icon(self.mapping[ext] + ".svg")
                        
            # Generic fallback
            return self.get_icon("document.svg")
            
        # Handle QFileIconProvider.IconType enum
        if self.fallback_to_native:
            return super().icon(icon_type_or_info)
        return QIcon()

    def get_icon(self, icon_file_name):
        if icon_file_name in self.icon_cache:
            return self.icon_cache[icon_file_name]
            
        path = str(self.icons_dir / icon_file_name)
        if os.path.exists(path):
            icon = QIcon(path)
            self.icon_cache[icon_file_name] = icon
            return icon
            
        # If not found, return empty or fallback to document
        if icon_file_name != "document.svg":
            return self.get_icon("document.svg")
            
        return QIcon()
