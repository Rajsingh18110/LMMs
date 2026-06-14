import os
import glob
import platform
import re
from playwright.sync_api import sync_playwright

class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    def _ensure_session(self, headless=True, user_data_dir=None, profile_name="Default"):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            
        if not self.browser:
            if user_data_dir:
                try:
                    self.browser = self.playwright.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=headless,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            f"--profile-directory={profile_name}"
                        ],
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                except Exception as e:
                    if "already in use" in str(e) or "lock" in str(e).lower() or "existing browser session" in str(e):
                        import tempfile
                        import shutil
                        print(f"  [dim]Browser is locked. Creating a temporary session clone to safely extract data...[/dim]")
                        temp_dir = tempfile.mkdtemp(prefix="lmms_browser_")
                        try:
                            # Copy the profile, ignoring massive cache folders to make it fast (usually < 2s)
                            shutil.copytree(
                                user_data_dir, temp_dir, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(
                                    "SingletonLock", "SingletonCookie", "SingletonSocket",
                                    "Cache", "Code Cache", "GPUCache", "DawnCache", "Network Action Predictor",
                                    "File System", "IndexedDB", "Service Worker", "VideoDecodeStats", "Shared Dictionary"
                                )
                            )
                        except Exception as copy_e:
                            pass # Might have permission errors but we proceed
                        
                        self.browser = self.playwright.chromium.launch_persistent_context(
                            user_data_dir=temp_dir,
                            headless=headless,
                            args=[
                                "--disable-blink-features=AutomationControlled",
                                f"--profile-directory={profile_name}"
                            ],
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                    else:
                        raise e
            else:
                self.browser = self.playwright.chromium.launch(headless=headless)
                
        if not self.page:
            if hasattr(self.browser, "pages") and len(self.browser.pages) > 0:
                self.page = self.browser.pages[0]
            elif hasattr(self.browser, "new_page"):
                self.page = self.browser.new_page()

    def _goto_if_needed(self, url: str):
        if not url: return
        # Check current URL, ignoring trailing slashes or hash
        current_url = self.page.url.split("#")[0].rstrip("/")
        target_url = url.split("#")[0].rstrip("/")
        if current_url != target_url and current_url != "about:blank":
            try:
                self.page.goto(url, timeout=30000)
            except:
                pass
        elif current_url == "about:blank":
            self.page.goto(url, timeout=30000)

    def close(self):
        if self.browser:
            try: self.browser.close()
            except: pass
            self.browser = None
            self.page = None
        if self.playwright:
            try: self.playwright.stop()
            except: pass
            self.playwright = None

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
                profile_dirs = glob.glob(os.path.join(base_path, "Profile*")) + [os.path.join(base_path, "Default")]
                for pdir in profile_dirs:
                    if os.path.exists(pdir):
                        name = os.path.basename(pdir)
                        browser_name = "Chrome" if "Chrome" in base_path else "Brave" if "Brave" in base_path else "Edge" if "Edge" in base_path else "Chromium"
                        
                        email = ""
                        pref_path = os.path.join(pdir, "Preferences")
                        if os.path.exists(pref_path):
                            try:
                                import json
                                with open(pref_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    # Try to extract email
                                    acc_info = data.get("account_info", [])
                                    if acc_info and len(acc_info) > 0:
                                        email = acc_info[0].get("email", "")
                            except Exception:
                                pass
                        
                        display_name = f"{browser_name}_{name}"
                        if email:
                            display_name += f" ({email})"
                            
                        profiles[display_name] = {
                            "base_path": base_path,
                            "dir_name": name
                        }
                        
        return profiles

    def open_authenticated(self, url: str, user_data_dir: str, profile_name: str = "Default", headless: bool = True) -> str:
        """Launch browser with persistent context to reuse cookies. Stays open for subsequent commands."""
        try:
            self.close() # Reset session
            self._ensure_session(headless=headless, user_data_dir=user_data_dir, profile_name=profile_name)
            self._goto_if_needed(url)
            self.page.wait_for_timeout(2000)
            content = self.page.evaluate("document.body.innerText")
            if content:
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r' +', ' ', content)
            return f"[AUTHENTICATED SESSION STARTED (Headless={headless})]\n{content[:4000]}"
        except Exception as e:
            return f"Failed to open authenticated URL: {str(e)}"

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
            return content[:3000]
        except Exception as e:
            return f"Failed to scroll: {str(e)}"

    def open_url(self, url: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            self.page.wait_for_timeout(2000)
            content = self.page.evaluate("document.body.innerText")
            if content:
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r' +', ' ', content)
            return content[:3000]
        except Exception as e:
            return f"Failed to open URL: {str(e)}"

    def click_element(self, url: str, selector: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            
            # Smart selector approach: if it's not a CSS selector but plain text, try clicking by text
            if not selector.startswith(".") and not selector.startswith("#") and not "[" in selector:
                try:
                    elem = self.page.get_by_text(selector, exact=True)
                    if elem.count() > 0:
                        elem.first.click(timeout=5000)
                    else:
                        elem = self.page.get_by_text(selector)
                        if elem.count() > 0:
                            elem.first.click(timeout=5000)
                        else:
                            self.page.click(selector, timeout=5000)
                except:
                    self.page.click(selector, timeout=5000)
            else:
                self.page.click(selector, timeout=5000)
                
            self.page.wait_for_timeout(3000)
            content = self.page.evaluate("document.body.innerText")
            return f"Clicked '{selector}'. New page URL: {self.page.url}\nPreview: {content[:1000]}"
        except Exception as e:
            return f"Failed to click element: {str(e)}"

    def fill_form(self, url: str, fields: dict) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            for selector, value in fields.items():
                self.page.fill(selector, value)
            return f"Filled form fields successfully on {self.page.url}"
        except Exception as e:
            return f"Failed to fill form: {str(e)}"

    def screenshot(self, url: str, save_path: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            self.page.screenshot(path=save_path)
            return f"Screenshot saved to {save_path}"
        except Exception as e:
            return f"Failed to take screenshot: {str(e)}"

    def scrape(self, url: str, selector: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            elements = self.page.query_selector_all(selector)
            content = "\n".join([el.inner_text() for el in elements if el])
            if not content:
                return f"No content found for selector: {selector}"
            return content[:5000]
        except Exception as e:
            return f"Failed to scrape: {str(e)}"

    def execute_js(self, url: str, js_code: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            result = self.page.evaluate(js_code)
            return f"JS Execution result: {result}"
        except Exception as e:
            return f"Failed to execute JS: {str(e)}"
