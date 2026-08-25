import os
import json
from typing import List, Dict, Any
from lmms.backend.contracts.provider import ProviderContract

class NativeProvider(ProviderContract):
    def scan_models(self) -> List[Dict[str, Any]]:
        manifests = []
        lmms_dir = os.path.expanduser("~/.lmms/models")
        if os.path.exists(lmms_dir):
            for file in os.listdir(lmms_dir):
                if file.endswith(".gguf"):
                    model_id = file.replace(".gguf", "")
                    size_gb = os.path.getsize(os.path.join(lmms_dir, file)) / (1000**3)
                    manifest = {
                        "id": model_id,
                        "provider": "LMMs",
                        "path": os.path.join(lmms_dir, file),
                        "format": "GGUF",
                        "size": int(size_gb * 1024 * 1024 * 1024),
                        "source": "Local"
                    }
                    manifests.append(manifest)
                    
        manifests_dir = os.path.expanduser("~/.lmms/manifests")
        if os.path.exists(manifests_dir):
            for file in os.listdir(manifests_dir):
                if file.endswith(".json"):
                    tag = file.replace(".json", "")
                    try:
                        with open(os.path.join(manifests_dir, file), "r") as f:
                            data = json.load(f)
                            base = data.get("base_model", "")
                            base_path = os.path.join(lmms_dir, f"{base.replace('.gguf', '')}.gguf")
                            if os.path.exists(base_path):
                                size_gb = os.path.getsize(base_path) / (1000**3)
                                manifest = {
                                    "id": tag,
                                    "provider": "LMMs",
                                    "path": base_path,
                                    "format": "GGUF",
                                    "size": int(size_gb * 1024 * 1024 * 1024),
                                    "source": "Local"
                                }
                                manifests.append(manifest)
                    except Exception:
                        pass
                        
        return manifests

    def fetch_model(self, model_id: str) -> bool:
        return False
