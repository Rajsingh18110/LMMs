import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ModelfileParser:
    def __init__(self, manifests_dir: str = os.path.expanduser("~/.lmms/manifests"), models_dir: str = os.path.expanduser("~/.lmms/models")):
        self.manifests_dir = manifests_dir
        self.models_dir = models_dir
        os.makedirs(self.manifests_dir, exist_ok=True)

    def parse(self, filepath: str) -> Dict[str, Any]:
        """Parses a Modelfile and returns its structured manifest dictionary."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Modelfile not found: {filepath}")

        manifest = {
            "base_model": "",
            "system_prompt": "",
            "template": "",
            "parameters": {}
        }
        
        current_block = None
        block_content = []

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue
                
            if current_block:
                if line == '"""':
                    # End block
                    if current_block == "SYSTEM":
                        manifest["system_prompt"] = "\n".join(block_content).strip()
                    elif current_block == "TEMPLATE":
                        manifest["template"] = "\n".join(block_content).strip()
                    current_block = None
                    block_content = []
                else:
                    block_content.append(line)
                i += 1
                continue

            parts = line.split(" ", 1)
            directive = parts[0].upper()
            args = parts[1].strip() if len(parts) > 1 else ""

            if directive == "FROM":
                manifest["base_model"] = args
            elif directive == "PARAMETER":
                param_parts = args.split(" ", 1)
                if len(param_parts) == 2:
                    key, val = param_parts
                    # Try to cast to int/float
                    try:
                        if "." in val: val = float(val)
                        else: val = int(val)
                    except ValueError:
                        if val.lower() == "true": val = True
                        elif val.lower() == "false": val = False
                    manifest["parameters"][key] = val
            elif directive in ["SYSTEM", "TEMPLATE"]:
                if args.startswith('"""'):
                    if args.endswith('"""') and len(args) > 3:
                        # Inline block
                        content = args[3:-3]
                        if directive == "SYSTEM": manifest["system_prompt"] = content
                        else: manifest["template"] = content
                    else:
                        current_block = directive
                else:
                    if directive == "SYSTEM": manifest["system_prompt"] = args
                    else: manifest["template"] = args
            i += 1

        return manifest

    def create(self, model_name: str, modelfile_path: str):
        """Compiles a Modelfile and saves it to the registry/manifests folder."""
        print(f"Parsing Modelfile '{modelfile_path}' for model '{model_name}'...")
        manifest = self.parse(modelfile_path)
        
        if not manifest["base_model"]:
            raise ValueError("Modelfile must contain a FROM directive.")
            
        base = manifest["base_model"]
        print(f"Base model identified: {base}")
        
        # Check if base model is local
        base_gguf = os.path.join(self.models_dir, f"{base}.gguf") if not base.endswith(".gguf") else os.path.join(self.models_dir, base)
        
        if not os.path.exists(base_gguf):
            if base.startswith("hf.co/") or base.startswith("huggingface.co/"):
                print("Base model points to HuggingFace. Please use 'lmms pull <model>' first.")
                raise FileNotFoundError(f"Base model file not found locally: {base_gguf}")
            else:
                print(f"Warning: Base model {base} not found locally. Assuming it will be downloaded later.")

        out_path = os.path.join(self.manifests_dir, f"{model_name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
            
        print(f"Success! Model '{model_name}' created from Modelfile.")
        return out_path
