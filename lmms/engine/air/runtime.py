from typing import Any, Dict
from lmms.engine.runtimes.base import RuntimeContract
from lmms.engine.air.scheduler import AirScheduler
from lmms.engine.air.monitor import AirMonitor

class AirRuntime(RuntimeContract):
    def __init__(self):
        self.scheduler = AirScheduler()
        self.monitor = AirMonitor(self.scheduler)
        self._is_loaded = True # Always conceptually "loaded" since it orchestrates

    def parse_pairing(self, config_string: str, group_id: int = 1):
        """
        Setup pairing mapping from CLI
        e.g., parse_pairing("text:qwen3:8b image:llava")
        """
        self.scheduler.parse_input_and_create_group(group_id, config_string)

    def load_model(self, model_id: str) -> bool:
        # In AIR mode, models are loaded dynamically. 
        # But we can default to text role for basic API compatibility.
        return True

    def unload_model(self) -> bool:
        # Evict everything
        self.scheduler.pager._park_current()
        return True

    def chat(self, model: str, messages: list, stream: bool = False, options: dict = None, **kwargs) -> Any:
        context = {'messages': messages, 'target_role': kwargs.get('target_role', 'text'), 'model': model}
        return self.generate(context, stream)

    def generate(self, context: Any, stream: bool = False) -> Any:
        messages = context.get("messages", [])
        # We assume group 1 and target role 'text' by default if not specified
        target_role = context.get("target_role", "text")
        
        # Fallback if no groups defined (API mode), just create one on the fly
        if not self.scheduler.groups:
            # We use the model passed inside the context if available
            model = context.get('model', 'qwen1_5-0_5b')
            self.scheduler.parse_input_and_create_group(1, f"text:{model}")
            
        print("\n[AirRuntime] Inference started")
        result = self.scheduler.route_request(1, target_role, messages)
        
        # It's a generator. Let's wrap it to print completion at the end.
        def stream_wrapper(gen):
            import time
            t0 = time.time()
            tokens = 0
            for item in gen:
                tokens += 1
                yield item
            total_time = time.time() - t0
            tps = tokens / max(total_time, 0.001)
            
            # Print performance metrics
            profile = self.scheduler.pager.active_profile
            gpu_pct = 0.0
            cpu_pct = 100.0
            if profile and profile.total_layers_est > 0:
                if profile.optimal_gpu_layers == -1:
                    gpu_pct = 100.0
                else:
                    gpu_pct = (profile.optimal_gpu_layers / profile.total_layers_est) * 100.0
                cpu_pct = 100.0 - gpu_pct
                
            print(f"\n\n[AirRuntime] Inference completed ({tps:.2f} tokens/sec)")
            print(f"[AirPlanner] Policy Assigned Split: GPU {gpu_pct:.1f}% | CPU {cpu_pct:.1f}% (Note: Physical execution depends on compiled backend)")
            
        return stream_wrapper(result)

    def embed(self, text: str) -> list[float]:
        return [0.0]

    def tokenize(self, text: str) -> list[int]:
        return []

    def health(self) -> Dict[str, Any]:
        return self.monitor.get_full_metrics()
