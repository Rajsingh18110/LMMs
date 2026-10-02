import os
import re
import json

class ThemeManager:
    def __init__(self, theme_json_path=None):
        self.theme_data = {}
        if theme_json_path and os.path.exists(theme_json_path):
            self.load_theme(theme_json_path)
            
    def load_theme(self, theme_json_path):
        try:
            with open(theme_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove block comments /* */
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove inline comments // (only at the beginning of lines to avoid URLs)
            content = re.sub(r'(?m)^\s*//.*$', '', content)
            # Remove trailing commas (simple fix for common JSON errors)
            content = re.sub(r',\s*\}', '}', content)
            content = re.sub(r',\s*\]', ']', content)
            self.theme_data = json.loads(content)
            return True
        except Exception as e:
            print(f"Theme Manager: Failed to parse {theme_json_path}: {e}")
            self.theme_data = {}
            return False

    def generate_qss_overrides(self):
        """Generates a QSS string that overrides the default colors with the theme colors."""
        if not self.theme_data:
            return ""
            
        colors = self.theme_data.get("colors", {})
        
        # VS Code color keys to QSS mappings
        editor_bg = colors.get("editor.background", "#1e1e1e")
        sidebar_bg = colors.get("sideBar.background", "#181818")
        accent_color = colors.get("button.background", "#1f6feb")
        text_primary = colors.get("editor.foreground", "#e5e7eb")
        text_secondary = colors.get("sideBar.foreground", "#8b949e")
        border_color = colors.get("sideBar.border", colors.get("panel.border", "#30363d"))
        tab_active_bg = colors.get("tab.activeBackground", editor_bg)
        tab_inactive_bg = colors.get("tab.inactiveBackground", "#2d2d2d")
        
        # Build the override stylesheet
        overrides = f"""
        /* --- DYNAMIC THEME OVERRIDES --- */
        QMainWindow {{ background-color: {editor_bg}; }}
        #Sidebar {{ background-color: {sidebar_bg}; border-right: 1px solid {border_color}; }}
        #ContentArea {{ background-color: {editor_bg}; }}
        
        QTabBar::tab {{ background-color: {tab_inactive_bg}; color: {text_secondary}; }}
        QTabBar::tab:selected {{ background-color: {tab_active_bg}; color: {text_primary}; border-top: 1px solid {accent_color}; }}
        
        QTreeView#explorerTree {{ background-color: {sidebar_bg}; }}
        QDockWidget::title {{ background: {sidebar_bg}; border-bottom: 1px solid {border_color}; }}
        QTextEdit#chatInput {{ background-color: {editor_bg}; border: 1px solid {border_color}; }}
        
        QPushButton#PrimaryButton {{ background-color: {accent_color}; border: 1px solid {accent_color}; }}
        QPushButton#sendBtn {{ background-color: {accent_color}; }}
        """
        return overrides

    def get_monaco_theme_json(self):
        """Returns the JSON string required to register the theme in Monaco Editor."""
        if not self.theme_data:
            return None
            
        # Monaco needs 'base', 'inherit', 'rules' (from tokenColors), and 'colors'
        monaco_theme = {
            "base": "vs-dark", # Default fallback
            "inherit": True,
            "rules": [],
            "colors": self.theme_data.get("colors", {})
        }
        
        token_colors = self.theme_data.get("tokenColors", [])
        for token in token_colors:
            scope = token.get("scope", [])
            settings = token.get("settings", {})
            
            if isinstance(scope, str):
                scope = [scope]
                
            for s in scope:
                rule = {"token": s}
                if "foreground" in settings:
                    rule["foreground"] = settings["foreground"].replace("#", "")
                if "background" in settings:
                    rule["background"] = settings["background"].replace("#", "")
                if "fontStyle" in settings:
                    rule["fontStyle"] = settings["fontStyle"]
                
                monaco_theme["rules"].append(rule)
                
        return json.dumps(monaco_theme)
