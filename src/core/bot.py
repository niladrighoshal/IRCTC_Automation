import time
import os
import re
import requests
import threading
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.core.webdriver_factory import create_webdriver
from src.utils.logger import setup_logger
from src.utils.time_utils import wait_until, get_synchronized_target_time
from src.core.ocr_solver import solve_captcha
import src.core.selectors as selectors

class IRCTCBot:
    def __init__(self, bot_config, excel_logger, config_filename, instance_id=0):
        self.bot_config = bot_config
        self.account = bot_config.get('account', {})
        self.excel_logger = excel_logger
        self.config_filename = config_filename
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.status = "INITIALIZED"
        self.stop_event = threading.Event()
        self.logger.info(f"Bot for user '{self.account.get('username', 'N/A')}' initialized.")

    # --- Core Methods ---
    def run(self):
        """Main entry point for the bot thread."""
        # This is the first action, setting up the Excel column with all static info.
        self.excel_logger.setup_column(self.instance_id, self.bot_config, self.config_filename)

        self._update_status("STARTING")
        popup_thread = None
        try:
            # Get preferences from the config dictionary
            prefs = self.bot_config.get("preferences", {})
            is_timed = prefs.get("timed", False)
            is_headless = prefs.get("headless", False)
            use_gpu = not prefs.get("ocr_cpu", True)

            # Create webdriver
            self.driver = create_webdriver(is_headless=is_headless, use_gpu=use_gpu)
            if not self.driver:
                self._update_status("FAILED: WebDriver creation")
                return

            # Start the popup killer thread
            popup_thread = threading.Thread(target=self._popup_killer_loop, daemon=True)
            popup_thread.start()

            self.driver.get("https://www.irctc.co.in/nget/train-search")

            if is_timed:
                self._run_timed_booking()
            else:
                self._run_normal_booking()

        except Exception as e:
            self.logger.error(f"A fatal error occurred: {e}", exc_info=True)
            self._update_status(f"FATAL ERROR: {e}")
        finally:
            self.logger.info("Bot run finished. Browser will close in 60s.")
            time.sleep(60)
            if self.driver:
                self.driver.quit()
            self.stop_event.set() # Signal popup killer to stop
            if popup_thread:
                popup_thread.join()
            self._update_status("FINISHED")

    def _run_normal_booking(self):
        """Executes a non-timed booking flow."""
        self.logger.info("Starting Normal Booking flow.")
        self._resilient_state_loop()

    def _run_timed_booking(self):
        """Executes a precision-timed Tatkal booking flow."""
        self.logger.info("Starting Timed (Tatkal) Booking flow.")
        prefs = self.booking_data.get("preferences", {})
        is_ac_tatkal = prefs.get("ac", False)
        is_sl_tatkal = prefs.get("sl", False)

        if not is_ac_tatkal and not is_sl_tatkal:
            raise ValueError("Timed booking selected, but neither AC nor SL toggle is on.")

        tatkal_hour = 10 if is_ac_tatkal else 11

        # 1. Wait until T-65 seconds to login
        login_time = get_synchronized_target_time(tatkal_hour, 0, offset_seconds=-65, logger=self.logger)
        self._update_status(f"Waiting to login at {login_time.strftime('%H:%M:%S')}")
        wait_until(login_time, self.logger)

        self._perform_login()

        # 2. Fill journey details to get to the train list page
        self._fill_journey_and_find_trains()

        # 3. Wait until the precise moment to book
        book_time = get_synchronized_target_time(tatkal_hour, 0, offset_seconds=0.5, logger=self.logger) # 500ms buffer
        self._update_status(f"On train list page. Waiting to book at {book_time.strftime('%H:%M:%S')}")
        wait_until(book_time, self.logger)

        # 4. Start the resilient loop from the train list page
        self._resilient_state_loop()

    def _resilient_state_loop(self):
        """The main state machine loop for handling booking steps."""
        self.logger.info("Entering resilient state-machine loop.")
        while not self.stop_event.is_set():
            try:
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
                    break # Exit loop on success
                else:
                    self.logger.warning("In UNKNOWN state, please check browser.")
                    time.sleep(5)
                time.sleep(1) # Small delay between state checks
            except Exception as e:
                self.logger.error(f"Error in state loop: {e}", exc_info=True)
                time.sleep(5) # Wait a bit after an error before retrying

    # --- Helper & Utility Methods ---
    def _update_status(self, new_status):
        self.status = new_status
        # Log to both the console logger and the Excel logger
        self.logger.info(f"Status: {self.status}")
        self.excel_logger.log(self.instance_id, new_status)

    def _wait(self, by, value, timeout=10):
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

    def _popup_killer_loop(self):
        """A daemon thread loop to continuously close popups."""
        self.logger.info("Popup killer thread started.")
        while not self.stop_event.is_set():
            try:
                # Use the user-provided selector for the Disha banner
                disha_close_button = self.driver.find_element(By.CSS_SELECTOR, "img#disha-banner-close")
                disha_close_button.click()
                self.logger.info("Closed Disha banner.")
            except:
                pass # Element not found, which is normal

            try:
                # Aadhar popup
                ok_button = self.driver.find_element(By.CSS_SELECTOR, "button.btn-primary[aria-label*='Aadhaar authenticated users']")
                ok_button.click()
                self.logger.info("Closed Aadhaar popup.")
            except:
                pass
            time.sleep(1) # Check every second
        self.logger.info("Popup killer thread stopped.")

    # --- Automation Step Methods ---
    def _perform_login(self):
        self._update_status("Performing Login")
        use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)

        self._wait(By.CSS_SELECTOR, selectors.LOGIN_BUTTON_HOME).click()
        self._wait(By.CSS_SELECTOR, selectors.USERNAME_INPUT).send_keys(self.account["username"])
        self._wait(By.CSS_SELECTOR, selectors.PASSWORD_INPUT).send_keys(self.account["password"])

        self.logger.info("Solving Captcha...")
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)
        if not solved_text: raise Exception("Captcha failed.")

        self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN).send_keys(solved_text)
        self._wait(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL).click()
        self._wait(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON) # Wait for logout button to appear to confirm login
        self.logger.info("Login Successful.")

    def _fill_journey_and_find_trains(self):
        self._update_status("Filling Journey Details")
        train_details = self.bot_config['train']

        # From Station
        from_input = self._wait(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT)
        from_input.send_keys(train_details['from_code'])
        self._wait(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION).click()

        # To Station
        to_input = self._wait(By.CSS_SELECTOR, selectors.JOURNEY_TO_INPUT)
        to_input.send_keys(train_details['to_code'])
        self._wait(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION).click()

        # Date
        date_input = self._wait(By.CSS_SELECTOR, selectors.DATE_INPUT)
        date_str_dmy = datetime.strptime(train_details['date'], '%d%m%Y').strftime('%d/%m/%Y')
        self.driver.execute_script(f"arguments[0].value = '{date_str_dmy}';", date_input)
        self.driver.find_element(By.CSS_SELECTOR, "body").click() # Click away to close calendar
        time.sleep(0.5)

        self._wait(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON).click()

    def _select_train_and_class(self):
        self._update_status("Selecting Train & Class")
        train_details = self.bot_config['train']

        # Select Quota
        quota_id = train_details['quota'].lower() # e.g., 'tatkal', 'general'
        self._wait(By.CSS_SELECTOR, f"p-radiobutton[id='{quota_id}']").click()
        time.sleep(1.5) # Wait for list to refresh

        # Extract class code from "AC 3 Tier (3A)" -> "3A"
        class_match = re.search(r'\((\S+)\)', train_details['class'])
        if not class_match: raise ValueError(f"Could not extract class code from '{train_details['class']}'")
        class_code = class_match.group(1)

        # Find the correct train and book
        for train_element in self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM):
            if train_details['train_no'] in train_element.text:
                self.logger.info(f"Found train {train_details['train_no']}. Selecting class {class_code}.")
                class_sel = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=class_code)
                train_element.find_element(By.CSS_SELECTOR, class_sel).click()
                time.sleep(0.5)
                train_element.find_element(By.CSS_SELECTOR, selectors.BOOK_NOW_BUTTON).click()
                return
        raise Exception(f"Train {train_details['train_no']} not found in the list.")

    def _fill_passenger_details(self):
        self._update_status("Filling Passenger Details")
        passengers = self.bot_config['passengers']
        contact_phone = self.bot_config['contact']['phone']

        for i, p in enumerate(passengers):
            if i > 0: # Click "Add Passenger" for subsequent passengers
                self._wait(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON).click()

            self._wait(By.CSS_SELECTOR, f"input[formcontrolname='passengerName'][id='psgn-name{i}']").send_keys(p['name'])
            self._wait(By.CSS_SELECTOR, f"input[formcontrolname='passengerAge'][id='psgn-age{i}']").send_keys(p['age'])

            # Gender
            self._wait(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerGender'][id='psgn-gender{i}']").click()
            gender_map = {"Male": "M", "Female": "F", "Transgender": "T"}
            self._wait(By.XPATH, f"//p-dropdownitem/li/span[contains(text(), '{gender_map.get(p['sex'])}')]").click()

            # Berth Preference
            if p.get('berth'):
                self._wait(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerBerthChoice'][id='psgn-berth-choice{i}']").click()
                self._wait(By.XPATH, selectors.BERTH_OPTION_XPATH.format(berth=p['berth'])).click()

        self._wait(By.CSS_SELECTOR, selectors.PASSENGER_MOBILE_INPUT).send_keys(contact_phone)
        self._wait(By.CSS_SELECTOR, selectors.SUBMIT_PASSENGER_DETAILS_BUTTON).click()

    def _handle_final_review(self):
        self._update_status("Final Review & Captcha")
        use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)

        self._update_status("Solving Final Review Captcha...")
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_REVIEW).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)
        if not solved_text: raise Exception("Review Captcha failed.")

        self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW).send_keys(solved_text)
        self._wait(By.CSS_SELECTOR, selectors.PROCEED_TO_PAY_BUTTON).click()

    def _perform_payment(self):
        self._update_status("Handling Payment")
        payment_method = self.bot_config['preferences']['payment']

        if payment_method == "Pay through BHIM UPI":
            upi_radio = self._wait(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH)
            self.driver.execute_script("arguments[0].click();", upi_radio)
            pay_button = self._wait(By.CSS_SELECTOR, selectors.PAY_AND_BOOK_BUTTON)
            self.driver.execute_script("arguments[0].click();", pay_button)
            self.logger.info("Payment initiated via UPI. Manual intervention required to complete.")
        else:
            self.logger.error(f"Payment method '{payment_method}' is not implemented.")
            raise NotImplementedError(f"Payment method '{payment_method}' is not supported.")
