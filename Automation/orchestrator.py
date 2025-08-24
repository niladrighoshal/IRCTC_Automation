import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
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
    STARTING = auto()
    LOGGED_OUT = auto()
    LOGGED_IN_HOME = auto()
    TRAIN_LIST_VISIBLE = auto()
    PASSENGER_DETAILS_PAGE = auto()
    PAYMENT_REVIEW_PAGE = auto()
    BOOKING_SUCCESSFUL = auto()
    UNKNOWN_ERROR = auto()

class BotOrchestrator:
    PAGE_LOAD_TIMEOUT = 300

    def __init__(self, bot_id, gui_manager, automation_folder, use_gpu=False):
        self.bot_id = bot_id
        self.gui_manager = gui_manager
        self.automation_folder = Path(automation_folder)
        self.driver = None
        self._stop_event = threading.Event()
        self.use_gpu = use_gpu
        self.ocr = CaptchaSolver(use_gpu=self.use_gpu) if CaptchaSolver else None
        self.login_task = LoginTask(self)
        self.search_task = SearchTask(self)
        self.passenger_task = PassengerTask(self)
        self.payment_task = PaymentTask(self)
        self.server_datetime = None
        self.last_sync_local_time = 0
        self.time_lock = threading.Lock()

    def get_current_state(self):
        if not self.driver or not self.driver.current_url or "about:blank" in self.driver.current_url:
            return AppState.STARTING
        try:
            url = self.driver.current_url
            if "login" in url or self._safe_find(By.CSS_SELECTOR, "a.loginText"): return AppState.LOGGED_OUT
            if "train-search" in url and self._safe_find(By.CSS_SELECTOR, "a[aria-label='Click here Logout from application']"): return AppState.LOGGED_IN_HOME
            if self._safe_find(By.CSS_SELECTOR, "app-train-avl-enq"): return AppState.TRAIN_LIST_VISIBLE
            if self._safe_find(By.CSS_SELECTOR, "input[formcontrolname='mobileNumber']"): return AppState.PASSENGER_DETAILS_PAGE
            if self._safe_find(By.CSS_SELECTOR, "div.payment-type-container"): return AppState.PAYMENT_REVIEW_PAGE
            if self._safe_find(By.XPATH, "//div[contains(., 'PNR No.')]"): return AppState.BOOKING_SUCCESSFUL
        except Exception as e:
            self._log(f"Error getting state: {e}")
            return AppState.UNKNOWN_ERROR
        return AppState.UNKNOWN_ERROR

    def run_booking_flow(self, brave_path, profile_path, timed_booking=False, ac_booking=False, sl_booking=False):
        self.launch_browser(brave_path, profile_path)

        threading.Thread(target=self._sync_server_time_loop, daemon=True).start()
        threading.Thread(target=self._update_display_loop, daemon=True).start()
        threading.Thread(target=self._auto_close_popups, daemon=True).start()
        threading.Thread(target=self._relogin_watchdog, daemon=True).start()

        while not self._stop_event.is_set():
            state = self.get_current_state()
            self._log(f"State: {state.name}")

            if state == AppState.STARTING:
                self.driver.get("https://www.irctc.co.in/nget/train-search")
            elif state == AppState.LOGGED_OUT:
                if not self.login_task.execute(brave_path, profile_path): self.stop()
            elif state == AppState.LOGGED_IN_HOME:
                if timed_booking and not self._handle_timed_waits(ac_booking): break
                if not self.search_task.fill_train_details(): self.stop(); break
                if not self.search_task.press_search_button(): self.stop()
            elif state == AppState.TRAIN_LIST_VISIBLE:
                if not self.search_task.select_train_and_book(): self.stop()
            elif state == AppState.PASSENGER_DETAILS_PAGE:
                if not self.passenger_task.execute(): self.stop()
            elif state == AppState.PAYMENT_REVIEW_PAGE:
                if not self.payment_task.execute(): self.stop()
            elif state == AppState.BOOKING_SUCCESSFUL:
                self._log("Booking successful! Halting.")
                self.stop()
            elif state == AppState.UNKNOWN_ERROR:
                self._log("Unknown state, attempting to recover by navigating to home.")
                self.driver.get("https://www.irctc.co.in/nget/train-search")

            time.sleep(1)

    def _handle_timed_waits(self, ac_booking):
        target_time = "09:59:00" if ac_booking else "10:59:00"
        if not self.wait_until(target_time): self.stop(); return False
        target_time_search = "10:00:00" if ac_booking else "11:00:00"
        if not self.wait_until(target_time_search): self.stop(); return False
        return True

    def _log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        txt = f"[{self.bot_id}] {stamp} {msg}"
        if self.gui_manager: self.gui_manager.post_update(self.bot_id, 'status', txt)
        else: print(txt)

    def _time_log(self, time_str):
        if self.gui_manager: self.gui_manager.post_update(self.bot_id, 'time', time_str)

    def _sync_server_time_loop(self):
        while not self._stop_event.is_set():
            if self.driver:
                try:
                    raw_time = self.driver.find_element(By.CSS_SELECTOR, "span strong").text.strip()
                    time_str = raw_time.split("[", 1)[1].split("]", 1)[0].strip()
                    with self.time_lock:
                        self.server_datetime = datetime.combine(datetime.today(), datetime.strptime(time_str, "%H:%M:%S").time())
                        self.last_sync_local_time = time.perf_counter()
                except: pass
            time.sleep(10)

    def _update_display_loop(self):
        while not self._stop_event.is_set():
            with self.time_lock:
                if self.server_datetime:
                    elapsed = time.perf_counter() - self.last_sync_local_time
                    current_time = self.server_datetime + timedelta(seconds=elapsed)
                    display_str = current_time.strftime("%H:%M:%S") + f".{current_time.microsecond // 1000:03d}"
                    self._time_log(display_str)
            time.sleep(0.05)

    def _auto_close_popups(self):
        while not self._stop_event.is_set():
            if self.driver:
                try:
                    aadhaar_selector = "//button[contains(@aria-label,'Aadhaar') and normalize-space(.)='OK']"
                    btn = self._safe_find(By.XPATH, aadhaar_selector, timeout=0.5)
                    if btn and btn.is_displayed(): self._click_with_retries(By.XPATH, aadhaar_selector, timeout=2)
                    disha_btn = self._safe_find(By.ID, "disha-banner-close", timeout=0.5)
                    if disha_btn and disha_btn.is_displayed(): self._click_with_retries(By.ID, "disha-banner-close", timeout=2)
                except: pass
            time.sleep(0.25)

    def _relogin_watchdog(self):
        while not self._stop_event.is_set():
            if self.driver:
                try:
                    login_link = self._safe_find(By.CSS_SELECTOR, "a.loginText")
                    if login_link and login_link.is_displayed():
                        self._click_with_retries(By.CSS_SELECTOR, "a.loginText", timeout=10)
                except: pass
            time.sleep(2)

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
            except (ElementClickInterceptedException, StaleElementReferenceException): time.sleep(retry_interval)
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
        self._log(f"Waiting until server time {target_time_str}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.server_datetime: time.sleep(0.1); continue
            with self.time_lock:
                elapsed = time.perf_counter() - self.last_sync_local_time
                current_time = self.server_datetime + timedelta(seconds=elapsed)
            if current_time.strftime("%H:%M:%S") >= target_time_str: return True
            time.sleep(0.05)
        self._log(f"Timeout waiting for {target_time_str}"); return False

    def stop(self):
        self._log("Stop signal received. Shutting down.")
        self._stop_event.set()
        if self.driver:
            try: self.driver.quit()
            except: pass
