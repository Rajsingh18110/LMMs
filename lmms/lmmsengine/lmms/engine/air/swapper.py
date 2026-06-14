class AirSwapper:
    def __init__(self, scheduler, ram_cache):
        self.scheduler = scheduler
        self.ram_cache = ram_cache
        
    def swap_to_ram(self, model_name: str):
        """
        Offloads a model from VRAM to RAM Cache.
        """
        if model_name in self.scheduler.active_models:
            info = self.scheduler.active_models[model_name]
            if info["location"] == "VRAM":
                self.ram_cache.stage_model(model_name, info["vram_gb"])
                self.scheduler.update_state(model_name, "Swapped to RAM")
                
                # Update stats logically
                self.scheduler.active_models[model_name]["ram_gb"] = info["vram_gb"]
                self.scheduler.active_models[model_name]["vram_gb"] = 0.0
                self.scheduler.active_models[model_name]["location"] = "RAM"
                return True
        return False
            
    def swap_to_vram(self, model_name: str):
        """
        Pulls a staged model from RAM Cache back to VRAM.
        """
        if model_name in self.ram_cache.staged_models:
            info = self.ram_cache.staged_models[model_name]
            self.ram_cache.evict_model(model_name)
            
            if model_name in self.scheduler.active_models:
                self.scheduler.active_models[model_name]["vram_gb"] = info["size_gb"]
                self.scheduler.active_models[model_name]["ram_gb"] = 0.0
                self.scheduler.active_models[model_name]["location"] = "VRAM"
                self.scheduler.update_state(model_name, "Loaded in VRAM")
            else:
                self.scheduler.register_model(model_name, "VRAM", info["size_gb"], 0.0)
            return True
        return False

    def ensure_vram_capacity(self, needed_gb: float) -> bool:
        """
        Ensures there is enough VRAM. If not, evicts the oldest models.
        """
        MAX_VRAM = 24.0 # Hardcoded for now
        
        def get_used():
            return sum(m["vram_gb"] for m in self.scheduler.active_models.values() if m["location"] == "VRAM")
            
        while get_used() + needed_gb > MAX_VRAM:
            # Find a model to evict (not Generating)
            evicted = False
            for name, info in self.scheduler.active_models.items():
                if info["location"] == "VRAM" and info["state"] != "Generating":
                    self.swap_to_ram(name)
                    # Unload from runtime
                    from lmms.engine.manager import engine_manager
                    engine_manager.runtime.unload_model(name)
                    evicted = True
                    break
            if not evicted:
                return False # Cannot evict anything else!
        return True
