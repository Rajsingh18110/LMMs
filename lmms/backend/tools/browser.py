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
        self._current_headless = None
        self.cookie_file = os.path.expanduser("~/.lmms/browser_cookies.json")

    def _ensure_session(self, headless=None, user_data_dir=None, profile_name="Default"):
        if headless is None:
            headless = self._current_headless if self._current_headless is not None else False

        if self.browser and self._current_headless != headless:
            self.close()

        if not self.playwright:
            self.playwright = sync_playwright().start()
            
        if user_data_dir is None:
            user_data_dir = os.path.expanduser("~/.lmms/browser_profile")

        self._current_headless = headless
            
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
                                    "VideoDecodeStats", "Shared Dictionary", "Media Cache"
                                )
                            )
                        except Exception as copy_e:
                            pass # Might have permission errors but we proceed
                        
                        try:
                            self.browser = self.playwright.chromium.launch_persistent_context(
                                user_data_dir=temp_dir,
                                headless=headless,
                                args=[
                                    "--disable-blink-features=AutomationControlled",
                                    f"--profile-directory={profile_name}"
                                ],
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            )
                        except Exception as temp_e:
                            print(f"  [dim]Temp session failed. Falling back to blank headless session.[/dim]")
                            self.browser = self.playwright.chromium.launch(headless=headless)
                    else:
                        print(f"  [dim]Persistent context failed ({e}). Falling back to blank headless session.[/dim]")
                        self.browser = self.playwright.chromium.launch(headless=headless)
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
        pass

    def save_cookies(self):
        pass

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
            
            # Extract interactive elements so AI knows what it can click/fill
            interactives = self.page.evaluate('''() => {
                const inputs = Array.from(document.querySelectorAll('input, textarea')).map(i => `[Input] name="${i.name || i.id || ''}" type="${i.type || ''}" placeholder="${i.placeholder || ''}"`);
                const links = Array.from(document.querySelectorAll('a, button')).map(b => `[Clickable] "${b.innerText.trim()}"`);
                return inputs.concat(links).filter(x => x.length > 10).join('\\n');
            }''')
            
            if content:
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r' +', ' ', content)
                
            full_output = f"[AUTHENTICATED SESSION STARTED (Headless={headless})]\n\n--- PAGE TEXT ---\n{content[:1000]}\n\n--- INTERACTIVE ELEMENTS ---\n{interactives[:800]}"
            return full_output
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

    def get_interactive_dom(self, url: str = None) -> str:
        """Scan active page and extract all interactive DOM elements (inputs, buttons, links) with unique IDs."""
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            self.page.wait_for_timeout(1000)

            # Injected script that tags and extracts interactive elements
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
                        placeholder: placeholder,
                        label: ariaLabel || text,
                        selector: sel
                    });
                }
                return {
                    title: document.title,
                    url: window.location.href,
                    elements: items.slice(0, 80)
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
                    if el['type']: desc_parts.append(f"type='{el['type']}'")
                    if el['name']: desc_parts.append(f"name='{el['name']}'")
                    if el['placeholder']: desc_parts.append(f"placeholder='{el['placeholder']}'")
                    if el['label']: desc_parts.append(f"label='{el['label']}'")
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

    def open_url(self, url: str, headless: bool = False) -> str:
        try:
            self._ensure_session(headless=headless)
            self._goto_if_needed(url)
            self.page.wait_for_timeout(2000)
            
            # Auto-detect CAPTCHA and fallback to human-like bypass
            content = self.page.evaluate("document.body.innerText || ''")
            content_lower = content.lower() if content else ""
            if "captcha" in content_lower or "verify you are human" in content_lower or "cloudflare" in content_lower or "checking your browser" in content_lower:
                print("\n[BrowserTool] CAPTCHA detected. Initiating Human-like Bypass...")
                success, msg = self.solve_captcha(url)
                if not success:
                    return f"[CAPTCHA_FAILED] {msg}"
            return self.get_interactive_dom()
        except Exception as e:
            return f"Failed to open URL: {str(e)}"

    def click_element(self, selector: str = None, url: str = None, id: int = None) -> str:
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
            
            sel = str(id if id is not None else selector).strip()
            # If selector is ID number like "1" or "[ID 1]" or 1
            id_match = re.search(r'\b(\d+)\b', sel)
            if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                target_sel = f"[data-lmms-id='{raw_id}']"
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
                
            self.page.wait_for_timeout(2500)
            self.save_cookies()
            return f"[CLICK_SUCCESS] Clicked '{sel}'.\n" + self.get_interactive_dom()
        except Exception as e:
            return f"Failed to click element '{selector}': {str(e)}"

    def fill_form(self, fields: dict, url: str = None) -> str:
        try:
            self._ensure_session()
            if url:
                self._goto_if_needed(url)
                
            filled_items = []
            for raw_sel, val in fields.items():
                sel = str(raw_sel).strip()
                id_match = re.search(r'\b(\d+)\b', sel)
                if sel.isdigit() or (sel.startswith("[ID") and id_match) or sel.startswith("@"):
                    raw_id = id_match.group(1) if id_match else sel.lstrip("@")
                    target_sel = f"[data-lmms-id='{raw_id}']"
                else:
                    target_sel = sel
                self.page.fill(target_sel, str(val))
                filled_items.append(f"{target_sel}='{val}'")
                
            self.page.wait_for_timeout(1000)
            self.save_cookies()
            return f"[FILL_SUCCESS] Filled fields: {', '.join(filled_items)}.\n" + self.get_interactive_dom()
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
                
            self.page.focus(target_sel)
            self.page.fill(target_sel, "")
            self.page.type(target_sel, text, delay=50)
            if press_enter:
                self.page.press(target_sel, "Enter")
                self.page.wait_for_timeout(2000)
            self.save_cookies()
            return f"[TYPE_SUCCESS] Typed '{text}' into {target_sel}.\n" + self.get_interactive_dom()
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
