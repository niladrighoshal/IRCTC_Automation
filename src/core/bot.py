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
from selenium.webdriver.common.action_chains import ActionChains

from src.core.webdriver_factory import create_webdriver
from src.utils.logger import setup_logger
from src.utils.time_utils import wait_until
from src.core.ocr_solver import solve_captcha
from src.core.state import BotState
import src.core.selectors as selectors

class IRCTCBot:
    """
    An intelligent, state-driven bot for booking tickets on IRCTC,
    built on a resilient Supervisor/Worker model.
    """
    def __init__(self, bot_config, instance_id=0):
        self.bot_config = bot_config
        self.account = bot_config.get('account', {})
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.stop_event = threading.Event()
        self.state_lock = threading.Lock()
        self._current_state = BotState.INITIALIZED
        self.last_processed_state = None
        self.action_log = deque(maxlen=30)
        self._log_action(f"Bot initialized for user: {self.account.get('username')}")

    @property
    def current_state(self):
        with self.state_lock:
            return self._current_state

    @current_state.setter
    def current_state(self, new_state):
        with self.state_lock:
            if self._current_state != new_state:
                self._current_state = new_state
                self._log_action(f"State changed to: {new_state.name}", is_state_change=True)

    def run(self):
        self.current_state = BotState.STARTING
        try:
            prefs = self.bot_config.get("preferences", {})
            self.driver = create_webdriver(self.instance_id, is_headless=prefs.get("headless", False))
            if not self.driver:
                self.current_state = BotState.FATAL_ERROR
                return

            # The Supervisor thread is the only place that changes the bot's state
            supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            # The Worker thread only reads the state and acts
            worker_thread = threading.Thread(target=self._worker_loop, daemon=True)

            supervisor_thread.start()
            worker_thread.start()

            self.driver.get("https://www.irctc.co.in/nget/train-search")
            # The supervisor will take over from here to set the first real state

            while not self.stop_event.is_set():
                if self.current_state in [BotState.BOOKING_CONFIRMED, BotState.FATAL_ERROR, BotState.STOPPED]:
                    break
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"A fatal error occurred: {e}", exc_info=True)
            self.current_state = BotState.FATAL_ERROR
        finally:
            self.stop()

    def stop(self):
        self._log_action("Stopping bot...")
        self.stop_event.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception: pass
        self.current_state = BotState.STOPPED

    def _supervisor_loop(self):
        while not self.stop_event.is_set():
            try:
                if not self.driver: time.sleep(0.1); continue
                self._close_popups()
                # Determine state by checking for unique elements on each page
                if self._is_visible(By.CSS_SELECTOR, selectors.USERNAME_INPUT):
                    self.current_state = BotState.LOGIN_STARTED
                elif self._is_visible(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON):
                    self.current_state = BotState.AT_DASHBOARD
                elif self._is_visible(By.XPATH, selectors.LOGIN_BUTTON_HOME):
                    self.current_state = BotState.LOGGED_OUT
                # Add other page checks here in future
            except Exception as e:
                if not isinstance(e, (StaleElementReferenceException, NoSuchElementException, TimeoutException)):
                    self.logger.warning(f"Supervisor loop exception: {e}")
            time.sleep(0.2)

    def _worker_loop(self):
        state_handlers = {
            BotState.LOGGED_OUT: self._handle_open_login_modal,
            BotState.LOGIN_STARTED: self._handle_login_flow,
            # Add other state handlers here
        }
        while not self.stop_event.is_set():
            state = self.current_state
            if state != self.last_processed_state:
                handler = state_handlers.get(state)
                if handler:
                    try:
                        self._log_action(f"Worker acting on new state: {state.name}")
                        handler()
                        self.last_processed_state = state
                    except Exception as e:
                        self._log_action(f"ERROR in {state.name}: {e}", is_error=True)
                        self.last_processed_state = None
                        self.current_state = BotState.RECOVERING
                else:
                    self.last_processed_state = state
            time.sleep(0.1)

    def _log_action(self, message, is_state_change=False, is_error=False):
        log_entry = { 'timestamp': datetime.now().isoformat(), 'message': message, 'is_state_change': is_state_change, 'is_error': is_error, 'state': self.current_state.name }
        self.action_log.append(log_entry)
        if is_error: self.logger.error(message)
        else: self.logger.info(message)
        try:
            with open(os.path.join('logs', f'bot_{self.instance_id}_status.json'), 'w') as f:
                json.dump(list(self.action_log), f)
        except Exception as e:
            self.logger.warning(f"Could not write status file: {e}")

    def _wait_for_element(self, by, value, timeout=10, condition=EC.element_to_be_clickable):
        try:
            return WebDriverWait(self.driver, timeout).until(condition((by, value)))
        except TimeoutException:
            self._log_action(f"TIMEOUT waiting for element: {value}", is_error=True)
            return None

    def _click_with_retries(self, by, value, timeout=20):
        self._log_action(f"Attempting to click: {value}")
        try:
            element = self._wait_for_element(by, value, timeout=timeout)
            if not element: return False
            ActionChains(self.driver).move_to_element(element).pause(0.1).click().perform()
            self._log_action(f"Successfully clicked: {value}")
            return True
        except Exception as e:
            self._log_action(f"Click failed for {value}. Trying JS click. Error: {e}", is_error=True)
            try:
                element = self._wait_for_element(by, value, timeout=1, condition=EC.presence_of_element_located)
                if element: self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_e:
                self._log_action(f"JS click also failed for {value}. Error: {js_e}", is_error=True)
                return False

    def _human_type(self, by, value, text: str):
        element = self._wait_for_element(by, value, timeout=10)
        if not element: raise TimeoutException(f"Could not find element {value} to type into.")
        ActionChains(self.driver).move_to_element(element).pause(0.1).click().perform()
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.005, 0.01))

    def _is_visible(self, by, value, timeout=0.1):
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return True
        except Exception: return False

    def _close_popups(self):
        popups = [(By.CSS_SELECTOR, "button.btn-primary[aria-label*='Aadhaar authenticated users']")]
        for by, selector in popups:
            try:
                elements = self.driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        element.click()
                        self._log_action(f"Closed popup: {selector}")
            except Exception: continue

    def _handle_open_login_modal(self):
        self._click_with_retries(By.XPATH, selectors.LOGIN_BUTTON_HOME)

    def _handle_login_flow(self):
        def solve_captcha_in_background(result_container):
            try:
                captcha_img = self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN, 10, EC.presence_of_element_located)
                if captcha_img:
                    result_container['solved_text'] = solve_captcha(captcha_img.get_attribute("src"), logger=self.logger)
            except Exception as e:
                self._log_action(f"Captcha solver thread failed: {e}", is_error=True)

        for attempt in range(1, 6):
            self._log_action(f"Login attempt {attempt}/5")
            captcha_result = {'solved_text': None}
            captcha_thread = threading.Thread(target=solve_captcha_in_background, args=(captcha_result,))
            captcha_thread.start()
            self._human_type(By.CSS_SELECTOR, selectors.USERNAME_INPUT, self.account["username"])
            self._human_type(By.CSS_SELECTOR, selectors.PASSWORD_INPUT, self.account["password"])
            captcha_thread.join(timeout=20)
            solved_text = captcha_result.get('solved_text')
            if not solved_text:
                self._log_action("Captcha solving failed. Retrying.", is_error=True)
                self._click_with_retries(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON, timeout=5)
                continue
            self._human_type(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN, solved_text)
            self._click_with_retries(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL)
            if self._wait_for_element(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON, timeout=2, condition=EC.visibility_of_element_located):
                self._log_action("Login successful!")
                return
            error_element = self._wait_for_element(By.XPATH, "//div[contains(@class, 'loginError')]", 1, EC.visibility_of_element_located)
            if error_element: self._log_action(f"Login failed: {error_element.text}", is_error=True)
            self._click_with_retries(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON, timeout=5)
        self._log_action("All login attempts failed.", is_error=True)
        self.current_state = BotState.LOGIN_FAILED
        # In a real scenario, you'd add handlers for these states
    def _handle_dashboard_flow(self): self._log_action("TODO: Implement dashboard handling"); time.sleep(5)
    def _handle_train_selection_flow(self): self._log_action("TODO: Implement train selection"); time.sleep(5)
    def _handle_passenger_details_flow(self): self._log_action("TODO: Implement passenger details"); time.sleep(5)
    def _handle_review_flow(self): self._log_action("TODO: Implement review handling"); time.sleep(5)
    def _handle_payment_flow(self): self._log_action("TODO: Implement payment"); time.sleep(5)
    def _handle_wait_for_payment(self): self._log_action("TODO: Implement payment wait"); time.sleep(5)
