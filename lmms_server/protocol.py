"""
lmms_server.protocol - JSON-RPC 2.0 message parsing, serialization, and error codes.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

# Standard JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Custom Application Error Codes
REQUEST_CANCELLED = -32001
UNAUTHORIZED = -32002
SESSION_NOT_FOUND = -32003
PERMISSION_DENIED = -32004
TOOL_ERROR = -32005
BACKPRESSURE_OVERFLOW = -32006


class JsonRpcError(Exception):
    """Exception carrying a JSON-RPC 2.0 error code and payload."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            res["data"] = self.data
        return res


@dataclass
class JsonRpcRequest:
    """Incoming JSON-RPC 2.0 request or notification."""
    id: Optional[Union[str, int]]
    method: str
    params: Any = None
    is_notification: bool = False


def parse_request(line: str) -> JsonRpcRequest:
    """
    Parses a single JSON-RPC 2.0 message string.
    Raises JsonRpcError with appropriate error codes on malformed inputs.
    """
    try:
        data = json.loads(line)
    except Exception as e:
        raise JsonRpcError(PARSE_ERROR, f"Parse error: invalid JSON: {e}")

    if not isinstance(data, dict):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: message must be a JSON object")

    if data.get("jsonrpc") != "2.0":
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: 'jsonrpc' must be '2.0'")

    if "method" not in data or not isinstance(data["method"], str):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: 'method' must be a string")

    req_id = data.get("id")
    if req_id is not None and not isinstance(req_id, (str, int)):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: 'id' must be string, integer, or null")

    is_notification = ("id" not in data or req_id is None)
    return JsonRpcRequest(
        id=req_id,
        method=data["method"],
        params=data.get("params"),
        is_notification=is_notification,
    )


def format_response(req_id: Optional[Union[str, int]], result: Any) -> str:
    """Serializes a JSON-RPC 2.0 successful response."""
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }
    return json.dumps(payload) + "\n"


def format_error(req_id: Optional[Union[str, int]], code: int, message: str, data: Any = None) -> str:
    """Serializes a JSON-RPC 2.0 error response."""
    err_dict: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err_dict["data"] = data
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": err_dict,
    }
    return json.dumps(payload) + "\n"


def format_notification(method: str, params: Any = None) -> str:
    """Serializes a JSON-RPC 2.0 notification (no 'id' field)."""
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    return json.dumps(payload) + "\n"
