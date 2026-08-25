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
                    repo_path = os.path.join(hf_dir, repo_dir)
                    has_gguf = False
                    for root, _, files in os.walk(repo_path):
                        if any(f.endswith(".gguf") for f in files):
                            has_gguf = True
                            break
                    if not has_gguf:
                        continue
                        
                    parts = repo_dir.split("--")
                    if len(parts) >= 3:
                        model_id = f"{parts[1]}/{parts[2]}"
                        manifest = {
                            "id": model_id,
                            "provider": "Hugging Face",
                            "path": repo_path,
                            "format": "GGUF",
                            "source": "Imported (HF Cache)"
                        }
                        manifests.append(manifest)
        return manifests

    def fetch_model(self, model_id: str) -> bool:
        return False
