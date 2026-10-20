"""
tests/test_mcp_gui.py - Automated Offscreen PyQt6 UI Tests for MCP & Tools Page.
Tests card rendering, template gallery, live status updates, search filter, and add/remove flows.
Saves dark and light mode screenshots to docs/screenshots/.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Enforce offscreen headless execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from lmms.gui.core.app_server_client import GUIAppServerClient
from lmms.gui.dialogs.add_mcp_server_dialog import AddMCPServerDialog
from lmms.gui.pages.mcp_page import MCPToolsPage, PulsingDot, ServerCard
from lmms.gui.qt import QApplication, QSize
from lmms_server.dispatcher import MethodDispatcher


@pytest.fixture(scope="session")
def qapp():
    """Session-wide offscreen QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def fake_gui_client():
    """Provides a GUIAppServerClient configured with in-memory MethodDispatcher."""
    dispatcher = MethodDispatcher()
    client = GUIAppServerClient()
    client.mock_dispatcher = dispatcher
    # Pre-populate sample servers
    dispatcher.mcp_config.add_server(
        name="filesystem",
        command_or_url="npx -y @modelcontextprotocol/server-filesystem /workspace",
        sandbox="bwrap",
        enabled=True,
    )
    dispatcher.mcp_config.add_server(
        name="github",
        command_or_url="npx -y @modelcontextprotocol/server-github",
        sandbox="none",
        enabled=True,
    )
    dispatcher.mcp_config.add_server(
        name="sqlite",
        command_or_url="uvx mcp-server-sqlite --db-path ~/.lmms/test.db",
        sandbox="bwrap",
        enabled=False,
    )
    return client


def test_pulsing_dot_states(qapp):
    """Verify PulsingDot updates colors and animation correctly based on status."""
    dot = PulsingDot()
    dot.set_status("connected")
    assert dot._color.name() == "#3fb950"

    dot.set_status("error")
    assert dot._color.name() == "#f85149"

    dot.set_status("starting")
    assert dot._color.name() == "#d29922"

    dot.set_status("disabled")
    assert dot._color.name() == "#8b949e"


def test_server_card_rendering_and_toggle(qapp, fake_gui_client):
    """Verify ServerCard displays metadata, badges, and toggle button works."""
    server_data = {
        "name": "filesystem",
        "command": "npx -y @modelcontextprotocol/server-filesystem /workspace",
        "transport": "stdio",
        "enabled": True,
        "sandbox": "bwrap",
        "tools": [{"name": "read_file"}, {"name": "write_file"}],
    }

    refreshed = False

    def on_refresh():
        nonlocal refreshed
        refreshed = True

    card = ServerCard(server_data=server_data, client=fake_gui_client, on_refresh=on_refresh)
    card.resize(400, 200)

    assert "filesystem" in card.server["name"]
    assert card.is_enabled is True
    assert "Enabled" in card.toggle_btn.text()
    assert "2 tools" in card.tools_badge.text()

    # Click toggle button
    card.toggle_btn.click()
    assert card.is_enabled is False
    assert "Disabled" in card.toggle_btn.text()


def test_mcp_page_search_filtering(qapp, fake_gui_client):
    """Verify search box dynamically filters server cards."""
    page = MCPToolsPage(client=fake_gui_client)
    page.resize(900, 600)
    page.load_servers()

    # All 3 servers should initially be rendered
    assert page.grid.count() == 3

    # Filter for 'github'
    page.search_box.setText("github")
    assert page.grid.count() == 1

    # Filter for non-existent server
    page.search_box.setText("non_existent_xyz")
    assert page.grid.count() == 0

    # Clear filter
    page.search_box.setText("")
    assert page.grid.count() == 3


def test_add_mcp_server_dialog_template_application(qapp, fake_gui_client):
    """Verify AddMCPServerDialog loads templates into custom form."""
    dlg = AddMCPServerDialog(client=fake_gui_client)
    dlg.resize(680, 500)

    # Apply 'github' template
    from lmms_mcp.config import CURATED_TEMPLATES
    dlg._apply_template("github", CURATED_TEMPLATES["github"])

    assert dlg.name_edit.text() == "github"
    assert dlg.cmd_edit.text() == "npx"
    assert "server-github" in dlg.args_edit.text()
    assert dlg.tabs.currentIndex() == 1  # Switched to custom tab


def test_render_and_save_screenshots(qapp, fake_gui_client):
    """Renders MCPToolsPage in Dark and Light themes and saves high-resolution screenshots."""
    screenshots_dir = Path("docs/screenshots")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    page = MCPToolsPage(client=fake_gui_client)
    page.resize(1100, 750)
    page.show()

    # 1. Dark Theme Screenshot
    page.set_theme(is_light=False)
    qapp.processEvents()
    dark_pixmap = page.grab()
    dark_path = screenshots_dir / "mcp_tools_dark.png"
    dark_pixmap.save(str(dark_path))
    assert dark_path.exists()
    assert dark_path.stat().st_size > 1000

    # 2. Light Theme Screenshot
    page.set_theme(is_light=True)
    qapp.processEvents()
    light_pixmap = page.grab()
    light_path = screenshots_dir / "mcp_tools_light.png"
    light_pixmap.save(str(light_path))
    assert light_path.exists()
    assert light_path.stat().st_size > 1000
