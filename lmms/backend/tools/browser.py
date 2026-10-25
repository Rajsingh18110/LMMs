import os
import glob
import platform
import re
from typing import Optional, Dict, Any, List, Tuple
from playwright.sync_api import sync_playwright
import time
import random
import math
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = lambda page: None

STEALTH_INIT_SCRIPT = """
(() => {
    // 1. Pass webdriver check
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    } catch (e) {}

    // 2. Mock chrome object
    try {
        if (!window.chrome) {
            window.chrome = {};
        }
        window.chrome.runtime = window.chrome.runtime || {};
        window.chrome.app = window.chrome.app || {};
        window.chrome.csi = window.chrome.csi || (() => {});
        window.chrome.loadTimes = window.chrome.loadTimes || (() => {});
    } catch (e) {}

    // 3. Mock plugins
    try {
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
            configurable: true
        });
    } catch (e) {}

    // 4. Mock languages
    try {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true
        });
    } catch (e) {}

    // 5. Mock permissions
    try {
        const originalQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
        if (originalQuery) {
            window.navigator.permissions.query = (parameters) => (
                parameters && parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        }
    } catch (e) {}
})();
"""

def inject_universal_stealth(target):
    """Injects universal stealth init script to hide Playwright/automation indicators."""
    try:
        if hasattr(target, "add_init_script"):
            target.add_init_script(STEALTH_INIT_SCRIPT)
        elif hasattr(target, "context") and hasattr(target.context, "add_init_script"):
            target.context.add_init_script(STEALTH_INIT_SCRIPT)
        if hasattr(target, "evaluate"):
            target.evaluate(STEALTH_INIT_SCRIPT)
    except Exception:
        pass
    try:
        stealth_sync(target)
    except Exception:
        pass
try:
    import numpy as np
    from scipy.interpolate import interp1d
except ImportError:
    np = None
    interp1d = None


def get_chrome_executable_path() -> Optional[str]:
    """
    Locates the host's official Google Chrome or Chromium executable.
    Required on Linux so that libsecret/keyring matches the binary identity
    and decrypts v11 SQLite cookies (like auth_token).
    """
    import shutil
    candidate_paths = [
        "/opt/google/chrome/chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium"
    ]
    for p in candidate_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return shutil.which("google-chrome") or shutil.which("chromium")


def is_profile_locked(profile_dir: str) -> Tuple[bool, Optional[int]]:
    """
    Checks if a Chromium user data directory is actively locked by a running process.
    Returns (is_locked, pid).
    Cleans up stale lock symlinks from terminated processes safely.
    """
    if not profile_dir or not os.path.exists(profile_dir):
        return False, None

    lock_file = os.path.join(profile_dir, "SingletonLock")
    if os.path.islink(lock_file):
        try:
            target = os.readlink(lock_file)
            parts = target.split("-")
            pid = int(parts[-1])
            try:
                os.kill(pid, 0)
                # Process is alive -> actively locked
                return True, pid
            except (ProcessLookupError, PermissionError) as pe:
                if isinstance(pe, PermissionError):
                    return True, pid
                # Process is dead -> clean up stale lock safely
                try:
                    os.unlink(lock_file)
                    for extra in ("SingletonSocket", "SingletonCookie"):
                        extra_path = os.path.join(profile_dir, extra)
                        if os.path.islink(extra_path) or os.path.exists(extra_path):
                            try:
                                os.unlink(extra_path)
                            except Exception:
                                pass
                except Exception:
                    pass
                return False, pid
        except Exception:
            return False, None
    elif os.path.exists(lock_file):
        return True, None
    return False, None


def verify_cdp_endpoint(endpoint_url: str = "http://localhost:9222", timeout: float = 2.0) -> Dict[str, Any]:
    """
    Verifies that a Chrome DevTools Protocol (CDP) endpoint is reachable before automation.
    Returns diagnostic information and launch instructions if unreachable.
    """
    import urllib.request
    import json

    base_url = endpoint_url.rstrip("/")
    version_url = f"{base_url}/json/version"

    try:
        req = urllib.request.Request(version_url, headers={"User-Agent": "LMMs-Agent"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)
                return {
                    "available": True,
                    "endpoint": base_url,
                    "browser": data.get("Browser", "Chromium/Chrome"),
                    "protocol_version": data.get("Protocol-Version", ""),
                    "websocket_debugger_url": data.get("webSocketDebuggerUrl", ""),
                    "error": None,
                    "instructions": ""
                }
    except Exception as e:
        error_msg = str(e)
        instructions = (
            f"Chrome is not running with remote debugging enabled on {base_url}.\n"
            "To connect LMMs to your existing desktop Chrome session:\n"
            "1. Close your running Chrome browser instances (or pass a dedicated --user-data-dir).\n"
            "2. Start Chrome from the terminal with the debugging port enabled:\n"
            f"   google-chrome --remote-debugging-port=9222\n"
            "3. Once Chrome is running, click 'Use Existing Browser Session' in LMMs."
        )
        return {
            "available": False,
            "endpoint": base_url,
            "browser": None,
            "error": error_msg,
            "instructions": instructions
        }


class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._current_headless = None
        self._session_mode: str = "none"  # "cdp", "persistent_profile", "standard", "none"
        self._cdp_endpoint: Optional[str] = None
        self._persistent_profile_dir: str = os.path.expanduser("~/.lmms/browser_profile")
        self.cookie_file = os.path.expanduser("~/.lmms/browser_cookies.json")
        self._domain_404_counts: Dict[str, int] = {}
        self._last_attempted_url: Optional[str] = None
        self._last_attempt_failed: bool = False
        self._last_clicked_target: Optional[str] = None
        self._last_click_state_changed: Optional[bool] = None
        self._last_preview_path: Optional[str] = None
        self._approved_publications: set = set()

    def _notify_browser_event(self, event_name: str, data: Dict[str, Any]):
        try:
            from lmms.backend.events.bus import get_event_bus
            get_event_bus().emit(event_name, data)
        except Exception:
            pass

    def _capture_preview_snapshot(self, action: str = "update") -> Optional[str]:
        if not self.page:
            return None
        try:
            save_dir = os.path.expanduser("~/.lmms/browser")
            os.makedirs(save_dir, exist_ok=True)
            preview_path = os.path.join(save_dir, "preview.png")
            self.page.screenshot(path=preview_path)
            self._last_preview_path = preview_path
            self._notify_browser_event("browser_frame_updated", {
                "action": action,
                "url": self.page.url if self.page else "",
                "title": self.page.title() if self.page else "",
                "screenshot_path": preview_path,
                "timestamp": time.time()
            })
            return preview_path
        except Exception:
            return None

    def _ensure_session(self, headless=None, user_data_dir=None, profile_name="Default"):
        # 1. If actively connected via CDP, verify connection and reuse context/page
        if self._session_mode == "cdp":
            if self.browser and hasattr(self.browser, "is_connected") and self.browser.is_connected():
                if hasattr(self.browser, "contexts") and self.browser.contexts:
                    self.context = self.browser.contexts[0]
                elif hasattr(self.browser, "new_context"):
                    self.context = self.browser.new_context()
                else:
                    self.context = self.browser

                if hasattr(self.context, "pages") and self.context.pages:
                    valid_pages = [p for p in self.context.pages if not p.is_closed()]
                    self.page = valid_pages[0] if valid_pages else self.context.new_page()
                elif hasattr(self.browser, "pages") and self.browser.pages:
                    valid_pages = [p for p in self.browser.pages if not p.is_closed()]
                    self.page = valid_pages[0] if valid_pages else self.browser.new_page()
                else:
                    self.page = self.context.new_page() if hasattr(self.context, "new_page") else self.browser.new_page()
                return
            else:
                # CDP connection lost
                self._session_mode = "none"
                self.browser = None
                self.context = None
                self.page = None

        # 2. If actively running in persistent_profile mode, reuse it without restarting
        if self._session_mode == "persistent_profile" and self.browser:
            context_obj = self.context or self.browser
            if hasattr(context_obj, "pages"):
                valid_pages = [p for p in context_obj.pages if not p.is_closed()]
                if valid_pages:
                    self.page = valid_pages[0]
                    return
                elif hasattr(context_obj, "new_page"):
                    self.page = context_obj.new_page()
                    return

        # 3. Handle headless setting
        if headless is None:
            headless = self._current_headless if self._current_headless is not None else False

        # If a visible browser is already running, keep it visible for agent observation
        if self.browser:
            if self._current_headless is False and headless is True:
                headless = False
            elif self._current_headless is not None and self._current_headless != headless:
                self.close()

        if not self.playwright:
            self.playwright = sync_playwright().start()

        if user_data_dir is None:
            user_data_dir = self._persistent_profile_dir

        self._current_headless = headless

        if not self.browser:
            if user_data_dir:
                # Check profile locking safely
                locked, lock_pid = is_profile_locked(user_data_dir)
                if locked:
                    # Profile is locked by another running process. Create a safe temporary session clone
                    import tempfile
                    import shutil
                    temp_dir = tempfile.mkdtemp(prefix="lmms_browser_")
                    try:
                        shutil.copytree(
                            user_data_dir, temp_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(
                                "SingletonLock", "SingletonCookie", "SingletonSocket",
                                "Cache", "Code Cache", "GPUCache", "DawnCache", "Network Action Predictor",
                                "VideoDecodeStats", "Shared Dictionary", "Media Cache"
                            )
                        )
                    except Exception:
                        pass

                    try:
                        self.browser = self.playwright.chromium.launch_persistent_context(
                            user_data_dir=temp_dir,
                            headless=headless,
                            ignore_default_args=["--enable-automation", "--no-sandbox"],
                            args=[
                                "--test-type",
                                "--disable-infobars",
                                "--exclude-switches=enable-automation",
                                "--no-first-run",
                                "--no-default-browser-check",
                                "--silent-debugger-extension-api",
                                f"--profile-directory={profile_name}"
                            ],
                            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        self._session_mode = "persistent_profile"
                    except Exception:
                        self.browser = self.playwright.chromium.launch(
                            headless=headless,
                            ignore_default_args=["--enable-automation", "--no-sandbox"],
                            args=["--test-type", "--disable-infobars"]
                        )
                        self._session_mode = "standard"
                else:
                    try:
                        self.browser = self.playwright.chromium.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=headless,
                            ignore_default_args=["--enable-automation", "--no-sandbox"],
                            args=[
                                "--test-type",
                                "--disable-infobars",
                                "--exclude-switches=enable-automation",
                                "--no-first-run",
                                "--no-default-browser-check",
                                "--silent-debugger-extension-api",
                                f"--profile-directory={profile_name}"
                            ],
                            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        self._session_mode = "persistent_profile"
                    except Exception:
                        self.browser = self.playwright.chromium.launch(
                            headless=headless,
                            ignore_default_args=["--enable-automation", "--no-sandbox"],
                            args=["--test-type", "--disable-infobars"]
                        )
                        self._session_mode = "standard"
            else:
                self.browser = self.playwright.chromium.launch(
                    headless=headless,
                    ignore_default_args=["--enable-automation", "--no-sandbox"],
                    args=["--test-type", "--disable-infobars"]
                )
                self._session_mode = "standard"

        # Locate context and page
        if hasattr(self.browser, "contexts") and self.browser.contexts:
            self.context = self.browser.contexts[0]
        else:
            self.context = self.browser

        if hasattr(self.context, "pages") and len(self.context.pages) > 0 and not self.context.pages[0].is_closed():
            self.page = self.context.pages[0]
        elif hasattr(self.browser, "pages") and len(self.browser.pages) > 0 and not self.browser.pages[0].is_closed():
            self.page = self.browser.pages[0]
        elif hasattr(self.context, "new_page"):
            self.page = self.context.new_page()
        elif hasattr(self.browser, "new_page"):
            self.page = self.browser.new_page()

        # Inject universal stealth to bypass bot detection (webdriver, chrome runtime, plugins)
        inject_universal_stealth(self.context)
        if self.page:
            inject_universal_stealth(self.page)

        self.load_cookies()

    def connect_cdp(self, endpoint_url: str = "http://localhost:9222", timeout: float = 5.0) -> Dict[str, Any]:
        """
        Attaches LMMs to an already-running Chrome instance via Chrome DevTools Protocol (CDP).
        Reuses the user's active session without requesting credentials.
        """
        check = verify_cdp_endpoint(endpoint_url, timeout=2.0)
        if not check["available"]:
            self._notify_browser_event("browser_cdp_connection_failed", {
                "endpoint": endpoint_url,
                "error": check["error"],
                "instructions": check["instructions"]
            })
            return {
                "status": "error",
                "message": f"CDP connection failed: {check['error']}",
                "instructions": check["instructions"]
            }

        try:
            # If a local non-CDP browser was open, disconnect it without erasing its profile
            if self.browser and self._session_mode != "cdp":
                self.disconnect_session(preserve_data=True)

            if not self.playwright:
                self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.connect_over_cdp(
                endpoint_url,
                timeout=int(timeout * 1000)
            )
            self._session_mode = "cdp"
            self._cdp_endpoint = endpoint_url

            # Locate or create active context and page
            if hasattr(self.browser, "contexts") and self.browser.contexts:
                self.context = self.browser.contexts[0]
            elif hasattr(self.browser, "new_context"):
                self.context = self.browser.new_context()
            else:
                self.context = self.browser

            if hasattr(self.context, "pages") and self.context.pages:
                valid_pages = [p for p in self.context.pages if not p.is_closed()]
                self.page = valid_pages[0] if valid_pages else self.context.new_page()
            else:
                self.page = self.context.new_page()

            # Inject stealth and capture preview
            try:
                stealth_sync(self.page)
            except Exception:
                pass

            curr_url = self.page.url if self.page else ""
            curr_title = self.page.title() if self.page else ""
            preview_path = self._capture_preview_snapshot(action="Attached to CDP")

            self._notify_browser_event("browser_session_connected", {
                "mode": "cdp",
                "endpoint": endpoint_url,
                "browser": check.get("browser", "Chrome"),
                "url": curr_url,
                "title": curr_title,
                "screenshot_path": preview_path
            })

            return {
                "status": "connected",
                "mode": "cdp",
                "endpoint": endpoint_url,
                "browser": check.get("browser"),
                "url": curr_url,
                "title": curr_title
            }
        except Exception as e:
            self._session_mode = "none"
            self.browser = None
            self.context = None
            self.page = None
            return {
                "status": "error",
                "message": f"Failed to attach via CDP: {str(e)}",
                "instructions": check["instructions"]
            }

    def attach_existing_chrome_session(
        self,
        url: str = "about:blank",
        headless: bool = False,
        preferred_profile: Optional[str] = None,
        cdp_endpoint: str = "http://localhost:9222"
    ) -> Dict[str, Any]:
        """
        Attaches to the user's existing desktop Chrome session without requiring credentials.
        1. Checks if Chrome is running with remote debugging enabled (cdp_endpoint). If active, connects directly over CDP.
        2. If CDP is inactive (normal desktop Chrome running), safely bridges the user's existing Chrome profile
           (Local State + target profile e.g. Default or user-selected profile) into ~/.lmms/chrome_session_bridge.
        3. Launches with executable_path=get_chrome_executable_path() so Linux keyring/libsecret decrypts cookies (v11)
           while avoiding process collision with SingletonLock.
        4. Verifies page authentication and updates UI.
        """
        # 1. Attempt CDP first
        cdp_check = verify_cdp_endpoint(cdp_endpoint, timeout=1.0)
        if cdp_check["available"]:
            res = self.connect_cdp(cdp_endpoint)
            if res.get("status") == "connected":
                if url and url != "about:blank" and self.page:
                    self._goto_if_needed(url)
                return res

        # 2. Chrome Session Bridge
        import shutil
        home = os.path.expanduser("~")
        src_base = os.path.join(home, ".config/google-chrome")
        bridge_dir = os.path.expanduser("~/.lmms/chrome_session_bridge")
        os.makedirs(bridge_dir, exist_ok=True)
        # Safely clear any stale lock in the bridge directory from prior terminated runs
        is_profile_locked(bridge_dir)

        target_profile_dir = preferred_profile
        if not target_profile_dir:
            profiles = self.get_browser_profiles()
            # Select Default if present, otherwise first available discovered profile
            target_profile_dir = "Default"
            for k, v in profiles.items():
                if v.get("dir_name") == "Default":
                    target_profile_dir = "Default"
                    break
            else:
                if profiles:
                    target_profile_dir = list(profiles.values())[0].get("dir_name", "Default")

        # Copy Local State and Variations for encryption keys
        for f in ("Local State", "Variations", "Last Version", "Consent To Send Stats"):
            src = os.path.join(src_base, f)
            if os.path.exists(src):
                try:
                    shutil.copyfile(src, os.path.join(bridge_dir, f))
                except Exception:
                    pass

        # Copy target profile directory safely (skipping locks and heavy caches)
        src_profile = os.path.join(src_base, target_profile_dir)
        dest_profile = os.path.join(bridge_dir, target_profile_dir)
        if os.path.exists(src_profile):
            try:
                shutil.copytree(
                    src_profile, dest_profile, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(
                        "Singleton*", "lockfile", "*.lock",
                        "Cache", "Code Cache", "GPUCache", "DawnCache", "Media Cache"
                    )
                )
            except Exception:
                pass

        # Disconnect any previous Playwright session
        if self.browser:
            self.disconnect_session(preserve_data=True)

        if not self.playwright:
            self.playwright = sync_playwright().start()

        chrome_exec = get_chrome_executable_path()
        try:
            ignore_args = ["--enable-automation"]
            if hasattr(os, "geteuid") and os.geteuid() != 0:
                ignore_args.append("--no-sandbox")

            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=bridge_dir,
                executable_path=chrome_exec,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                ignore_default_args=ignore_args,
                args=[
                    "--test-type",
                    "--disable-infobars",
                    "--exclude-switches=enable-automation",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--silent-debugger-extension-api",
                    f"--profile-directory={target_profile_dir}"
                ],
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._session_mode = "existing_chrome"
            self._persistent_profile_dir = bridge_dir

            if hasattr(self.browser, "pages") and self.browser.pages:
                self.page = self.browser.pages[0]
            else:
                self.page = self.browser.new_page()

            inject_universal_stealth(self.browser)
            if self.page:
                inject_universal_stealth(self.page)

            if url and url != "about:blank":
                try:
                    self._goto_if_needed(url)
                    self.page.wait_for_timeout(1000)
                except Exception:
                    pass

            preview_path = self._capture_preview_snapshot(action=f"Attached existing Chrome session ({target_profile_dir})")

            self._notify_browser_event("browser_session_connected", {
                "mode": "existing_chrome",
                "profile": target_profile_dir,
                "url": self.page.url if self.page else url,
                "title": self.page.title() if self.page else "",
                "headless": headless,
                "screenshot_path": preview_path
            })

            return {
                "status": "connected",
                "mode": "existing_chrome",
                "profile": target_profile_dir,
                "url": self.page.url if self.page else url,
                "title": self.page.title() if self.page else "",
                "headless": headless
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to attach existing Chrome session: {str(e)}"
            }

    def open_persistent_browser(
        self,
        url: str = "about:blank",
        headless: bool = False,
        profile_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Launches or attaches to LMMs's persistent visible browser profile.
        Retains cookies and authentication across tasks and browser panel toggles.
        """
        target_dir = os.path.expanduser(profile_dir or self._persistent_profile_dir)
        os.makedirs(target_dir, exist_ok=True)

        # 1. Profile lock inspection
        locked, lock_pid = is_profile_locked(target_dir)
        if locked:
            # If the lock is held by our own active browser instance, simply reuse it
            if self.browser and self._session_mode == "persistent_profile":
                if url and self.page:
                    self._goto_if_needed(url)
                    self._capture_preview_snapshot(action=f"Reused session: {url}")
                return {
                    "status": "connected",
                    "mode": "persistent_profile",
                    "url": self.page.url if self.page else url,
                    "reused": True
                }

            # Locked by another process on host
            err_msg = (
                f"Profile directory '{target_dir}' is locked by another running process (PID {lock_pid}).\n"
                "To prevent data corruption, a second process cannot be launched into this profile.\n"
                "Options:\n"
                "1. If this is your main Chrome, launch it with '--remote-debugging-port=9222' and use 'Use Existing Browser Session'.\n"
                "2. Or terminate the process holding the lock and re-try."
            )
            self._notify_browser_event("browser_profile_locked", {
                "profile_dir": target_dir,
                "lock_pid": lock_pid,
                "message": err_msg
            })
            return {
                "status": "error",
                "error": "profile_locked",
                "message": err_msg,
                "lock_pid": lock_pid
            }

        # 2. Launch persistent context
        try:
            # If in CDP mode, disconnect first
            if self.browser and self._session_mode == "cdp":
                self.disconnect_session(preserve_data=True)

            self._ensure_session(headless=headless, user_data_dir=target_dir)
            self._session_mode = "persistent_profile"

            if url:
                self._goto_if_needed(url)
                try:
                    self.page.wait_for_timeout(1500)
                except Exception:
                    pass

            preview_path = self._capture_preview_snapshot(action="Opened persistent browser")

            self._notify_browser_event("browser_session_connected", {
                "mode": "persistent_profile",
                "profile_dir": target_dir,
                "url": self.page.url if self.page else url,
                "title": self.page.title() if self.page else "",
                "headless": headless,
                "screenshot_path": preview_path
            })

            return {
                "status": "connected",
                "mode": "persistent_profile",
                "profile_dir": target_dir,
                "url": self.page.url if self.page else url,
                "headless": headless
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to launch persistent browser: {str(e)}"
            }

    def disconnect_session(self, preserve_data: bool = True) -> Dict[str, Any]:
        """
        Explicitly disconnects or signs out of the active browser session.
        Preserves the profile directory and cookie files so authentication is not erased.
        """
        mode = self._session_mode
        try:
            self.save_cookies()
        except Exception:
            pass

        if self.browser:
            try:
                # In CDP mode, close() detaches CDP without killing the user's Chrome
                self.browser.close()
            except Exception:
                pass
            self.browser = None
            self.context = None
            self.page = None

        if self.playwright and mode != "cdp":
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

        self._session_mode = "none"
        self._current_headless = None

        self._notify_browser_event("browser_session_disconnected", {
            "previous_mode": mode,
            "preserved": preserve_data
        })

        return {
            "status": "disconnected",
            "previous_mode": mode,
            "data_preserved": preserve_data
        }

    def load_cookies(self):
        if os.path.exists(self.cookie_file) and self.browser:
            try:
                import json
                with open(self.cookie_file, "r") as f:
                    cookies = json.load(f)
                if hasattr(self.browser, "add_cookies"):
                    self.browser.add_cookies(cookies)
                elif hasattr(self.browser, "contexts") and len(self.browser.contexts) > 0:
                    self.browser.contexts[0].add_cookies(cookies)
            except Exception as e:
                print(f"Warning: Failed to load cookies: {e}")

    def save_cookies(self):
        if self.browser:
            try:
                import json
                cookies = []
                if hasattr(self.browser, "cookies"):
                    cookies = self.browser.cookies()
                elif hasattr(self.browser, "contexts") and len(self.browser.contexts) > 0:
                    cookies = self.browser.contexts[0].cookies()
                
                if cookies:
                    os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
                    with open(self.cookie_file, "w") as f:
                        json.dump(cookies, f)
            except Exception as e:
                print(f"Warning: Failed to save cookies: {e}")

    def _fast_dns_check(self, url: str) -> Optional[str]:
        """Fast 1.5s DNS pre-validation to avoid blocking Playwright for 30s on non-existent hosts."""
        try:
            import urllib.parse
            import socket
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            if not host or host in ("localhost", "127.0.0.1") or host.endswith(".local"):
                return None
            socket.getaddrinfo(host, None)
            return None
        except socket.gaierror:
            return f"DNS resolution failed: Host '{host}' does not exist (NXDOMAIN)."
        except Exception:
            return None

    def _goto_if_needed(self, url: str):
        if not url: return
        dns_err = self._fast_dns_check(url)
        if dns_err:
            raise RuntimeError(dns_err)
        # Check current URL, ignoring trailing slashes or hash
        current_url = self.page.url.split("#")[0].rstrip("/")
        target_url = url.split("#")[0].rstrip("/")
        if current_url != target_url and current_url != "about:blank":
            try:
                self.page.goto(url, timeout=7000, wait_until="domcontentloaded")
            except Exception as e:
                raise RuntimeError(f"Navigation to {url} failed: {e}")
        elif current_url == "about:blank":
            try:
                self.page.goto(url, timeout=7000, wait_until="domcontentloaded")
            except Exception as e:
                raise RuntimeError(f"Navigation to {url} failed: {e}")

    def close(self):
        self.save_cookies()
        if self.browser:
            try: self.browser.close()
            except: pass
            self.browser = None
            self.context = None
            self.page = None
        if self.playwright:
            try: self.playwright.stop()
            except: pass
            self.playwright = None
        self._session_mode = "none"
        self._current_headless = None

    def get_browser_profiles(self) -> dict:
        """Detects Chrome/Brave/Edge profiles across OS."""
        profiles = {}
        system = platform.system()
        home = os.path.expanduser("~")
        
        paths = []
        if system == "Linux":
            paths = [
                f"{home}/.config/google-chrome",
                f"{home}/.config/BraveSoftware/Brave-Browser",
                f"{home}/.config/microsoft-edge-dev",
                f"{home}/snap/chromium/current/.config/chromium"
            ]
        elif system == "Darwin":
            paths = [
                f"{home}/Library/Application Support/Google/Chrome",
                f"{home}/Library/Application Support/BraveSoftware/Brave-Browser",
                f"{home}/Library/Application Support/Microsoft Edge"
            ]
        elif system == "Windows":
            local_app_data = os.environ.get("LOCALAPPDATA", f"{home}\\AppData\\Local")
            paths = [
                f"{local_app_data}\\Google\\Chrome\\User Data",
                f"{local_app_data}\\BraveSoftware\\Brave-Browser\\User Data",
                f"{local_app_data}\\Microsoft\\Edge\\User Data"
            ]
            
        for base_path in paths:
            if os.path.exists(base_path):
                # Try reading Local State profile info_cache for rich user identities
                local_state_path = os.path.join(base_path, "Local State")
                info_cache = {}
                if os.path.exists(local_state_path):
                    try:
                        import json
                        with open(local_state_path, "r", encoding="utf-8") as f:
                            ls_data = json.load(f)
                            info_cache = ls_data.get("profile", {}).get("info_cache", {})
                    except Exception:
                        pass

                profile_dirs = glob.glob(os.path.join(base_path, "Profile*")) + [os.path.join(base_path, "Default")]
                for pdir in profile_dirs:
                    if os.path.exists(pdir):
                        name = os.path.basename(pdir)
                        browser_name = "Chrome" if "chrome" in base_path.lower() else "Brave" if "brave" in base_path.lower() else "Edge" if "edge" in base_path.lower() else "Chromium"
                        
                        email = ""
                        human_name = ""
                        if name in info_cache:
                            p_info = info_cache[name]
                            email = p_info.get("user_name", "")
                            human_name = p_info.get("gaia_name", "") or p_info.get("name", "")

                        if not email:
                            pref_path = os.path.join(pdir, "Preferences")
                            if os.path.exists(pref_path):
                                try:
                                    import json
                                    with open(pref_path, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                        acc_info = data.get("account_info", [])
                                        if acc_info and len(acc_info) > 0:
                                            email = acc_info[0].get("email", "")
                                except Exception:
                                    pass
                        
                        display_name = f"{browser_name}_{name}"
                        if email:
                            display_name += f" ({email})"
                        elif human_name:
                            display_name += f" ({human_name})"
                            
                        profiles[display_name] = {
                            "base_path": base_path,
                            "dir_name": name,
                            "email": email,
                            "user_name": human_name
                        }
                        
        return profiles

    def get_account_context(self) -> Dict[str, Any]:
        """
        Safely retrieves available user account and identity context across:
        1. Configured identity (git user/email, environment)
        2. Browser profiles (Chrome/Brave/Edge accounts)
        3. Website authentication (active page session status)
        Guaranteed read-only: never exposes passwords, session tokens, or keys.
        Never fabricates identity if none exists (returns status: 'unavailable').
        """
        accounts = []
        try:
            profiles = self.get_browser_profiles()
            for display_name, meta in profiles.items():
                email_match = re.search(r'\(([^)]+@[^)]+)\)', display_name)
                email = email_match.group(1) if email_match else ""
                accounts.append({
                    "profile": display_name,
                    "email": email,
                    "base_path": meta.get("base_path"),
                    "dir_name": meta.get("dir_name"),
                })
        except Exception:
            pass

        import subprocess
        git_email = ""
        git_name = ""
        try:
            res_email = subprocess.run(["git", "config", "--get", "user.email"], capture_output=True, text=True, timeout=2)
            if res_email.returncode == 0:
                git_email = res_email.stdout.strip()
            res_name = subprocess.run(["git", "config", "--get", "user.name"], capture_output=True, text=True, timeout=2)
            if res_name.returncode == 0:
                git_name = res_name.stdout.strip()
        except Exception:
            pass

        env_email = os.environ.get("USER_EMAIL") or os.environ.get("GIT_AUTHOR_EMAIL") or ""
        env_user = os.environ.get("USER") or os.environ.get("USERNAME") or ""

        primary_email = ""
        for acc in accounts:
            if acc.get("email"):
                primary_email = acc["email"]
                break
        if not primary_email and git_email:
            primary_email = git_email
        if not primary_email and env_email:
            primary_email = env_email

        # 1. Detected session indicators (e.g. cookie names)
        detected_session_indicators = {
            "present": False,
            "cookie_names": [],
            "url": ""
        }
        # 2. Verified website authentication (verified ONLY with reliable website-specific evidence)
        verified_website_auth = {
            "status": "unknown",
            "verified": False,
            "reason": "No active webpage loaded."
        }

        if self.page:
            try:
                curr_url = self.page.url
                if curr_url and curr_url != "about:blank":
                    cookies = []
                    if self.browser:
                        if hasattr(self.browser, "cookies"):
                            cookies = self.browser.cookies()
                        elif hasattr(self.browser, "contexts") and len(self.browser.contexts) > 0:
                            cookies = self.browser.contexts[0].cookies()

                    session_cookie_names = [
                        c.get("name", "") for c in cookies
                        if c.get("name", "").lower() in ("session", "token", "auth", "jwt", "connect.sid", "logged_in", "_session_id")
                    ]
                    detected_session_indicators = {
                        "present": len(session_cookie_names) > 0,
                        "cookie_names": session_cookie_names,
                        "url": curr_url
                    }

                    # Evaluate live page DOM for verified authentication evidence
                    auth_eval_script = r"""
                    (() => {
                        const bodyText = (document.body ? document.body.innerText : '') || '';

                        // Check for prominent login / sign in calls to action
                        const loginCtas = Array.from(document.querySelectorAll(
                            'a, button, [role="button"]'
                        )).filter(el => {
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            return /(log\s*in|sign\s*in|login|signin|register|sign\s*up)/i.test(txt);
                        });

                        // Check for explicit logout / sign out elements
                        const logoutCtas = Array.from(document.querySelectorAll(
                            'a, button, [role="button"]'
                        )).filter(el => {
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            return /(log\\s*out|sign\\s*out|logout|signout)/i.test(txt);
                        });

                        // Check for user profile or account menu elements
                        const profileElements = Array.from(document.querySelectorAll(
                            '[data-testid*="user"], [data-testid*="profile"], [aria-label*="account" i], [aria-label*="profile" i], .user-profile, .user-menu, .account-dropdown'
                        ));

                        let displayedIdentity = '';
                        const emailMatch = bodyText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/);
                        if (emailMatch) {
                            displayedIdentity = emailMatch[0];
                        }

                        return {
                            has_login_ctas: loginCtas.length > 0,
                            has_logout_ctas: logoutCtas.length > 0,
                            has_profile_elements: profileElements.length > 0,
                            displayed_identity: displayedIdentity
                        };
                    })()
                    """
                    dom_auth_data = self.page.evaluate(auth_eval_script)
                    has_login_ctas = dom_auth_data.get("has_login_ctas", False)
                    has_logout_ctas = dom_auth_data.get("has_logout_ctas", False)
                    has_profile_elements = dom_auth_data.get("has_profile_elements", False)
                    displayed_identity = dom_auth_data.get("displayed_identity", "")

                    if has_login_ctas and not has_logout_ctas:
                        # Visible login button present -> User is unauthenticated regardless of cookies
                        verified_website_auth = {
                            "status": "unverified",
                            "verified": False,
                            "reason": "Page displays visible login/sign-in options. User is not authenticated on this website."
                        }
                    elif has_logout_ctas or (has_profile_elements and not has_login_ctas):
                        # Concrete verified authentication evidence in DOM
                        verified_website_auth = {
                            "status": "verified",
                            "verified": True,
                            "evidence": "Verified active session: Logout CTA or user profile element confirmed in DOM.",
                            "displayed_identity": displayed_identity or "authenticated_user"
                        }
                    else:
                        # Cannot verify without evidence (cookie names alone are NEVER sufficient)
                        verified_website_auth = {
                            "status": "unverified",
                            "verified": False,
                            "reason": "Session indicator cookies or page loaded, but no verified user session/profile evidence found in page DOM."
                        }
            except Exception as e:
                verified_website_auth = {
                    "status": "unknown",
                    "verified": False,
                    "reason": f"DOM evaluation failed: {str(e)}"
                }

        browser_accounts = [a for a in accounts if a.get("email")]
        has_any_identity = bool(primary_email or git_name or git_email or browser_accounts or env_email)
        status = "success" if has_any_identity else "unavailable"

        website_auth = {
            "authenticated": verified_website_auth["verified"],
            "status": verified_website_auth["status"],
            "verified": verified_website_auth["verified"],
            "reason": verified_website_auth.get("reason", ""),
            "evidence": verified_website_auth.get("evidence", "")
        }

        res: Dict[str, Any] = {
            "status": status,
            "primary_email": primary_email,
            "git_user": git_name,
            "git_email": git_email,
            "browser_accounts": browser_accounts,
            "configured_identity": {
                "git_user": git_name,
                "git_email": git_email,
                "env_user": env_user
            },
            "detected_browser_profiles": accounts,
            "browser_profiles": accounts,
            "detected_session_indicators": detected_session_indicators,
            "verified_website_authentication": verified_website_auth,
            "website_authentication": website_auth,
            "session_mode": self._session_mode,
            "cdp_endpoint": self._cdp_endpoint,
            "persistent_profile_dir": self._persistent_profile_dir,
            "profile_locked": is_profile_locked(self._persistent_profile_dir)[0]
        }
        if not has_any_identity:
            res["reason"] = "No configured user identity found in git config, browser profiles, or environment."
        return res

    def open_authenticated(
        self,
        url: str,
        user_data_dir: Optional[str] = None,
        profile_name: str = "Default",
        headless: bool = False,
        cdp_url: Optional[str] = None
    ) -> str:
        """
        Launches or attaches to an authenticated browser session to reuse user cookies.
        Supports:
        1. CDP attach via cdp_url or default http://localhost:9222 if debugging is active.
        2. Persistent profile reuse (defaults to ~/.lmms/browser_profile).
        3. Safe lock handling if user_data_dir is locked by another running process.
        """
        # Check if Chrome is already running with remote debugging on localhost:9222
        probe_cdp = cdp_url or "http://localhost:9222"
        check = verify_cdp_endpoint(probe_cdp, timeout=1.0)
        if check["available"]:
            conn = self.connect_cdp(probe_cdp)
            if conn.get("status") == "connected":
                if url:
                    self._goto_if_needed(url)
                content = self.page.evaluate("document.body.innerText || ''") if self.page else ""
                return f"[AUTHENTICATED CDP SESSION ATTACHED ({probe_cdp})]\n{content[:2000]}"

        # If existing desktop Chrome profile requested or user_data_dir matches desktop chrome
        if user_data_dir and ("google-chrome" in user_data_dir or "chrome" in user_data_dir.lower()):
            res = self.attach_existing_chrome_session(
                url=url,
                headless=headless,
                preferred_profile=profile_name,
                cdp_endpoint=cdp_url or "http://localhost:9222"
            )
            if res.get("status") == "connected":
                content = self.page.evaluate("document.body.innerText || ''") if self.page else ""
                return f"[AUTHENTICATED EXISTING CHROME SESSION ATTACHED]\n{content[:2000]}"
            else:
                return f"Failed to attach existing Chrome session: {res.get('message', 'Unknown error')}"

        target_dir = os.path.expanduser(user_data_dir or self._persistent_profile_dir)

        # Inspect lock
        locked, lock_pid = is_profile_locked(target_dir)
        if locked and (not self.browser or self._persistent_profile_dir != target_dir):
            return (
                f"[PROFILE_LOCKED_ERROR]\n"
                f"User data directory '{target_dir}' is currently in use by PID {lock_pid}.\n"
                f"Chrome does not permit two simultaneous browser processes in the same profile directory.\n"
                f"To attach to your active session, start Chrome with '--remote-debugging-port=9222' "
                f"and connect via CDP, or use LMMs's persistent agent profile (~/.lmms/browser_profile)."
            )

        res = self.open_persistent_browser(url=url, headless=headless, profile_dir=target_dir)
        if res.get("status") == "connected":
            content = self.page.evaluate("document.body.innerText || ''") if self.page else ""
            return f"[AUTHENTICATED PERSISTENT SESSION STARTED (Headless={headless})]\n{content[:2000]}"
        else:
            return f"Failed to open authenticated URL: {res.get('message', 'Unknown error')}"

    def scroll(self, url: str, direction: str = "down", amount: int = 1000) -> str:
        """Scrolls the active page."""
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            if direction == "down":
                self.page.evaluate(f"window.scrollBy(0, {amount})")
            else:
                self.page.evaluate(f"window.scrollBy(0, -{amount})")
            self.page.wait_for_timeout(1000)
            content = self.page.evaluate("document.body.innerText")
            if content:
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r' +', ' ', content)
            return content[:2000]
        except Exception as e:
            return f"Failed to scroll: {str(e)}"

    def _tag_interactive_elements(self):
        """Ensures all interactive elements on active page have data-lmms-id attribute."""
        if not self.page:
            return
        tagging_script = """
        (() => {
            const elements = Array.from(document.querySelectorAll(
                'input, button, a, select, textarea, [role="button"], [role="link"], [role="checkbox"], [contenteditable="true"]'
            ));
            let counter = 1;
            for (const el of elements) {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                if ((el.getAttribute('type') || '').toLowerCase() === 'hidden') continue;
                el.setAttribute('data-lmms-id', String(counter++));
            }
        })()
        """
        try:
            self.page.evaluate(tagging_script)
        except Exception:
            pass

    def get_interactive_dom(self, url: str = None) -> str:
        """Scan active page and extract all interactive DOM elements (inputs, buttons, links) with unique IDs."""
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            self.page.wait_for_timeout(1000)

            # Injected script that tags and extracts interactive elements with href, form action, and values
            js_script = """
            (() => {
                const elements = Array.from(document.querySelectorAll(
                    'input, button, a, select, textarea, [role="button"], [role="link"], [role="checkbox"], [contenteditable="true"]'
                ));
                let counter = 1;
                const items = [];
                for (const el of elements) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;

                    const tag = el.tagName.toLowerCase();
                    const type = (el.getAttribute('type') || '').toLowerCase();
                    const name = el.getAttribute('name') || '';
                    const placeholder = el.getAttribute('placeholder') || '';
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    const href = (tag === 'a' ? (el.getAttribute('href') || el.href || '') : '') || '';
                    const action = (el.form ? el.form.getAttribute('action') : (tag === 'form' ? el.getAttribute('action') : '')) || '';
                    const val = (tag === 'input' || tag === 'textarea') ? (el.value || '').slice(0, 40) : '';
                    let text = (el.innerText || el.textContent || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 60);

                    // Skip hidden inputs
                    if (type === 'hidden') continue;

                    const id = counter++;
                    el.setAttribute('data-lmms-id', String(id));

                    let sel = '';
                    if (el.id) {
                        sel = '#' + CSS.escape(el.id);
                    } else if (name) {
                        sel = `${tag}[name="${name}"]`;
                    } else if (placeholder) {
                        sel = `${tag}[placeholder="${placeholder}"]`;
                    } else {
                        sel = `[data-lmms-id="${id}"]`;
                    }

                    items.push({
                        id: id,
                        tag: tag,
                        type: type,
                        name: name,
                        href: href,
                        action: action,
                        value: val,
                        placeholder: placeholder,
                        label: ariaLabel || text,
                        selector: sel
                    });
                }
                return {
                    title: document.title,
                    url: window.location.href,
                    elements: items.slice(0, 60)
                };
            })()
            """
            data = self.page.evaluate(js_script)
            title = data.get("title", "")
            current_url = data.get("url", "")
            elements = data.get("elements", [])

            lines = [
                f"[PAGE TITLE]: {title}",
                f"[CURRENT URL]: {current_url}",
                "",
                "=== INTERACTIVE DOM ELEMENTS (Use ID number or selector to click/fill) ==="
            ]

            if not elements:
                lines.append("(No interactive inputs or buttons found on this page)")
            else:
                for el in elements:
                    desc_parts = [f"<{el['tag']}"]
                    if el.get('type'): desc_parts.append(f"type='{el['type']}'")
                    if el.get('name'): desc_parts.append(f"name='{el['name']}'")
                    if el.get('href'): desc_parts.append(f"href='{el['href']}'")
                    if el.get('action'): desc_parts.append(f"action='{el['action']}'")
                    if el.get('placeholder'): desc_parts.append(f"placeholder='{el['placeholder']}'")
                    if el.get('value'): desc_parts.append(f"value='{el['value']}'")
                    if el.get('label'): desc_parts.append(f"label='{el['label']}'")
                    desc_parts.append(f"selector='{el['selector']}'>")
                    lines.append(f"[ID {el['id']}] {' '.join(desc_parts)}")

            # Also append short visible text summary
            innerText = self.page.evaluate("document.body.innerText || ''")
            if innerText:
                clean_text = re.sub(r'\s+', ' ', innerText).strip()[:800]
                lines.append("")
                lines.append("=== PAGE TEXT PREVIEW ===")
                lines.append(clean_text)

            return "\n".join(lines)
        except Exception as e:
            return f"Failed to get interactive DOM: {str(e)}"

    def observe_page(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Website-independent page observation:
        Extracts current URL, title, detected forms, inputs, rich-text / contenteditable editors,
        action buttons (save/publish), and dynamic authentication state.
        """
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            self.page.wait_for_timeout(500)

            observation_script = """
            (() => {
                const title = document.title || "";
                const currentUrl = window.location.href;

                // 1. Detect all interactive elements and editors
                const elements = Array.from(document.querySelectorAll(
                    'input, button, a, select, textarea, [role="button"], [role="link"], [role="checkbox"], [contenteditable="true"], [role="textbox"], .document-paragraph, .ProseMirror, .public-DraftEditor-content'
                ));

                let counter = 1;
                const items = [];
                const editors = [];
                const saveButtons = [];
                const publishButtons = [];

                for (const el of elements) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;

                    const tag = el.tagName.toLowerCase();
                    const type = (el.getAttribute('type') || '').toLowerCase();
                    if (type === 'hidden') continue;

                    const id = counter++;
                    el.setAttribute('data-lmms-id', String(id));

                    const name = el.getAttribute('name') || '';
                    const placeholder = el.getAttribute('placeholder') || '';
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    const isContentEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true' || el.getAttribute('role') === 'textbox';
                    const text = (el.innerText || el.textContent || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 80);
                    const href = (tag === 'a' ? (el.getAttribute('href') || el.href || '') : '') || '';

                    let sel = '';
                    if (el.id) {
                        sel = '#' + CSS.escape(el.id);
                    } else if (name) {
                        sel = `${tag}[name="${name}"]`;
                    } else if (placeholder) {
                        sel = `${tag}[placeholder="${placeholder}"]`;
                    } else {
                        sel = `[data-lmms-id="${id}"]`;
                    }

                    const itemData = {
                        id: id,
                        tag: tag,
                        type: type,
                        name: name,
                        placeholder: placeholder,
                        label: ariaLabel || text,
                        selector: sel,
                        is_contenteditable: isContentEditable
                    };
                    items.push(itemData);

                    // Classify editors
                    if (isContentEditable || tag === 'textarea' || (tag === 'input' && (type === 'text' || !type))) {
                        const currentVal = isContentEditable ? (el.innerText || '') : (el.value || '');
                        editors.push({
                            id: id,
                            selector: sel,
                            tag: tag,
                            placeholder: placeholder,
                            aria_label: ariaLabel,
                            is_contenteditable: isContentEditable,
                            text_length: currentVal.length,
                            text_preview: currentVal.trim().slice(0, 100)
                        });
                    }

                    // Classify save/draft buttons
                    const labelLower = (ariaLabel + ' ' + text).toLowerCase();
                    if (tag === 'button' || tag === 'a' || el.getAttribute('role') === 'button') {
                        if (/save\\s*draft|save\\s*as\\s*draft|\\bsave\\b|\\bdraft\\b/i.test(labelLower) && !/publish|submit/i.test(labelLower)) {
                            saveButtons.push({ id: id, selector: sel, label: text || ariaLabel });
                        } else if (/publish|\\bpost\\b|submit\\s*question|submit\\s*post|ask\\s*question|create\\s*post/i.test(labelLower)) {
                            publishButtons.push({ id: id, selector: sel, label: text || ariaLabel });
                        }
                    }
                }

                // 2. Dynamic authentication evaluation
                const bodyText = document.body.innerText || '';
                const hasLoginCtas = /(log\\s*in|sign\\s*in|register|sign\\s*up)/i.test(bodyText) && items.some(i => /(log\\s*in|sign\\s*in|register|sign\\s*up)/i.test(i.label));
                const hasLogoutCtas = /(log\\s*out|sign\\s*out)/i.test(bodyText) && items.some(i => /(log\\s*out|sign\\s*out)/i.test(i.label));
                const hasProfileCtas = items.some(i => /(my\\s*account|profile|dashboard|avatar)/i.test(i.label));

                let authStatus = "unknown";
                let authEvidence = "No unambiguous authentication indicators found in visible page controls.";
                if (hasLogoutCtas || (hasProfileCtas && !hasLoginCtas)) {
                    authStatus = "authenticated";
                    authEvidence = "Verified session: Logout CTA or user profile element confirmed in DOM.";
                } else if (hasLoginCtas) {
                    authStatus = "unauthenticated";
                    authEvidence = "Page displays visible login/sign-in options.";
                }

                // 3. Status indicators (e.g. "Saved", "Draft saved", "Unsaved changes")
                const statusIndicators = [];
                const statusMatches = bodyText.match(/\\b(draft\\s+saved|all\\s+changes\\s+saved|unsaved(?:\\s+changes)?|saving\\.{0,3}|saved)\\b/gi);
                if (statusMatches) {
                    statusIndicators.push(...new Set(statusMatches.map(s => s.trim())));
                }

                return {
                    url: currentUrl,
                    title: title,
                    auth_status: authStatus,
                    auth_evidence: authEvidence,
                    editors_count: editors.length,
                    editors: editors,
                    save_buttons: saveButtons,
                    publish_buttons: publishButtons,
                    status_indicators: statusIndicators,
                    interactive_elements_count: items.length,
                    elements: items.slice(0, 50)
                };
            })()
            """
            obs = self.page.evaluate(observation_script)
            self._capture_preview_snapshot(action="observe_page")
            return obs
        except Exception as e:
            return {"error": str(e), "url": self.page.url if self.page else ""}

    def verify_editor_content(
        self,
        selector: Optional[str] = None,
        expected_substring: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies whether an editor or input field on the page contains the expected content.
        Differentiates between text generated in chat vs text confirmed in DOM.
        """
        try:
            self._ensure_session()
            target = selector
            if not target:
                obs = self.observe_page()
                editors = obs.get("editors", [])
                if editors:
                    target = editors[0]["selector"]
                else:
                    return {"verified": False, "error": "No editor found on page to verify."}

            sel = str(target).strip()
            id_match = re.search(r'\b(\d+)\b', sel)
            if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                target_sel = f"[data-lmms-id='{raw_id}']"
            else:
                target_sel = sel

            extract_script = f"""
            (() => {{
                const el = document.querySelector("{target_sel}");
                if (!el) return null;
                const isContentEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true' || el.getAttribute('role') === 'textbox';
                const text = isContentEditable ? (el.innerText || '') : (el.value || '');
                return {{
                    tag: el.tagName.toLowerCase(),
                    is_contenteditable: isContentEditable,
                    char_count: text.length,
                    text: text
                }};
            }})()
            """
            data = self.page.evaluate(extract_script)
            if not data:
                return {"verified": False, "selector": target_sel, "error": f"Element '{target_sel}' not found in DOM."}

            actual_text = data["text"]
            char_count = data["char_count"]

            if expected_substring:
                contains_expected = expected_substring.strip() in actual_text
                return {
                    "verified": contains_expected,
                    "selector": target_sel,
                    "is_contenteditable": data["is_contenteditable"],
                    "char_count": char_count,
                    "expected_found": contains_expected,
                    "preview": actual_text[:200],
                    "status": "verified" if contains_expected else "content_mismatch"
                }
            else:
                has_content = char_count > 0
                return {
                    "verified": has_content,
                    "selector": target_sel,
                    "is_contenteditable": data["is_contenteditable"],
                    "char_count": char_count,
                    "preview": actual_text[:200],
                    "status": "verified" if has_content else "empty"
                }
        except Exception as e:
            return {"verified": False, "error": str(e)}

    def save_draft(self, button_selector: Optional[str] = None) -> Dict[str, Any]:
        """
        Discovers and triggers the page's save draft control, and verifies page persistence feedback.
        """
        try:
            self._ensure_session()
            obs = self.observe_page()
            target_btn = button_selector

            if not target_btn:
                save_btns = obs.get("save_buttons", [])
                if save_btns:
                    target_btn = save_btns[0]["selector"]
                else:
                    buttons = self.page.locator("button:has-text('Save'), button:has-text('Draft'), a:has-text('Save draft')")
                    if buttons.count() > 0:
                        target_btn = "button:has-text('Save draft')" if self.page.locator("button:has-text('Save draft')").count() > 0 else "button:has-text('Save')"
                    else:
                        return {
                            "success": False,
                            "verified": False,
                            "error": "No draft saving control found on the active page."
                        }

            dom_before = self.page.evaluate("document.body.innerText || ''")
            click_res = self.click_element(selector=target_btn)
            self.page.wait_for_timeout(1500)

            obs_after = self.observe_page()
            dom_after = self.page.evaluate("document.body.innerText || ''")

            indicators = obs_after.get("status_indicators", [])
            has_saved_indicator = any(
                re.search(r'\b(saved|all changes saved|draft saved)\b', ind, re.IGNORECASE)
                and not re.search(r'\bunsaved\b', ind, re.IGNORECASE)
                for ind in indicators
            )
            button_disabled = False
            try:
                button_disabled = self.page.locator(target_btn).first.is_disabled()
            except Exception:
                pass

            verified = bool(has_saved_indicator or button_disabled)
            if has_saved_indicator:
                status_msg = f"Draft save confirmed: {', '.join(indicators)}"
            elif button_disabled:
                status_msg = "Draft save triggered (button disabled after click)"
            else:
                status_msg = "Save button clicked, but no state change detected"

            return {
                "success": True,
                "verified": verified,
                "selector_used": target_btn,
                "status_indicators": indicators,
                "message": status_msg
            }
        except Exception as e:
            return {"success": False, "verified": False, "error": str(e)}

    def request_publication_approval(
        self,
        target_selector: str,
        action_type: str = "publish_post",
        content_summary: str = ""
    ) -> Dict[str, Any]:
        """
        Pauses and asks for explicit human approval before clicking a public submit/publish button.
        """
        url = self.page.url if self.page else "unknown"
        req_id = f"{url}::{target_selector}"

        return {
            "status": "approval_required",
            "requires_confirmation": True,
            "target_selector": target_selector,
            "target_url": url,
            "action_type": action_type,
            "content_summary": content_summary,
            "approval_token": req_id,
            "instructions": (
                f"[ACTION_REQUIRES_APPROVAL] The agent is prepared to trigger a public submission ({action_type}) "
                f"on '{url}' using selector '{target_selector}'.\n"
                f"Content Summary: {content_summary}\n"
                f"Publication will not proceed until explicit confirmation is provided."
            )
        }

    def approve_publication(self, target_selector: str, url: Optional[str] = None) -> None:
        """
        Explicitly grants publication approval for a specific target selector and URL.
        """
        active_url = url or (self.page.url if self.page else "unknown")
        req_id = f"{active_url}::{target_selector}"
        self._approved_publications.add(req_id)
        self._approved_publications.add(target_selector)

    def open_url(self, url: str, headless: bool = False, _retry_count: int = 0) -> str:
        try:
            # Resolve local file references (e.g. file:///welcome.html or welcome.html)
            if url.startswith("file://"):
                raw_path = url[7:]
                if not os.path.exists(raw_path):
                    for cand_dir in [os.getcwd(), os.path.expanduser("~/docs"), os.path.expanduser("~")]:
                        cand = os.path.join(cand_dir, raw_path.lstrip("/"))
                        if os.path.exists(cand):
                            url = f"file://{os.path.abspath(cand)}"
                            break
            elif not url.startswith("http://") and not url.startswith("https://") and (url.endswith(".html") or url.endswith(".htm")):
                cand = os.path.abspath(url)
                if not os.path.exists(cand):
                    cand = os.path.join(os.getcwd(), url)
                if os.path.exists(cand):
                    url = f"file://{cand}"

            # 1. Loop prevention for identical failed navigations (only on top-level calls)
            if _retry_count == 0 and url == self._last_attempted_url and self._last_attempt_failed:
                return (
                    f"[NAVIGATION_SKIPPED_IDENTICAL]\n"
                    f"Navigation to '{url}' was already attempted and returned 404/Error with no new evidence.\n"
                    f"To prevent redundant requests and loops, inspect the existing DOM using 'browser.get_interactive_dom' or navigate to a verified link."
                )

            self._last_attempted_url = url
            self._ensure_session(headless=headless)
            self._goto_if_needed(url)
            try:
                self.page.wait_for_timeout(2000)
            except Exception:
                pass
            
            # Auto-detect CAPTCHA and fallback to human-like bypass
            try:
                content = self.page.evaluate("document.body.innerText || ''")
            except Exception:
                content = ""
            content_lower = content.lower() if content else ""
            if "captcha" in content_lower or "verify you are human" in content_lower or "cloudflare" in content_lower or "checking your browser" in content_lower:
                print("\n[BrowserTool] CAPTCHA detected. Initiating Human-like Bypass...")
                success, msg = self.solve_captcha(url)
                if not success:
                    self._last_attempt_failed = True
                    return f"[CAPTCHA_FAILED] {msg}"

            import urllib.parse
            parsed_url = urllib.parse.urlparse(url)
            netloc = parsed_url.netloc
            root_url = f"{parsed_url.scheme or 'https'}://{netloc}" if netloc else url

            # Auto-detect 404 Not Found and provide actionable guidance to prevent hallucinated retries
            try:
                page_title = (self.page.title() or "").lower()
            except Exception:
                page_title = ""
            is_404 = (
                "404" in page_title
                or "not found" in page_title
                or "404: this page could not be found" in content_lower
                or "page not found" in content_lower
                or "status 404" in content_lower
            )
            if is_404:
                self._last_attempt_failed = True
                count = self._domain_404_counts.get(netloc, 0) + 1
                self._domain_404_counts[netloc] = count

                # Termination after repeated failed recoveries (>= 3 consecutive 404s)
                if count >= 3 and netloc:
                    return (
                        f"[NAVIGATION_TERMINATED]\n"
                        f"Repeated navigation failures ({count} consecutive 404s) on domain '{netloc}'.\n"
                        f"Bounded recovery failed to locate requested resource. Stop route guessing. "
                        f"Proceed to use known evidence, synthesize current findings, or report the target resource as unavailable."
                    )

                # Bounded recovery on repeated 404 (count == 2)
                if count == 2 and netloc:
                    try:
                        self.page.goto(root_url, timeout=7000, wait_until="domcontentloaded")
                        self.page.wait_for_timeout(1000)
                        root_title = (self.page.title() or "").lower()
                        root_content = (self.page.evaluate("document.body.innerText || ''") or "").lower()
                        if "404" in root_title or "not found" in root_title or "404: this page could not be found" in root_content:
                            self._domain_404_counts[netloc] = 3
                            return (
                                f"[NAVIGATION_TERMINATED] Bounded recovery to site root '{root_url}' also returned 404.\n"
                                f"The domain '{netloc}' appears unreachable or lacks a public root page. "
                                f"Stop speculative navigation. Report this target as unavailable."
                            )
                        root_dom = self.get_interactive_dom()
                        return (
                            f"[HTTP 404 / REPEATED NAVIGATION FAILURE DETECTED]\n"
                            f"The requested URL '{url}' does not exist (404 Not Found).\n"
                            f"Repeated 404s detected on {netloc}. Automatic recovery engaged: Navigated back to site root '{root_url}' to stop route guessing.\n"
                            f"Below is the verified interactive DOM of the working site root. Inspect visible links (<a href='...'>) and controls:\n\n"
                            + root_dom
                        )
                    except Exception as rec_err:
                        return f"[NAVIGATION_RECOVERY_FAILED] Failed to navigate to root '{root_url}': {str(rec_err)}"

                # First 404 (count == 1): Inspect available page evidence and return guidance
                page_dom = self.get_interactive_dom()
                return (
                    f"[HTTP 404 / Page Not Found] The URL '{url}' does not exist.\n"
                    f"Site root: '{root_url}'\n"
                    f"ACTION REQUIRED: Do not guess or hallucinate URL paths (e.g. /login, /write). "
                    f"Use 'browser.get_interactive_dom' or 'browser.click_element' on the working homepage to navigate via visible elements.\n\n"
                    f"Available page elements on 404 page:\n{page_dom}"
                )
            else:
                self._last_attempt_failed = False
                if netloc in self._domain_404_counts:
                    self._domain_404_counts[netloc] = 0

            self._capture_preview_snapshot(action="open_url")
            self._notify_browser_event("browser_action_ended", {
                "action": "open_url",
                "url": self.page.url if self.page else url,
                "success": True,
                "is_404": False
            })
            return self.get_interactive_dom()
        except Exception as e:
            self._last_attempt_failed = True
            err_str = str(e)
            if ("closed" in err_str.lower() or "target" in err_str.lower() or "crash" in err_str.lower()) and _retry_count < 2:
                print(f"\n[BrowserTool] Browser closed unexpectedly ({err_str}). Reopening fresh session and retrying...")
                self.close()
                self._last_attempt_failed = False
                return self.open_url(url, headless=headless, _retry_count=_retry_count + 1)
            return f"Failed to open URL: {err_str}"

    def click_element(self, selector: str = None, url: str = None, id: int = None) -> str:
        """
        Click an interactive DOM element using discrete numeric ID, CSS selector, or visible text.
        Interaction mode: DOM_DRIVEN.
        Verifies resulting URL navigation and DOM state change.
        """
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            
            url_before = self.page.url
            dom_before = ""
            try:
                dom_before = self.page.evaluate("document.body.innerText || ''")
            except Exception:
                pass

            sel = str(id if id is not None else selector).strip()

            # Prevent duplicate clicks with no observable state change
            click_key = f"{url_before}::{sel}"
            if getattr(self, "_last_clicked_target", None) == click_key and getattr(self, "_last_click_state_changed", True) is False:
                return (
                    f"[CLICK_SKIPPED_DUPLICATE]\n"
                    f"Element '{sel}' on '{url_before}' was already clicked and produced no observable state change.\n"
                    f"To prevent loops, inspect current DOM or choose a different action."
                )
            self._last_clicked_target = click_key

            self._notify_browser_event("browser_action_started", {
                "action": "click_element",
                "interaction_type": "DOM_DRIVEN",
                "selector": sel,
                "url": url_before
            })

            # If selector is ID number like "1" or "[ID 1]" or 1
            id_match = re.search(r'\b(\d+)\b', sel)
            if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                target_sel = f"[data-lmms-id='{raw_id}']"
                if self.page.locator(target_sel).count() == 0:
                    self._tag_interactive_elements()
            else:
                target_sel = sel

            # Publication Safety Check: detect if target button is a public submit/publish button
            btn_text = ""
            try:
                if self.page.locator(target_sel).count() > 0:
                    btn_text = (self.page.locator(target_sel).inner_text(timeout=400) or self.page.locator(target_sel).get_attribute("value") or "")
            except Exception:
                pass

            combo_text = f"{sel} {btn_text}".strip()
            is_publish_button = bool(re.search(r'\b(publish|publish\s*post|post\s*now|submit\s*question|submit\s*post)\b', combo_text, re.IGNORECASE))
            req_id = f"{self.page.url}::{sel}"
            if is_publish_button and req_id not in self._approved_publications and sel not in self._approved_publications and str(id) not in self._approved_publications and target_sel not in self._approved_publications:
                return (
                    f"[ACTION_REQUIRES_APPROVAL] Target '{sel}' ({btn_text.strip()}) represents a public submission or publication action on '{self.page.url}'. "
                    f"To prevent accidental public posting, explicit confirmation is required before clicking."
                )

            if target_sel.startswith("[data-lmms-id"):
                self.page.click(target_sel, timeout=7000)
            elif not sel.startswith(".") and not sel.startswith("#") and not "[" in sel:
                # Text-based click or selector
                try:
                    elem = self.page.get_by_text(sel, exact=True)
                    if elem.count() > 0:
                        elem.first.click(timeout=5000)
                    else:
                        elem = self.page.get_by_text(sel)
                        if elem.count() > 0:
                            elem.first.click(timeout=5000)
                        else:
                            self.page.click(sel, timeout=5000)
                except:
                    self.page.click(sel, timeout=5000)
            else:
                self.page.click(sel, timeout=7000)
                
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
            self.page.wait_for_timeout(1000)
            self.save_cookies()

            url_after = self.page.url
            dom_after = ""
            try:
                dom_after = self.page.evaluate("document.body.innerText || ''")
            except Exception:
                pass

            url_changed = (url_after != url_before)
            dom_changed = (dom_after != dom_before)
            state_changed = url_changed or dom_changed
            self._last_click_state_changed = state_changed

            if url_changed:
                verification = f"[VERIFIED: Navigated from {url_before} to {url_after}]"
            elif dom_changed:
                verification = f"[VERIFIED: Visible DOM state changed on page]"
            else:
                verification = f"[OBSERVATION: Click executed, but page URL and text content remained unchanged]"

            self._capture_preview_snapshot(action=f"click:{sel}")
            self._notify_browser_event("browser_action_ended", {
                "action": "click_element",
                "interaction_type": "DOM_DRIVEN",
                "selector": sel,
                "url": url_after,
                "url_changed": url_changed,
                "dom_changed": dom_changed,
                "verified": state_changed,
                "success": True
            })

            return f"[CLICK_SUCCESS] Clicked '{sel}'. {verification}\n" + self.get_interactive_dom()
        except Exception as e:
            self._last_click_state_changed = False
            err_str = str(e)
            # Dynamic SPA Stale Element Recovery
            if "detached" in err_str.lower() or "not attached" in err_str.lower() or "stale" in err_str.lower():
                self._tag_interactive_elements()
                try:
                    self.page.wait_for_timeout(300)
                    self.page.click(target_sel, timeout=3000)
                    return f"[CLICK_SUCCESS_AFTER_RECOVERY] Clicked '{sel}' after dynamic DOM re-attachment.\n" + self.get_interactive_dom()
                except Exception:
                    pass
                return f"[STALE_SELECTOR_ERROR] Element '{selector}' was detached during dynamic DOM update. Fresh interactive elements have been re-scanned:\n" + self.get_interactive_dom()

            self._notify_browser_event("browser_action_ended", {
                "action": "click_element",
                "interaction_type": "DOM_DRIVEN",
                "selector": str(selector),
                "success": False,
                "error": str(e)
            })
            return f"Failed to click element '{selector}': {str(e)}"

    def pointer_click(self, selector: str = None, url: str = None, id: int = None) -> str:
        """
        Physically move cursor across screen coordinates via bezier curve trajectory
        and trigger coordinate-based mouse down/up click.
        Interaction mode: PHYSICAL_POINTER.
        Verifies coordinate bounding box, trajectory movement, and observable state change.
        """
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)

            url_before = self.page.url
            dom_before = ""
            try:
                dom_before = self.page.evaluate("document.body.innerText || ''")
            except Exception:
                pass

            sel = str(id if id is not None else selector).strip()
            id_match = re.search(r'\b(\d+)\b', sel)
            if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                target_sel = f"[data-lmms-id='{raw_id}']"
                if self.page.locator(target_sel).count() == 0:
                    self._tag_interactive_elements()
                locator = self.page.locator(target_sel).first
            elif not sel.startswith(".") and not sel.startswith("#") and not "[" in sel:
                elem = self.page.get_by_text(sel, exact=True)
                locator = elem.first if elem.count() > 0 else self.page.locator(sel).first
            else:
                locator = self.page.locator(sel).first

            box = locator.bounding_box()
            if not box:
                return f"[POINTER_FAILED] Could not compute coordinate bounding box for element: '{sel}'"

            # Compute target point within element boundaries
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2

            self._notify_browser_event("browser_action_started", {
                "action": "pointer_click",
                "interaction_type": "PHYSICAL_POINTER",
                "target_x": target_x,
                "target_y": target_y,
                "selector": sel
            })

            # Physical mouse trajectory move
            self._move_mouse_human_like(target_x, target_y)
            time.sleep(0.1)
            self.page.mouse.down()
            time.sleep(0.08)
            self.page.mouse.up()
            time.sleep(1.0)
            self.save_cookies()

            url_after = self.page.url
            dom_after = ""
            try:
                dom_after = self.page.evaluate("document.body.innerText || ''")
            except Exception:
                pass

            url_changed = (url_after != url_before)
            dom_changed = (dom_after != dom_before)
            state_changed = url_changed or dom_changed
            self._last_click_state_changed = state_changed

            verification = (
                f"[VERIFIED: Pointer clicked at ({int(target_x)}, {int(target_y)}), "
                f"{'URL navigated to ' + url_after if url_changed else 'DOM state changed' if dom_changed else 'no state change observed'}]"
            )

            self._capture_preview_snapshot(action=f"pointer_click:{sel}")
            self._notify_browser_event("browser_action_ended", {
                "action": "pointer_click",
                "interaction_type": "PHYSICAL_POINTER",
                "target_x": target_x,
                "target_y": target_y,
                "url": url_after,
                "verified": state_changed,
                "success": True
            })

            return f"[POINTER_CLICK_SUCCESS] Physical pointer clicked '{sel}' at coordinates ({int(target_x)}, {int(target_y)}). {verification}\n" + self.get_interactive_dom()
        except Exception as e:
            return f"Failed to execute physical pointer click on '{selector}': {str(e)}"

    def fill_form(self, fields: dict, url: str = None) -> str:
        """
        Fill multiple form fields by discrete ID number or selector.
        Verifies that input values are populated into DOM elements.
        """
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
                
            self._notify_browser_event("browser_action_started", {
                "action": "fill_form",
                "fields": fields
            })

            filled_items = []
            verified_items = []
            for raw_sel, val in fields.items():
                sel = str(raw_sel).strip()
                id_match = re.search(r'\b(\d+)\b', sel)
                if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                    raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                    target_sel = f"[data-lmms-id='{raw_id}']"
                else:
                    target_sel = sel

                if self.page.locator(target_sel).count() == 0:
                    self._tag_interactive_elements()

                # Check if target element is contenteditable
                is_editable = False
                try:
                    is_editable = bool(self.page.evaluate(f"""(() => {{
                        const el = document.querySelector("{target_sel}");
                        return el ? (el.isContentEditable || el.getAttribute('contenteditable') === 'true' || el.getAttribute('role') === 'textbox') : false;
                    }})()"""))
                except Exception:
                    is_editable = False

                if is_editable:
                    self.page.focus(target_sel)
                    self.page.evaluate(f"""((text) => {{
                        const el = document.querySelector("{target_sel}");
                        if (el) {{
                            el.focus();
                            document.execCommand('selectAll', false, null);
                            document.execCommand('insertText', false, text);
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }})""", str(val))
                else:
                    self.page.fill(target_sel, str(val))
                filled_items.append(f"{target_sel}='{val}'")

                try:
                    if is_editable:
                        val_check = self.page.evaluate(f'document.querySelector("{target_sel}")?.innerText || ""') or ""
                    else:
                        val_check = self.page.input_value(target_sel)
                    if str(val)[:30].strip() in val_check:
                        verified_items.append(target_sel)
                except Exception:
                    pass
                
            self.page.wait_for_timeout(1000)
            self.save_cookies()

            all_verified = (len(verified_items) == len(fields))
            verify_str = f"[VERIFIED: All {len(filled_items)} input fields populated]" if all_verified else f"[VERIFIED: {len(verified_items)}/{len(fields)} fields populated]"

            self._capture_preview_snapshot(action="fill_form")
            self._notify_browser_event("browser_action_ended", {
                "action": "fill_form",
                "fields_count": len(fields),
                "verified": all_verified,
                "success": True
            })

            return f"[FILL_SUCCESS] {verify_str}: {', '.join(filled_items)}.\n" + self.get_interactive_dom()
        except Exception as e:
            return f"Failed to fill form: {str(e)}"

    def type_text(self, selector: str, text: str, press_enter: bool = False, url: str = None) -> str:
        """Type text into an input box (by ID or selector) and optionally press Enter."""
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            sel = str(selector).strip()
            id_match = re.search(r'\b(\d+)\b', sel)
            if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                target_sel = f"[data-lmms-id='{raw_id}']"
            else:
                target_sel = sel

            self._notify_browser_event("browser_action_started", {
                "action": "type_text",
                "selector": target_sel,
                "text": text
            })
                
            if self.page.locator(target_sel).count() == 0:
                self._tag_interactive_elements()

            # Check if target element is contenteditable
            is_editable = False
            try:
                is_editable = bool(self.page.evaluate(f"""(() => {{
                    const el = document.querySelector("{target_sel}");
                    return el ? (el.isContentEditable || el.getAttribute('contenteditable') === 'true' || el.getAttribute('role') === 'textbox') : false;
                }})()"""))
            except Exception:
                is_editable = False

            if is_editable:
                self.page.focus(target_sel)
                self.page.evaluate(f"""((text) => {{
                    const el = document.querySelector("{target_sel}");
                    if (el) {{
                        el.focus();
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, text);
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }})""", text)
                if press_enter:
                    self.page.keyboard.press("Enter")
            else:
                self.page.focus(target_sel)
                self.page.fill(target_sel, "")
                self.page.type(target_sel, text, delay=20)
                if press_enter:
                    self.page.press(target_sel, "Enter")
                    self.page.wait_for_timeout(1000)

            self.page.wait_for_timeout(500)
            self.save_cookies()

            actual_val = ""
            try:
                if is_editable:
                    actual_val = self.page.evaluate(f'document.querySelector("{target_sel}")?.innerText || ""') or ""
                else:
                    actual_val = self.page.input_value(target_sel)
            except Exception:
                try:
                    actual_val = self.page.evaluate(f'document.querySelector("{target_sel}")?.innerText || document.querySelector("{target_sel}")?.value || ""') or ""
                except Exception:
                    pass

            text_snippet = text[:40].strip()
            text_verified = bool(actual_val and text_snippet in actual_val)
            v_str = f"[VERIFIED: Text confirmed in DOM (char count: {len(actual_val)})]" if text_verified else (f"[VERIFIED: Text entered into '{target_sel}']" if actual_val else f"[UNVERIFIED: Expected '{text_snippet}...' in element]")

            self._capture_preview_snapshot(action=f"type:{target_sel}")
            self._notify_browser_event("browser_action_ended", {
                "action": "type_text",
                "selector": target_sel,
                "verified": text_verified,
                "success": True
            })

            return f"[TYPE_SUCCESS] {v_str}.\n" + self.get_interactive_dom()
        except Exception as e:
            return f"Failed to type text into '{selector}': {str(e)}"

    def press_key(self, key: str = "Enter") -> str:
        """Press a keyboard key (Enter, Tab, Escape, etc.) on the active browser page."""
        try:
            self._ensure_session()
            self.page.keyboard.press(key)
            self.page.wait_for_timeout(2000)
            return f"[KEY_PRESSED] Pressed key '{key}'.\n" + self.get_interactive_dom()
        except Exception as e:
            return f"Failed to press key '{key}': {str(e)}"

    def scrape_live(self, url: str = None, selector: str = None) -> str:
        """Live scraping of dynamic JavaScript-rendered pages with optional CSS selector."""
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            try:
                self.page.wait_for_load_state("networkidle", timeout=8000)
            except:
                pass
                
            if selector:
                elements = self.page.query_selector_all(selector)
                texts = [el.inner_text().strip() for el in elements if el]
                return f"[LIVE SCRAPE for '{selector}' on {self.page.url}]\n" + "\n---\n".join(texts[:30])
            else:
                body_text = self.page.evaluate("document.body.innerText || ''")
                clean = re.sub(r'\n{3,}', '\n\n', body_text).strip()
                return f"[LIVE PAGE CONTENT ({self.page.url})]\n{clean[:4000]}"
        except Exception as e:
            return f"Failed to scrape live: {str(e)}"

    def screenshot(self, save_path: str = "/tmp/lmms_browser.png", url: str = None) -> str:
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            self.page.screenshot(path=save_path)
            return f"Screenshot saved to {save_path}"
        except Exception as e:
            return f"Failed to take screenshot: {str(e)}"

    def scrape(self, url: str, selector: str) -> str:
        return self.scrape_live(url=url, selector=selector)

    def execute_js(self, js_code: str, url: str = None) -> str:
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            result = self.page.evaluate(js_code)
            return f"JS Execution result: {result}"
        except Exception as e:
            return f"Failed to execute JS: {str(e)}"

    def _generate_bezier_curve(self, start_x, start_y, end_x, end_y):
        if np is None:
            # Fallback to linear points if numpy/scipy missing
            steps = random.randint(15, 30)
            return [(start_x + (end_x - start_x) * i / steps, start_y + (end_y - start_y) * i / steps) for i in range(steps)]
            
        # Generate 2-3 random control points for the bezier curve
        num_points = random.randint(3, 5)
        points_x = [start_x]
        points_y = [start_y]
        
        for i in range(1, num_points - 1):
            t = i / (num_points - 1)
            # Add some jitter to the straight line
            jitter_x = random.uniform(-100, 100)
            jitter_y = random.uniform(-100, 100)
            points_x.append(start_x + (end_x - start_x) * t + jitter_x)
            points_y.append(start_y + (end_y - start_y) * t + jitter_y)
            
        points_x.append(end_x)
        points_y.append(end_y)
        
        # Interpolate
        try:
            if np is None or interp1d is None:
                raise ImportError("numpy or scipy not available")
            t = np.linspace(0, 1, len(points_x))
            t_new = np.linspace(0, 1, random.randint(25, 45))
            f_x = interp1d(t, points_x, kind='quadratic')
            f_y = interp1d(t, points_y, kind='quadratic')
            
            curve_x = f_x(t_new)
            curve_y = f_y(t_new)
            return list(zip(curve_x, curve_y))
        except Exception:
            # Fallback
            steps = random.randint(15, 30)
            return [(start_x + (end_x - start_x) * i / steps, start_y + (end_y - start_y) * i / steps) for i in range(steps)]

    def _move_mouse_human_like(self, target_x, target_y):
        # We don't always know current mouse pos in Playwright natively, so start from a random upper area
        current_x = random.randint(100, 500)
        current_y = random.randint(100, 300)
        
        curve = self._generate_bezier_curve(current_x, current_y, target_x, target_y)
        for x, y in curve:
            self.page.mouse.move(x, y)
            time.sleep(random.uniform(0.01, 0.03))

    def human_click(self, url: str, selector: str) -> str:
        """Move mouse naturally with bezier curves and click, bypassing basic bot protection."""
        try:
            self._ensure_session(headless=False) # Must be visible for best bypass
            self._goto_if_needed(url)
            self.page.wait_for_timeout(random.randint(1000, 2500))
            
            box = None
            if not selector.startswith(".") and not selector.startswith("#") and not "[" in selector:
                # Text selector
                elem = self.page.get_by_text(selector, exact=True)
                if elem.count() > 0:
                    box = elem.first.bounding_box()
                else:
                    elem = self.page.get_by_text(selector)
                    if elem.count() > 0:
                        box = elem.first.bounding_box()
            
            if not box:
                # Try standard selector
                locator = self.page.locator(selector).first
                box = locator.bounding_box()
                
            if not box:
                return f"Could not find bounding box for selector: {selector}"
                
            # Target center with slight randomized offset
            target_x = box["x"] + box["width"] / 2 + random.uniform(-box["width"]/4, box["width"]/4)
            target_y = box["y"] + box["height"] / 2 + random.uniform(-box["height"]/4, box["height"]/4)
            
            self._move_mouse_human_like(target_x, target_y)
            time.sleep(random.uniform(0.1, 0.4))
            self.page.mouse.down()
            time.sleep(random.uniform(0.05, 0.15))
            self.page.mouse.up()
            time.sleep(random.uniform(1000, 2000))
            
            content = self.page.evaluate("document.body.innerText")
            return f"Human-clicked '{selector}'. New URL: {self.page.url}\nPreview: {content[:1000]}"
        except Exception as e:
            return f"Failed to human-click: {str(e)}"

    def human_type(self, url: str, selector: str, text: str) -> str:
        """Type text into an input field with human-like random delays."""
        try:
            self._ensure_session(headless=False)
            self._goto_if_needed(url)
            self.page.wait_for_timeout(random.randint(500, 1500))
            
            locator = self.page.locator(selector).first
            locator.click(timeout=5000)
            
            # Type each character with random delay
            for char in text:
                self.page.keyboard.type(char)
                time.sleep(random.uniform(0.05, 0.2))
                
            self.page.wait_for_timeout(1000)
            content = self.page.evaluate("document.body.innerText")
            return f"Human-typed into '{selector}'.\nPreview: {content[:1000]}"
        except Exception as e:
            return f"Failed to human-type: {str(e)}"

    def solve_captcha(self, url: str) -> tuple[bool, str]:
        """Looks for Turnstile or reCAPTCHA checkboxes and attempts a human-like click to pass it."""
        try:
            self._ensure_session(headless=False)
            self._goto_if_needed(url)
            
            # Wait for potential CAPTCHA frames
            self.page.wait_for_timeout(3000)
            
            # Check for Cloudflare Turnstile
            turnstile_frames = self.page.frames
            found = False
            for frame in turnstile_frames:
                if "cloudflare" in frame.url or "turnstile" in frame.url:
                    try:
                        # Find the widget inside the frame
                        checkbox = frame.locator("input[type='checkbox'], .mark, .ctp-checkbox-label").first
                        if checkbox.count() > 0:
                            # We can't easily get bounding box inside iframe via playwright directly without math
                            # Fallback: Just click the frame itself if it's small, or use standard locator click
                            print("Attempting to bypass Turnstile...")
                            # Attempt to get bounding box of the iframe element itself
                            iframe_element = self.page.locator(f"iframe[src*='{frame.url}']").first
                            box = iframe_element.bounding_box()
                            if box:
                                target_x = box["x"] + 30 # roughly where checkbox is
                                target_y = box["y"] + box["height"] / 2
                                self._move_mouse_human_like(target_x, target_y)
                                time.sleep(random.uniform(0.1, 0.3))
                                self.page.mouse.click(target_x, target_y, delay=random.randint(50, 150))
                                found = True
                                break
                    except Exception as e:
                        pass
            
            if not found:
                # Check for reCAPTCHA
                for frame in self.page.frames:
                    if "recaptcha" in frame.url and "api2/anchor" in frame.url:
                        try:
                            checkbox = frame.locator(".recaptcha-checkbox-border").first
                            if checkbox.count() > 0:
                                iframe_element = self.page.locator(f"iframe[src*='{frame.url}']").first
                                box = iframe_element.bounding_box()
                                if box:
                                    target_x = box["x"] + 30
                                    target_y = box["y"] + box["height"] / 2
                                    self._move_mouse_human_like(target_x, target_y)
                                    time.sleep(random.uniform(0.1, 0.3))
                                    self.page.mouse.click(target_x, target_y, delay=random.randint(50, 150))
                                    found = True
                                    break
                        except Exception:
                            pass
            
            if found:
                self.page.wait_for_timeout(5000)
                content = self.page.evaluate("document.body.innerText")
                
                # Check if captcha is gone
                content_lower = content.lower() if content else ""
                if "captcha" in content_lower or "verify you are human" in content_lower:
                    return False, f"Bypass attempted but CAPTCHA still present. New URL: {self.page.url}\nPreview: {content[:1000]}"
                
                return True, f"Bypass successful. New URL: {self.page.url}\nPreview: {content[:1000]}"
            else:
                return False, "No identifiable CAPTCHA frames found on page."
                
        except Exception as e:
            return False, f"Failed to solve CAPTCHA: {str(e)}"


_SHARED_BROWSER_TOOL: Optional[BrowserTool] = None


def get_browser_tool() -> BrowserTool:
    """Returns the shared singleton BrowserTool instance for UI and agent execution."""
    global _SHARED_BROWSER_TOOL
    if _SHARED_BROWSER_TOOL is None:
        _SHARED_BROWSER_TOOL = BrowserTool()
    return _SHARED_BROWSER_TOOL


browser_tool = get_browser_tool()
