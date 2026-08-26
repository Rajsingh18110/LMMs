import os
import json
import glob

REGISTRY_FILE = os.path.expanduser("~/.lmms/lmms_models.json")

class ModelRegistry:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)

    @staticmethod
    def load_registry() -> dict:
        """Returns the registry dictionary: {model_id: {path, source, format, params...}}"""
        if not os.path.exists(REGISTRY_FILE):
            return {}
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            cleaned = {}
            changed = False
            for k, v in registry.items():
                if "path" in v and os.path.exists(v["path"]):
                    cleaned[k] = v
                else:
                    changed = True
            
            if changed:
                ModelRegistry.save_registry(cleaned)
                
            return cleaned
        except Exception:
            return {}

    @staticmethod
    def save_registry(registry: dict):
        ModelRegistry._ensure_dir()
        try:
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=4)
        except Exception as e:
            print(f"Error saving model registry: {e}")

    @staticmethod
    def scan_local_providers():
        """Scans known directories for models and adds them to the registry as 'Imported (Linked)'"""
        registry = ModelRegistry.load_registry()
        added_count = 0

        # 1. Native LMMS Models (~/.lmms/models/)
        lmms_dir = os.path.expanduser("~/.lmms/models")
        if os.path.exists(lmms_dir):
            for file in os.listdir(lmms_dir):
                if file.endswith(".gguf"):
                    model_id = file.replace(".gguf", "")
                    if model_id not in registry:
                        registry[model_id] = {
                            "source": "Local",
                            "path": os.path.join(lmms_dir, file),
                            "format": "GGUF",
                            "status": "Downloaded"
                        }
                        added_count += 1

        # 2. LM Studio Models (~/.cache/lm-studio/models)
        lm_studio_dir = os.path.expanduser("~/.cache/lm-studio/models")
        if os.path.exists(lm_studio_dir):
            for root, _, files in os.walk(lm_studio_dir):
                for f in files:
                    if f.endswith(".gguf") or f.endswith(".safetensors"):
                        path = os.path.join(root, f)
                        # Derive a faux ID from path
                        rel_path = os.path.relpath(path, lm_studio_dir)
                        model_id = f"lmstudio/{rel_path}"
                        if model_id not in registry:
                            registry[model_id] = {
                                "source": "LM Studio",
                                "path": path,
                                "format": "GGUF" if f.endswith(".gguf") else "Safetensors",
                                "status": "Imported (Linked)"
                            }
                            added_count += 1
                            
        # 3. HuggingFace Cache
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
                        if model_id not in registry:
                            registry[model_id] = {
                                "source": "Hugging Face",
                                "path": repo_path,
                                "format": "GGUF",
                                "status": "Imported (Linked)"
                            }
                            added_count += 1
                            
        # Cleanup ghost entries (where path was deleted or doesn't have GGUF)
        keys_to_delete = []
        for mid, info in registry.items():
            path = info.get("path", "")
            if not os.path.exists(path):
                keys_to_delete.append(mid)
            elif info.get("source") == "Hugging Face":
                has_gguf = False
                for root, _, files in os.walk(path):
                    if any(f.endswith(".gguf") for f in files):
                        has_gguf = True
                        break
                if not has_gguf:
                    keys_to_delete.append(mid)
        
        for mid in keys_to_delete:
            del registry[mid]
            added_count += 1 # force save

        if added_count > 0:
            ModelRegistry.save_registry(registry)

    @staticmethod
    def get_model(model_id: str):
        return ModelRegistry.load_registry().get(model_id)

    @staticmethod
    def add_local_model(model_id: str, path: str, format_str: str):
        registry = ModelRegistry.load_registry()
        registry[model_id] = {
            "source": "Local",
            "path": path,
            "format": format_str,
            "status": "Downloaded"
        }
        ModelRegistry.save_registry(registry)

    @staticmethod
    def remove_model(model_id: str):
        registry = ModelRegistry.load_registry()
        if model_id in registry:
            # We don't delete files for linked imports, only local downloads.
            # But we leave actual file deletion to the UI logic.
            del registry[model_id]
            ModelRegistry.save_registry(registry)

    @staticmethod
    def save_model_profile(model_id: str, profile: dict):
        registry = ModelRegistry.load_registry()
        if model_id not in registry:
            registry[model_id] = {}
        registry[model_id]["profile"] = profile
        ModelRegistry.save_registry(registry)

    @staticmethod
    def get_model_profile(model_id: str):
        registry = ModelRegistry.load_registry()
        return registry.get(model_id, {}).get("profile", {
            "temperature": 0.7,
            "top_p": 0.9,
            "context_length": 4096,
            "gpu_layers": -1,
            "system_prompt": "You are a helpful AI assistant."
        })
