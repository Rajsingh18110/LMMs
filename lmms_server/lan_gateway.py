"""
lmms_server.lan_gateway - Authenticated LAN MCP Gateway.
Implements:
1. TLS encryption with self-signed certificate generation and SHA-256 fingerprint pinning (TOFU).
2. Ephemeral single-use pairing codes (5-minute TTL) with brute-force rate-limiting lockout.
3. Per-client revocable session tokens.
4. Host-side permission enforcement, ExecPolicy, sandbox isolation, and audit log attribution.
5. Strict LAN sharing filtering: only servers with share_on_lan=True are exposed.
6. Zero secret leakage: tool lists contain zero environment variables, credentials, or commands.
7. Opt-in UDP discovery beacon without leaking tool or server names.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import os
import secrets
import socket
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from lmms_server.dispatcher import MethodDispatcher
from lmms_server.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PERMISSION_DENIED,
    UNAUTHORIZED,
    JsonRpcError,
    format_error,
    format_response,
    parse_request,
)

DEFAULT_LAN_GATEWAY_PORT = 11438
DEFAULT_BEACON_PORT = 11436
BEACON_PING = b"LMMS_MCP_PING"
BEACON_PONG_PREFIX = b"LMMS_MCP_PONG:"


# ============================================================================
# 1. TLS CERTIFICATE & PINNING MANAGER
# ============================================================================

class TLSCertManager:
    """Generates and manages self-signed TLS certificates for the LAN Gateway."""

    @staticmethod
    def ensure_certificate(
        cert_path: Path,
        key_path: Path,
        common_name: str = "lmms-lan-gateway",
    ) -> Tuple[Path, Path, str]:
        """
        Ensures a valid TLS certificate and private key exist, generating them if needed.
        Returns (cert_path, key_path, sha256_fingerprint).
        """
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(cert_path.parent), 0o700)
        except OSError:
            pass

        if not cert_path.exists() or not key_path.exists():
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LMMs LAN Gateway"),
            ])
            now = datetime.datetime.now(datetime.timezone.utc)
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .sign(key, hashes.SHA256())
            )

            # Write private key with 0600 mode
            key_pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            key_path.write_bytes(key_pem)
            try:
                os.chmod(str(key_path), 0o600)
            except OSError:
                pass

            # Write certificate
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            cert_path.write_bytes(cert_pem)
            try:
                os.chmod(str(cert_path), 0o600)
            except OSError:
                pass

        # Compute SHA-256 fingerprint from certificate DER
        cert_data = cert_path.read_bytes()
        loaded_cert = x509.load_pem_x509_certificate(cert_data)
        fingerprint = loaded_cert.fingerprint(hashes.SHA256()).hex().lower()

        return cert_path, key_path, fingerprint

    @staticmethod
    def create_server_ssl_context(cert_path: Path, key_path: Path) -> ssl.SSLContext:
        """Creates an SSLContext configured for the gateway server."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx

    @staticmethod
    def create_client_ssl_context() -> ssl.SSLContext:
        """Creates an SSLContext configured for LAN client connections."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


# ============================================================================
# 2. PAIRING & TOKEN MANAGER
# ============================================================================

@dataclass
class PairingCodeRecord:
    code: str
    expires_at: float
    used: bool = False


@dataclass
class ClientSessionRecord:
    token: str
    client_peer_id: str
    client_name: str
    client_ip: str
    created_at: float
    revoked: bool = False


class PairingManager:
    """
    Manages expiring single-use pairing codes and per-client revocable session tokens.
    Implements rate-limiting to prevent brute force of pairing codes.
    """

    def __init__(self, code_ttl_seconds: float = 300.0, max_attempts: int = 5, lockout_seconds: float = 60.0):
        self.code_ttl_seconds = code_ttl_seconds
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds

        self._active_codes: Dict[str, PairingCodeRecord] = {}
        self._tokens: Dict[str, ClientSessionRecord] = {}
        self._failed_attempts: Dict[str, List[float]] = {}  # ip -> list of timestamps

    def generate_pairing_code(self) -> str:
        """Generates an ephemeral 6-digit single-use pairing code with 5-minute TTL."""
        # Cleanup expired codes
        now = time.time()
        self._active_codes = {k: v for k, v in self._active_codes.items() if v.expires_at > now and not v.used}

        code = "".join(secrets.choice("0123456789") for _ in range(6))
        self._active_codes[code] = PairingCodeRecord(
            code=code,
            expires_at=now + self.code_ttl_seconds,
            used=False,
        )
        return code

    def is_ip_locked_out(self, client_ip: str) -> bool:
        """Checks if a client IP is temporarily locked out due to too many failed pairing attempts."""
        now = time.time()
        attempts = [t for t in self._failed_attempts.get(client_ip, []) if now - t < self.lockout_seconds]
        self._failed_attempts[client_ip] = attempts
        return len(attempts) >= self.max_attempts

    def register_failed_attempt(self, client_ip: str) -> None:
        """Records a failed pairing attempt for an IP address."""
        now = time.time()
        attempts = [t for t in self._failed_attempts.get(client_ip, []) if now - t < self.lockout_seconds]
        attempts.append(now)
        self._failed_attempts[client_ip] = attempts

    def pair(self, code: str, client_peer_id: str, client_name: str, client_ip: str) -> str:
        """
        Validates pairing code, invalidates it (single-use), and issues a revocable token.
        Raises JsonRpcError on failure or rate-limiting.
        """
        if self.is_ip_locked_out(client_ip):
            raise JsonRpcError(
                PERMISSION_DENIED,
                f"Too many failed pairing attempts. IP {client_ip} is temporarily locked out for {int(self.lockout_seconds)}s.",
            )

        now = time.time()
        record = self._active_codes.get(code)

        if not record or record.used or record.expires_at <= now:
            self.register_failed_attempt(client_ip)
            raise JsonRpcError(UNAUTHORIZED, "Invalid or expired pairing code")

        # Mark code as consumed immediately (single-use)
        record.used = True
        self._active_codes.pop(code, None)

        # Clear failed attempts on success
        self._failed_attempts.pop(client_ip, None)

        # Issue cryptographically secure 256-bit token
        token = secrets.token_hex(32)
        session = ClientSessionRecord(
            token=token,
            client_peer_id=client_peer_id,
            client_name=client_name,
            client_ip=client_ip,
            created_at=now,
            revoked=False,
        )
        self._tokens[token] = session
        return token

    def validate_token(self, token: Optional[str]) -> ClientSessionRecord:
        """Validates a client session token, ensuring it exists and is not revoked."""
        if not token:
            raise JsonRpcError(UNAUTHORIZED, "Missing authentication token")

        session = self._tokens.get(token)
        if not session or session.revoked:
            raise JsonRpcError(UNAUTHORIZED, "Invalid or revoked authentication token")

        return session

    def revoke_token(self, token: str) -> bool:
        """Revokes a specific client session token."""
        session = self._tokens.get(token)
        if session:
            session.revoked = True
            return True
        return False

    def revoke_client(self, client_peer_id: str) -> int:
        """Revokes all active session tokens for a given peer ID."""
        count = 0
        for session in self._tokens.values():
            if session.client_peer_id == client_peer_id and not session.revoked:
                session.revoked = True
                count += 1
        return count

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """Returns safe metadata of active client sessions (tokens redacted)."""
        return [
            {
                "client_peer_id": s.client_peer_id,
                "client_name": s.client_name,
                "client_ip": s.client_ip,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s.created_at)),
                "revoked": s.revoked,
            }
            for s in self._tokens.values()
        ]


# ============================================================================
# 3. LAN MCP GATEWAY SERVER
# ============================================================================

class LANGatewayServer:
    """
    Super Host MCP Gateway server.
    Serves authenticated remote clients over TLS with per-server LAN sharing rules.
    """

    def __init__(
        self,
        dispatcher: MethodDispatcher,
        host: str = "127.0.0.1",
        port: int = DEFAULT_LAN_GATEWAY_PORT,
        cert_dir: Optional[Path] = None,
        host_name: Optional[str] = None,
        lan_discovery_enabled: bool = False,
        use_tls: bool = True,
    ):
        self.dispatcher = dispatcher
        self.host = host
        self.port = port
        self.host_name = host_name or socket.gethostname()
        self.lan_discovery_enabled = lan_discovery_enabled
        self.use_tls = use_tls

        base_dir = cert_dir or (Path.home() / ".lmms")
        self.cert_path = base_dir / "lan_gateway_cert.pem"
        self.key_path = base_dir / "lan_gateway_key.pem"

        self.pairing_mgr = PairingManager()
        self.cert_mgr = TLSCertManager()
        self.cert_fingerprint = ""

        self._server: Optional[asyncio.Server] = None
        self._beacon_transport: Optional[asyncio.DatagramTransport] = None
        self._is_running = False

    async def start(self) -> None:
        """Starts the TLS TCP server and optional discovery beacon."""
        ssl_ctx: Optional[ssl.SSLContext] = None
        if self.use_tls:
            _, _, self.cert_fingerprint = self.cert_mgr.ensure_certificate(
                self.cert_path, self.key_path, common_name=self.host_name
            )
            ssl_ctx = self.cert_mgr.create_server_ssl_context(self.cert_path, self.key_path)

        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
            ssl=ssl_ctx,
        )
        self._is_running = True

        if self.lan_discovery_enabled:
            await self._start_beacon()

    async def stop(self) -> None:
        """Stops the gateway server and beacon."""
        self._is_running = False
        if self._beacon_transport:
            self._beacon_transport.close()
            self._beacon_transport = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _start_beacon(self) -> None:
        """Starts the UDP discovery beacon listener on port 11436."""
        loop = asyncio.get_running_loop()

        class BeaconProtocol(asyncio.DatagramProtocol):
            def __init__(self, outer: LANGatewayServer):
                self.outer = outer
                self.transport: Optional[asyncio.DatagramTransport] = None

            def connection_made(self, transport: asyncio.BaseTransport) -> None:
                if isinstance(transport, asyncio.DatagramTransport):
                    self.transport = transport

            def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
                if not self.outer.lan_discovery_enabled or not self.outer._is_running:
                    return

                if data in (BEACON_PING, b"LMMS_DISCOVERY_PING"):
                    # Safe payload with ZERO tool names or secrets
                    payload = {
                        "host_name": self.outer.host_name,
                        "gateway_port": self.outer.port,
                        "tls_enabled": self.outer.use_tls,
                        "cert_fingerprint": self.outer.cert_fingerprint,
                        "version": "1.0",
                    }
                    reply = BEACON_PONG_PREFIX + json.dumps(payload).encode("utf-8")
                    if self.transport:
                        self.transport.sendto(reply, addr)

        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: BeaconProtocol(self),
                local_addr=("", DEFAULT_BEACON_PORT),
                allow_broadcast=True,
            )
            self._beacon_transport = transport
        except Exception:
            # Beacon port might be in use by another instance; continue serving gateway
            pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles an incoming client TCP connection."""
        peername = writer.get_extra_info("peername")
        client_ip = peername[0] if peername else "unknown"

        try:
            while self._is_running:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                resp_str = await self._dispatch_line(line, client_ip)
                if resp_str:
                    out = resp_str.rstrip("\n") + "\n"
                    writer.write(out.encode("utf-8"))
                    await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_line(self, line: str, client_ip: str) -> str:
        """Parses JSON-RPC line and executes gateway method."""
        req_id = None
        try:
            req = parse_request(line)
            req_id = req.id
            method = req.method
            params = req.params if isinstance(req.params, dict) else {}
        except JsonRpcError as je:
            return format_error(None, je.code, je.message)
        except Exception as e:
            return format_error(None, PARSE_ERROR, f"Parse error: {e}")

        try:
            result = await self._execute_method(method, params, client_ip, req_id)
            return format_response(req_id, result)
        except JsonRpcError as je:
            return format_error(req_id, je.code, je.message)
        except Exception as e:
            return format_error(req_id, INTERNAL_ERROR, f"Internal error: {e}")

    async def _execute_method(
        self,
        method: str,
        params: Dict[str, Any],
        client_ip: str,
        req_id: Any,
    ) -> Any:
        """Dispatches RPC methods according to authentication and authorization rules."""
        # 1. Unauthenticated methods
        if method == "lan.pair":
            code = str(params.get("pairing_code", "")).strip()
            peer_id = str(params.get("client_peer_id", "")).strip()
            name = str(params.get("client_name", peer_id or client_ip)).strip()
            if not code or not peer_id:
                raise JsonRpcError(INVALID_PARAMS, "Missing required 'pairing_code' or 'client_peer_id'")

            token = self.pairing_mgr.pair(code, peer_id, name, client_ip)
            return {
                "token": token,
                "host_name": self.host_name,
                "cert_fingerprint": self.cert_fingerprint,
            }

        # 2. Authenticated methods: require valid token
        auth_token = params.get("auth_token") or params.get("token")
        client_session = self.pairing_mgr.validate_token(auth_token)

        if method == "lan.token.revoke":
            tok_to_revoke = str(params.get("target_token") or auth_token)
            ok = self.pairing_mgr.revoke_token(tok_to_revoke)
            return {"revoked": ok}

        elif method == "remote.tools.list":
            return await self._handle_remote_tools_list()

        elif method == "remote.tool.call":
            return await self._handle_remote_tool_call(params, client_session)

        elif method == "remote.host.info":
            return {
                "host_name": self.host_name,
                "cert_fingerprint": self.cert_fingerprint,
                "lan_discovery_enabled": self.lan_discovery_enabled,
            }

        else:
            raise JsonRpcError(METHOD_NOT_FOUND, f"Method '{method}' not found")

    async def _handle_remote_tools_list(self) -> List[Dict[str, Any]]:
        """
        Lists MCP tools exposed on LAN.
        STRICT SECURITY FILTER:
        Only servers with share_on_lan=True and enabled=True are listed!
        Tool names are namespaced as {host_name}/{server_name}/{tool_name}.
        No environment variables, server configs, or secrets are leaked.
        """
        from lmms_mcp.manager import default_mcp_manager

        active_tools = default_mcp_manager.list_tools()
        exposed_tools: List[Dict[str, Any]] = []

        for server in self.dispatcher.mcp_config.list_servers():
            # Security filter: must be explicitly shared on LAN and enabled
            if not server.share_on_lan or not server.enabled:
                continue

            for t in active_tools:
                if t.get("server") == server.name:
                    tool_name = t.get("name", "")
                    namespaced_name = f"{self.host_name}/{server.name}/{tool_name}"
                    exposed_tools.append({
                        "name": namespaced_name,
                        "server": server.name,
                        "original_name": tool_name,
                        "description": t.get("description", ""),
                        "inputSchema": t.get("inputSchema", {}),
                    })

        return exposed_tools

    async def _handle_remote_tool_call(
        self,
        params: Dict[str, Any],
        client_session: ClientSessionRecord,
    ) -> Dict[str, Any]:
        """
        Executes an MCP tool call on behalf of a LAN client.
        Enforces:
        - Server must be configured with share_on_lan=True and enabled=True.
        - Host permission matrix (allow, ask, deny).
        - ExecPolicy and sandbox isolation (bwrap/Landlock).
        - Cryptographic audit logging with client attribution.
        """
        tool_spec = str(params.get("tool") or params.get("tool_name", "")).strip()
        server_name = params.get("server") or params.get("server_name")
        arguments = params.get("arguments", {})

        # Resolve namespaced tool: host/server/tool
        if not server_name and "/" in tool_spec:
            parts = tool_spec.split("/")
            if len(parts) >= 3:
                # host_name / server_name / tool_name
                server_name = parts[1]
                tool_spec = "/".join(parts[2:])
            elif len(parts) == 2:
                # server_name / tool_name
                server_name = parts[0]
                tool_spec = parts[1]

        if not server_name or not tool_spec:
            raise JsonRpcError(INVALID_PARAMS, "Missing 'tool' or 'server'")

        server_cfg = self.dispatcher.mcp_config.get_server(server_name)
        if not server_cfg or not server_cfg.enabled or not server_cfg.share_on_lan:
            raise JsonRpcError(
                PERMISSION_DENIED,
                f"Server '{server_name}' is not shared on LAN or is disabled on host '{self.host_name}'",
            )

        # Build execution payload with client identity attribution for audit logger
        call_params = {
            "server_name": server_name,
            "tool_name": tool_spec,
            "arguments": arguments,
            "origin": "lan_client",
            "client_peer_id": client_session.client_peer_id,
            "client_ip": client_session.client_ip,
        }

        # Route through host's standard dispatcher handle_mcp_call
        # This triggers permission check (including interactive ask prompt on host if required),
        # ExecPolicy check, sandbox runner, and audit log!
        async def _noop_emit(m: str, p: Any):
            pass

        return await self.dispatcher.handle_mcp_call(call_params, _noop_emit)


# ============================================================================
# 4. LAN CLIENT
# ============================================================================

class LANClient:
    """
    Client for interacting with a remote LMMs Super Host MCP Gateway over TLS.
    Supports TOFU fingerprint pinning, single-use code pairing, and remote tool execution.
    """

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_LAN_GATEWAY_PORT,
        pinned_fingerprint: Optional[str] = None,
        auth_token: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.pinned_fingerprint = pinned_fingerprint.lower() if pinned_fingerprint else None
        self.auth_token = auth_token
        self.use_tls = use_tls

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.server_fingerprint: Optional[str] = None
        self._next_id = 1

    async def connect(self) -> None:
        """Establishes TLS connection and verifies pinned certificate fingerprint."""
        ssl_ctx: Optional[ssl.SSLContext] = None
        if self.use_tls:
            ssl_ctx = TLSCertManager.create_client_ssl_context()

        self.reader, self.writer = await asyncio.open_connection(
            self.host,
            self.port,
            ssl=ssl_ctx,
        )

        if self.use_tls and self.writer:
            ssl_obj = self.writer.get_extra_info("ssl_object")
            if ssl_obj:
                peercert_der = ssl_obj.getpeercert(binary_form=True)
                if peercert_der:
                    self.server_fingerprint = hashlib.sha256(peercert_der).hexdigest().lower()
                    if self.pinned_fingerprint and self.server_fingerprint != self.pinned_fingerprint:
                        await self.close()
                        raise ssl.SSLError(
                            f"TLS Certificate pinning mismatch! Expected {self.pinned_fingerprint}, got {self.server_fingerprint}"
                        )
                    if not self.pinned_fingerprint:
                        # Trust on first use
                        self.pinned_fingerprint = self.server_fingerprint

    async def close(self) -> None:
        """Closes connection."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Sends a JSON-RPC request and awaits response."""
        if not self.writer or not self.reader:
            raise ConnectionError("Not connected to LAN Gateway")

        req_id = self._next_id
        self._next_id += 1

        payload_params = dict(params or {})
        if self.auth_token and "auth_token" not in payload_params:
            payload_params["auth_token"] = self.auth_token

        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": payload_params,
        }

        line = json.dumps(req) + "\n"
        self.writer.write(line.encode("utf-8"))
        await self.writer.drain()

        resp_line = await self.reader.readline()
        while resp_line and resp_line.strip() == b"":
            resp_line = await self.reader.readline()

        if not resp_line:
            raise ConnectionResetError("Connection closed by gateway server")

        data = json.loads(resp_line.decode("utf-8"))
        if "error" in data:
            err = data["error"]
            raise JsonRpcError(err.get("code", INTERNAL_ERROR), err.get("message", "RPC Error"))

        return data.get("result")

    async def pair(self, pairing_code: str, client_peer_id: str, client_name: str) -> str:
        """Exchanges single-use pairing code for a session auth token."""
        res = await self.call("lan.pair", {
            "pairing_code": pairing_code,
            "client_peer_id": client_peer_id,
            "client_name": client_name,
        })
        token = res["token"]
        self.auth_token = token
        return token

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Retrieves list of shared tools from host."""
        res = await self.call("remote.tools.list")
        return res if isinstance(res, list) else []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None,
    ) -> Any:
        """Executes tool on host with host-side sandboxing and approval enforcement."""
        params: Dict[str, Any] = {
            "tool": tool_name,
            "arguments": arguments,
        }
        if server_name:
            params["server"] = server_name

        res = await self.call("remote.tool.call", params)
        return res.get("result") if isinstance(res, dict) else res
