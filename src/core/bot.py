import time
import os
import re
import json
import random
import threading
from datetime import datetime
from collections import deque

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException

from src.core.webdriver_factory import create_webdriver
from src.utils.logger import setup_logger
from src.utils.time_utils import wait_until, get_synchronized_target_time
from src.core.ocr_solver import solve_captcha
from src.core.state import BotState
import src.core.selectors as selectors

class IRCTCBot:
    """
    An intelligent, state-driven bot for booking tickets on IRCTC.
    This class uses a Supervisor/Worker model to separate observation from action,
    making it more resilient to unexpected UI changes and errors.
    """
    def __init__(self, bot_config, instance_id=0):
        self.bot_config = bot_config
        self.account = bot_config.get('account', {})
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.stop_event = threading.Event()

        # State management
        self.state_lock = threading.Lock()
        self._current_state = BotState.INITIALIZED
        self.action_log = deque(maxlen=30) # For UI display
        self.internal_state_data = {} # For multi-step operations like login

        self.logger.info(f"Bot for user '{self.account.get('username', 'N/A')}' initialized.")
        self._log_action(f"Bot initialized for user: {self.account.get('username')}")

    @property
    def current_state(self):
        with self.state_lock:
            return self._current_state

    @current_state.setter
    def current_state(self, new_state):
        with self.state_lock:
            if self._current_state != new_state:
                # Reset internal state data when a major state transition occurs
                if self._current_state.name.split('_')[0] != new_state.name.split('_')[0]:
                    self.internal_state_data = {}
                self._current_state = new_state
                self._log_action(f"State changed to: {new_state.name}", is_state_change=True)

    # --- Main Execution Flow ---
    def run(self):
        """Main entry point. Sets up threads and starts the state machine."""
        self.current_state = BotState.STARTING

        supervisor_thread = None
        worker_thread = None

        try:
            prefs = self.bot_config.get("preferences", {})
            self.driver = create_webdriver(
                self.instance_id,
                is_headless=prefs.get("headless", False),
                use_gpu=not prefs.get("ocr_cpu", True)
            )
            if not self.driver:
                self.current_state = BotState.FATAL_ERROR
                self._log_action("FATAL: WebDriver creation failed", is_error=True)
                return

            supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            worker_thread = threading.Thread(target=self._worker_loop, daemon=True)

            supervisor_thread.start()
            worker_thread.start()

            self.driver.get("https://www.irctc.co.in/nget/train-search")
            self.current_state = BotState.IDLE

            while not self.stop_event.is_set():
                if self.current_state in [BotState.BOOKING_CONFIRMED, BotState.FATAL_ERROR, BotState.STOPPED]:
                    break
                time.sleep(1)

        except Exception as e:
            self.logger.error(f"A fatal error occurred in the main run method: {e}", exc_info=True)
            self.current_state = BotState.FATAL_ERROR
        finally:
            self.logger.info("Bot run finishing. Signaling all threads to stop.")
            self.stop_event.set()

            if worker_thread: worker_thread.join(timeout=5)
            if supervisor_thread: supervisor_thread.join(timeout=5)

            if self.driver:
                self.logger.info("Closing browser in 10 seconds.")
                time.sleep(10)
                self.driver.quit()

            self.current_state = BotState.STOPPED

    # --- Supervisor/Worker Threads ---
    def _supervisor_loop(self):
        """
        Observes the browser, closes popups, and updates the bot's state.
        """
        self.logger.info("Supervisor thread started.")
        while not self.stop_event.is_set():
            try:
                if self.driver:
                    # Task 1: Close any popups
                    self._close_popups()

                    # Task 2: Determine current state
                    if self._is_visible(By.CSS_SELECTOR, selectors.USERNAME_INPUT):
                        if self.current_state != BotState.LOGIN_SUCCESSFUL:
                           self.current_state = BotState.LOGIN_STARTED
                    elif self._is_visible(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH):
                        self.current_state = BotState.PAYMENT_PAGE
                    elif self._is_visible(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW):
                        self.current_state = BotState.REVIEW_PAGE
                    elif self._is_visible(By.CSS_SELECTOR, selectors.PASSENGER_NAME_INPUT):
                        self.current_state = BotState.PASSENGER_DETAILS_PAGE
                    elif self._is_visible(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM):
                        self.current_state = BotState.TRAIN_LIST_PAGE
                    elif self._is_visible(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON):
                        self.current_state = BotState.AT_DASHBOARD
                    elif self._is_visible(By.CSS_SELECTOR, selectors.LOGIN_BUTTON_HOME):
                        self.current_state = BotState.LOGGED_OUT
            except Exception as e:
                if not isinstance(e, (StaleElementReferenceException, NoSuchElementException)):
                    self.logger.warning(f"Supervisor loop exception: {e}")
            time.sleep(0.5) # Loop twice a second
        self.logger.info("Supervisor thread stopped.")

    def _worker_loop(self):
        """Executes actions based on the current state."""
        self.logger.info("Worker thread started.")

        state_handlers = {
            BotState.LOGGED_OUT: self._handle_open_login_modal,
            BotState.LOGIN_STARTED: self._handle_login_flow,
            BotState.AT_DASHBOARD: self._handle_dashboard_flow,
            BotState.TRAIN_LIST_PAGE: self._handle_train_selection_flow,
            BotState.PASSENGER_DETAILS_PAGE: self._handle_passenger_details_flow,
            BotState.REVIEW_PAGE: self._handle_review_flow,
            BotState.PAYMENT_PAGE: self._handle_payment_flow,
            BotState.WAITING_FOR_UPI_MANDATE: self._handle_wait_for_payment,
        }

        while not self.stop_event.is_set():
            state = self.current_state
            # Worker should not act if supervisor is still figuring things out
            if state in [BotState.INITIALIZED, BotState.STARTING, BotState.IDLE]:
                time.sleep(1)
                continue

            handler = state_handlers.get(state)

            if handler:
                try:
                    handler()
                except Exception as e:
                    self.logger.error(f"Error in worker handling state {state.name}: {e}", exc_info=True)
                    self._log_action(f"ERROR in {state.name}: {e}", is_error=True)
                    self.current_state = BotState.RECOVERING
                    time.sleep(3)

            time.sleep(0.5)
        self.logger.info("Worker thread stopped.")

    # --- Granular State Handlers ---
    def _handle_open_login_modal(self):
        self._click(By.XPATH, selectors.LOGIN_BUTTON_HOME)

    def _handle_login_flow(self):
        if not self.internal_state_data.get('creds_entered'):
            self.current_state = BotState.LOGIN_ENTERING_CREDENTIALS
            self._human_type(self._wait(By.CSS_SELECTOR, selectors.USERNAME_INPUT), self.account["username"])
            self._human_type(self._wait(By.CSS_SELECTOR, selectors.PASSWORD_INPUT), self.account["password"])
            self.internal_state_data['creds_entered'] = True
            self.internal_state_data['login_attempts'] = 0

        attempt = self.internal_state_data.get('login_attempts', 0)
        if attempt >= 5:
            self.current_state = BotState.LOGIN_FAILED
            self._log_action("Login failed after 5 attempts.", is_error=True)
            self.driver.refresh()
            return

        self.current_state = BotState.LOGIN_SOLVING_CAPTCHA
        use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)

        if not solved_text:
            self._log_action("Captcha solve failed, refreshing captcha.")
            self._click(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON)
            self.internal_state_data['login_attempts'] += 1
            return

        self._human_type(self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN), solved_text)

        self.current_state = BotState.LOGIN_SUBMITTING
        self._click(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL)

        time.sleep(2)
        if self.current_state != BotState.AT_DASHBOARD:
             self.internal_state_data['login_attempts'] += 1
             self._log_action(f"Login attempt {attempt + 1} may have failed. Retrying captcha.")
        else:
             self.current_state = BotState.LOGIN_SUCCESSFUL

    def _handle_dashboard_flow(self):
        self.current_state = BotState.FILLING_JOURNEY_DETAILS
        train_details = self.bot_config['train']
        self._human_type(self._wait(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT), train_details['from_code'])
        self._click(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION)
        self._human_type(self._wait(By.CSS_SELECTOR, selectors.JOURNEY_TO_INPUT), train_details['to_code'])
        self._click(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION)
        date_input = self._wait(By.CSS_SELECTOR, selectors.DATE_INPUT)
        date_str_dmy = datetime.strptime(train_details['date'], '%d%m%Y').strftime('%d/%m/%Y')
        self.driver.execute_script(f"arguments[0].value = '{date_str_dmy}';", date_input)
        self._click(By.CSS_SELECTOR, "body")
        self.current_state = BotState.SUBMITTING_JOURNEY
        self._click(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON)

    def _handle_train_selection_flow(self):
        train_details = self.bot_config['train']

        self.current_state = BotState.SELECTING_QUOTA
        quota_id = train_details['quota'].lower()
        self._click(By.CSS_SELECTOR, f"p-radiobutton[id='{quota_id}']")
        time.sleep(1)

        self.current_state = BotState.SELECTING_CLASS
        class_match = re.search(r'\((\S+)\)', train_details['class'])
        class_code = class_match.group(1)

        for train_element in self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM):
            if train_details['train_no'] in train_element.text:
                class_sel = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=class_code)
                class_button = WebDriverWait(train_element, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, class_sel)))
                class_button.click()

                self.current_state = BotState.CLICKING_BOOK_NOW
                book_now_button = train_element.find_element(By.CSS_SELECTOR, selectors.BOOK_NOW_BUTTON)
                book_now_button.click()
                return
        raise Exception(f"Train {train_details['train_no']} not found.")

    def _handle_passenger_details_flow(self):
        self.current_state = BotState.FILLING_PASSENGER_DETAILS
        passengers = self.bot_config['passengers']
        for i, p in enumerate(passengers):
            if i > 0: self._click(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON)
            self._log_action(f"Filling details for passenger {i+1}: {p['name']}")
            self._human_type(self._wait(By.CSS_SELECTOR, f"input[formcontrolname='passengerName'][id='psgn-name{i}']"), p['name'])
            self._human_type(self._wait(By.CSS_SELECTOR, f"input[formcontrolname='passengerAge'][id='psgn-age{i}']"), p['age'])
            self._click(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerGender'][id='psgn-gender{i}']")
            gender_map = {"Male": "M", "Female": "F", "Transgender": "T"}
            self._click(By.XPATH, f"//p-dropdownitem/li/span[contains(text(), '{gender_map.get(p['sex'])}')]")
            if p.get('berth'):
                self._click(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerBerthChoice'][id='psgn-berth-choice{i}']")
                self._click(By.XPATH, selectors.BERTH_OPTION_XPATH.format(berth=p['berth']))

        self._human_type(self._wait(By.CSS_SELECTOR, selectors.PASSENGER_MOBILE_INPUT), self.bot_config['contact']['phone'])
        self.current_state = BotState.SUBMITTING_PASSENGERS
        self._click(By.CSS_SELECTOR, selectors.SUBMIT_PASSENGER_DETAILS_BUTTON)

    def _handle_review_flow(self):
        self.current_state = BotState.REVIEW_SOLVING_CAPTCHA
        use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)
        captcha_src = self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_REVIEW).get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)
        if not solved_text: raise Exception("Review Captcha failed.")
        self._human_type(self._wait(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW), solved_text)
        self.current_state = BotState.PROCEEDING_TO_PAYMENT
        self._click(By.CSS_SELECTOR, selectors.PROCEED_TO_PAY_BUTTON)

    def _handle_payment_flow(self):
        self.current_state = BotState.SELECTING_PAYMENT_METHOD
        payment_method = self.bot_config['preferences']['payment']
        if payment_method == "Pay through BHIM UPI":
            upi_radio = self._wait(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH)
            self.driver.execute_script("arguments[0].click();", upi_radio)
            self.current_state = BotState.INITIATING_PAYMENT
            pay_button = self._wait(By.CSS_SELECTOR, selectors.PAY_AND_BOOK_BUTTON)
            self.driver.execute_script("arguments[0].click();", pay_button)
            self.current_state = BotState.WAITING_FOR_UPI_MANDATE
        else:
            raise NotImplementedError(f"Payment method '{payment_method}' is not supported.")

    def _handle_wait_for_payment(self):
        self._log_action("Waiting for UPI mandate approval from user's phone (120s).")
        for _ in range(24):
            if self._is_visible(By.XPATH, "//*[contains(text(), 'PNR')]"):
                 self.current_state = BotState.BOOKING_CONFIRMED
                 self._log_action("SUCCESS: PNR confirmation detected!", is_state_change=True)
                 return
            time.sleep(5)
        self.current_state = BotState.BOOKING_FAILED
        self._log_action("FAILURE: Did not detect PNR confirmation page in time.", is_error=True)

    # --- Helper & Utility Methods ---
    def _log_action(self, message, is_state_change=False, is_error=False):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'is_state_change': is_state_change,
            'is_error': is_error,
            'state': self._current_state.name if self._current_state else "None"
        }
        self.action_log.append(log_entry)
        if is_error: self.logger.error(message)
        else: self.logger.info(message)

        try:
            status_file = os.path.join('logs', f'bot_{self.instance_id}_status.json')
            with open(status_file, 'w') as f:
                json.dump(list(self.action_log), f)
        except Exception as e:
            self.logger.warning(f"Could not write status file: {e}")

    def _wait(self, by, value, timeout=10):
        self._log_action(f"Waiting for: {value}")
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))
            self._log_action(f"Found: {value}")
            return element
        except TimeoutException:
            self._log_action(f"TIMEOUT: Element not found {value}", is_error=True)
            raise

    def _click(self, by, value):
        self._log_action(f"Clicking: {value}")
        element = self._wait(by, value)
        try:
            element.click()
            self._log_action(f"Clicked: {value}")
        except Exception:
            self._log_action(f"Click failed, trying JS click: {value}", is_error=True)
            self.driver.execute_script("arguments[0].click();", element)

    def _is_visible(self, by, value, timeout=0.1):
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return True
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            return False

    def _human_type(self, element, text: str):
        self._log_action(f"Typing '{text[:15]}...'")
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.12))
        self._log_action(f"Finished typing.")

    def _close_popups(self):
        """Finds and closes known popups. Called by the supervisor."""
        popups = [
            (By.CSS_SELECTOR, "img#disha-banner-close"),
            (By.CSS_SELECTOR, "button.btn-primary[aria-label*='Aadhaar authenticated users']"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]"),
        ]
        for by, selector in popups:
            try:
                elements = self.driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        self._log_action(f"Closing popup: {selector}")
                        element.click()
            except Exception:
                continue
