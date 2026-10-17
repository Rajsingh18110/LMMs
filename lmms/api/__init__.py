"""
LMMs API Layer
Standalone HTTP & WebSocket API server with modular routing for dual engines.
"""

try:
    from .app import app, create_app
    from .server import run_server
except ImportError:
    app = None
    create_app = None
    run_server = None

from .client import LMMsClient
from .service import start_server_daemon, stop_server_daemon, get_server_daemon_status

__all__ = [
    "app",
    "create_app",
    "run_server",
    "LMMsClient",
    "start_server_daemon",
    "stop_server_daemon",
    "get_server_daemon_status",
]
