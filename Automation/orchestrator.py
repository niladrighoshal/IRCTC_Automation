import json
import time
import threading
from pathlib import Path
from datetime import datetime
from enum import Enum, auto

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Automation.ocr import CaptchaSolver
from Automation.tasks.login_task import LoginTask
from Automation.tasks.search_task import SearchTask
from Automation.tasks.passenger_task import PassengerTask
from Automation.tasks.payment_task import PaymentTask

class AppState(Enum):
    INITIALIZING = auto()
    LOGGED_OUT = auto()
    LOGGED_IN_HOME = auto()
    TRAIN_LIST_VISIBLE = auto()
    PASSENGER_DETAILS_PAGE = auto()
    PAYMENT_REVIEW_PAGE = auto()
    BOOKING_SUCCESSFUL = auto()
    UNKNOWN_ERROR = auto()

class BotOrchestrator:
    PAGE_LOAD_TIMEOUT = 300

    def __init__(self, automation_folder, gui=None, use_gpu=False):
        self.automation_folder = Path(automation_folder)
        self.gui = gui
        self.driver = None
        self._stop_event = threading.Event()
        self.use_gpu = use_gpu
        self.ocr = CaptchaSolver(use_gpu=self.use_gpu) if CaptchaSolver else None
        self.login_task = LoginTask(self)
        self.search_task = SearchTask(self)
        self.passenger_task = PassengerTask(self)
        self.payment_task = PaymentTask(self)

    def get_current_state(self):
        try:
            url = self.driver.current_url
            if "login" in url or self._safe_find(By.CSS_SELECTOR, "a.loginText"):
                return AppState.LOGGED_OUT
            if "train-search" in url and self._safe_find(By.CSS_SELECTOR, "a[aria-label='Click here Logout from application']"):
                return AppState.LOGGED_IN_HOME
            if self._safe_find(By.CSS_SELECTOR, "app-train-avl-enq"):
                return AppState.TRAIN_LIST_VISIBLE
            if self._safe_find(By.CSS_SELECTOR, "input[formcontrolname='mobileNumber']"):
                return AppState.PASSENGER_DETAILS_PAGE
            if self._safe_find(By.CSS_SELECTOR, "div.payment-type-container"):
                 return AppState.PAYMENT_REVIEW_PAGE
            if self._safe_find(By.XPATH, "//div[contains(., 'PNR No.')]"):
                return AppState.BOOKING_SUCCESSFUL
        except Exception as e:
            self._log(f"Error getting state: {e}")
            return AppState.UNKNOWN_ERROR
        return AppState.UNKNOWN_ERROR

    def run_booking_flow(self, brave_path, profile_path, timed_booking=False, ac_booking=False, sl_booking=False):
        self.launch_browser(brave_path, profile_path)
        if self.gui: self.gui.set_driver(self.driver)

        while not self._stop_event.is_set():
            state = self.get_current_state()
            self._log(f"Current state: {state.name}")

            if state == AppState.LOGGED_OUT:
                if not self.login_task.execute(brave_path, profile_path): self.stop()
            elif state == AppState.LOGGED_IN_HOME:
                if timed_booking:
                    target_time = "09:59:00" if ac_booking else "10:59:00"
                    if not self.wait_until(target_time): self.stop(); break
                if not self.search_task.fill_train_details(): self.stop(); break
                if timed_booking:
                    target_time_search = "10:00:00" if ac_booking else "11:00:00"
                    if not self.wait_until(target_time_search): self.stop(); break
                if not self.search_task.press_search_button(): self.stop()
            elif state == AppState.TRAIN_LIST_VISIBLE:
                if not self.search_task.select_train_and_book(): self.stop()
            elif state == AppState.PASSENGER_DETAILS_PAGE:
                if not self.passenger_task.execute(): self.stop()
            elif state == AppState.PAYMENT_REVIEW_PAGE:
                if not self.payment_task.execute(): self.stop()
            elif state == AppState.BOOKING_SUCCESSFUL:
                self._log("Booking successful! Halting.")
                self.gui.set_status_text("SUCCESS!")
                self.stop()
            else: # UNKNOWN_ERROR or INITIALIZING
                self._log("Unknown state or error. Waiting...")

            time.sleep(1)

    def _log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        txt = f"[{threading.get_ident() % 1000}] {stamp} {msg}"
        if self.gui: self.gui.set_status_text(txt)
        else: print(txt)

    def _safe_find(self, by, selector, timeout=1):
        try: return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, selector)))
        except: return None

    def _click_with_retries(self, by, selector, timeout=300, retry_interval=1):
        end = time.time() + timeout
        while time.time() < end and not self._stop_event.is_set():
            try:
                el = self._safe_find(by, selector, timeout=retry_interval)
                if not el: time.sleep(retry_interval); continue
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
                el.click()
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                time.sleep(retry_interval)
            except Exception:
                try: self.driver.execute_script("arguments[0].click();", el); return True
                except: pass
        return False

    def get_latest_json(self):
        try:
            folder = self.automation_folder.parent / "Form" / "Saved_Details"
            files = list(folder.glob("*.json"))
            if not files: return None
            return json.loads(max(files, key=lambda f: f.stat().st_mtime).read_text(encoding="utf-8"))
        except Exception as e: self._log(f"JSON Error: {e}"); return None

    def launch_browser(self, brave_path=None, profile_path=None):
        opts = uc.ChromeOptions()
        if brave_path: opts.binary_location = brave_path
        if profile_path: opts.add_argument(f"--user-data-dir={profile_path}")
        opts.add_argument("--start-maximized")
        self.driver = uc.Chrome(options=opts)

    def wait_until(self, target_time_str, timeout=300):
        # This should use the GUI's synced time, but for simplicity we use local time here.
        # The GUI will display the accurate time.
        self._log(f"Waiting until local time {target_time_str}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            now = datetime.now().strftime("%H:%M:%S")
            if now >= target_time_str: return True
            time.sleep(0.05)
        return False

    def stop(self):
        self._log("Stop signal received. Shutting down.")
        self._stop_event.set()
        if self.driver:
            try: self.driver.quit()
            except: pass
