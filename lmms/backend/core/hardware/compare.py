from typing import Dict, Any, List

class ModelComparer:
    """
    Compares the results of multiple model benchmarks and generates 
    a structured comparison report.
    """
    def __init__(self):
        pass

    def compare(self, benchmark_results: List[Dict[str, Any]]) -> str:
        """
        Takes a list of benchmark result dicts (from BenchmarkSuite)
        and returns a Markdown-formatted comparison report.
        """
        if not benchmark_results:
            return "No benchmarks provided for comparison."

        # Sort by TPS descending (fastest first)
        sorted_results = sorted(benchmark_results, key=lambda x: x.get("tps_avg", 0), reverse=True)
        
        report = "## Model Benchmark Comparison\n\n"
        report += "| Model | TTFT (ms) | Speed (TPS) |\n"
        report += "|---|---|---|\n"
        
        for res in sorted_results:
            model = res.get("model", "Unknown")
            ttft = res.get("ttft_avg_ms", 0.0)
            tps = res.get("tps_avg", 0.0)
            report += f"| {model} | {ttft} ms | {tps} tok/s |\n"
            
        report += "\n### Details\n"
        
        fastest = sorted_results[0]
        report += f"**Fastest Model:** `{fastest['model']}` at {fastest['tps_avg']} TPS.\n"
        
        # Sort by TTFT ascending (lowest latency first)
        latency_results = sorted(benchmark_results, key=lambda x: x.get("ttft_avg_ms", 0))
        lowest_latency = latency_results[0]
        report += f"**Lowest Latency:** `{lowest_latency['model']}` at {lowest_latency['ttft_avg_ms']} ms.\n"
        
        return report
