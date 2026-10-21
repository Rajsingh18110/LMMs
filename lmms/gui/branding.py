"""
lmms.gui.branding - Centralized Design Tokens & Visual Assets.
Provides brand colors, theme tokens, node category palettes, and code-drawn vector logo marks.
Strictly zero hardcoded colors across the automation studio.
"""

from __future__ import annotations

from typing import Dict, Any
from lmms.gui.qt import QColor, QIcon, QPixmap, QPainter, QPainterPath, QPen, QBrush, Qt


class AutomationBranding:
    APP_NAME = "LMMs Automation"
    STUDIO_TITLE = "Automation Studio"
    STUDIO_SUBTITLE = "Visual workflow orchestrator & node-based automation engine"

    # Brand Core Accents
    ACCENT_PURPLE = "#7c3aed"     # n8n-style node accent / glow
    ACCENT_ORANGE = "#f97316"     # Primary action / Open chat button
    ACCENT_BLUE = "#3b82f6"       # Active state / connection pipe
    COLOR_SUCCESS = "#10b981"     # Successful node status
    COLOR_ERROR = "#ef4444"       # Failed node status / warning badge
    COLOR_WARNING = "#f59e0b"     # Warning badge
    COLOR_IDLE = "#71717a"        # Idle node ring
    COLOR_RUNNING = "#60a5fa"     # Running node pulse

    # Node Category Palette
    CATEGORY_COLORS: Dict[str, str] = {
        "trigger": "#f97316",      # Vibrant orange
        "model": "#8b5cf6",        # AI Purple
        "action": "#3b82f6",       # Tool blue
        "logic": "#06b6d4",        # Logic cyan
        "output": "#10b981",       # Success green
        "integration": "#ec4899",  # Integration pink
        "utility": "#a855f7",      # Utility violet
        "custom": "#64748b",       # Custom slate
    }

    # Theme Token Tables
    THEMES: Dict[str, Dict[str, str]] = {
        "dark": {
            "canvas_bg": "#121214",
            "canvas_dot": "#2a2b30",
            "card_bg": "#1e1f26",
            "card_bg_selected": "#282a36",
            "card_border": "#2f313d",
            "card_border_selected": "#8b5cf6",
            "header_bg": "#16171d",
            "drawer_bg": "#181920",
            "text_primary": "#f4f4f5",
            "text_secondary": "#9ca3af",
            "text_muted": "#6b7280",
            "pipe_color": "#4b5563",
            "pipe_active": "#818cf8",
            "button_bg": "#27272a",
            "button_hover": "#3f3f46",
        },
        "light": {
            "canvas_bg": "#f8fafc",
            "canvas_dot": "#cbd5e1",
            "card_bg": "#ffffff",
            "card_bg_selected": "#f1f5f9",
            "card_border": "#e2e8f0",
            "card_border_selected": "#7c3aed",
            "header_bg": "#ffffff",
            "drawer_bg": "#ffffff",
            "text_primary": "#0f172a",
            "text_secondary": "#475569",
            "text_muted": "#94a3b8",
            "pipe_color": "#94a3b8",
            "pipe_active": "#7c3aed",
            "button_bg": "#f1f5f9",
            "button_hover": "#e2e8f0",
        },
    }

    @classmethod
    def get_token(cls, key: str, theme: str = "dark") -> str:
        tokens = cls.THEMES.get(theme, cls.THEMES["dark"])
        return tokens.get(key, "#ffffff")

    @classmethod
    def get_category_color(cls, category: str) -> str:
        return cls.CATEGORY_COLORS.get(category.lower(), cls.CATEGORY_COLORS["custom"])

    @classmethod
    def get_logo_pixmap(cls, size: int = 32) -> QPixmap:
        """Draws a crisp modern vector automation workflow logo entirely in Qt code."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw hexagon / node badge
        margin = size * 0.08
        rect = pixmap.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))

        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), 6.0, 6.0)

        # Gradient fill
        gradient_brush = QBrush(QColor(cls.ACCENT_PURPLE))
        painter.fillPath(path, gradient_brush)

        # Draw connecting nodes inside badge
        pen = QPen(QColor("#ffffff"), max(2.0, size * 0.08))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Node points
        cx, cy = size / 2.0, size / 2.0
        p1 = (cx - size * 0.22, cy - size * 0.15)
        p2 = (cx + size * 0.22, cy - size * 0.15)
        p3 = (cx, cy + size * 0.22)

        # Lines connecting nodes
        painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
        painter.drawLine(int(p2[0]), int(p2[1]), int(p3[0]), int(p3[1]))

        # Node circles
        painter.setBrush(QBrush(QColor("#ffffff")))
        r = max(2.5, size * 0.1)
        for px, py in (p1, p2, p3):
            painter.drawEllipse(int(px - r), int(py - r), int(r * 2), int(r * 2))

        painter.end()
        return pixmap

    @classmethod
    def get_logo_icon(cls, size: int = 32) -> QIcon:
        return QIcon(cls.get_logo_pixmap(size))
