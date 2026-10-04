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
        """Generates a QSS string that overrides the default colors with the premium theme."""
        if not self.theme_data:
            return ""
            
        colors = self.theme_data.get("colors", {})
        
        # Color mappings
        base_bg = colors.get("editor.background", "#0A0910")
        panel_bg = colors.get("sideBar.background", "#12111A")
        elevated_bg = colors.get("editorWidget.background", "#1B1926")
        accent_color = colors.get("button.background", "#8B5CF6")
        accent_hover = colors.get("button.hoverBackground", "#7C3AED")
        text_primary = colors.get("editor.foreground", "#E2E8F0")
        text_secondary = colors.get("sideBar.foreground", "#94A3B8")
        border_color = colors.get("sideBar.border", "#2D2A3E")
        tab_active_bg = colors.get("tab.activeBackground", "#1B1926")
        tab_inactive_bg = colors.get("tab.inactiveBackground", base_bg)
        selection_bg = colors.get("list.activeSelectionBackground", "#8B5CF640")
        
        # Build the luxury override stylesheet
        overrides = f"""
        /* --- PREMIUM DYNAMIC THEME OVERRIDES --- */
        
        /* 1. Base Window & Floating Panels */
        QMainWindow {{ background-color: {base_bg}; }}
        #ContentArea {{ background-color: {base_bg}; }}
        
        /* Floating Dock Widget styling (gives a "floating" feel around panels) */
        QDockWidget > QWidget {{
            background-color: {panel_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            margin: 4px; /* Creates the floating gap */
        }}
        
        /* Sidebars & Explorer Tree */
        #Sidebar {{ background-color: transparent; border: none; }}
        QTreeView#explorerTree {{ background-color: transparent; border: none; }}
        QTreeView#explorerTree::item {{ padding: 4px; border-radius: 6px; margin: 2px 8px; }}
        QTreeView#explorerTree::item:hover {{ background-color: rgba(255, 255, 255, 0.06); }}
        QTreeView#explorerTree::item:selected {{ background-color: {selection_bg}; color: {text_primary}; }}
        
        /* 2. Pill-Shaped Tabs */
        QTabBar::tab {{
            background-color: {tab_inactive_bg};
            color: {text_secondary};
            padding: 8px 16px;
            margin: 4px 2px;
            border-radius: 10px;
            border: 1px solid transparent;
        }}
        QTabBar::tab:selected {{
            background-color: {tab_active_bg};
            color: {text_primary};
            border: 1px solid {border_color};
            border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #06B6D4);
        }}
        QTabBar::tab:hover:!selected {{
            background-color: rgba(255, 255, 255, 0.05);
        }}
        
        /* 3. Terminal & AI Chat Input */
        QTextEdit#chatInput {{
            background-color: {elevated_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 10px;
        }}
        QTextEdit#chatInput:focus {{
            border: 1px solid {accent_color};
            background-color: {panel_bg};
        }}
        
        QFrame#ChatInputFrame {{
            background-color: {elevated_bg};
            border: 1px solid {border_color};
            border-radius: 14px;
        }}
        QFrame#ChatInputFrame:focus-within {{
            border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #06B6D4);
        }}
        
        /* Buttons */
        QPushButton#PrimaryButton, QPushButton#sendBtn {{
            background-color: {accent_color};
            color: #ffffff;
            border-radius: 8px;
            padding: 6px 12px;
            border: none;
        }}
        QPushButton#PrimaryButton:hover, QPushButton#sendBtn:hover {{
            background-color: {accent_hover};
        }}
        
        /* Dock Title Bars */
        QDockWidget::title {{
            background: transparent;
            text-align: left;
            padding: 8px 14px;
            font-weight: bold;
            font-size: 12px;
            color: {text_primary};
        }}
        
        /* Custom Status Bar Pill */
        QWidget#CustomStatusBar {{
            background-color: {panel_bg};
            border-top: 1px solid {border_color};
            border-radius: 12px;
            margin: 4px;
        }}
        
        /* Chat Action Buttons */
        QPushButton#AgentModeToggle {{
            background: transparent; border: 1px solid transparent; color: {text_secondary}; font-size: 14px; border-radius: 4px;
        }}
        QPushButton#AgentModeToggle:checked {{
            background: {accent_color}40; color: {text_primary}; border: 1px solid {accent_color};
        }}
        QPushButton#AgentModeToggle:hover:!checked {{
            background: rgba(255, 255, 255, 0.1);
        }}
        
        QPushButton#attachBtn, QPushButton#micBtn {{
            background: transparent; border: none; color: {text_secondary}; font-size: 14px; border-radius: 4px;
        }}
        QPushButton#attachBtn:hover, QPushButton#micBtn:hover {{
            background: rgba(255, 255, 255, 0.1); color: {text_primary};
        }}
        
        QPushButton#sendBtn {{
            background: transparent; color: {text_primary}; border-radius: 4px; border: none; font-size: 14px;
        }}
        QPushButton#sendBtn:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}
        
        QPushButton#ChatTextLinkBtn {{
            background: transparent; color: {accent_color}; font-size: 11px; padding: 2px 4px; border: none; text-align: left;
        }}
        QPushButton#ChatTextLinkBtn:hover {{
            text-decoration: underline; color: {accent_hover};
        }}
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
