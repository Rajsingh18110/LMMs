from typing import Dict, Any, Type
from lmms.engine.hardware import HardwareProfiler
from lmms.engine.benchmark import BenchmarkEngine
from lmms.engine.runtimes.base import RuntimeContract
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime
from lmms.engine.runtimes.air import AirRuntime

class SmartScheduler:
    def __init__(self):
        self.profiler = HardwareProfiler()
        self.benchmark = BenchmarkEngine()
        
    def select_runtime(self, model_size_label: str) -> Type[RuntimeContract]:
        """
        Capabilities Needed -> Model -> Hardware -> Runtime
        """
        hw = self.profiler.profile()
        benchmarks = self.benchmark.run_benchmarks(hw)
        
        recommendation = benchmarks.get(model_size_label, {})
        runtime_name = recommendation.get("recommended_runtime", "llama_cpp")
        
        if runtime_name == "air":
            return AirRuntime
        return LlamaCppRuntime
