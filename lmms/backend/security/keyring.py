"""
lmms.backend.security.keyring - Secure credentials vault for API keys and tokens.
Stores API keys in ~/.lmms/credentials.json with restrictive 0600 file permissions.
"""

from __future__ import annotations

import os
import json
import base64
from typing import Dict, List, Optional


class KeyringVault:
    """Manages sensitive API credentials and keys."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.expanduser("~/.lmms/credentials.json")
        self._ensure_secure_file()

    def _ensure_secure_file(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            try:
                fd = os.open(self.storage_path, os.O_WRONLY | os.O_CREAT, 0o600)
                os.write(fd, b"{}")
                os.close(fd)
            except OSError:
                pass
        else:
            try:
                os.chmod(self.storage_path, 0o600)
            except OSError:
                pass

    def _load_data(self) -> Dict[str, str]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_data(self, data: Dict[str, str]):
        try:
            tmp = self.storage_path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT, 0o600)
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.storage_path)
            os.chmod(self.storage_path, 0o600)
        except Exception:
            pass

    def set_key(self, service: str, api_key: str):
        data = self._load_data()
        data[service.lower().strip()] = api_key.strip()
        self._save_data(data)

    def get_key(self, service: str) -> Optional[str]:
        data = self._load_data()
        return data.get(service.lower().strip())

    def delete_key(self, service: str) -> bool:
        data = self._load_data()
        s = service.lower().strip()
        if s in data:
            del data[s]
            self._save_data(data)
            return True
        return False

    def list_services(self) -> List[str]:
        data = self._load_data()
        return sorted(list(data.keys()))


default_vault = KeyringVault()
