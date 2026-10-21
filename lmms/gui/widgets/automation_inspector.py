"""
lmms.gui.widgets.automation_inspector - Node Inspector Panel.
Provides an n8n-style parameter configuration form, single-step execution testing,
and live JSON input/output data viewer for the selected canvas node.
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

from lmms.gui.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    Qt,
    QColor,
    QCursor,
    pyqtSignal,
    QApplication,
)
from lmms.gui.branding import AutomationBranding


class AutomationInspector(QWidget):
    """
    Right-side Node Inspector panel.
    Opens when a node is selected or double-clicked on the canvas.
    """
    closed = pyqtSignal()
    step_executed = pyqtSignal(object)
    node_deleted = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationInspector")
        self.setFixedWidth(360)
        self.setStyleSheet("""
            QWidget#AutomationInspector {
                background-color: #16171d;
                border-left: 1px solid #282a35;
            }
        """)

        self.current_node = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 14)
        main_layout.setSpacing(12)

        # 1. Header: Icon, Name, Category chip, Close
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_icon = QLabel("⚡")
        self.lbl_icon.setStyleSheet("font-size: 18px; background: transparent;")

        self.name_edit = QLineEdit("Node")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: #1f2029;
                border: 1px solid #323544;
                border-radius: 6px;
                color: #f4f4f5;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #8b5cf6;
            }
        """)
        self.name_edit.textChanged.connect(self._on_name_changed)

        self.chip_cat = QLabel("ACTION")
        self.chip_cat.setStyleSheet("""
            color: #3b82f6;
            background-color: rgba(59, 130, 246, 0.15);
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 9px;
            font-weight: 700;
        """)

        self.btn_close = QPushButton("✕")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #71717a;
                font-size: 14px;
                border: none;
                width: 24px;
                height: 24px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #272832;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.closed)

        header_layout.addWidget(self.lbl_icon)
        header_layout.addWidget(self.name_edit)
        header_layout.addWidget(self.chip_cat)
        header_layout.addWidget(self.btn_close)
        main_layout.addLayout(header_layout)

        # 2. Action Buttons: [▶ Test step] [⏻ Active] [🗑]
        actions_box = QHBoxLayout()
        actions_box.setSpacing(8)

        self.btn_test = QPushButton("▶ Test step")
        self.btn_test.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_test.clicked.connect(self._on_test_step)

        self.btn_toggle = QPushButton("⏻ Active")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #20212a;
                color: #9ca3af;
                border: 1px solid #2d303e;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:checked {
                color: #10b981;
                border-color: rgba(16, 185, 129, 0.4);
            }
        """)
        self.btn_toggle.clicked.connect(self._on_toggle_active)

        self.btn_delete = QPushButton("🗑")
        self.btn_delete.setToolTip("Delete node")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #71717a;
                border: 1px solid #2d303e;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ef4444;
                border-color: #ef4444;
            }
        """)
        self.btn_delete.clicked.connect(self._on_delete_node)

        actions_box.addWidget(self.btn_test)
        actions_box.addWidget(self.btn_toggle)
        actions_box.addWidget(self.btn_delete)
        main_layout.addLayout(actions_box)

        # 3. Mode Switcher: [Parameters] [Input / Output Data]
        mode_box = QHBoxLayout()
        mode_box.setSpacing(4)

        self.btn_tab_params = QPushButton("Parameters")
        self.btn_tab_params.setCheckable(True)
        self.btn_tab_params.setChecked(True)
        self.btn_tab_params.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_tab_data = QPushButton("Input / Output Data")
        self.btn_tab_data.setCheckable(True)
        self.btn_tab_data.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        tab_style = """
            QPushButton {
                background: transparent;
                color: #9ca3af;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:checked {
                color: #f4f4f5;
                font-weight: 600;
                border-bottom: 2px solid #8b5cf6;
            }
            QPushButton:hover:!checked {
                color: #ffffff;
            }
        """
        self.btn_tab_params.setStyleSheet(tab_style)
        self.btn_tab_data.setStyleSheet(tab_style)

        self.btn_tab_params.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_data.clicked.connect(lambda: self._switch_tab(1))

        mode_box.addWidget(self.btn_tab_params)
        mode_box.addWidget(self.btn_tab_data)
        mode_box.addStretch()
        main_layout.addLayout(mode_box)

        # 4. Content Area
        # View 1: Parameters Scroll Area
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.params_container = QWidget()
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 4, 0, 4)
        self.params_layout.setSpacing(10)
        self.params_scroll.setWidget(self.params_container)
        main_layout.addWidget(self.params_scroll)

        # View 2: Data JSON Viewer
        self.data_container = QWidget()
        self.data_layout = QVBoxLayout(self.data_container)
        self.data_layout.setContentsMargins(0, 4, 0, 4)
        self.data_layout.setSpacing(8)

        lbl_out = QLabel("Latest Output Payload (JSON):")
        lbl_out.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: 600;")
        self.data_text = QPlainTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #121318;
                border: 1px solid #282a35;
                border-radius: 6px;
                color: #a7f3d0;
                font-family: monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)

        btn_copy = QPushButton("Copy JSON")
        btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #20212a;
                color: #d4d4d8;
                border: 1px solid #2d303e;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2e303e;
                color: #ffffff;
            }
        """)
        btn_copy.clicked.connect(self._copy_data_json)

        self.data_layout.addWidget(lbl_out)
        self.data_layout.addWidget(self.data_text)
        self.data_layout.addWidget(btn_copy)
        self.data_container.hide()
        main_layout.addWidget(self.data_container)

    def _switch_tab(self, idx: int):
        self.btn_tab_params.setChecked(idx == 0)
        self.btn_tab_data.setChecked(idx == 1)
        self.params_scroll.setVisible(idx == 0)
        self.data_container.setVisible(idx == 1)

    def inspect_node(self, node):
        """Populates the inspector with properties of the selected node."""
        self.current_node = node
        if not node:
            return

        self.name_edit.setText(node.name())

        # Category and icon
        cat = getattr(node, "CATEGORY", "action")
        self.chip_cat.setText(cat.upper())
        cat_color = AutomationBranding.get_category_color(cat)
        self.chip_cat.setStyleSheet(f"""
            color: {cat_color};
            background-color: rgba({QColor(cat_color).red()}, {QColor(cat_color).green()}, {QColor(cat_color).blue()}, 0.15);
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 9px;
            font-weight: 700;
        """)

        icon_char = getattr(node, "NODE_ICON", "⚡")
        self.lbl_icon.setText(icon_char)

        # Toggle state
        self.btn_toggle.setChecked(not node.disabled())
        self.btn_toggle.setText("Active" if not node.disabled() else "Disabled")

        # Build parameters form
        self._build_parameters_form(node)

        # Build output data JSON
        sample_output = getattr(node, "last_output", None) or {
            "status": "success",
            "node": node.name(),
            "category": cat,
            "data": {"result": "Step executed successfully."},
        }
        self.data_text.setPlainText(json.dumps(sample_output, indent=2))

    def _build_parameters_form(self, node):
        # Clear existing form widgets
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Iterate node properties
        props = node.model.custom_properties
        if not props:
            lbl_empty = QLabel("No configurable properties for this node.")
            lbl_empty.setStyleSheet("color: #71717a; font-size: 12px; font-style: italic;")
            self.params_layout.addWidget(lbl_empty)
            self.params_layout.addStretch()
            return

        for prop_name, prop_val in props.items():
            field_box = QVBoxLayout()
            field_box.setSpacing(3)

            lbl = QLabel(prop_name.replace("_", " ").title())
            lbl.setStyleSheet("color: #d4d4d8; font-size: 11px; font-weight: 600;")
            field_box.addWidget(lbl)

            if isinstance(prop_val, str) and ("\n" in prop_val or len(prop_val) > 40):
                edit = QPlainTextEdit(prop_val)
                edit.setFixedHeight(70)
                edit.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #1f2029;
                        border: 1px solid #323544;
                        border-radius: 6px;
                        color: #f4f4f5;
                        font-family: monospace;
                        font-size: 11px;
                        padding: 4px;
                    }
                    QPlainTextEdit:focus {
                        border: 1px solid #8b5cf6;
                    }
                """)
                edit.textChanged.connect(lambda e=edit, p=prop_name: node.set_property(p, e.toPlainText()))
                field_box.addWidget(edit)
            elif isinstance(prop_val, (int, float)):
                spin = QSpinBox() if isinstance(prop_val, int) else QDoubleSpinBox()
                spin.setRange(-99999, 99999)
                spin.setValue(prop_val)
                spin.setStyleSheet("""
                    QSpinBox, QDoubleSpinBox {
                        background-color: #1f2029;
                        border: 1px solid #323544;
                        border-radius: 6px;
                        color: #f4f4f5;
                        padding: 4px;
                    }
                """)
                spin.valueChanged.connect(lambda val, p=prop_name: node.set_property(p, val))
                field_box.addWidget(spin)
            else:
                line_edit = QLineEdit(str(prop_val))
                line_edit.setStyleSheet("""
                    QLineEdit {
                        background-color: #1f2029;
                        border: 1px solid #323544;
                        border-radius: 6px;
                        color: #f4f4f5;
                        font-size: 12px;
                        padding: 4px 8px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #8b5cf6;
                    }
                """)
                line_edit.textChanged.connect(lambda text, p=prop_name: node.set_property(p, text))
                field_box.addWidget(line_edit)

            self.params_layout.addLayout(field_box)

        self.params_layout.addStretch()

    def _on_name_changed(self, text: str):
        if self.current_node:
            self.current_node.set_name(text)

    def _on_test_step(self):
        if self.current_node:
            if hasattr(self.current_node, "test_step"):
                self.current_node.test_step()
            self.step_executed.emit(self.current_node)

    def _on_toggle_active(self, checked: bool):
        if self.current_node:
            self.current_node.set_disabled(not checked)
            self.btn_toggle.setText("Active" if checked else "Disabled")

    def _on_delete_node(self):
        if self.current_node:
            self.node_deleted.emit(self.current_node)
            graph = getattr(self.current_node, "graph", None)
            if graph:
                graph.delete_node(self.current_node)
            self.closed.emit()

    def _copy_data_json(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.data_text.toPlainText())
