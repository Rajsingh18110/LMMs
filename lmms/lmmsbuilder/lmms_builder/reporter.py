from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def print_header():
    console.print(Panel("[bold cyan]LMMs Builder[/bold cyan]\n[bold yellow]Powered by MarkanM. For more details: Lmms.markanm.com[/bold yellow]\n[dim]Bootstrapper & Hardware Profiler[/dim]", border_style="cyan"))

def print_hardware_report(hw):
    table = Table(title="Hardware Detection Report", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Details", style="green")
    
    os_info = f"{hw['os']['system']} {hw['os']['release']} ({hw['os']['architecture']})"
    table.add_row("OS", os_info)
    
    cpu_info = f"{hw['cpu']['cores']} Cores / {hw['cpu']['threads']} Threads"
    table.add_row("CPU", cpu_info)
    
    ram_info = f"{hw['ram']['total_gb']} GB (Available: {hw['ram']['available_gb']} GB)"
    table.add_row("RAM", ram_info)
    
    if hw['gpu']['detected']:
        gpu_info = f"{hw['gpu']['name']} ({hw['gpu']['vram_gb']} GB VRAM)"
    else:
        gpu_info = "None Detected"
    table.add_row("GPU", gpu_info)
    
    if hw['cuda']['available']:
        cuda_info = f"Version {hw['cuda']['version']}"
    else:
        cuda_info = "Not Available"
    table.add_row("CUDA", cuda_info)
    
    table.add_row("Python", hw['python']['version'])
    
    console.print(table)

def print_compatibility_report(hw):
    console.print("\n[bold magenta]========================[/bold magenta]")
    console.print("[bold cyan]LMMS Compatibility[/bold cyan]\n")
    
    engine_comp = 100
    cli_comp = 100
    gui_comp = 100
    air_comp = 100 if hw['ram']['total_gb'] >= 16 else 50
    vllm_comp = 100 if hw['gpu']['detected'] and hw['gpu']['vram_gb'] >= 8 else 0
    
    console.print(f"Engine: {engine_comp}%")
    console.print(f"CLI: {cli_comp}%")
    console.print(f"GUI: {gui_comp}%")
    console.print(f"Air Engine: {air_comp}%")
    console.print(f"vLLM: {vllm_comp}%")
    
    overall = (engine_comp + cli_comp + gui_comp + air_comp + vllm_comp) // 5
    console.print(f"\n[bold green]Overall: {overall}%[/bold green]")
    console.print("[bold magenta]========================[/bold magenta]\n")

def print_benchmark_estimate(hw):
    console.print("\n[bold cyan]Hardware Benchmark (Estimated)[/bold cyan]")
    
    # Calculate an estimated TPS multiplier based on hardware
    base = 5.0
    if hw['gpu']['detected']:
        base += hw['gpu']['vram_gb'] * 2
    else:
        base += hw['cpu']['cores'] * 1.5
        
    console.print("llama.cpp (7B): ~[green]{:.1f} tok/s[/green]".format(base))
    console.print("ollama (7B): ~[green]{:.1f} tok/s[/green]".format(base * 0.95))
    if hw['ram']['total_gb'] >= 16:
        console.print("air (70B): ~[yellow]{:.1f} tok/s[/yellow]".format(max(1.0, base / 10)))
    else:
        console.print("air (70B): [red]Not Recommended (Insufficent RAM)[/red]")
        
def print_step(step_msg):
    console.print(f"[bold blue]>[/bold blue] {step_msg}")

def print_success(msg):
    console.print(f"[bold green]✓[/bold green] {msg}")

def print_error(msg):
    console.print(f"[bold red]✗[/bold red] {msg}")

def print_autoset_summary(mode, runtime):
    console.print(Panel(
        f"[bold green]AutoSet Complete![/bold green]\n\n"
        f"[cyan]Default Mode:[/cyan] {mode}\n"
        f"[cyan]Default Runtime:[/cyan] {runtime}\n\n"
        "Run [bold magenta]lmms[/bold magenta] to launch.",
        border_style="green"
    ))
