import re

with open("lmms/gui/core/main_window.py", "r") as f:
    content = f.read()

icon_func = """
        def get_symbol_icon(kind):
            from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
            from PyQt6.QtCore import Qt
            
            # Map kind to (character, color)
            mapping = {
                1: ('F', '#cccccc'), 2: ('{}', '#cccccc'), 3: ('{}', '#cccccc'), 4: ('P', '#cccccc'),
                5: ('C', '#007acc'), 6: ('M', '#b180d7'), 7: ('P', '#cccccc'), 8: ('f', '#007acc'),
                9: ('C', '#b180d7'), 10: ('E', '#ee9d28'), 11: ('I', '#007acc'), 12: ('f', '#b180d7'),
                13: ('v', '#007acc'), 14: ('c', '#cccccc'), 22: ('e', '#ee9d28'), 23: ('S', '#cccccc'),
                24: ('E', '#ee9d28')
            }
            char, color = mapping.get(kind, ('?', '#cccccc'))
            
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw a subtle background for the icon
            painter.setPen(Qt.PenStyle.NoPen)
            # painter.setBrush(QColor(color).darker(150))
            # painter.drawRoundedRect(0, 0, 16, 16, 3, 3)
            
            painter.setPen(QColor(color))
            font = QFont("Arial", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(0, 0, 16, 16, Qt.AlignmentFlag.AlignCenter, char)
            painter.end()
            
            return QIcon(pixmap)

        try:
"""

new_add_symbols = """
            def add_symbols(parent_item, syms):
                for s in syms:
                    name = s.get("name", "Unknown")
                    kind = s.get("kind", 0)
                    
                    # Filter out spammy module-level variables (like 'sys', 'os' imports) in Python
                    if kind == 13 and not s.get("children") and name in ("sys", "os", "json", "urllib", "typing", "subprocess"):
                        continue
                    
                    item = QStandardItem(name)
                    item.setToolTip(s.get("detail", ""))
                    item.setIcon(get_symbol_icon(kind))
"""

content = content.replace("        try:", icon_func)
content = re.sub(r"            def add_symbols\(parent_item, syms\):[\s\S]*?item = QStandardItem\(name\)\n                    item.setToolTip\(s.get\(\"detail\", \"\"\)\)", new_add_symbols.strip(), content)

with open("lmms/gui/core/main_window.py", "w") as f:
    f.write(content)

print("Done")
