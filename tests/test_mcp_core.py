"""
Unit Tests for LMMs MCP Subsystem
Tests config persistence, server manager lifecycle, tool-calling loop, and prompt fallback parser.
"""

import asyncio
import json
import os
import tempfile
import pytest

from lmms_mcp.config import MCPConfig, MCPServerConfig
from lmms_mcp.manager import MCPServerManager
from lmms_mcp.loop import MCPToolLoop
from lmms.cli.cligui.mcp_dashboard import MCPTerminalDashboard


@pytest.fixture
def temp_config_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_mcp_config_crud(temp_config_file):
    cfg = MCPConfig(config_path=temp_config_file)
    assert len(cfg.list_servers()) == 0

    # 1. Add server
    server = cfg.add_server(
        name="test_stdio",
        command_or_url="python3",
        transport="stdio",
        args=["-m", "mcp_dummy"],
        env={"TEST_VAR": "1"},
        sandbox="none",
    )
    assert server.name == "test_stdio"
    assert server.command == "python3"
    assert server.args == ["-m", "mcp_dummy"]
    assert server.env == {"TEST_VAR": "1"}

    # 2. Reload and verify persistence
    cfg_reloaded = MCPConfig(config_path=temp_config_file)
    reloaded_server = cfg_reloaded.get_server("test_stdio")
    assert reloaded_server is not None
    assert reloaded_server.name == "test_stdio"
    assert reloaded_server.enabled is True

    # 3. Disable and Enable
    cfg_reloaded.disable_server("test_stdio")
    s_disabled = cfg_reloaded.get_server("test_stdio")
    assert s_disabled is not None
    assert s_disabled.enabled is False

    cfg_reloaded.enable_server("test_stdio")
    s_enabled = cfg_reloaded.get_server("test_stdio")
    assert s_enabled is not None
    assert s_enabled.enabled is True

    # 4. Permissions
    cfg_reloaded.set_tool_permission("test_stdio", "read_file", "ask")
    s_perm = cfg_reloaded.get_server("test_stdio")
    assert s_perm is not None
    assert s_perm.permissions["read_file"] == "ask"

    # 5. Remove
    assert cfg_reloaded.remove_server("test_stdio") is True
    assert cfg_reloaded.get_server("test_stdio") is None


def test_mcp_config_templates(temp_config_file):
    cfg = MCPConfig(config_path=temp_config_file)
    res = cfg.apply_template("filesystem")
    assert res is not None
    assert res.name == "filesystem"
    assert res.transport == "stdio"
    assert res.command == "npx"

    # Custom name
    res2 = cfg.apply_template("sqlite", name="my_sqlite")
    assert res2 is not None
    assert res2.name == "my_sqlite"
    assert "mcp-server-sqlite" in res2.args


def test_mcp_tool_loop_conversion():
    raw_tools = [
        {
            "name": "read_file",
            "description": "Read file contents",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            "server": "fs",
        }
    ]

    # OpenAI format
    openai_tools = MCPToolLoop.to_openai_tool_definitions(raw_tools)
    assert len(openai_tools) == 1
    fn = openai_tools[0]["function"]
    assert fn["name"] == "fs__read_file"
    assert fn["description"] == "Read file contents"
    assert "path" in fn["parameters"]["properties"]

    # System instruction fallback
    sys_prompt = MCPToolLoop.to_prompt_system_instruction(raw_tools)
    assert "### AVAILABLE TOOLS" in sys_prompt
    assert "fs__read_file" in sys_prompt
    assert "Read file contents" in sys_prompt


def test_mcp_tool_loop_extraction():
    # 1. Markdown code block
    text1 = 'Here is the file:\n```json\n{"tool": "fs__read_file", "arguments": {"path": "main.py"}}\n```'
    call1 = MCPToolLoop.extract_tool_call(text1)
    assert call1 is not None
    assert call1[0] == "fs__read_file"
    assert call1[1] == {"path": "main.py"}

    # 2. XML tag
    text2 = '<tool_call>{"tool": "git__status", "arguments": {}}</tool_call>'
    call2 = MCPToolLoop.extract_tool_call(text2)
    assert call2 is not None
    assert call2[0] == "git__status"
    assert call2[1] == {}

    # 3. Naked JSON
    text3 = 'Sure, calling tool: {"tool": "terminal__run", "arguments": {"cmd": "ls"}} done.'
    call3 = MCPToolLoop.extract_tool_call(text3)
    assert call3 is not None
    assert call3[0] == "terminal__run"
    assert call3[1] == {"cmd": "ls"}

    # 4. No tool call
    text4 = "Hello! I am ready to help you write code."
    assert MCPToolLoop.extract_tool_call(text4) is None


def test_mcp_tool_loop_permissions(temp_config_file):
    async def _async_test():
        cfg = MCPConfig(config_path=temp_config_file)
        cfg.add_server("sec_server", "dummy", transport="stdio", enabled=True)
        cfg.set_tool_permission("sec_server", "delete_db", "deny")
        cfg.set_tool_permission("sec_server", "wipe_cache", "ask")

        manager = MCPServerManager(cfg)
        loop = MCPToolLoop(manager)

        # Denied tool
        res = await loop.execute_extracted_tool_call("sec_server__delete_db", {})
        assert "DENIED by policy" in res

        # Ask tool with user confirmation rejection
        async def fake_confirm(s, t, args):
            return False

        res_ask = await loop.execute_extracted_tool_call(
            "sec_server__wipe_cache", {}, confirm_callback=fake_confirm
        )
        assert "cancelled by the user" in res_ask

    asyncio.run(_async_test())


def test_mcp_terminal_dashboard(temp_config_file):
    cfg = MCPConfig(config_path=temp_config_file)
    cfg.apply_template("filesystem")
    manager = MCPServerManager(cfg)
    dashboard = MCPTerminalDashboard(manager)

    chips = dashboard.render_summary_chips()
    assert chips is not None

    table = dashboard.render_server_table()
    assert table is not None
    assert table.row_count >= 1


def test_mcp_manager_live_stdio(temp_config_file):
    """Starts lmms_mcp.server via python3 stdio, connects, discovers tools, and calls a tool."""
    async def _live_test():
        cfg = MCPConfig(config_path=temp_config_file)
        cfg.add_server(
            name="lmms_builtin",
            command_or_url="python3",
            transport="stdio",
            args=["-m", "lmms_mcp.server"],
            enabled=True,
        )
        manager = MCPServerManager(cfg)
        try:
            # Test connection
            ok, msg, tools = await manager.test_connection("lmms_builtin")
            assert ok is True
            assert len(tools) >= 3

            tool_names = [t["name"] for t in tools]
            assert "read_file" in tool_names
            assert "write_file" in tool_names
            assert "run_terminal" in tool_names

            # Call read_file on this test file
            this_file = os.path.abspath(__file__)
            res = await manager.call_tool(
                server_name="lmms_builtin",
                tool_name="read_file",
                arguments={"path": this_file},
            )
            assert hasattr(res, "content")
            assert len(res.content) > 0
            assert "test_mcp_manager_live_stdio" in res.content[0].text
        finally:
            await manager.stop_all()

    asyncio.run(_live_test())

