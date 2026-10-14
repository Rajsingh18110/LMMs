"""
LMMs TUI (Terminal User Interface) Entry Point
Evolving LMMs CLI into an interactive Codex-style TUI.
"""
import sys
from lmms.backend.main import run_cli

def main():
    """Launch the interactive terminal interface."""
    run_cli()

if __name__ == "__main__":
    main()
