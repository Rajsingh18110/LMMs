import os
import json

def migrate():
    ollama_manifest_dir = os.path.expanduser("~/.ollama/models/manifests/registry.ollama.ai/library")
    ollama_blobs_dir = os.path.expanduser("~/.ollama/models/blobs")
    lmms_models_dir = os.path.expanduser("~/.lmms/models")
    registry_file = os.path.expanduser("~/.lmms/lmms_models.json")
    
    os.makedirs(lmms_models_dir, exist_ok=True)
    
    registry = {}
    if os.path.exists(registry_file):
        try:
            with open(registry_file, "r") as f:
                registry = json.load(f)
        except Exception:
            pass
            
    added = 0
    # Process Ollama models
    if os.path.exists(ollama_manifest_dir):
        for model in os.listdir(ollama_manifest_dir):
            model_path = os.path.join(ollama_manifest_dir, model)
            if os.path.isdir(model_path):
                for tag in os.listdir(model_path):
                    manifest_path = os.path.join(model_path, tag)
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                        for layer in manifest.get("layers", []):
                            if layer.get("mediaType") == "application/vnd.ollama.image.model":
                                digest = layer.get("digest")
                                if digest:
                                    blob_path = os.path.join(ollama_blobs_dir, digest.replace(":", "-"))
                                    if not os.path.exists(blob_path):
                                        blob_path = os.path.join(ollama_blobs_dir, digest)
                                    
                                    if os.path.exists(blob_path):
                                        new_name = f"{model}-{tag}.gguf"
                                        target_path = os.path.join(lmms_models_dir, new_name)
                                        
                                        if not os.path.exists(target_path):
                                            print(f"Migrating {model}:{tag} -> {new_name}")
                                            os.link(blob_path, target_path)
                                        
                                        registry[f"{model}:{tag}"] = {
                                            "source": "Local",
                                            "path": target_path,
                                            "format": "GGUF",
                                            "status": "Migrated from Ollama"
                                        }
                                        added += 1
                    except Exception as e:
                        print(f"Failed to process {model}:{tag} - {e}")
    else:
        print("No Ollama models found to migrate.")
        
    # Scan LMMS models directory for existing .gguf files
    for file in os.listdir(lmms_models_dir):
        if file.endswith(".gguf"):
            path = os.path.join(lmms_models_dir, file)
            model_id = file.replace(".gguf", "")
            if model_id not in registry:
                registry[model_id] = {
                    "source": "Local",
                    "path": path,
                    "format": "GGUF",
                    "status": "Downloaded"
                }
                print(f"Registered existing LMMS model: {file}")
                added += 1
                
    with open(registry_file, "w") as f:
        json.dump(registry, f, indent=4)
        
    print(f"Migration complete. Registry updated with {added} models.")

if __name__ == "__main__":
    migrate()
