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
from src.utils.time_utils import wait_until, get_synchronized_target_time
from src.core.ocr_solver import solve_captcha
from src.core.state import BotState
import src.core.selectors as selectors

WARMUP_SITES = {
    "Neocities": "https://neocities.org", "Dillo Showcase": "https://dillo-browser.github.io", "W3C": "https://www.w3.org",
    "Example": "https://www.example.com", "IANA Reserved Domains": "https://www.iana.org/domains/reserved", "TextFiles": "https://www.textfiles.com",
    "Simple HTML Guide": "https://www.simplehtmlguide.com", "Lipsum": "https://www.lipsum.com", "HTML.com": "https://www.html.com",
    "Freesound": "https://www.freesound.org", "512KB Club": "https://512kb.club", "1MB Club": "https://1mb.club",
    "250KB Club": "https://250kb.club", "Motherfucking Website": "https://motherfuckingwebsite.com", "No-JS Club": "https://no-js.club",
    "Podd App": "https://podd.app", "Danluu": "https://danluu.com", "Piuvas": "https://piuvas.net", "Rojen": "https://rojen.uk",
    "Phreedom": "https://phreedom.club", "I Need More Coffee": "https://ineedmore.coffee", "0xff": "https://0xff.nu",
    "Avid Seeker": "https://avidseeker.github.io", "Osiux": "https://osiux.com", "Rectangles": "https://rectangles.app",
    "Daniel Cuttridge": "https://danielcuttridge.com", "Jackie Chalarca": "https://jackiechalarca.org", "Hybras": "https://hybras.dev",
    "Arkensys": "https://arkensys.dedyn.io", "Demidfr": "https://demidfr.com", "HTTP Guides": "https://httpguides.com",
    "Pantsu Fan": "https://pantsufan.github.io", "Tunes Heavy": "https://tunesheavy.com", "Saladhax": "https://saladhax.site",
    "Portable": "https://portable.fyi", "Tairesh": "https://tairesh.dev", "Sno.ws": "https://sno.ws", "How WTF": "https://how.wtf",
    "Jason Thai": "https://jasonthai.me", "B0ba": "https://b0ba.dev", "Logan Connolly": "https://loganconnolly.com",
    "Seirdy": "https://seirdy.one", "Chez Ice Man": "https://cheziceman.fr", "Imsky": "https://imsky.co",
    "Mathieu De Ruiter": "https://mathieuderuiter.nl", "Level News": "https://levelnews.org", "GTMetrix": "https://gtmetrix.com",
    "Cliffle": "https://cliffle.com", "JS Bin": "https://jsbin.com", "JSFiddle": "https://jsfiddle.net", "CodePen": "https://codepen.io",
    "CSS Desk": "https://cssdesk.com", "Liveweave": "https://liveweave.com", "Plunker": "https://plnkr.co",
    "PHP Fiddle": "https://phpfiddle.org", "W3Schools": "https://www.w3schools.com", "WebFiddle": "https://webfiddle.io",
    "JSFeed": "https://jsfeed.com", "LiveGap Editor": "https://livegap.com/editor", "ScratchPad": "https://scratchpad.io",
    "Runnable": "https://runnable.com", "jsdo.it": "https://jsdo.it", "snip2code": "https://snip2code.com"
}


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
        self.last_processed_state = None
        self.action_log = deque(maxlen=30)
        self.internal_state_data = {}

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
                if self._current_state.name.split('_')[0] != new_state.name.split('_')[0]:
                    self.internal_state_data = {}
                self._current_state = new_state
                self._log_action(f"State changed to: {new_state.name}", is_state_change=True)

    def run(self):
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
                return

            # self._warm_up_profile() # Disabling warming for speed test

            supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            supervisor_thread.start()
            worker_thread.start()

            self.driver.get("https://www.irctc.co.in/nget/train-search")
            self._log_action("Navigated to IRCTC website.")
            self.current_state = BotState.IDLE

            while not self.stop_event.is_set():
                if self.current_state in [BotState.BOOKING_CONFIRMED, BotState.FATAL_ERROR, BotState.STOPPED]:
                    break
                time.sleep(0.5) # Main loop sleep

        except Exception as e:
            self.logger.error(f"A fatal error occurred in the main run method: {e}", exc_info=True)
            self.current_state = BotState.FATAL_ERROR
        finally:
            self.logger.info("Bot run finishing. Signaling all threads to stop.")
            self.stop_event.set()
            if worker_thread: worker_thread.join(timeout=5)
            if supervisor_thread: supervisor_thread.join(timeout=5)
            if self.driver:
                self.logger.info("Closing browser in 5 seconds.")
                time.sleep(5)
                self.driver.quit()
            self.current_state = BotState.STOPPED

    def _supervisor_loop(self):
        self.logger.info("Supervisor thread started.")
        while not self.stop_event.is_set():
            try:
                if not self.driver:
                    time.sleep(0.1)
                    continue
                self._close_popups()
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
                elif self._is_visible(By.XPATH, selectors.LOGIN_BUTTON_HOME):
                    self.current_state = BotState.LOGGED_OUT
            except Exception as e:
                if not isinstance(e, (StaleElementReferenceException, NoSuchElementException, TimeoutException)):
                    self.logger.warning(f"Supervisor loop exception: {e}")
            time.sleep(0.1) # Faster supervisor loop
        self.logger.info("Supervisor thread stopped.")

    def _worker_loop(self):
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
            current_state = self.current_state
            if current_state != self.last_processed_state:
                handler = state_handlers.get(current_state)
                if handler:
                    try:
                        self.logger.info(f"Worker acting on new state: {current_state.name}")
                        handler()
                        self.last_processed_state = current_state
                    except Exception as e:
                        self.logger.error(f"Error in worker handling state {current_state.name}: {e}", exc_info=True)
                        self._log_action(f"ERROR in {current_state.name}: {e}", is_error=True)
                        self.last_processed_state = None
                        self.current_state = BotState.RECOVERING
                else:
                    self.last_processed_state = current_state
            time.sleep(0.05) # Blazing fast worker loop
        self.logger.info("Worker thread stopped.")

    def _warm_up_profile(self):
        self._log_action("Starting advanced profile warming routine.")
        try:
            original_window = self.driver.current_window_handle
            sites_to_visit = random.sample(list(WARMUP_SITES.values()), random.randint(5, 8))
            for i in range(len(sites_to_visit) - 1):
                try:
                    self.driver.execute_script("window.open('');")
                except Exception as e:
                    self._log_action(f"Warm-up: Could not open new tab {i+1}. Error: {e}", is_error=True)
            all_windows = self.driver.window_handles
            for i, window_handle in enumerate(all_windows):
                if i >= len(sites_to_visit): break
                try:
                    self.driver.switch_to.window(window_handle)
                    site = sites_to_visit[i]
                    self._log_action(f"Warming Tab {i+1}: Navigating to {site}")
                    self.driver.get(site)
                    time.sleep(random.uniform(1, 2)) # Shorter wait
                    self._close_popups()
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
                    time.sleep(random.uniform(0.2, 0.5))
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                except Exception as e:
                    self._log_action(f"Error warming tab {i+1} with site {site}: {e}", is_error=True)
            self._log_action("Closing extra warm-up tabs.")
            for window_handle in self.driver.window_handles:
                if window_handle != original_window:
                    try:
                        self.driver.switch_to.window(window_handle)
                        self.driver.close()
                    except Exception:
                        pass
            self.driver.switch_to.window(original_window)
            self._log_action("Profile warming complete.")
        except Exception as e:
            self._log_action(f"A critical error occurred during profile warming: {e}", is_error=True)
            self._log_action("Continuing with booking attempt despite warming failure.", is_error=True)

    def _handle_open_login_modal(self):
        self._click_with_retries(By.XPATH, selectors.LOGIN_BUTTON_HOME)

    def _handle_login_flow(self):
        self.current_state = BotState.LOGIN_ENTERING_CREDENTIALS
        def solve_captcha_in_background(result_container):
            try:
                captcha_img = self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_LOGIN, timeout=10)
                if captcha_img:
                    captcha_src = captcha_img.get_attribute("src")
                    use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)
                    result_container['solved_text'] = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)
            except Exception as e:
                self._log_action(f"Captcha solver thread failed: {e}", is_error=True)

        for attempt in range(1, 6):
            self._log_action(f"Login attempt {attempt}/5")
            captcha_result = {'solved_text': None}
            captcha_thread = threading.Thread(target=solve_captcha_in_background, args=(captcha_result,))
            captcha_thread.start()
            self._human_type(By.CSS_SELECTOR, selectors.USERNAME_INPUT, self.account["username"])
            self._human_type(By.CSS_SELECTOR, selectors.PASSWORD_INPUT, self.account["password"])
            self._log_action("Waiting for captcha result...")
            captcha_thread.join(timeout=20)
            solved_text = captcha_result.get('solved_text')
            if not solved_text:
                self._log_action("Captcha solving failed or timed out. Retrying.", is_error=True)
                self._click_with_retries(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON, timeout=5)
                continue
            self._human_type(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN, solved_text)
            self._click_with_retries(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL)
            time.sleep(1) # Reduced wait
            if self._is_visible(By.CSS_SELECTOR, selectors.LOGOUT_BUTTON):
                self.current_state = BotState.LOGIN_SUCCESSFUL
                self._log_action("Login successful!")
                return
            else:
                self._log_action(f"Login attempt {attempt} failed. Checking for error message.")
                if self._is_visible(By.XPATH, "//div[contains(text(), 'Invalid Captcha')]"):
                     self._log_action("Reason: Invalid Captcha.")
                self._click_with_retries(By.CSS_SELECTOR, selectors.CAPTCHA_REFRESH_BUTTON, timeout=5)
        self._log_action("All login attempts failed.", is_error=True)
        self.current_state = BotState.LOGIN_FAILED

    def _handle_dashboard_flow(self):
        self.current_state = BotState.FILLING_JOURNEY_DETAILS
        train_details = self.bot_config['train']
        self._human_type(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT, train_details['from_code'])
        self._click_with_retries(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION)
        self._human_type(By.CSS_SELECTOR, selectors.JOURNEY_TO_INPUT, train_details['to_code'])
        self._click_with_retries(By.CSS_SELECTOR, selectors.AUTOCOMPLETE_OPTION)
        date_input = self._wait_for_element(By.CSS_SELECTOR, selectors.DATE_INPUT)
        if not date_input: raise Exception("Date input not found")
        date_str_dmy = datetime.strptime(train_details['date'], '%d%m%Y').strftime('%d/%m/%Y')
        self.driver.execute_script(f"arguments[0].value = '{date_str_dmy}';", date_input)
        self.current_state = BotState.SUBMITTING_JOURNEY
        self._click_with_retries(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON)

    def _handle_train_selection_flow(self):
        train_details = self.bot_config['train']
        self.current_state = BotState.SELECTING_QUOTA
        self._click_with_retries(By.CSS_SELECTOR, f"p-radiobutton[id='{train_details['quota'].lower()}']")
        # Removed sleep, relying on explicit waits
        self.current_state = BotState.SELECTING_CLASS
        class_match = re.search(r'\((\S+)\)', train_details['class'])
        class_code = class_match.group(1)
        train_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM)
        if not train_elements: raise Exception("Train list is not visible.")
        for train_element in train_elements:
            if train_details['train_no'] in train_element.text:
                class_sel = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=class_code)
                self._click_with_retries(By.CSS_SELECTOR, class_sel, context=train_element)
                self.current_state = BotState.CLICKING_BOOK_NOW
                self._click_with_retries(By.CSS_SELECTOR, selectors.BOOK_NOW_BUTTON, context=train_element)
                return
        raise Exception(f"Train {train_details['train_no']} not found.")

    def _handle_passenger_details_flow(self):
        self.current_state = BotState.FILLING_PASSENGER_DETAILS
        passengers = self.bot_config['passengers']
        for i, p in enumerate(passengers):
            if i > 0: self._click_with_retries(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON)
            self._log_action(f"Filling details for passenger {i+1}: {p['name']}")
            self._human_type(By.CSS_SELECTOR, f"input[formcontrolname='passengerName'][id='psgn-name{i}']", p['name'])
            self._human_type(By.CSS_SELECTOR, f"input[formcontrolname='passengerAge'][id='psgn-age{i}']", p['age'])
            self._click_with_retries(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerGender'][id='psgn-gender{i}']")
            gender_map = {"Male": "M", "Female": "F", "Transgender": "T"}
            self._click_with_retries(By.XPATH, f"//p-dropdownitem/li/span[contains(text(), '{gender_map.get(p['sex'])}')]")
            if p.get('berth'):
                self._click_with_retries(By.CSS_SELECTOR, f"p-dropdown[formcontrolname='passengerBerthChoice'][id='psgn-berth-choice{i}']")
                self._click_with_retries(By.XPATH, selectors.BERTH_OPTION_XPATH.format(berth=p['berth']))
        self._human_type(By.CSS_SELECTOR, selectors.PASSENGER_MOBILE_INPUT, self.bot_config['contact']['phone'])
        self.current_state = BotState.SUBMITTING_PASSENGERS
        self._click_with_retries(By.CSS_SELECTOR, selectors.SUBMIT_PASSENGER_DETAILS_BUTTON)

    def _handle_review_flow(self):
        self.current_state = BotState.REVIEW_SOLVING_CAPTCHA
        use_gpu = not self.bot_config["preferences"].get("ocr_cpu", True)
        captcha_img = self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_IMAGE_REVIEW, timeout=5)
        if not captcha_img: raise Exception("Review Captcha image not found.")
        captcha_src = captcha_img.get_attribute("src")
        solved_text = solve_captcha(captcha_src, use_gpu=use_gpu, logger=self.logger)
        if not solved_text: raise Exception("Review Captcha failed.")
        self._human_type(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW, solved_text)
        self.current_state = BotState.PROCEEDING_TO_PAYMENT
        self._click_with_retries(By.CSS_SELECTOR, selectors.PROCEED_TO_PAY_BUTTON)

    def _handle_payment_flow(self):
        self.current_state = BotState.SELECTING_PAYMENT_METHOD
        payment_method = self.bot_config['preferences']['payment']
        if payment_method == "Pay through BHIM UPI":
            upi_radio = self._wait_for_element(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH, timeout=10)
            if not upi_radio: raise Exception("UPI Payment option not found")
            self.driver.execute_script("arguments[0].click();", upi_radio)
            self.current_state = BotState.INITIATING_PAYMENT
            pay_button = self._wait_for_element(By.CSS_SELECTOR, selectors.PAY_AND_BOOK_BUTTON, timeout=10)
            if not pay_button: raise Exception("Pay and Book button not found")
            self.driver.execute_script("arguments[0].click();", pay_button)
            self.current_state = BotState.WAITING_FOR_UPI_MANDATE
        else:
            raise NotImplementedError(f"Payment method '{payment_method}' is not supported.")

    def _handle_wait_for_payment(self):
        self._log_action("Waiting for UPI mandate approval from user's phone (60s).")
        for _ in range(12): # Check every 5s for 60s
            if self._is_visible(By.XPATH, "//*[contains(text(), 'PNR')]"):
                 self.current_state = BotState.BOOKING_CONFIRMED
                 self._log_action("SUCCESS: PNR confirmation detected!", is_state_change=True)
                 return
            time.sleep(5)
        self.current_state = BotState.BOOKING_FAILED
        self._log_action("FAILURE: Did not detect PNR confirmation page in time.", is_error=True)

    def _log_action(self, message, is_state_change=False, is_error=False):
        log_entry = { 'timestamp': datetime.now().isoformat(), 'message': message, 'is_state_change': is_state_change, 'is_error': is_error, 'state': self._current_state.name if self._current_state else "None" }
        self.action_log.append(log_entry)
        if is_error: self.logger.error(message)
        else: self.logger.info(message)
        try:
            status_file = os.path.join('logs', f'bot_{self.instance_id}_status.json')
            with open(status_file, 'w') as f:
                json.dump(list(self.action_log), f)
        except Exception as e:
            self.logger.warning(f"Could not write status file: {e}")

    def _wait_for_element(self, by, value, timeout=10, condition=EC.presence_of_element_located):
        self._log_action(f"Waiting for element ({condition.__name__}): {value}")
        try:
            element = WebDriverWait(self.driver, timeout).until(condition((by, value)))
            self._log_action(f"Found element: {value}")
            return element
        except TimeoutException:
            self._log_action(f"TIMEOUT waiting for element: {value}", is_error=True)
            return None

    def _click_with_retries(self, by, value, timeout=300, context=None):
        self._log_action(f"Attempting to click: {value}")
        search_context = context or self.driver
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(lambda d: search_context.find_element(by, value))
            ActionChains(self.driver).move_to_element(element).perform()
            self._log_action(f"Moved mouse to: {value}")
            time.sleep(0.05) # Minimal pause
            clickable_element = wait.until(EC.element_to_be_clickable((by, value)))
            clickable_element.click()
            self._log_action(f"Successfully clicked: {value}")
            return True
        except Exception as e:
            self._log_action(f"Click failed for {value}. Error: {e}", is_error=True)
            try:
                self._log_action("Attempting JS click fallback...")
                element = self.driver.find_element(by, value)
                self.driver.execute_script("arguments[0].click();", element)
                self._log_action(f"Successfully clicked via JS: {value}")
                return True
            except Exception as js_e:
                self._log_action(f"JS click also failed for {value}. Error: {js_e}", is_error=True)
                return False

    def _is_visible(self, by, value, timeout=0.1):
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, value)))
            return True
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            return False

    def _human_type(self, by, value, text: str):
        self._log_action(f"Typing '{text[:15]}...' into {value}")
        element = self._wait_for_element(by, value, timeout=10)
        if not element:
            raise TimeoutException(f"Could not find element {value} to type into after 10 seconds.")
        ActionChains(self.driver).move_to_element(element).pause(0.1).click().perform()
        element.clear()
        for char in text:
            element.send_keys(char)
            # User requested paste-like speed. This is the absolute minimum delay.
            time.sleep(random.uniform(0.005, 0.01))
        self._log_action(f"Finished typing.")

    def _close_popups(self):
        popups = [ (By.CSS_SELECTOR, "button.btn-primary[aria-label*='Aadhaar authenticated users']"), ]
        for by, selector in popups:
            try:
                elements = self.driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        self._log_action(f"Closing popup: {selector}")
                        element.click()
            except StaleElementReferenceException:
                continue
            except Exception:
                continue
