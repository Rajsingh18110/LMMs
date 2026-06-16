import os
from typing import List, Dict, Any
from lmms.backend.contracts.provider import ProviderContract


class HuggingFaceProvider(ProviderContract):
    def scan_models(self) -> List[Dict[str, Any]]:
        manifests = []
        hf_dir = os.path.expanduser("~/.cache/huggingface/hub")
        if os.path.exists(hf_dir):
            for repo_dir in os.listdir(hf_dir):
                if repo_dir.startswith("models--"):
                    parts = repo_dir.split("--")
                    if len(parts) >= 3:
                        model_id = f"{parts[1]}/{parts[2]}"
                        manifest = {
                            "id": model_id,
                            "provider": "Hugging Face",
                            "path": os.path.join(hf_dir, repo_dir),
                            "format": "Unknown",
                            "source": "Imported (HF Cache)"
                        }
                        manifests.append(manifest)
        return manifests

    def fetch_model(self, model_id: str) -> bool:
        return False
