# Automation/login.py
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# optional OCR module (if present)
try:
    from Automation.ocr import CaptchaSolver
except Exception:
    CaptchaSolver = None


class IRCTCLogin:
    """
    Robust, blocking login helper.
    - automation_folder: Path to Automation folder (used to find Form/Saved_Details)
    - gui: gui_status.FloatingGUI instance (optional)
    """

    def __init__(self, automation_folder, gui=None, use_gpu=False):
        self.automation_folder = Path(automation_folder)
        self.gui = gui
        self.driver = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.ocr = CaptchaSolver() if CaptchaSolver else None
        self.use_gpu = use_gpu

    def _log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        txt = f"{stamp} {msg}"
        if self.gui:
            self.gui.set_status_text(txt)
        else:
            print(txt)

    def _safe_find(self, by, selector, timeout=1):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except Exception:
            return None

    def _click_with_retries(self, by, selector, timeout=300, retry_interval=1):
        end = time.time() + timeout
        while time.time() < end and not self._stop_event.is_set():
            try:
                el = self._safe_find(by, selector, timeout=retry_interval)
                if not el:
                    time.sleep(retry_interval)
                    continue
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
                except Exception:
                    pass
                try:
                    el.click()
                    time.sleep(0.2)
                    return True
                except (ElementClickInterceptedException, WebDriverException):
                    try:
                        self.driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.2)
                        return True
                    except Exception:
                        pass
                time.sleep(retry_interval)
            except StaleElementReferenceException:
                time.sleep(0.2)
            except Exception:
                time.sleep(retry_interval)
        self._log(f"click timeout: {selector}")
        return False

    def get_latest_json(self):
        saved_folder = self.automation_folder.parent / "Form" / "Saved_Details"
        files = list(saved_folder.glob("*.json"))
        if not files:
            return None
        latest = max(files, key=lambda f: f.stat().st_mtime)
        try:
            return json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return None

    def launch_browser(self, brave_path=None, profile_path=None):
        opts = uc.ChromeOptions()
        if brave_path:
            opts.binary_location = brave_path
        if profile_path:
            opts.add_argument(f"--user-data-dir={profile_path}")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--disable-extensions")
        opts.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        })
        self.driver = uc.Chrome(options=opts)
        time.sleep(1)
        self._log("Browser launched")

    def _auto_close_popups(self):
        """
        Runs in background. Closes:
         - Aadhaar OK popup matching aria-label containing 'Aadhaar'
         - DISHA close button with id dша-banner-close or img#disha-banner-close
         - overlay masks (attempts removal)
         - extension/other overlays
        """
        while not self._stop_event.is_set():
            try:
                if not self.driver:
                    time.sleep(0.2)
                    continue

                # Aadhaar
                try:
                    btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label,'Aadhaar') or contains(.,'Aadhaar')]")
                    if btn.is_displayed() and btn.is_enabled():
                        try:
                            btn.click()
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", btn)
                            except Exception:
                                pass
                        self._log("Closed Aadhaar popup")
                except Exception:
                    pass

                # DISHA close
                try:
                    btn = self.driver.find_element(By.ID, "disha-banner-close")
                    if btn.is_displayed():
                        try:
                            btn.click()
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", btn)
                            except Exception:
                                pass
                        self._log("Closed DISHA popup")
                except Exception:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, "img#disha-banner-close, svg#disha-banner-close")
                        if btn.is_displayed():
                            try:
                                btn.click()
                            except Exception:
                                try:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                except Exception:
                                    pass
                            self._log("Closed DISHA popup")
                    except Exception:
                        pass

                # Generic overlay cleanup (best-effort)
                try:
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, "div.ui-dialog-mask, div.ui-widget-overlay, .modal-backdrop, div.popup-overlay")
                    for ov in overlays:
                        try:
                            self.driver.execute_script("arguments[0].parentNode.removeChild(arguments[0]);", ov)
                        except Exception:
                            pass
                    if overlays:
                        self._log("Removed overlays")
                except Exception:
                    pass

                # If logged-out link appears, click it to go back to login
                try:
                    relinks = self.driver.find_elements(By.XPATH, "//a[contains(.,'Click here to login') or normalize-space(.)='Click Here']")
                    for r in relinks:
                        if r.is_displayed():
                            try:
                                r.click()
                                self._log("Clicked re-login link")
                            except Exception:
                                try:
                                    self.driver.execute_script("arguments[0].click();", r)
                                    self._log("Clicked re-login link (js)")
                                except Exception:
                                    pass
                except Exception:
                    pass

            except Exception:
                pass
            time.sleep(0.25)

    def _relogin_watchdog(self):
        """
        If logout occurs unexpectedly, attempt to re-enter login flow.
        This thread will attempt the login button to re-initiate.
        """
        while not self._stop_event.is_set():
            try:
                if not self.driver:
                    time.sleep(1)
                    continue
                # if logout link not present and the login link is visible, try to re-initiate
                try:
                    login_link = self.driver.find_element(By.CSS_SELECTOR, "a.loginText")
                    # if displayed and clickable try clicking (tolerant)
                    if login_link.is_displayed():
                        self._click_with_retries(By.CSS_SELECTOR, "a.loginText", timeout=10, retry_interval=0.5)
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(2)

    def _fetch_irctc_time(self):
        if not self.driver:
            return None
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, "span strong")
            raw = el.text.strip()
            if "[" in raw and "]" in raw:
                return raw.split("[", 1)[1].split("]", 1)[0].strip()
            return raw
        except Exception:
            return None

    def login(self, brave_path=None, profile_path=None, max_captcha_attempts=20):
        """Launch browser (if needed), close popups continuously, click login, fill creds, solve captcha."""
        if not self.driver:
            self.launch_browser(brave_path=brave_path or None, profile_path=profile_path or None)

        # start helper threads
        threading.Thread(target=self._auto_close_popups, daemon=True).start()
        threading.Thread(target=self._relogin_watchdog, daemon=True).start()

        # go to train-search
        try:
            self.driver.get("https://www.irctc.co.in/nget/train-search")
        except Exception:
            pass
        self._log("Navigated to IRCTC page")

        # ensure login button clickable (tolerant up to 5 minutes)
        if not self._click_with_retries(By.CSS_SELECTOR, "a.loginText", timeout=300, retry_interval=1):
            self._log("Could not click login button")
            return False
        self._log("Login button clicked")

        # read latest saved JSON
        data = self.get_latest_json()
        if not data:
            self._log("No saved details file found")
            return False
        username = data["login"]["username"]
        password = data["login"]["password"]

        # username field
        if self._click_with_retries(By.CSS_SELECTOR, 'input[formcontrolname="userid"]', timeout=120, retry_interval=0.5):
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="userid"]')
                el.clear()
                el.send_keys(username)
            except Exception:
                pass
        else:
            self._log("Username input not available")

        # password field
        if self._click_with_retries(By.CSS_SELECTOR, 'input[formcontrolname="password"]', timeout=120, retry_interval=0.5):
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="password"]')
                el.clear()
                el.send_keys(password)
            except Exception:
                pass
        else:
            self._log("Password input not available")

        # attempt captcha up to max_captcha_attempts
        for attempt in range(max_captcha_attempts):
            if self._stop_event.is_set():
                break

            img = self._safe_find(By.CSS_SELECTOR, "img.captcha-img", timeout=10)
            if not img:
                self._log(f"Captcha not present (attempt {attempt+1})")
                time.sleep(1)
                continue

            src = None
            try:
                src = img.get_attribute("src")
            except Exception:
                src = None

            solved = None
            if self.ocr and src:
                try:
                    solved, _ = self.ocr.solve_captcha(src)
                except Exception:
                    solved = None

            if solved:
                try:
                    inp = self.driver.find_element(By.CSS_SELECTOR, "input#captcha")
                    inp.clear()
                    inp.send_keys(solved)
                except Exception:
                    pass

            # click sign in
            clicked = self._click_with_retries(By.XPATH, "//button[text()='SIGN IN']", timeout=5, retry_interval=0.5)
            if not clicked:
                self._log("Sign-in click failed, retrying")
                continue

            # check for logout button (successful login)
            try:
                WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/nget/logout']")))
                self._log(f"Logged in successfully (captcha:{solved})")
                return True
            except Exception:
                self._log(f"Login attempt {attempt+1} failed")
                # click captcha reload icon if present
                try:
                    self._click_with_retries(By.CSS_SELECTOR, "span.glyphicon-repeat", timeout=3, retry_interval=0.5)
                except Exception:
                    pass
                time.sleep(1)
                continue

        self._log("Login failed after attempts")
        return False

    def wait_until(self, target_time_str):
        """target_time_str: HH:MM:SS – busy wait tolerant"""
        self._log(f"Waiting until {target_time_str}")
        while True:
            now = time.strftime("%H:%M:%S")
            if now >= target_time_str:
                return
            time.sleep(0.05)

    def fill_train_details(self, AC=True, SL=False):
        self._log(f"Filling train details AC={AC}, SL={SL}")
        # placeholder - implement later

    def press_search_button(self):
        self._log("Press search button (placeholder)")
        # placeholder - implement later

    def stop(self):
        self._stop_event.set()
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
