import json
from pathlib import Path
from .base import ToolDefinition

KEYS_PATH = Path.home() / ".lmms" / "tools" / "keys.json"
# Stored locally, never sent anywhere

class KeyManager:
    def __init__(self):
        self._keys = {}
        self._load()

    def _load(self):
        if KEYS_PATH.exists():
            self._keys = json.loads(
                KEYS_PATH.read_text())

    def set(self, tool_name: str, key: str):
        self._keys[tool_name] = key
        KEYS_PATH.parent.mkdir(
            parents=True, exist_ok=True)
        KEYS_PATH.write_text(
            json.dumps(self._keys, indent=2))

    def get(self, tool_name: str) -> str | None:
        return self._keys.get(tool_name)

    def has(self, tool_name: str) -> bool:
        return tool_name in self._keys

    def list_missing(self, 
                     tools: list[ToolDefinition]
                     ) -> list[str]:
        return [
            t.name for t in tools
            if t.requires_key 
            and not self.has(t.name)
        ]
