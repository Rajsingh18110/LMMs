import os
from typing import List, Dict, Any
from lmms.contracts.provider import ProviderContract
from lmms.models.manifest import ModelManifest

class LMStudioProvider(ProviderContract):
    def scan_models(self) -> List[Dict[str, Any]]:
        manifests = []
        lm_studio_dir = os.path.expanduser("~/.cache/lm-studio/models")
        if os.path.exists(lm_studio_dir):
            for root, _, files in os.walk(lm_studio_dir):
                for f in files:
                    if f.endswith(".gguf") or f.endswith(".safetensors"):
                        path = os.path.join(root, f)
                        rel_path = os.path.relpath(path, lm_studio_dir)
                        model_id = f"lmstudio/{rel_path}"
                        size = os.path.getsize(path)
                        manifest = ModelManifest(
                            model_id=model_id,
                            provider="LM Studio",
                            path=path,
                            format="GGUF" if f.endswith(".gguf") else "Safetensors",
                            size=size,
                            source="Imported (LM Studio)"
                        )
                        manifests.append(manifest.to_dict())
        return manifests

    def fetch_model(self, model_id: str) -> bool:
        return False
