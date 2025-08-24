# Automation/tasks/payment_task.py

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class PaymentTask:
    def __init__(self, orchestrator):
        self.bot = orchestrator
        self.driver = self.bot.driver
        self._log = self.bot._log
        self._click_with_retries = self.bot._click_with_retries

    def _get_payment_details(self):
        data = self.bot.get_latest_json()
        if not data:
            self._log("Could not read saved details for payment.")
            return None, None

        method = data.get("preferences", {}).get("payment_method")
        upi_id = data.get("preferences", {}).get("upi_id")
        return method, upi_id

    def execute(self):
        self._log("On review page, handling final captcha before payment...")

        # --- Captcha Loop on Review Page ---
        for attempt in range(20):
            pay_and_book_btn = self.bot._safe_find(By.XPATH, "//button[contains(., 'Pay & Book')]", timeout=1)
            if pay_and_book_btn and pay_and_book_btn.is_enabled():
                self._log("Captcha passed, 'Pay & Book' button is visible.")
                break

            self._log(f"Attempting review page captcha: {attempt + 1}/20")

            img = self.bot._safe_find(By.CSS_SELECTOR, "img.captcha-img", timeout=10)
            if not img:
                self._log("Could not find captcha image on review page. Checking for Pay&Book btn again.")
                time.sleep(1)
                continue

            try:
                src = img.get_attribute("src")
                solved, _ = self.bot.ocr.solve_captcha(src)
                if solved:
                    inp = self.driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='captcha']")
                    inp.clear()
                    inp.send_keys(solved)
                    self._click_with_retries(By.XPATH, "//button[contains(., 'Continue')]", timeout=3)
                else:
                    self._click_with_retries(By.CSS_SELECTOR, "a .glyphicon-repeat", timeout=2)
            except Exception as e:
                self._log(f"Error in review page captcha attempt: {e}")
                self._click_with_retries(By.CSS_SELECTOR, "a .glyphicon-repeat", timeout=2)

            time.sleep(1)
        else:
            self._log("Failed to solve review page captcha after 20 attempts.")
            return False

        # --- Click Pay & Book ---
        if not self._click_with_retries(By.XPATH, "//button[contains(., 'Pay & Book')]", timeout=10):
            self._log("Failed to click 'Pay & Book' button.")
            return False

        # --- Handle Payment Gateway ---
        payment_method, upi_id = self._get_payment_details()
        if "BHIM UPI" in payment_method:
            return self._handle_upi_gateway(upi_id)
        elif "IRCTC Wallet" in payment_method:
            return self._pay_with_wallet()
        else:
            self._log(f"Unsupported payment method: {payment_method}")
            return False

    def _handle_upi_gateway(self, upi_id):
        if not upi_id:
            self._log("UPI ID not provided for payment.")
            return False

        self._log("On payment gateway, entering UPI details...")
        try:
            bhim_upi_option_selector = "//label[contains(., 'Pay through BHIM/UPI')]"
            if not self._click_with_retries(By.XPATH, bhim_upi_option_selector, timeout=self.bot.PAGE_LOAD_TIMEOUT):
                 self._log("Could not find BHIM/UPI payment method on gateway.")
                 return False

            upi_input_selector = "input#vpaCheck"
            upi_input = WebDriverWait(self.driver, self.bot.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, upi_input_selector))
            )
            upi_input.send_keys(upi_id)

            pay_btn_selector = "input#upi-sbmt"
            self._click_with_retries(By.CSS_SELECTOR, pay_btn_selector, timeout=5)

            self._log(f"Final payment submission for {upi_id}. Waiting for user approval and PNR...")

            pnr_selector = "//div[contains(., 'PNR No.')]"
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.XPATH, pnr_selector))
            )
            self._log("PNR Detected! Booking successful.")
            return True
        except Exception as e:
            self._log(f"Error on UPI gateway page: {e}")
            return False

    def _pay_with_wallet(self):
        self._log("IRCTC Wallet payment is not yet implemented.")
        return False
