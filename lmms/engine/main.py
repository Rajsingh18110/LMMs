"""
LMMs Engine CLI Entry Point
Handles commands: lmms run, lmms ps, lmms stop, lmms list, lmms air, lmms server.
"""
import sys
from lmms.lmmsengine.main import main, ensure_server_running

if __name__ == "__main__":
    main()
