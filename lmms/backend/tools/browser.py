import os
import glob
import platform
import re
from playwright.sync_api import sync_playwright
import time
import random
import math
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = lambda page: None
try:
    import numpy as np
    from scipy.interpolate import interp1d
except ImportError:
    np = None
class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.cookie_file = os.path.expanduser("~/.lmms/browser_cookies.json")

    def _ensure_session(self, headless=True, user_data_dir=None, profile_name="Default"):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            
        if user_data_dir is None:
            user_data_dir = os.path.expanduser("~/.lmms/browser_profile")
            
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
            
            # Inject stealth to bypass detection
            try:
                stealth_sync(self.page)
            except Exception as e:
                print(f"Warning: Failed to inject stealth: {e}")
                
            self.load_cookies()

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
        self.save_cookies()
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
            return f"[AUTHENTICATED SESSION STARTED (Headless={headless})]\n{content[:2000]}"
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
            return content[:2000]
        except Exception as e:
            return f"Failed to scroll: {str(e)}"

    def open_url(self, url: str) -> str:
        try:
            self._ensure_session()
            self._goto_if_needed(url)
            self.page.wait_for_timeout(2000)
            content = self.page.evaluate("document.body.innerText")
            
            # Auto-detect CAPTCHA and fallback to human-like bypass
            content_lower = content.lower() if content else ""
            if "captcha" in content_lower or "verify you are human" in content_lower or "cloudflare" in content_lower or "checking your browser" in content_lower:
                print("\n[BrowserTool] CAPTCHA detected. Initiating Human-like Bypass...")
                return self.solve_captcha(url)
                
            if content:
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r' +', ' ', content)
            return content[:2000]
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
            self.save_cookies()
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
            return content[:2000]
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

    def solve_captcha(self, url: str) -> str:
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
                return f"Captcha Bypass Attempted. New URL: {self.page.url}\nPreview: {content[:1000]}"
            else:
                return "No identifiable CAPTCHA frames found on page."
                
        except Exception as e:
            return f"Failed to solve CAPTCHA: {str(e)}"
