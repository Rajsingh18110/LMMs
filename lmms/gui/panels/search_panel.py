import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox, QDockWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

class SearchPanel(QDockWidget):
    # Emits (filepath, line_number, column) when a result is clicked
    result_clicked = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__("Search", parent)
        self.setObjectName("SearchDock")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0e1116;
                color: #c9d1d9;
                border: 1px solid #30363d;
                padding: 4px;
                border-radius: 4px;
            }
            QLineEdit:focus { border: 1px solid #58a6ff; }
        """)
        self.search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.search_input)

        # Replace Input
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.setStyleSheet(self.search_input.styleSheet())
        layout.addWidget(self.replace_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("Search")
        self.replace_all_btn = QPushButton("Replace All")
        
        btn_style = """
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #30363d; }
        """
        self.search_btn.setStyleSheet(btn_style)
        self.replace_all_btn.setStyleSheet(btn_style)
        
        self.search_btn.clicked.connect(self.perform_search)
        self.replace_all_btn.clicked.connect(self.perform_replace_all)
        
        btn_layout.addWidget(self.search_btn)
        btn_layout.addWidget(self.replace_all_btn)
        layout.addLayout(btn_layout)

        # Results Tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderHidden(True)
        self.results_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                color: #c9d1d9;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #2b313a;
            }
            QTreeWidget::item:hover {
                background-color: #21262d;
            }
        """)
        self.results_tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_tree)

        self.setWidget(container)

    def perform_search(self):
        query = self.search_input.text()
        if not query:
            return
            
        self.results_tree.clear()
        
        # Simple workspace search
        cwd = os.getcwd()
        exclude_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', '.gemini'}
        
        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Basic filter to avoid searching binaries
                if not file.endswith(('.py', '.js', '.ts', '.html', '.css', '.txt', '.md', '.json', '.yml', '.yaml', '.sh')):
                    continue
                    
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    matches = []
                    for i, line in enumerate(lines):
                        if query in line:
                            col = line.find(query)
                            matches.append((i+1, col, line.strip()))
                            
                    if matches:
                        file_item = QTreeWidgetItem(self.results_tree)
                        file_item.setText(0, os.path.relpath(path, cwd))
                        file_item.setData(0, Qt.ItemDataRole.UserRole, path)
                        
                        for line_num, col, snippet in matches:
                            match_item = QTreeWidgetItem(file_item)
                            match_item.setText(0, f"  {line_num}: {snippet}")
                            match_item.setData(0, Qt.ItemDataRole.UserRole, (path, line_num, col))
                            
                        file_item.setExpanded(True)
                except Exception:
                    pass

    def perform_replace_all(self):
        query = self.search_input.text()
        replacement = self.replace_input.text()
        if not query:
            return
            
        count = 0
        file_count = 0
        
        # Iterate over results currently shown
        for i in range(self.results_tree.topLevelItemCount()):
            file_item = self.results_tree.topLevelItem(i)
            path = file_item.data(0, Qt.ItemDataRole.UserRole)
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if query in content:
                    occurrences = content.count(query)
                    new_content = content.replace(query, replacement)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    count += occurrences
                    file_count += 1
            except Exception:
                pass
                
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences in {file_count} files.")
        self.perform_search() # Refresh results

    def on_item_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and len(data) == 3:
            path, line, col = data
            self.result_clicked.emit(path, line, col)
        elif isinstance(data, str): # It's a file root
            self.result_clicked.emit(data, 1, 0)
