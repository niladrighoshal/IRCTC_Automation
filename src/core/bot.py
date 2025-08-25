import time
import os
import re
import json
import random
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
    def __init__(self, bot_config, instance_id=0):
        self.bot_config = bot_config
        self.account = bot_config.get('account', {})
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.status = "INITIALIZED"
        self.stop_event = threading.Event()
        self.logger.info(f"Bot for user '{self.account.get('username', 'N/A')}' initialized.")

    # --- Core Methods ---
    def run(self):
        """Main entry point for the bot thread."""
        self._update_status("STARTING")
        popup_thread = None
        try:
            # Get preferences from the config dictionary
            prefs = self.bot_config.get("preferences", {})
            is_timed = prefs.get("timed", False)
            is_headless = prefs.get("headless", False)
            use_gpu = not prefs.get("ocr_cpu", True)

            # Create webdriver
            self.driver = create_webdriver(self.instance_id, is_headless=is_headless, use_gpu=use_gpu)
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
                    self.driver.save_screenshot(f"unknown_state_{self.instance_id}_{datetime.now().strftime('%H%M%S')}.png")
                    time.sleep(5)
                time.sleep(1) # Small delay between state checks
            except Exception as e:
                self.logger.error(f"Error in state loop: {e}", exc_info=True)
                time.sleep(5) # Wait a bit after an error before retrying

    # --- Helper & Utility Methods ---
    def _update_status(self, new_status):
        self.status = new_status
        self.logger.info(f"Status: {self.status}")
        try:
            # Write the latest status to a dedicated file for the UI to read
            status_file = os.path.join('logs', f'bot_{self.instance_id}_status.json')
            with open(status_file, 'w') as f:
                payload = {'timestamp': datetime.now().isoformat(), 'status': new_status}
                json.dump(payload, f)
        except Exception as e:
            self.logger.warning(f"Could not write status file: {e}")

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

    def _human_type(self, element, text: str):
        """Types a string into an element character by character with random delays."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def _popup_killer_loop(self):
        """A daemon thread loop to continuously close popups."""
        self.logger.info("Popup killer thread started.")
        while not self.stop_event.is_set():
            popups = [
                # Disha banner
                (By.CSS_SELECTOR, "img#disha-banner-close"),
                # Aadhar popup
                (By.CSS_SELECTOR, "button.btn-primary[aria-label*='Aadhaar authenticated users']"),
                # Generic cookie / consent buttons
                (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"),
                (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]"),
                (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]"),
            ]
            for by, selector in popups:
                try:
                    # Use find_elements to avoid exceptions when not found
                    elements = self.driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self.logger.info(f"Clicked a potential popup with selector: {selector}")
                            time.sleep(0.5) # Small pause after a click
                except Exception:
                    continue # Ignore errors and continue to the next popup type
            time.sleep(1) # Check every second
        self.logger.info("Popup killer thread stopped.")

    # --- Automation Step Methods ---
    def _perform_login(self):
        self._update_status("Navigating to Login Modal")

        # Resiliently click the main login button until the modal appears
        while not self.stop_event.is_set():
            try:
                # Wait for the button to be clickable, not just present
                login_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selectors.LOGIN_BUTTON_HOME))
                )
                login_button.click()
                # Check if the username field is now visible to confirm modal is open
                self._wait(By.CSS_SELECTOR, selectors.USERNAME_INPUT, timeout=2)
                self.logger.info("Login modal is open.")
                break
            except Exception as e:
                self.logger.warning(f"Could not open login modal, retrying... Error: {e}")
                time.sleep(1)

        # Fill username and password once before the loop
        try:
            user_input = self._wait(By.CSS_SELECTOR, selectors.USERNAME_INPUT, timeout=5)
            user_input.clear()
            self._human_type(user_input, self.account["username"])

            pass_input = self._wait(By.CSS_SELECTOR, selectors.PASSWORD_INPUT)
            pass_input.clear()
            self._human_type(pass_input, self.account["password"])
        except Exception as e:
            self.logger.error(f"Failed to fill username/password fields: {e}")
            raise # Re-raise exception as this is a fatal error for login

        # Loop up to 20 times to attempt login by only re-solving captcha
        for attempt in range(1, 21):
            if self.stop_event.is_set(): return

            self._update_status(f"Login Attempt {attempt}/20")
            try:
                # Solve and fill captcha
                use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)
                self._update_status(f"Attempt {attempt}: Solving Captcha...")
                captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN).get_attribute("src")
                solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)

                if not solved_text:
                    self.logger.warning(f"Attempt {attempt}: Captcha solving failed. Retrying.")
                    self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON).click()
                    time.sleep(1)
                    continue

                captcha_input = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN)
                self._human_type(captcha_input, solved_text)

                self._wait(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL).click()

                # Check for successful login by looking for the logout button
                self._wait(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON, timeout=5)
                self._update_status("Login Successful")
                self.logger.info("Login Successful.")
                return # Exit the method on success

            except Exception as e:
                self.logger.warning(f"Login attempt {attempt} failed: {e}. Retrying...")
                # Check if we are still in the modal, if not, break to outer state machine
                if not self._is_visible(By.CSS_SELECTOR, selectors.USERNAME_INPUT, timeout=1):
                    self.logger.error("No longer on login modal. Breaking login loop.")
                    break
                time.sleep(1)

        raise Exception("Failed to login after 20 attempts.")

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

        self._wait(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON).click()

    def _select_train_and_class(self):
        self._update_status("Selecting Train & Class")
        train_details = self.bot_config['train']

        # Select Quota
        quota_id = train_details['quota'].lower() # e.g., 'tatkal', 'general'
        self._wait(By.CSS_SELECTOR, f"p-radiobutton[id='{quota_id}']").click()

        # Extract class code from "AC 3 Tier (3A)" -> "3A"
        class_match = re.search(r'\((\S+)\)', train_details['class'])
        if not class_match: raise ValueError(f"Could not extract class code from '{train_details['class']}'")
        class_code = class_match.group(1)

        # Find the correct train and book
        for train_element in self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM):
            if train_details['train_no'] in train_element.text:
                self.logger.info(f"Found train {train_details['train_no']}. Selecting class {class_code}.")
                class_sel = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=class_code)
                # We need to wait for the train list to refresh after changing quota
                WebDriverWait(train_element, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, class_sel))).click()

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
