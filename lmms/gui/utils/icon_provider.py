import os
from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo

class CustomIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.icon_cache = {}
        # Use the newly generated PNG icons directory
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "material_icons")

    def icon(self, icon_type_or_info):
        if isinstance(icon_type_or_info, QFileInfo):
            info = icon_type_or_info
            if info.isDir():
                name = info.fileName().lower()
                if name == "src" or name == "source":
                    return self.get_icon("folder_src.png")
                return self.get_icon("folder_closed.png")
            else:
                ext = info.suffix().lower()
                name = info.fileName().lower()
                
                # Exact file name matches
                if name == ".gitignore":
                    return self.get_icon("file_git.png")
                if "dockerfile" in name or name == ".dockerignore":
                    return self.get_icon("file_docker.png")
                if name == "package.json" or name == "package-lock.json":
                    return self.get_icon("file_npm.png")
                
                # Extension matches
                ext_map = {
                    "py": "file_python", "pyc": "file_python",
                    "js": "file_javascript", "mjs": "file_javascript", "cjs": "file_javascript",
                    "ts": "file_typescript",
                    "jsx": "file_react", "tsx": "file_react_ts",
                    "html": "file_html", "htm": "file_html",
                    "css": "file_css", "scss": "file_css", "sass": "file_css", "less": "file_css",
                    "json": "file_json", "jsonc": "file_json",
                    "md": "file_markdown", "mdx": "file_markdown",
                    "sh": "file_console", "bash": "file_console", "zsh": "file_console", "bat": "file_console", "cmd": "file_console",
                    "txt": "file_document", "log": "file_document", "csv": "file_document",
                    "cpp": "file_cpp", "cc": "file_cpp", "cxx": "file_cpp",
                    "c": "file_c",
                    "h": "file_h", "hpp": "file_h",
                    "java": "file_java", "class": "file_java", "jar": "file_java",
                    "xml": "file_xml", "svg": "file_svg",
                    "yml": "file_yaml", "yaml": "file_yaml", "toml": "file_yaml", "ini": "file_yaml", "cfg": "file_yaml", "conf": "file_yaml", "env": "file_yaml",
                    "png": "file_image", "jpg": "file_image", "jpeg": "file_image", "gif": "file_image", "webp": "file_image", "ico": "file_image",
                    "zip": "file_zip", "tar": "file_zip", "gz": "file_zip", "rar": "file_zip", "7z": "file_zip",
                    "sql": "file_database", "db": "file_database", "sqlite": "file_database", "sqlite3": "file_database",
                    "rs": "file_rust",
                    "go": "file_go",
                    "rb": "file_ruby",
                    "php": "file_php",
                    "vue": "file_vue"
                }
                
                if ext in ext_map:
                    return self.get_icon(ext_map[ext] + ".png")
                return self.get_icon("file_document.png")
                
        return super().icon(icon_type_or_info)

    def get_icon(self, icon_name):
        if icon_name in self.icon_cache:
            return self.icon_cache[icon_name]
        
        path = os.path.join(self.assets_dir, icon_name).replace("\\", "/")
        if os.path.exists(path):
            icon = QIcon(path)
        else:
            icon = QIcon() # empty fallback
            
        self.icon_cache[icon_name] = icon
        return icon
