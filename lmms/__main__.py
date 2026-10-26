"""
LMMs package entrypoint for 'python -m lmms'.
Dispatches cleanly to launcher.main().
"""
import os
import sys

# Ensure repository root is on sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from launcher import main

if __name__ == "__main__":
    main()
