"""
Gemini / Antigravity CLI-style permission prompter for LMMs.
Provides an interactive menu with arrow key navigation, Esc-to-cancel,
session allowlisting, and persistent settings.json/config.json storage.
"""

import os
import sys
import json
import re
import shlex
from enum import Enum
from typing import Optional, Set, Tuple

# In-memory allowlist for current conversation / session
_SESSION_ALLOWED_PREFIXES: Set[str] = set()

CONFIG_PATH = os.path.expanduser("~/.lmms/config.json")
SETTINGS_PATH = os.path.expanduser("~/.lmms/settings.json")


class PermissionAction(str, Enum):
    ALLOW_ONCE = "allow_once"
    ALLOW_SESSION = "allow_session"
    ALLOW_PERSIST = "allow_persist"
    DENY = "deny"


class PermissionResult(tuple):
    """
    Subclass of tuple (action, prefix) for full backward compatibility
    with existing callers `action, prefix = ask_permission_interactive(...)`,
    while also exposing `.command`, `.action`, and `.prefix`.
    """
    def __new__(cls, action: PermissionAction, prefix: str, command: Optional[str] = None):
        return super(PermissionResult, cls).__new__(cls, (action, prefix))

    def __init__(self, action: PermissionAction, prefix: str, command: Optional[str] = None):
        self.action = action
        self.prefix = prefix
        self.command = command or prefix


def load_persistent_allowed_prefixes() -> Set[str]:
    """Loads persistent allowed command prefixes from config.json or settings.json."""
    allowed = set()
    for path in (SETTINGS_PATH, CONFIG_PATH):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cmd_list = data.get("allowed_commands", [])
                    if isinstance(cmd_list, list):
                        for c in cmd_list:
                            if isinstance(c, str) and c.strip():
                                allowed.add(c.strip())
            except Exception:
                pass
    return allowed


def save_persistent_allowed_prefix(prefix: str) -> None:
    """Persists an allowed command prefix to ~/.lmms/config.json and settings.json."""
    prefix = prefix.strip()
    if not prefix:
        return

    _SESSION_ALLOWED_PREFIXES.add(prefix)

    # 1. Update config.json
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        data = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        current = data.get("allowed_commands", [])
        if not isinstance(current, list):
            current = []
        if prefix not in current:
            current.append(prefix)
        data["allowed_commands"] = current
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

    # 2. Update settings.json (for direct Gemini/Antigravity parity)
    try:
        data = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        current = data.get("allowed_commands", [])
        if not isinstance(current, list):
            current = []
        if prefix not in current:
            current.append(prefix)
        data["allowed_commands"] = current
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


def is_command_always_allowed(command_str: str) -> bool:
    """Returns True if the command starts with any session or persistent allowed prefix."""
    cmd = command_str.strip()
    if not cmd:
        return False

    # Check session allowlist
    for p in _SESSION_ALLOWED_PREFIXES:
        if cmd == p or cmd.startswith(p + " ") or cmd.startswith(p + "\t"):
            return True

    # Check persistent allowlist
    persistent = load_persistent_allowed_prefixes()
    for p in persistent:
        if cmd == p or cmd.startswith(p + " ") or cmd.startswith(p + "\t"):
            _SESSION_ALLOWED_PREFIXES.add(p)
            return True

    return False


def extract_base_command_prefix(command_str: str) -> str:
    """
    Extracts an intuitive, safe command prefix for allowlisting.
    e.g. 'git status -s' -> 'git status'
         'git diff HEAD~1' -> 'git diff'
         'npm test --watch' -> 'npm test'
         'pytest tests/test_foo.py' -> 'pytest'
         'ls -la /foo' -> 'ls'
         'du -sh Projects' -> 'du'
    """
    cmd = command_str.strip()
    if not cmd:
        return "command"

    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()

    if not parts:
        return cmd

    first = parts[0]
    multi_token_tools = {
        "git": ["status", "diff", "log", "branch", "show", "rev-parse", "grep", "checkout", "add", "commit"],
        "npm": ["test", "run", "start", "list", "install", "i"],
        "pnpm": ["test", "run", "start", "list", "install", "i"],
        "yarn": ["test", "run", "start", "list", "install"],
        "cargo": ["test", "check", "build", "run"],
        "docker": ["ps", "images", "logs", "inspect"],
        "kubectl": ["get", "describe", "logs"],
    }

    if first in multi_token_tools and len(parts) > 1 and not parts[1].startswith("-"):
        sub = parts[1]
        if sub in multi_token_tools[first]:
            return f"{first} {sub}"

    return first


def _flush_input_buffer(fd: Optional[int] = None) -> None:
    """Flushes any leftover keystrokes in stdin to prevent buffer bleeding into subsequent prompts."""
    if os.name == "nt":
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        except Exception:
            pass
    else:
        try:
            import termios
            if fd is not None:
                termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass


def _read_single_key(fd: Optional[int] = None) -> str:
    """Reads a single key or ANSI escape sequence from stdin cross-platform."""
    if os.name == "nt":
        try:
            import msvcrt
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):
                ch2 = msvcrt.getch()
                if ch2 == b"H": return "\x1b[A"
                elif ch2 == b"P": return "\x1b[B"
                elif ch2 == b"K": return "\x1b[D"
                elif ch2 == b"M": return "\x1b[C"
                return ""
            elif ch in (b"\r", b"\n"):
                return "\n"
            elif ch == b"\x1b":
                return "\x1b"
            elif ch == b"\t":
                return "\t"
            elif ch == b"\x07":
                return "\x07"
            elif ch == b"\x12":
                return "\x12"
            elif ch == b"\x03":
                return "\x03"
            try:
                return ch.decode("latin1", errors="ignore")
            except Exception:
                return ""
        except Exception:
            return ""

    try:
        raw = os.read(fd, 32).decode("utf-8", errors="ignore")
    except Exception:
        raw = sys.stdin.read(1)
    if not raw:
        return ""
    if raw == "\x1b":
        # Check if more characters are immediately available (escape sequence)
        try:
            import select
            r, _, _ = select.select([fd], [], [], 0.08)
            if r:
                more = os.read(fd, 31).decode("utf-8", errors="ignore")
                raw += more
        except Exception:
            pass
    return raw


def _is_up_key(k: str) -> bool:
    return k in ("\x1b[A", "\x1bOA", "k", "K")


def _is_down_key(k: str) -> bool:
    return k in ("\x1b[B", "\x1bOB", "j", "J")


def ask_permission_interactive(
    command_str: str,
    target_type: str = "command",
    details: Optional[str] = None
) -> PermissionResult:
    """
    Renders an interactive Gemini/Antigravity CLI style permission dialog:
    
    Requesting permission for:
      git status
    
    Run this command?
    > 1. Yes, run command
      2. Yes, and always allow in this conversation for commands that start with 'git status'
      3. Yes, and always allow for commands that start with 'git status' (Persist to settings.json)
      4. No, cancel
    
    ↑/↓ Navigate • tab Amend • ctrl+g edit/expand command • ctrl+r Review
    esc to cancel
    """
    clean_cmd = command_str.strip()
    prefix = extract_base_command_prefix(clean_cmd)

    # Check if already allowed in session or settings
    if is_command_always_allowed(clean_cmd):
        return PermissionResult(PermissionAction.ALLOW_SESSION, prefix, clean_cmd)

    def build_options(p_prefix: str) -> list:
        return [
            f"1. Yes, run {target_type}",
            f"2. Yes, and always allow in this conversation for commands that start with '{p_prefix}'",
            f"3. Yes, and always allow for commands that start with '{p_prefix}' (Persist to settings.json)",
            "4. No, cancel"
        ]

    options = build_options(prefix)

    # Non-interactive / headless fallback
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        sys.stdout.write(f"\n\033[1;37mRequesting permission for:\033[0m\n  \033[36m{clean_cmd}\033[0m\n\n")
        sys.stdout.write(f"Run this {target_type}?\n")
        for opt in options:
            sys.stdout.write(f"  {opt}\n")
        sys.stdout.write("Select [1-4] (default 4): ")
        sys.stdout.flush()
        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            choice = "4"
        if choice in ("1", "y", "yes"):
            return PermissionResult(PermissionAction.ALLOW_ONCE, prefix, clean_cmd)
        elif choice == "2":
            _SESSION_ALLOWED_PREFIXES.add(prefix)
            return PermissionResult(PermissionAction.ALLOW_SESSION, prefix, clean_cmd)
        elif choice == "3":
            save_persistent_allowed_prefix(prefix)
            return PermissionResult(PermissionAction.ALLOW_PERSIST, prefix, clean_cmd)
        else:
            return PermissionResult(PermissionAction.DENY, prefix, clean_cmd)

    # Interactive TTY mode with ANSI navigation
    old_settings = None
    fd = None
    if os.name != "nt":
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
        except Exception:
            pass

    selected_idx = 0
    num_options = len(options)

    def print_header(cmd_text: str):
        sys.stdout.write(f"\n\033[1;37mRequesting permission for:\033[0m\n")
        sys.stdout.write(f"  \033[1m{cmd_text}\033[0m\n")
        if details:
            sys.stdout.write(f"  \033[2m{details}\033[0m\n")
        sys.stdout.write(f"\n\033[1;37mRun this {target_type}?\033[0m\n")
        sys.stdout.flush()

    print_header(clean_cmd)

    def render_menu(current_idx: int, first_time: bool = False):
        if not first_time:
            # Move cursor up num_options + 3 lines (options + 2 footer lines)
            sys.stdout.write(f"\033[{num_options + 3}A")

        for idx, opt in enumerate(options):
            sys.stdout.write("\033[2K\r")  # clear line
            if idx == current_idx:
                sys.stdout.write(f"\033[1;36m> {opt}\033[0m\n")
            else:
                sys.stdout.write(f"  \033[37m{opt}\033[0m\n")

        sys.stdout.write("\033[2K\r\n")  # blank line
        sys.stdout.write("\033[2K\r\033[36m↑/↓ Navigate • tab Amend • ctrl+g edit/expand command • ctrl+r Review\033[0m\n")
        sys.stdout.write("\033[2K\r\033[36mesc to cancel\033[0m\n")
        sys.stdout.flush()

    try:
        _flush_input_buffer(fd)
        if os.name != "nt" and fd is not None:
            try:
                import tty
                tty.setcbreak(fd)
            except Exception:
                pass
        render_menu(selected_idx, first_time=True)

        while True:
            key = _read_single_key(fd)

            if key in ("\r", "\n"):
                # Enter pressed
                break
            elif _is_up_key(key):
                selected_idx = (selected_idx - 1) % num_options
                render_menu(selected_idx)
            elif _is_down_key(key):
                selected_idx = (selected_idx + 1) % num_options
                render_menu(selected_idx)
            elif key in ("1", "2", "3", "4"):
                selected_idx = int(key) - 1
                render_menu(selected_idx)
                break
            elif key in ("\t", "\x07"):  # Tab (Amend) or Ctrl+G (edit/expand)
                if os.name != "nt" and old_settings is not None and fd is not None:
                    try:
                        import termios
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    except Exception:
                        pass
                sys.stdout.write("\n\033[1;33mAmend command:\033[0m ")
                sys.stdout.flush()
                try:
                    try:
                        import readline
                        readline.set_startup_hook(lambda: readline.insert_text(clean_cmd))
                    except ImportError:
                        readline = None
                    amended = input().strip()
                    if readline:
                        readline.set_startup_hook(None)
                    if amended:
                        clean_cmd = amended
                        prefix = extract_base_command_prefix(clean_cmd)
                        options = build_options(prefix)
                except Exception:
                    pass
                if os.name != "nt" and fd is not None:
                    try:
                        import tty
                        tty.setcbreak(fd)
                    except Exception:
                        pass
                print_header(clean_cmd)
                render_menu(selected_idx, first_time=True)

            elif key == "\x12":  # Ctrl+R (Review)
                if os.name != "nt" and old_settings is not None and fd is not None:
                    try:
                        import termios
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    except Exception:
                        pass
                sys.stdout.write("\n\033[1;34m─── Command Review ───────────────────────────\033[0m\n")
                sys.stdout.write(f"  \033[1;37mCommand:\033[0m   {clean_cmd}\n")
                sys.stdout.write(f"  \033[1;37mPrefix:\033[0m    {prefix}\n")
                sys.stdout.write(f"  \033[1;37mTarget:\033[0m    {target_type}\n")
                if details:
                    sys.stdout.write(f"  \033[1;37mDetails:\033[0m   {details}\n")
                sys.stdout.write("  \033[2mSafety: Audited via CompletionGuard & PermissionManager\033[0m\n")
                sys.stdout.write("\033[1;34m──────────────────────────────────────────────\033[0m\n")
                sys.stdout.write("\033[dim]Press any key to return to menu...\033[0m")
                sys.stdout.flush()
                if os.name != "nt" and fd is not None:
                    try:
                        import tty
                        tty.setcbreak(fd)
                    except Exception:
                        pass
                _read_single_key(fd)
                print_header(clean_cmd)
                render_menu(selected_idx, first_time=True)

            elif key in ("\x1b", "\x03", "q", "Q", "n", "N"):  # Esc, Ctrl+C, q, n
                selected_idx = 3  # cancel
                break
    except Exception:
        selected_idx = 3
    finally:
        if os.name != "nt" and old_settings is not None and fd is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
        _flush_input_buffer(fd)
        sys.stdout.write("\n")
        sys.stdout.flush()

    if selected_idx == 0:
        return PermissionResult(PermissionAction.ALLOW_ONCE, prefix, clean_cmd)
    elif selected_idx == 1:
        _SESSION_ALLOWED_PREFIXES.add(prefix)
        return PermissionResult(PermissionAction.ALLOW_SESSION, prefix, clean_cmd)
    elif selected_idx == 2:
        save_persistent_allowed_prefix(prefix)
        return PermissionResult(PermissionAction.ALLOW_PERSIST, prefix, clean_cmd)
    else:
        return PermissionResult(PermissionAction.DENY, prefix, clean_cmd)


def ask_browser_profile_interactive(profiles: dict) -> Optional[dict]:
    """
    Renders an interactive menu showing discovered Chrome accounts and email IDs.
    Returns the selected profile metadata dict or None if cancelled.
    """
    if not profiles:
        return None

    profile_list = list(profiles.items())
    options = []
    for idx, (display_name, data) in enumerate(profile_list, 1):
        options.append(f"{idx}. {display_name}")
    options.append(f"{len(profile_list) + 1}. Cancel / Deny")

    cancel_idx = len(options) - 1

    # Non-interactive fallback
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        sys.stdout.write("\n\033[1;37mRequesting permission for:\033[0m\n  \033[36mbrowser.open_authenticated (access existing logged-in browser session)\033[0m\n\n")
        sys.stdout.write("Select which Chrome account session to open:\n")
        for opt in options:
            sys.stdout.write(f"  {opt}\n")
        sys.stdout.write(f"Select [1-{len(options)}] (default {len(options)}): ")
        sys.stdout.flush()
        try:
            choice = input().strip()
            num = int(choice) - 1
            if 0 <= num < len(profile_list):
                return profile_list[num][1]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        return None

    # Interactive TTY mode with ANSI navigation
    old_settings = None
    fd = None
    if os.name != "nt":
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
        except Exception:
            pass

    selected_idx = 0
    num_options = len(options)

    sys.stdout.write("\n\033[1;37mRequesting permission for:\033[0m\n")
    sys.stdout.write("  \033[1;36mbrowser.open_authenticated (access existing logged-in browser session)\033[0m\n")
    sys.stdout.write("\033[1;37mSelect which Chrome account session to open:\033[0m\n")
    sys.stdout.flush()

    MAX_VISIBLE = 8
    last_drawn_lines = [0]

    def render_menu(current_idx: int, first_time: bool = False):
        if not first_time and last_drawn_lines[0] > 0:
            sys.stdout.write(f"\033[{last_drawn_lines[0]}A")

        lines_printed = 0
        if num_options <= MAX_VISIBLE:
            visible_range = range(num_options)
            show_top_more = False
            show_bottom_more = False
        else:
            half = MAX_VISIBLE // 2
            start = max(0, min(current_idx - half, num_options - MAX_VISIBLE))
            end = min(num_options, start + MAX_VISIBLE)
            visible_range = range(start, end)
            show_top_more = (start > 0)
            show_bottom_more = (end < num_options)

        if show_top_more:
            sys.stdout.write("\033[2K\r  \033[2m▲  ... additional accounts above ...\033[0m\n")
            lines_printed += 1

        for idx in visible_range:
            opt = options[idx]
            sys.stdout.write("\033[2K\r")
            if idx == current_idx:
                sys.stdout.write(f"\033[1;36m> {opt}\033[0m\n")
            else:
                sys.stdout.write(f"  \033[37m{opt}\033[0m\n")
            lines_printed += 1

        if show_bottom_more:
            sys.stdout.write("\033[2K\r  \033[2m▼  ... additional accounts below ...\033[0m\n")
            lines_printed += 1

        sys.stdout.write("\033[2K\r\n")
        lines_printed += 1
        sys.stdout.write("\033[2K\r\033[36m↑/↓ Navigate • enter to select • type number (e.g. 12)\033[0m\n")
        lines_printed += 1
        sys.stdout.write("\033[2K\r\033[36mesc to cancel\033[0m\n")
        lines_printed += 1
        sys.stdout.flush()
        last_drawn_lines[0] = lines_printed

    try:
        _flush_input_buffer(fd)
        if os.name != "nt" and fd is not None:
            try:
                import tty
                tty.setcbreak(fd)
            except Exception:
                pass
        render_menu(selected_idx, first_time=True)

        num_buffer = ""
        while True:
            key = _read_single_key(fd)

            if key in ("\r", "\n"):
                break
            elif _is_up_key(key):
                num_buffer = ""
                selected_idx = (selected_idx - 1) % num_options
                render_menu(selected_idx)
            elif _is_down_key(key):
                num_buffer = ""
                selected_idx = (selected_idx + 1) % num_options
                render_menu(selected_idx)
            elif key.isdigit():
                candidate = num_buffer + key
                try:
                    c_num = int(candidate)
                    if 1 <= c_num <= num_options:
                        num_buffer = candidate
                        selected_idx = c_num - 1
                        render_menu(selected_idx)
                    else:
                        single_num = int(key)
                        if 1 <= single_num <= num_options:
                            num_buffer = key
                            selected_idx = single_num - 1
                            render_menu(selected_idx)
                except ValueError:
                    num_buffer = ""
            elif key in ("\x1b", "\x03", "q", "Q", "c", "C"):
                selected_idx = cancel_idx
                break
    except Exception:
        selected_idx = cancel_idx
    finally:
        if os.name != "nt" and old_settings is not None and fd is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
        _flush_input_buffer(fd)
        sys.stdout.write("\n")
        sys.stdout.flush()

    if selected_idx < len(profile_list):
        return profile_list[selected_idx][1]
    return None
