"""
LMMs CLI GUI (cligui) Package
Provides terminal-native Rich UI components, dashboards, status bars, and inspectors
for the LMMs CLI without requiring heavy desktop GUI dependencies.
"""

from lmms.cli.cligui.mcp_dashboard import MCPTerminalDashboard

__all__ = ["MCPTerminalDashboard"]
