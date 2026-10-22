"""
lmms.backend.notifications - Desktop and OS-level notification manager.
Delivers notifications via notify-send (Linux), osascript (macOS), or stdout/bell fallback.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
from typing import Optional


def send_notification(title: str, message: str, urgency: str = "normal") -> bool:
    """Delivers an OS desktop notification."""
    # 1. Linux notify-send
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, "-a", "LMMs OS", title, message],
                capture_output=True,
                check=False,
                timeout=2,
            )
            return True
        except Exception:
            pass

    # 2. macOS osascript
    if sys.platform == "darwin" and shutil.which("osascript"):
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, check=False, timeout=2)
            return True
        except Exception:
            pass

    # 3. Terminal audible/visual bell fallback
    try:
        sys.stderr.write(f"\a[Notification: {title}] {message}\n")
        sys.stderr.flush()
        return True
    except Exception:
        return False
