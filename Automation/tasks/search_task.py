import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SearchTask:
    def __init__(self, orchestrator):
        self.bot = orchestrator
        self.driver = self.bot.driver
        self._log = self.bot._log
        self._safe_find = self.bot._safe_find
        self._click_with_retries = self.bot._click_with_retries

    def fill_train_details(self):
        self._log("Filling train details...")
        data = self.bot.get_latest_json()
        if not data:
            self._log("No saved details file found for filling train details.")
            return False

        try:
            train_info = data["train"]
            from_station = train_info["from_station"]
            to_station = train_info["to_station"]
            travel_date_obj = datetime.strptime(train_info["date"], "%d%m%Y")
            travel_date_str = travel_date_obj.strftime("%d/%m/%Y")
            train_class = train_info["class"]
            quota = train_info["quota"]
        except (KeyError, ValueError) as e:
            self._log(f"Error reading train details from JSON: {e}")
            return False

        # --- Fill From Station ---
        from_selector = 'input[aria-autocomplete="list"][formcontrolname="fromStation"]'
        if self._click_with_retries(By.CSS_SELECTOR, from_selector, timeout=10):
            try:
                from_input = self.driver.find_element(By.CSS_SELECTOR, from_selector)
                from_input.clear()
                from_input.send_keys(from_station)
                time.sleep(1)
                option_selector = f"//li[contains(@class, 'ui-autocomplete-list-item')]//span[contains(text(), '{from_station}')]"
                self._click_with_retries(By.XPATH, option_selector, timeout=5)
            except Exception as e:
                self._log(f"Error filling 'From' station: {e}")
                return False
        else:
            self._log("Could not find 'From' station input.")
            return False

        # --- Fill To Station ---
        to_selector = 'input[aria-autocomplete="list"][formcontrolname="toStation"]'
        if self._click_with_retries(By.CSS_SELECTOR, to_selector, timeout=10):
            try:
                to_input = self.driver.find_element(By.CSS_SELECTOR, to_selector)
                to_input.clear()
                to_input.send_keys(to_station)
                time.sleep(1)
                option_selector = f"//li[contains(@class, 'ui-autocomplete-list-item')]//span[contains(text(), '{to_station}')]"
                self._click_with_retries(By.XPATH, option_selector, timeout=5)
            except Exception as e:
                self._log(f"Error filling 'To' station: {e}")
                return False
        else:
            self._log("Could not find 'To' station input.")
            return False

        # --- Fill Date ---
        date_selector = 'input[formcontrolname="journeyDate"]'
        date_input = self._safe_find(By.CSS_SELECTOR, date_selector, timeout=5)
        if date_input:
            try:
                self.driver.execute_script(f"arguments[0].value = '{travel_date_str}'; arguments[0].dispatchEvent(new Event('change'));", date_input)
            except Exception as e:
                self._log(f"Error setting date via JS: {e}")
                return False
        else:
            self._log("Could not find date input.")
            return False

        # --- Select Class ---
        class_dropdown_selector = 'p-dropdown[formcontrolname="journeyClass"]'
        if self._click_with_retries(By.CSS_SELECTOR, class_dropdown_selector, timeout=10):
            try:
                class_code = train_class.split('(')[-1].split(')')[0]
                class_option_selector = f"//p-dropdownitem/li/span[contains(., '{class_code}')]"
                self._click_with_retries(By.XPATH, class_option_selector, timeout=5)
            except Exception as e:
                self._log(f"Error selecting class: {e}")
                return False
        else:
            self._log("Could not find class dropdown.")
            return False

        # --- Select Quota ---
        quota_dropdown_selector = 'p-dropdown[formcontrolname="journeyQuota"]'
        if self._click_with_retries(By.CSS_SELECTOR, quota_dropdown_selector, timeout=10):
            try:
                quota_option_selector = f"//p-dropdownitem/li/span[text()='{quota}']"
                self._click_with_retries(By.XPATH, quota_option_selector, timeout=5)
            except Exception as e:
                self._log(f"Error selecting quota: {e}")
                return False
        else:
            self._log("Could not find quota dropdown.")
            return False

        self._log("Train details filled successfully.")
        return True

    def press_search_button(self):
        self._log("Pressing search button...")
        search_button_selector = "button.train_Search[label='Find Trains']"
        if self._click_with_retries(By.CSS_SELECTOR, search_button_selector, timeout=10):
            self._log("Search button pressed successfully.")
            return True
        else:
            self._log("Failed to press search button.")
            return False

    def select_train_and_book(self):
        self._log("Selecting train and class, then booking...")
        data = self.bot.get_latest_json()
        if not data:
            self._log("No saved details file found.")
            return False

        try:
            train_no = data["train"]["train_no"]
            train_class = data["train"]["class"]
        except KeyError as e:
            self._log(f"Missing train details in JSON: {e}")
            return False

        try:
            WebDriverWait(self.driver, self.bot.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "app-train-avl-enq"))
            )
            self._log("Train list page loaded.")
        except Exception:
            self._log("Train list did not load in time.")
            return False

        train_card_selector = f"//app-train-avl-enq[.//strong[contains(text(), '({train_no})')]]"
        train_card = self._safe_find(By.XPATH, train_card_selector, timeout=20)

        if not train_card:
            self._log(f"Train {train_no} not found in the list.")
            return False

        self._log(f"Found train card for {train_no}.")

        class_selector = f".//div[contains(@class, 'pre-avl')]//strong[contains(text(), '{train_class}')]"

        try:
            class_element = train_card.find_element(By.XPATH, class_selector)
            self.driver.execute_script("arguments[0].click();", class_element)
            self._log(f"Clicked on class '{train_class}'.")
            time.sleep(1)
        except Exception:
            self._log(f"Could not find or click class '{train_class}'.")
            return False

        book_now_selector = ".//button[contains(., 'Book Now')]"
        try:
            book_now_button = WebDriverWait(train_card, 10).until(
                EC.element_to_be_clickable((By.XPATH, book_now_selector))
            )
            self.driver.execute_script("arguments[0].click();", book_now_button)
            self._log("Clicked 'Book Now' button.")
            return True
        except Exception:
            self._log("'Book Now' button not found or not clickable. Ticket may not be available.")
            return False
