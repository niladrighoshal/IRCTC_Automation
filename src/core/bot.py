import time, os, requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import src.config as config
from src.core.webdriver_factory import create_webdriver
from src.utils.logger import setup_logger
from src.utils.time_utils import wait_until, get_synchronized_target_time
from src.core.ocr_solver import solve_captcha
import src.core.selectors as selectors

class IRCTCBot:
    def __init__(self, account, booking_data, instance_id=0):
        self.account = account
        self.booking_data = booking_data
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.status = "INITIALIZED"
        self.logger.info(f"Bot for user '{self.account['username']}' initialized.")

    def _update_status(self, new_status):
        self.status = new_status
        self.logger.info(f"Status: {self.status}")
        try:
            requests.post(f"http://localhost:8000/status/{self.instance_id}", json={"status": self.status}, timeout=1)
        except:
            self.logger.warning("Could not update dashboard.")

    def _wait(self, by, value, timeout=300):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))

    def _is_visible(self, by, value, timeout=0.1):
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return True
        except: return False

    def _get_state(self):
        if self._is_visible(By.CSS_SELECTOR, selectors.LOGIN_BUTTON_HOME): return "LOGGED_OUT"
        if self._is_visible(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT): return "AT_DASHBOARD"
        if self._is_visible(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM): return "TRAIN_LIST_PAGE"
        if self._is_visible(By.CSS_SELECTOR, selectors.PASSENGER_NAME_INPUT): return "PASSENGER_DETAILS_PAGE"
        if self._is_visible(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW): return "REVIEW_PAGE"
        if self._is_visible(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH): return "PAYMENT_PAGE"
        return "UNKNOWN"

    def _handle_popups(self):
        try:
            self._wait(By.CSS_SELECTOR, selectors.AADHAAR_OK_BUTTON, timeout=0.2).click()
            self.logger.info("Closed Aadhaar popup.")
        except: pass
        try:
            self._wait(By.CSS_SELECTOR, selectors.DISHA_BANNER_CLOSE_BUTTON, timeout=0.2).click()
            self.logger.info("Closed Disha banner.")
        except: pass

    def run(self):
        self._update_status("STARTING")

        try:
            if config.TIMED_BOOKING:
                tatkal_hour = 11 if config.IS_SL else 10
                open_time = get_synchronized_target_time(tatkal_hour, 0, offset_seconds=-180, logger=self.logger)
                self._update_status(f"Wait to open browser: {open_time.strftime('%H:%M:%S')}")
                wait_until(open_time, self.logger)

            self.driver = create_webdriver()
            if not self.driver: self._update_status("FAILED: WebDriver creation"); return
            self.driver.get("https://www.irctc.co.in/nget/train-search")

            if config.TIMED_BOOKING:
                tatkal_hour = 11 if config.IS_SL else 10
                login_time = get_synchronized_target_time(tatkal_hour, 0, offset_seconds=-65, logger=self.logger)
                self._update_status(f"Wait to login: {login_time.strftime('%H:%M:%S')}")
                wait_until(login_time, self.logger)
                self._perform_login()
                self._fill_journey_and_find_trains()

            self.logger.info("Entering resilient state-machine loop.")
            while True:
                self._handle_popups()
                current_state = self._get_state()
                self._update_status(f"State: {current_state}")

                if current_state == "LOGGED_OUT": self._perform_login()
                elif current_state == "AT_DASHBOARD": self._fill_journey_and_find_trains()
                elif current_state == "TRAIN_LIST_PAGE": self._select_train_and_class()
                elif current_state == "PASSENGER_DETAILS_PAGE": self._fill_passenger_details()
                elif current_state == "REVIEW_PAGE": self._handle_final_review()
                elif current_state == "PAYMENT_PAGE":
                    self._perform_payment()
                    self._update_status("BOOKING COMPLETE")
                    break
                else: self.logger.warning(f"In UNKNOWN state, please check browser."); time.sleep(5)
                time.sleep(1)

        except Exception as e:
            self._update_status(f"FATAL ERROR: {e}")
        finally:
            self.logger.info("Bot run finished. Browser will close in 60s.")
            time.sleep(60)
            if self.driver: self.driver.quit()
            self._update_status("FINISHED")

    def _perform_login(self):
        self._update_status("Performing Login")
        self._wait(By.CSS_SELECTOR, selectors.LOGIN_BUTTON_HOME).click()
        self._wait(By.CSS_SELECTOR, selectors.USERNAME_INPUT).send_keys(self.account["username"])
        self._wait(By.CSS_SELECTOR, selectors.PASSWORD_INPUT).send_keys(self.account["password"])
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=config.USE_GPU, logger=self.logger)
        if not solved_text: raise Exception("Captcha failed.")
        self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN).send_keys(solved_text)
        self._wait(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL).click()
        self._wait(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON)
    def _fill_journey_and_find_trains(self):
        self._update_status("Filling Journey Details")
        from_input = self._wait(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT)
        from_input.send_keys(self.booking_data['train']['from_station'])
        self._wait(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION).click()
        to_input = self._wait(By.CSS_SELECTOR, selectors.JOURNEY_TO_INPUT)
        to_input.send_keys(self.booking_data['train']['to_station'])
        self._wait(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION).click()
        date_input = self._wait(By.CSS_SELECTOR, selectors.DATE_INPUT)
        self.driver.execute_script(f"arguments[0].value = '{self.booking_data['train']['date']}';", date_input)
        self._wait(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON).click()
    def _select_train_and_class(self):
        self._update_status("Selecting Train & Class")
        self._wait(By.CSS_SELECTOR, selectors.QUOTA_TATKAL_RADIO).click()
        time.sleep(1.5)
        for train in self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM):
            if self.booking_data['train']['train_no'] in train.text:
                class_sel = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=self.booking_data['train']['class'])
                train.find_element(By.CSS_SELECTOR, class_sel).click()
                time.sleep(1)
                train.find_element(By.CSS_SELECTOR, selectors.BOOK_NOW_BUTTON).click()
                return
        raise Exception(f"Train {self.booking_data['train']['train_no']} not found.")
    def _fill_passenger_details(self):
        self._update_status("Filling Passenger Details")
        for i, p in enumerate(self.booking_data['passengers']):
            self._wait(By.CSS_SELECTOR, selectors.PASSENGER_NAME_INPUT).send_keys(p['name'])
            self._wait(By.CSS_SELECTOR, selectors.PASSENGER_AGE_INPUT).send_keys(p['age'])
            self._wait(By.CSS_SELECTOR, selectors.PASSENGER_GENDER_DROPDOWN).click()
            self._wait(By.XPATH, selectors.GENDER_OPTION_XPATH.format(gender=p['sex'])).click()
            if i < len(self.booking_data['passengers']) - 1:
                self._wait(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON).click()
        self._wait(By.CSS_SELECTOR, selectors.PASSENGER_MOBILE_INPUT).send_keys(self.booking_data["preferences"]["phone_number"])
        self._wait(By.CSS_SELECTOR, selectors.SUBMIT_PASSENGER_DETAILS_BUTTON).click()
    def _handle_final_review(self):
        self._update_status("Final Review & Captcha")
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_REVIEW).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=config.USE_GPU, logger=self.logger)
        if not solved_text: raise Exception("Review Captcha failed.")
        self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW).send_keys(solved_text)
        self._wait(By.CSS_SELECTOR, selectors.PROCEED_TO_PAY_BUTTON).click()
    def _perform_payment(self):
        self._update_status("Handling Payment")
        if self.booking_data['preferences']['payment_method'] == "Pay through BHIM UPI":
            upi_radio = self._wait(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH)
            self.driver.execute_script("arguments[0].click();", upi_radio)
            pay_button = self._wait(By.CSS_SELECTOR, selectors.PAY_AND_BOOK_BUTTON)
            self.driver.execute_script("arguments[0].click();", pay_button)
            self.logger.info("Payment initiated.")
        else:
            raise NotImplementedError("Only UPI payment is currently supported.")
