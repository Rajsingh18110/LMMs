import os
import json

CONFIG_PATH = os.path.expanduser("~/.lmms/config.json")

class ConfigManager:
    def __init__(self):
        self._cache = None

    def get_all(self):
        if self._cache is not None:
            return self._cache
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    self._cache = json.load(f)
                    return self._cache
            except:
                pass
        self._cache = {}
        return self._cache

    def get(self, key, default=None):
        return self.get_all().get(key, default)

    def set(self, key, value):
        data = self.get_all()
        data[key] = value
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)
        self._cache = data
