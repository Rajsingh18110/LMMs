"""
PyQt6 Compatibility Layer for NodeGraphQt.
Enables NodeGraphQt (which relies on Qt.py and Qt5/PySide2-era scoped enums) to run
flawlessly on pure PyQt6 without importing PySide or PyQt5, and without editing site-packages.
"""

from __future__ import annotations

import os
import sys
import types
import enum

# Enforce PyQt6 binding for Qt.py
os.environ["QT_PREFERRED_BINDING"] = "PyQt6"

import PyQt6
from PyQt6 import QtCore, QtGui, QtWidgets


def _promote_enums_from_package(pkg: object) -> None:
    """Promote scoped Qt6 enums onto their parent classes for Qt5 backwards compatibility."""
    for class_name in dir(pkg):
        if class_name.startswith("_"):
            continue
        try:
            cls = getattr(pkg, class_name)
            if isinstance(cls, type):
                for name in dir(cls):
                    if name.startswith("_"):
                        continue
                    try:
                        val = getattr(cls, name)
                        if isinstance(val, type) and issubclass(val, enum.Enum):
                            if hasattr(val, "_member_map_"):
                                for m_name, m_val in val._member_map_.items():
                                    if not hasattr(cls, m_name):
                                        setattr(cls, m_name, m_val)
                    except Exception:
                        pass
        except Exception:
            pass


# Promote enums across all core Qt packages
_promote_enums_from_package(QtCore)
_promote_enums_from_package(QtGui)
_promote_enums_from_package(QtWidgets)

# Promote enums on QtCore.Qt itself
for name in dir(QtCore.Qt):
    if name.startswith("_"):
        continue
    try:
        val = getattr(QtCore.Qt, name)
        if isinstance(val, type) and issubclass(val, enum.Enum):
            if hasattr(val, "_member_map_"):
                for m_name, m_val in val._member_map_.items():
                    if not hasattr(QtCore.Qt, m_name):
                        setattr(QtCore.Qt, m_name, m_val)
    except Exception:
        pass

# Ensure QtSvg shim exists if system lacks python3-pyqt6.qtsvg
if not hasattr(PyQt6, "QtSvg"):
    class _DummySvgRenderer:
        def __init__(self, *args, **kwargs):
            pass
        def isValid(self):
            return False
        def render(self, *args, **kwargs):
            pass
        def defaultSize(self):
            return QtCore.QSize(32, 32)

    _qtsvg_mod = types.ModuleType("PyQt6.QtSvg")
    _qtsvg_mod.QSvgRenderer = _DummySvgRenderer  # type: ignore[attr-defined]
    sys.modules["PyQt6.QtSvg"] = _qtsvg_mod
    setattr(PyQt6, "QtSvg", _qtsvg_mod)

# Ensure Qt.py picks up the safe PyQt6 environment
import Qt
if not hasattr(Qt, "QtSvg"):
    setattr(Qt, "QtSvg", getattr(PyQt6, "QtSvg"))
    sys.modules["Qt.QtSvg"] = getattr(PyQt6, "QtSvg")

# Now safe to import NodeGraphQt
import NodeGraphQt
from NodeGraphQt.widgets.scene import NodeScene

# PyQt6 strictly requires integer width for QPen.setWidth
def _safe_draw_dots(self, painter, rect, pen, grid_size):
    zoom = self.viewer().get_zoom()
    if zoom < 0:
        grid_size = int(abs(zoom) / 0.3 + 1) * grid_size

    left = int(rect.left())
    right = int(rect.right())
    top = int(rect.top())
    bottom = int(rect.bottom())

    first_left = left - (left % grid_size)
    first_top = top - (top % grid_size)

    pen.setWidth(max(1, grid_size // 10))
    painter.setPen(pen)

    for x in range(first_left, right, grid_size):
        for y in range(first_top, bottom, grid_size):
            painter.drawPoint(x, y)

NodeScene._draw_dots = _safe_draw_dots

__all__ = ["NodeGraphQt"]
