from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

class BottomPanel(QWidget):
    def __init__(self, terminal_panel):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        from lmms.gui.panels.output_tab import OutputTab
        from lmms.gui.panels.problems_tab import ProblemsTab
        from lmms.gui.panels.debug_console_tab import DebugConsoleTab
        from lmms.gui.panels.ports_tab import PortsTab
        
        # Placeholders for future tabs
        self.problems_tab = ProblemsTab()
        self.output_tab = OutputTab()
        self.debug_console_tab = DebugConsoleTab()
        self.ports_tab = PortsTab()
        
        self.terminal_panel = terminal_panel
        
        self.tabs.addTab(self.problems_tab, "Problems 0")
        self.tabs.addTab(self.output_tab, "Output")
        self.tabs.addTab(self.debug_console_tab, "Debug Console")
        self.tabs.addTab(self.terminal_panel, "Terminal")
        self.tabs.addTab(self.ports_tab, "Ports")
        
        self.tabs.setCurrentWidget(self.terminal_panel)
        
        from lmms.gui.utils.diagnostic_manager import DiagnosticManager
        self.diag_mgr = DiagnosticManager.get_instance()
        self.diag_mgr.diagnostics_updated.connect(self.update_problems_badge)
        
    def update_problems_badge(self):
        count = sum(len(diags) for diags in self.diag_mgr.get_diagnostics().values())
        idx = self.tabs.indexOf(self.problems_tab)
        if idx != -1:
            if count > 0:
                self.tabs.setTabText(idx, f"Problems {count}")
            else:
                self.tabs.setTabText(idx, "Problems")
        
        self.layout.addWidget(self.tabs)
        
        self.setStyleSheet("""
            QTabWidget::pane { border: none; border-top: 1px solid #30363d; background: #181818; }
            QTabBar::tab { background: transparent; color: #8b949e; padding: 6px 16px; font-size: 11px; font-weight: 500; letter-spacing: 0.5px; border: none; text-transform: uppercase; }
            QTabBar::tab:selected { color: #e5e7eb; border-bottom: 1px solid #e5e7eb; }
            QTabBar::tab:hover:!selected { color: #e5e7eb; }
        """)
