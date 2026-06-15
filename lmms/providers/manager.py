from typing import List, Dict, Any

from .lmstudio.provider import LMStudioProvider
from .huggingface.provider import HuggingFaceProvider
from lmms.core.services.events import event_bus

class ProviderManager:
    """
    Coordinates across all model providers to sync registries.
    """
    def __init__(self, registry):
        self.registry = registry
        self.providers = [

            LMStudioProvider(),
            HuggingFaceProvider()
        ]

    def scan_local_providers(self) -> int:
        """Scans all registered providers and adds them to the registry."""
        added_count = 0
        for provider in self.providers:
            try:
                manifests = provider.scan_models()
                for manifest in manifests:
                    if not self.registry.get_model(manifest["id"]):
                        self.registry.add_model(
                            model_id=manifest["id"],
                            provider=manifest["provider"],
                            path=manifest["path"],
                            format=manifest["format"],
                            size=manifest.get("size", 0),
                            source=manifest["source"],
                            capabilities=manifest.get("capabilities", ["Text"])
                        )
                        added_count += 1
                        if manifest["provider"] == "Hugging Face":
                            event_bus.publish("ModelImported", {"model_id": manifest["id"], "provider": manifest["provider"]})
            except Exception as e:
                print(f"Error scanning provider {provider.__class__.__name__}: {e}")
        return added_count
