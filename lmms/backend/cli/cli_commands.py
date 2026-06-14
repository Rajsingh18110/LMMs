"""
cli_commands.py - Central registry for all LMMs CLI Commands.
"""

CLI_COMMANDS = {
    "/fast": "Switch to FAST mode (quick response, no tools).",
    "/deep": "Switch to DEEP mode (reasoning with tools, default).",
    "/dual": "Switch to DUAL mode (multi-model debate).",
    "/qwen": "Set text model to qwen3:8b.",
    "/gemma": "Set text model to gemma4.",
    "/model": "Switch to any Ollama model (e.g., /model llama3).",
    "/help": "Show this help message with all commands.",
    "/history": "Show the recent chat history.",
    "/clear": "Clear the context/memory of the current session.",
    "/attach": "Open GUI file picker to attach a file to context.",
    "/file": "Attach a specific file to context (e.g., /file main.py).",
    "/folder": "Attach an entire folder to context (e.g., /folder src).",
    "/connector": "Manage Cloud API connectors (OpenAI, Anthropic).",
    "/download": "Search and download GGUF models directly from HuggingFace.",
    "/airllm": "Run extremely large models (70B+) via AirLLM disk-offloading.",
    "/undo": "Undo the last AI action or code edit.",
    "/redo": "Redo the last AI action or code edit.",
    "/copy": "Copy the AI's last response to clipboard.",
    "/paste": "Paste text or images from the clipboard into the prompt.",
    "/models": "Show status table of all local and cloud models.",
    "/autoset": "Automatically install all missing dependencies.",
    "/vscode": "Open the current project in VS Code with LMMs integration.",
    "/canvas": "Show a rich terminal rendering of the context graph.",
    "/code": "Enter deep code generation/editing mode for complex tasks.",
    "/smart": "Toggle Smart Chat mode (Intelligent Agent Routing).",
    "/screenshot": "Take a screenshot of the screen and attach it to context.",
    "/status": "Show system status, VRAM usage, and capabilities.",
    "/doctor": "Diagnose system dependencies, permissions, and tools.",
    "/cloud": "Switch backend to a cloud API (e.g., /cloud openai).",
    "/routing": "Toggle intelligent background agent routing.",
    "/gui": "Launch the graphical user interface (PyQt6).",
    "/exit": "Exit LMMs CLI."
}

def get_help_table():
    from rich.table import Table
    table = Table(show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("Command", style="bold cyan", min_width=15)
    table.add_column("Description", min_width=50)

    for cmd, desc in CLI_COMMANDS.items():
        table.add_row(cmd, desc)
        
    return table
