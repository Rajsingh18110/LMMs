from dataclasses import dataclass, asdict
import json
from pathlib import Path

PROFILES_PATH = Path.home() / ".lmms" / "profiles.json"

@dataclass
class RuntimeProfile:
    name:         str
    context_len:  int
    temperature:  float
    top_p:        float
    top_k:        int
    n_gpu_layers: int    # -1 = all layers to GPU, 0 = CPU only
    n_threads:    int
    batch_size:   int
    max_tokens:   int

DEFAULT_PROFILES: dict[str, RuntimeProfile] = {
    "coding": RuntimeProfile(
        name="coding",      context_len=8192,
        temperature=0.2,    top_p=0.95,  top_k=40,
        n_gpu_layers=-1,    n_threads=8,
        batch_size=512,     max_tokens=4096),

    "reasoning": RuntimeProfile(
        name="reasoning",   context_len=16384,
        temperature=0.7,    top_p=0.9,   top_k=50,
        n_gpu_layers=-1,    n_threads=8,
        batch_size=256,     max_tokens=8192),

    "vision": RuntimeProfile(
        name="vision",      context_len=4096,
        temperature=0.3,    top_p=0.95,  top_k=40,
        n_gpu_layers=-1,    n_threads=4,
        batch_size=256,     max_tokens=2048),

    "audio": RuntimeProfile(
        name="audio",       context_len=2048,
        temperature=0.1,    top_p=0.99,  top_k=10,
        n_gpu_layers=-1,    n_threads=4,
        batch_size=128,     max_tokens=1024),

    "general": RuntimeProfile(
        name="general",     context_len=4096,
        temperature=0.8,    top_p=0.95,  top_k=50,
        n_gpu_layers=-1,    n_threads=8,
        batch_size=256,     max_tokens=2048),
}

class ProfileManager:
    def __init__(self):
        self._profiles = dict(DEFAULT_PROFILES)
        self._model_map: dict[str, str] = {}  # model_id → profile_name
        self._load()

    def _load(self):
        if PROFILES_PATH.exists():
            data = json.loads(PROFILES_PATH.read_text())
            self._model_map = data.get("model_map", {})
            for name, p in data.get("custom", {}).items():
                self._profiles[name] = RuntimeProfile(**p)

    def save(self):
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILES_PATH.write_text(json.dumps({
            "model_map": self._model_map,
            "custom": {
                k: asdict(v) for k, v in self._profiles.items()
                if k not in DEFAULT_PROFILES
            }
        }, indent=2))

    def get(self, name: str) -> RuntimeProfile:
        return self._profiles.get(name, DEFAULT_PROFILES["general"])

    def assign(self, model_id: str, profile_name: str):
        if profile_name not in self._profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        self._model_map[model_id] = profile_name
        self.save()

    def for_model(self, model_id: str) -> RuntimeProfile:
        name = self._model_map.get(model_id, "general")
        return self.get(name)

    def list_all(self) -> dict:
        return {k: asdict(v) for k, v in self._profiles.items()}

if __name__ == "__main__":
    pm = ProfileManager()
    print("Loaded 5 default profiles")
    for name, p in pm.list_all().items():
        if name in ["coding", "reasoning"]:
            print(f"{name}: ctx={p['context_len']} temp={p['temperature']} gpu_layers={p['n_gpu_layers']}")
