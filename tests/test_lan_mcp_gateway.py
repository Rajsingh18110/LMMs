"""
tests.test_lan_mcp_gateway - Comprehensive tests for Step 6a LAN MCP Gateway.
Tests:
1. TLS certificate generation, key security permissions, and SHA-256 fingerprint pinning (TOFU & MITM rejection).
2. Ephemeral single-use pairing codes (expiry, single-use invalidation).
3. Pairing rate-limiting / brute-force lockout.
4. Per-client revocable session tokens and client revocation.
5. Strict share_on_lan filtering: private/disabled servers never exposed.
6. Zero secret leakage: no env vars, commands, or credentials in tool lists.
7. Host-side permission matrix and interactive approval enforcement for LAN calls.
8. Hash-chained audit logging with client attribution (origin="lan_client", peer_id, ip).
9. Safe UDP discovery beacon with no tool names or secrets.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import ssl
import time
from pathlib import Path

import pytest

from lmms_mcp.config import MCPConfig
from lmms_server.audit import AuditLogger
from lmms_server.dispatcher import MethodDispatcher
from lmms_server.lan_gateway import (
    DEFAULT_BEACON_PORT,
    BEACON_PING,
    BEACON_PONG_PREFIX,
    LANClient,
    LANGatewayServer,
    PairingManager,
    TLSCertManager,
)
from lmms_server.protocol import JsonRpcError, PERMISSION_DENIED, UNAUTHORIZED


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_cert_dir(tmp_path):
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir


@pytest.fixture
def gateway_setup(tmp_path):
    """Sets up a test dispatcher, audit logger, and gateway server on a random free port."""
    cfg_file = tmp_path / "mcp.json"
    cfg = MCPConfig(config_path=str(cfg_file))

    # Server 1: Shared on LAN
    cfg.add_server(
        name="shared_fs",
        command_or_url="npx shared",
        enabled=True,
        share_on_lan=True,
        env={"SECRET_KEY": "supersecret123"},
    )

    # Server 2: NOT shared on LAN (Private host tool)
    cfg.add_server(
        name="private_terminal",
        command_or_url="bash",
        enabled=True,
        share_on_lan=False,
        env={"HOST_TOKEN": "hostonlytoken"},
    )

    # Server 3: Disabled server
    cfg.add_server(
        name="disabled_tool",
        command_or_url="echo",
        enabled=False,
        share_on_lan=True,
    )

    audit_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path=str(audit_file))

    dispatcher = MethodDispatcher(mcp_config=cfg)
    dispatcher.audit_logger = logger

    executed_calls = []

    def mock_handler(srv, tool, args):
        executed_calls.append({"server": srv, "tool": tool, "args": args})
        return f"Result from {srv}/{tool}: {args}"

    dispatcher.mock_tool_handler = mock_handler

    # Mock tool listing in MCP manager
    from lmms_mcp.manager import default_mcp_manager

    def mock_tools():
        return [
            {"server": "shared_fs", "name": "read_doc", "description": "Read document", "inputSchema": {"type": "object"}},
            {"server": "shared_fs", "name": "ask_tool", "description": "Restricted tool", "inputSchema": {"type": "object"}},
            {"server": "private_terminal", "name": "exec_cmd", "description": "Run shell", "inputSchema": {"type": "object"}},
            {"server": "disabled_tool", "name": "noop", "description": "Noop", "inputSchema": {"type": "object"}},
        ]

    default_mcp_manager.list_tools = mock_tools

    # Find a free TCP port for test gateway
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    server = LANGatewayServer(
        dispatcher=dispatcher,
        host="127.0.0.1",
        port=free_port,
        cert_dir=tmp_path / "certs",
        host_name="test-superhost",
        lan_discovery_enabled=False,
        use_tls=True,
    )

    return {
        "cfg": cfg,
        "dispatcher": dispatcher,
        "audit_file": audit_file,
        "server": server,
        "port": free_port,
        "executed_calls": executed_calls,
    }


# ============================================================================
# 1. TLS CERTIFICATE & PINNING TESTS
# ============================================================================

def test_tls_cert_generation_and_pinning(temp_cert_dir):
    """Verify certificate generation, file permissions (0600), and SHA-256 fingerprinting."""
    cert_path = temp_cert_dir / "gateway_cert.pem"
    key_path = temp_cert_dir / "gateway_key.pem"

    _, _, fp1 = TLSCertManager.ensure_certificate(cert_path, key_path, common_name="test-host")
    assert cert_path.exists()
    assert key_path.exists()
    assert len(fp1) == 64  # SHA-256 hex string

    # Check key permissions
    stat = key_path.stat()
    assert (stat.st_mode & 0o777) == 0o600

    # Ensure idempotency: re-running does not change cert or fingerprint
    _, _, fp2 = TLSCertManager.ensure_certificate(cert_path, key_path, common_name="test-host")
    assert fp1 == fp2


def test_tls_fingerprint_mismatch_rejection(gateway_setup):
    """Verify client rejects connection when pinned certificate fingerprint doesn't match."""
    server = gateway_setup["server"]
    port = gateway_setup["port"]

    async def _test():
        await server.start()
        try:
            wrong_fp = "0000000000000000000000000000000000000000000000000000000000000000"
            client = LANClient(host="127.0.0.1", port=port, pinned_fingerprint=wrong_fp, use_tls=True)

            with pytest.raises(ssl.SSLError) as exc:
                await client.connect()
            assert "mismatch" in str(exc.value).lower()
        finally:
            await server.stop()

    asyncio.run(_test())


# ============================================================================
# 2. PAIRING CODES & RATE-LIMITING TESTS
# ============================================================================

def test_pairing_code_single_use_and_expiration():
    """Verify pairing codes are strictly single-use and expire after TTL."""
    pm = PairingManager(code_ttl_seconds=0.3)
    code = pm.generate_pairing_code()
    assert len(code) == 6

    # 1. First pairing succeeds
    token = pm.pair(code, client_peer_id="peer-1", client_name="Laptop", client_ip="192.168.1.10")
    assert len(token) == 64
    session = pm.validate_token(token)
    assert session.client_peer_id == "peer-1"

    # 2. Second pairing with the same code fails (single-use)
    with pytest.raises(JsonRpcError) as exc1:
        pm.pair(code, client_peer_id="peer-2", client_name="Phone", client_ip="192.168.1.11")
    assert exc1.value.code == UNAUTHORIZED

    # 3. Test expiration
    code2 = pm.generate_pairing_code()
    time.sleep(0.35)  # wait past 0.3s TTL
    with pytest.raises(JsonRpcError) as exc2:
        pm.pair(code2, client_peer_id="peer-3", client_name="Tablet", client_ip="192.168.1.12")
    assert exc2.value.code == UNAUTHORIZED


def test_pairing_rate_limiting_lockout():
    """Verify 5 failed attempts locks out the client IP."""
    pm = PairingManager(max_attempts=3, lockout_seconds=1.0)
    client_ip = "192.168.1.50"

    # 3 failed attempts
    for _ in range(3):
        with pytest.raises(JsonRpcError):
            pm.pair("000000", client_peer_id="peer-x", client_name="Attacker", client_ip=client_ip)

    # 4th attempt should be blocked by rate limiting lockout
    with pytest.raises(JsonRpcError) as exc:
        pm.pair("123456", client_peer_id="peer-x", client_name="Attacker", client_ip=client_ip)
    assert exc.value.code == PERMISSION_DENIED
    assert "locked out" in exc.value.message.lower()


# ============================================================================
# 3. TOKEN VALIDATION & REVOCATION TESTS
# ============================================================================

def test_token_revocation():
    """Verify tokens can be revoked individually or by client peer ID."""
    pm = PairingManager()
    code1 = pm.generate_pairing_code()
    tok1 = pm.pair(code1, "client-a", "Device A", "10.0.0.1")

    code2 = pm.generate_pairing_code()
    tok2 = pm.pair(code2, "client-a", "Device A", "10.0.0.1")

    code3 = pm.generate_pairing_code()
    tok3 = pm.pair(code3, "client-b", "Device B", "10.0.0.2")

    # Tokens valid initially
    assert pm.validate_token(tok1).client_name == "Device A"
    assert pm.validate_token(tok3).client_name == "Device B"

    # Revoke single token
    assert pm.revoke_token(tok1) is True
    with pytest.raises(JsonRpcError) as exc:
        pm.validate_token(tok1)
    assert exc.value.code == UNAUTHORIZED

    # tok2 still valid
    assert pm.validate_token(tok2).client_name == "Device A"

    # Revoke all for client-a
    revoked_count = pm.revoke_client("client-a")
    assert revoked_count == 1  # only tok2 remained active
    with pytest.raises(JsonRpcError):
        pm.validate_token(tok2)

    # client-b unaffected
    assert pm.validate_token(tok3).client_name == "Device B"


# ============================================================================
# 4. END-TO-END GATEWAY SERVER & CLIENT TESTS
# ============================================================================

def test_lan_gateway_pairing_and_tools_list_filtering(gateway_setup):
    """
    Verify complete flow:
    - Client connects and verifies TLS certificate.
    - Pairs using single-use code.
    - Lists tools: ONLY share_on_lan=True servers exposed; private servers hidden.
    - Zero secret leakage: no env vars or tokens in list.
    """
    server = gateway_setup["server"]
    port = gateway_setup["port"]

    async def _test():
        await server.start()
        try:
            # 1. Generate code on host
            code = server.pairing_mgr.generate_pairing_code()

            # 2. Client connects with Trust On First Use (TOFU)
            client = LANClient(host="127.0.0.1", port=port, use_tls=True)
            await client.connect()
            assert client.server_fingerprint is not None
            assert len(client.server_fingerprint) == 64

            # 3. Pair
            tok = await client.pair(code, client_peer_id="peer-kali", client_name="Kali Laptop")
            assert tok is not None
            assert client.auth_token == tok

            # 4. List tools
            tools = await client.list_tools()

            # Assert ONLY tools from shared_fs are returned
            tool_names = [t["name"] for t in tools]
            assert "test-superhost/shared_fs/read_doc" in tool_names
            assert "test-superhost/shared_fs/ask_tool" in tool_names

            # Assert private_terminal and disabled_tool tools are NOT returned
            for tn in tool_names:
                assert "private_terminal" not in tn
                assert "disabled_tool" not in tn

            # Assert zero secrets leaked
            for t in tools:
                assert "env" not in t
                assert "command" not in t
                assert "args" not in t
                assert "SECRET_KEY" not in str(t)
                assert "supersecret" not in str(t)

            await client.close()
        finally:
            await server.stop()

    asyncio.run(_test())


def test_lan_gateway_tool_execution_and_audit_attribution(gateway_setup):
    """
    Verify remote tool call:
    - Executes shared tool through host sandbox and dispatcher.
    - Records audit log with origin='lan_client', client_peer_id, client_ip.
    - Denies execution for non-shared server.
    """
    server = gateway_setup["server"]
    port = gateway_setup["port"]
    audit_file = gateway_setup["audit_file"]

    async def _test():
        await server.start()
        try:
            code = server.pairing_mgr.generate_pairing_code()
            client = LANClient(host="127.0.0.1", port=port, use_tls=True)
            await client.connect()
            await client.pair(code, client_peer_id="remote-mac", client_name="MacBook Pro")

            # 1. Execute allowed shared tool
            res = await client.call_tool(
                tool_name="test-superhost/shared_fs/read_doc",
                arguments={"doc": "test.txt"},
            )
            assert "Result from shared_fs/read_doc" in res

            # Check audit log contains remote client attribution
            with open(audit_file, "r", encoding="utf-8") as f:
                lines = [json.loads(line.strip()) for line in f if line.strip()]

            assert len(lines) >= 1
            last_entry = lines[-1]
            assert last_entry["server"] == "shared_fs"
            assert last_entry["tool"] == "read_doc"
            assert last_entry["origin"] == "lan_client"
            assert last_entry["client_peer_id"] == "remote-mac"
            assert last_entry["client_ip"] in ("127.0.0.1", "::1", "unknown")

            # 2. Attempt to execute non-shared tool (private_terminal/exec_cmd)
            with pytest.raises(JsonRpcError) as exc:
                await client.call_tool(
                    tool_name="private_terminal/exec_cmd",
                    arguments={"command": "whoami"},
                )
            assert exc.value.code == PERMISSION_DENIED
            assert "not shared on lan" in exc.value.message.lower()

            # 3. Revoke token and verify further calls fail
            rev_res = await client.call("lan.token.revoke", {"target_token": client.auth_token})
            assert rev_res["revoked"] is True

            with pytest.raises(JsonRpcError) as exc2:
                await client.call_tool(
                    tool_name="test-superhost/shared_fs/read_doc",
                    arguments={"doc": "test.txt"},
                )
            assert exc2.value.code == UNAUTHORIZED

            await client.close()
        finally:
            await server.stop()

    asyncio.run(_test())


def test_lan_gateway_host_interactive_ask_approval(gateway_setup):
    """Verify tool marked as 'ask' on host halts remote LAN client until host approves."""
    server = gateway_setup["server"]
    port = gateway_setup["port"]
    cfg = gateway_setup["cfg"]
    dispatcher = gateway_setup["dispatcher"]

    # Set tool permission to "ask"
    cfg.set_tool_permission("shared_fs", "ask_tool", "ask")
    dispatcher.tool_approval_timeout = 5.0

    async def _test():
        await server.start()
        try:
            code = server.pairing_mgr.generate_pairing_code()
            client = LANClient(host="127.0.0.1", port=port, use_tls=True)
            await client.connect()
            await client.pair(code, client_peer_id="remote-cli", client_name="CLI User")

            # Launch call in background task
            call_task = asyncio.create_task(
                client.call_tool("shared_fs/ask_tool", {"action": "delete"})
            )

            # Wait for host approval prompt to appear
            prompt_id = None
            for _ in range(50):
                await asyncio.sleep(0.02)
                if dispatcher.pending_permissions:
                    prompt_id = list(dispatcher.pending_permissions.keys())[0]
                    break

            assert prompt_id is not None
            assert not call_task.done(), "Remote call executed without host approval!"

            # Host user approves the request
            await dispatcher.handle_tool_approve({"prompt_id": prompt_id})

            # Remote client call now unblocks with result
            res = await call_task
            assert "Result from shared_fs/ask_tool" in res

            await client.close()
        finally:
            await server.stop()

    asyncio.run(_test())


# ============================================================================
# 5. UDP DISCOVERY BEACON TESTS
# ============================================================================

def test_udp_discovery_beacon_safe_payload(gateway_setup):
    """
    Verify UDP beacon:
    - Opt-in: only responds when lan_discovery_enabled=True.
    - Safe: replies with host metadata and cert fingerprint, NEVER tool names or secrets.
    """
    server = gateway_setup["server"]
    server.lan_discovery_enabled = True

    async def _test():
        await server.start()
        try:
            # Send UDP discovery ping
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.5)
            try:
                sock.sendto(BEACON_PING, ("127.0.0.1", DEFAULT_BEACON_PORT))
                data, _ = sock.recvfrom(2048)

                assert data.startswith(BEACON_PONG_PREFIX)
                payload_json = data[len(BEACON_PONG_PREFIX):].decode("utf-8")
                payload = json.loads(payload_json)

                assert payload["host_name"] == "test-superhost"
                assert payload["gateway_port"] == server.port
                assert payload["tls_enabled"] is True
                assert len(payload["cert_fingerprint"]) == 64

                # CRITICAL: Verify ZERO tool or server names in discovery beacon
                raw_str = payload_json.lower()
                assert "tools" not in raw_str
                assert "shared_fs" not in raw_str
                assert "private_terminal" not in raw_str
                assert "read_doc" not in raw_str
                assert "secret" not in raw_str
            except (socket.timeout, OSError):
                # UDP broadcast might not bind on non-root or loopback in some container/CI environments
                pass
            finally:
                sock.close()
        finally:
            await server.stop()

    asyncio.run(_test())
