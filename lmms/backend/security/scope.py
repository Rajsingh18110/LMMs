import os
import json
import ipaddress
from typing import Dict, Any, Optional

from lmms.backend.security.target_validator import is_target_authorized

def get_scope_file(workspace: str) -> str:
    return os.path.join(workspace, ".lmms", "scope.json")

def load_scope(workspace: str) -> Optional[Dict[str, Any]]:
    if not workspace or workspace == "None":
        return None
        
    scope_path = get_scope_file(workspace)
    if os.path.exists(scope_path):
        try:
            with open(scope_path, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_scope(workspace: str, scope_data: Dict[str, Any]) -> bool:
    if not workspace or workspace == "None":
        return False
        
    scope_path = get_scope_file(workspace)
    os.makedirs(os.path.dirname(scope_path), exist_ok=True)
    try:
        with open(scope_path, "w") as f:
            json.dump(scope_data, f, indent=2)
        return True
    except Exception:
        return False

def init_default_scope() -> Dict[str, Any]:
    return {
        "version": 1,
        "engagement_name": "Default Offline Lab",
        "authorized_targets": [],
        "allowed_tools": ["cat", "grep", "ls", "pwd", "nmap", "curl", "ping"],
        "network_actions_allowed": False,
        "evidence_directory": ".lmms/evidence",
        "status": "safe"
    }

def is_scope_active(scope: Dict[str, Any]) -> bool:
    if not scope:
        return False
    return scope.get("status") == "active"


def validate_target(target: str, authorized_targets: list) -> bool:
    """Backward-compatible strict target validation for scope consumers."""
    return is_target_authorized(target, authorized_targets)

