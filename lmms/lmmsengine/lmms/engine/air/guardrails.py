from typing import Dict, Any

class AirGuardrails:
    def validate_load(self, model_size_gb: float, hw_profile: Dict[str, Any]) -> bool:
        """
        Safety layer to prevent OS freeze.
        """
        total_sys_ram = hw_profile.get("ram_total_mb", 0) / 1024
        if model_size_gb > (total_sys_ram * 0.8):
            # E.g. trying to load a 140GB model on 16GB RAM
            raise MemoryError(f"Model size {model_size_gb}GB exceeds safe RAM limits. Rejecting to prevent freeze.")
        return True
