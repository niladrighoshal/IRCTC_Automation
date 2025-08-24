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

    def execute(self, config, max_captcha_attempts=20):
        if not self.driver:
            self.driver = self.bot.driver

        # Extract login credentials from the config
        login_data = config.get("login", {})
        username = login_data.get("username")
        password = login_data.get("password")

        if not username or not password:
            self._log("Username or password not found in config.")
            return False

        # The rest of the login logic remains the same...
        # ... it uses the username and password variables.

        # Click login button
        if not self._click_with_retries(By.CSS_SELECTOR, "a.loginText.search_btn"):
            self._log("Could not click login button"); return False

        # Fill fields
        self.driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="userid"]').send_keys(username)
        self.driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="password"]').send_keys(password)

        # Captcha loop
        for attempt in range(max_captcha_attempts):
            # ... (captcha logic)
            img = self._safe_find(By.CSS_SELECTOR, "img.captcha-img", timeout=10)
            if not img: time.sleep(1); continue

            src = img.get_attribute("src")
            solved, _ = self.bot.ocr.solve_captcha(src)
            self.driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='captcha']").send_keys(solved)

            self._click_with_retries(By.CSS_SELECTOR, "button.train_Search")

            # Check for success
            try:
                WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[aria-label='Click here Logout from application']")))
                self._log("Logged in successfully.")
                return True
            except:
                self._log(f"Login attempt {attempt + 1} failed.")
                self._click_with_retries(By.CSS_SELECTOR, "a .glyphicon-repeat", timeout=2)

        return False
