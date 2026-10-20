"""
lmms.gui.qt - Unified Qt module wrapper.
Consolidates all PyQt6 widget, core, and gui types through a single import facade.
Strictly PyQt6; zero PySide6 dependencies.
"""

from __future__ import annotations

# Core
from PyQt6.QtCore import (
    QDir,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)

import PyQt6.QtCore as _QtCore
pyqtProperty: Any = getattr(_QtCore, "pyqtProperty", property)


# GUI & Graphics
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

# Widgets
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import asyncio
from typing import Any, Coroutine

def run_coro_safe(coro: Coroutine[Any, Any, Any]) -> Any:
    """Safely runs or schedules a coroutine whether an event loop is active or not."""
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        return asyncio.run(coro)
