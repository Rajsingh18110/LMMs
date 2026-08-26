import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any

class RegistryMigration:
    """
    Migrates `~/.lmms/lmms_models.json` to the new architecture schema.
    """
    OLD_REGISTRY_PATH = os.path.expanduser("~/.lmms/lmms_models.json")
    NEW_MODELS_PATH = os.path.expanduser("~/.lmms/models.json")
    NEW_PROVIDERS_PATH = os.path.expanduser("~/.lmms/providers.json")
    BACKUP_DIR = os.path.expanduser("~/.lmms/migration_backups")

    @classmethod
    def migrate(cls) -> bool:
        if not os.path.exists(cls.OLD_REGISTRY_PATH):
            return True  # Nothing to migrate

        try:
            # Step 1: Backup
            os.makedirs(cls.BACKUP_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(cls.BACKUP_DIR, f"lmms_models_backup_{timestamp}.json")
            shutil.copy2(cls.OLD_REGISTRY_PATH, backup_file)
            print(f"Backed up old registry to {backup_file}")

            # Step 2: Read Old Data
            with open(cls.OLD_REGISTRY_PATH, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            # Step 3: Parse Providers & Models
            # Ensure local native provider exists
            from lmms.backend.core.registry.provider_registry import ProviderRegistry
            from lmms.backend.core.registry.model_registry import ModelRegistry
            
            # Check if local_native exists
            local_p = ProviderRegistry.get("local_native")
            if not local_p:
                ProviderRegistry.create_with_id(
                    "local_native",
                    "LMMs Built-in Local Engine",
                    "llama_cpp",
                    "", "", ""
                )

            # Step 4: Convert Models
            for old_id, model_info in old_data.items():
                if "path" not in model_info:
                    continue
                    
                # Format capabilities
                old_caps = model_info.get("capabilities", ["Text"])
                new_caps = {
                    "text": False,
                    "vision": False,
                    "streaming": True,
                    "tools": False,
                    "thinking": False
                }
                
                if isinstance(old_caps, list):
                    for cap in old_caps:
                        cap_lower = str(cap).lower()
                        if cap_lower == "text": new_caps["text"] = True
                        if cap_lower == "vision": new_caps["vision"] = True
                        if cap_lower == "tools": new_caps["tools"] = True
                
                # Check if it already exists
                existing = ModelRegistry.get(f"local_native::{old_id}")
                if existing:
                    continue
                    
                # Register
                ModelRegistry.register(
                    model_id=old_id,
                    provider_id="local_native",
                    display_name=old_id,
                    modality="text",
                    capabilities=new_caps,
                    context_window=4096,
                    metadata={
                        "path": model_info["path"],
                        "format": model_info.get("format", "Unknown"),
                        "source": model_info.get("source", "Local")
                    }
                )

            # Step 5: Mark old file as migrated by renaming it
            migrated_file = f"{cls.OLD_REGISTRY_PATH}.migrated"
            os.rename(cls.OLD_REGISTRY_PATH, migrated_file)
            print("Migration completed successfully.")
            return True
            
        except Exception as e:
            print(f"Migration failed: {e}")
            return False

if __name__ == "__main__":
    RegistryMigration.migrate()
