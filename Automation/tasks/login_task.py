import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginTask:
    def __init__(self, orchestrator):
        self.bot = orchestrator
        self.driver = self.bot.driver
        self._log = self.bot._log
        self._safe_find = self.bot._safe_find
        self._click_with_retries = self.bot._click_with_retries

    def execute(self, brave_path=None, profile_path=None, max_captcha_attempts=20):
        """Launch browser (if needed), close popups continuously, click login, fill creds, solve captcha."""
        if not self.driver:
            self.bot.launch_browser(brave_path=brave_path or None, profile_path=profile_path or None)
            self.driver = self.bot.driver # Re-assign driver after launch

        # Start helper threads that are part of the orchestrator
        threading.Thread(target=self.bot._auto_close_popups, daemon=True).start()
        threading.Thread(target=self.bot._relogin_watchdog, daemon=True).start()

        # go to train-search
        try:
            self.driver.get("https://www.irctc.co.in/nget/train-search")
        except Exception:
            pass
        self._log("Navigated to IRCTC page")

        # ensure login button clickable (tolerant up to 5 minutes)
        if not self._click_with_retries(By.CSS_SELECTOR, "a.loginText.search_btn", timeout=300, retry_interval=1):
            self._log("Could not click login button")
            return False
        self._log("Login button clicked")

        # read latest saved JSON
        data = self.bot.get_latest_json()
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
            if self.bot._stop_event.is_set():
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
            if self.bot.ocr and src:
                try:
                    solved, _ = self.bot.ocr.solve_captcha(src)
                except Exception:
                    solved = None

            if solved:
                try:
                    inp = self.driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='captcha']")
                    inp.clear()
                    inp.send_keys(solved)
                except Exception:
                    pass

            # click sign in
            clicked = self._click_with_retries(By.CSS_SELECTOR, "button.train_Search", timeout=5, retry_interval=0.5)
            if not clicked:
                self._log("Sign-in click failed, retrying")
                continue

            # check for logout button (successful login)
            try:
                logout_selector = "a[aria-label='Click here Logout from application']"
                WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, logout_selector)))
                self._log(f"Logged in successfully (captcha:{solved})")
                return True
            except Exception:
                self._log(f"Login attempt {attempt+1} failed")
                # click captcha reload icon if present
                try:
                    self._click_with_retries(By.CSS_SELECTOR, "a .glyphicon-repeat", timeout=3, retry_interval=0.5)
                except Exception:
                    pass
                time.sleep(1)
                continue

        self._log("Login failed after attempts")
        return False
