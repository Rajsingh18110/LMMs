import os
import json
from rich.console import Console
from rich.table import Table

class RegistryManager:
    def __init__(self, manifests_dir: str = os.path.expanduser("~/.lmms/manifests"), models_dir: str = os.path.expanduser("~/.lmms/models")):
        self.manifests_dir = manifests_dir
        self.models_dir = models_dir
        os.makedirs(self.manifests_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)

    def list_models(self):
        c = Console()
        table = Table(title="LMMs Local Registry")
        table.add_column("TAG")
        table.add_column("BASE MODEL")
        table.add_column("SIZE (GB)")
        
        # List raw gguf files first
        raw_models = {}
        for f in os.listdir(self.models_dir):
            if f.endswith(".gguf"):
                size_gb = os.path.getsize(os.path.join(self.models_dir, f)) / (1000**3)
                raw_models[f.replace(".gguf", "")] = size_gb

        # List manifests (custom tags)
        manifests = {}
        for f in os.listdir(self.manifests_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.manifests_dir, f), "r") as json_file:
                        data = json.load(json_file)
                        tag = f.replace(".json", "")
                        base = data.get("base_model", "")
                        base_size = raw_models.get(base, raw_models.get(base.replace(".gguf", ""), 0))
                        manifests[tag] = {"base": base, "size": base_size}
                except Exception:
                    pass
        
        # Add manifests to table
        for tag, info in manifests.items():
            table.add_row(tag, info["base"], f"{info['size']:.2f}")
            
        # Add raw models that aren't base models for any manifest
        used_bases = set(info["base"].replace(".gguf", "") for info in manifests.values())
        for tag, size in raw_models.items():
            if tag not in used_bases:
                table.add_row(tag, "<raw file>", f"{size:.2f}")
                
        c.print(table)

    def rm_model(self, tag: str):
        # Check if it's a manifest
        manifest_path = os.path.join(self.manifests_dir, f"{tag}.json")
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
            print(f"Deleted manifest '{tag}'.")
            return
            
        # Check if it's a raw file
        gguf_path = os.path.join(self.models_dir, f"{tag}.gguf")
        if os.path.exists(gguf_path):
            os.remove(gguf_path)
            print(f"Deleted raw model '{tag}'.")
            return
            
        print(f"Model '{tag}' not found in registry.")

    def info_model(self, tag: str):
        c = Console()
        manifest_path = os.path.join(self.manifests_dir, f"{tag}.json")
        gguf_path = os.path.join(self.models_dir, f"{tag}.gguf")
        
        info = {
            "Model Name": tag,
            "Size": "Unknown",
            "Quant": "Unknown",
            "Context": "Unknown",
            "Provider": "LMMs Engine (Local)",
            "Path": "Unknown"
        }
        
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                data = json.load(f)
            base = data.get("base_model", "")
            base_path = os.path.join(self.models_dir, f"{base}.gguf") if not base.endswith(".gguf") else os.path.join(self.models_dir, base)
            if os.path.exists(base_path):
                info["Size"] = f"{os.path.getsize(base_path) / (1000**3):.2f} GB"
                info["Path"] = base_path
            else:
                info["Path"] = f"{base_path} (Missing)"
        elif os.path.exists(gguf_path):
            info["Size"] = f"{os.path.getsize(gguf_path) / (1000**3):.2f} GB"
            info["Path"] = gguf_path
        else:
            c.print(f"[red]Model '{tag}' not found in registry.[/red]")
            return
            
        # Try to infer quant from name
        if "q4_k_m" in tag.lower() or (info["Path"] and "q4_k_m" in info["Path"].lower()):
            info["Quant"] = "Q4_K_M"
        elif "q8_0" in tag.lower() or (info["Path"] and "q8_0" in info["Path"].lower()):
            info["Quant"] = "Q8_0"
            
        # Default context for now
        info["Context"] = "8192"
        
        table = Table(title=f"Model Info: {tag}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        for k, v in info.items():
            table.add_row(k, str(v))
        c.print(table)
