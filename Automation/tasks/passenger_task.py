import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

class PassengerTask:
    def __init__(self, orchestrator):
        self.bot = orchestrator
        self.driver = self.bot.driver
        self._log = self.bot._log
        self._safe_find = self.bot._safe_find
        self._click_with_retries = self.bot._click_with_retries

    def execute(self):
        self._log("Filling passenger details...")
        data = self.bot.get_latest_json()
        if not data:
            self._log("No saved details file found.")
            return False

        try:
            passengers = data["passengers"]
            preferences = data["preferences"]
            mobile_number = data["contact"]["mobile_number"]
        except KeyError as e:
            self._log(f"Missing passenger/contact/preference details in JSON: {e}")
            return False

        # Wait for passenger details page to load
        try:
            WebDriverWait(self.driver, self.bot.PAGE_LOAD_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='mobileNumber']")))
            self._log("Passenger details page loaded.")
        except Exception:
            self._log("Passenger details page did not load in time.")
            return False

        # Fill mobile number
        try:
            mobile_input = self.driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='mobileNumber']")
            mobile_input.clear()
            mobile_input.send_keys(mobile_number)
        except Exception as e:
            self._log(f"Could not fill mobile number: {e}")
            return False

        # Fill details for each passenger
        for i, p in enumerate(passengers):
            if i > 0:
                self._click_with_retries(By.CSS_SELECTOR, "span.prenext", timeout=5)
                time.sleep(0.5)

            # Find all passenger form containers
            forms = self.driver.find_elements(By.CSS_SELECTOR, "app-passenger")
            if i >= len(forms):
                self._log(f"Could not find form for passenger {i + 1}.")
                return False

            form = forms[i]
            try:
                form.find_element(By.CSS_SELECTOR, "input[placeholder='Name']").send_keys(p["name"])
                form.find_element(By.CSS_SELECTOR, "input[placeholder='Age']").send_keys(str(p["age"]))

                gender_select_el = form.find_element(By.CSS_SELECTOR, "select[formcontrolname='passengerGender']")
                Select(gender_select_el).select_by_visible_text(p["sex"])

                if p.get("berth") and p["berth"] != "No Preference":
                    berth_select_el = form.find_element(By.CSS_SELECTOR, "select[formcontrolname='passengerBerthChoice']")
                    Select(berth_select_el).select_by_visible_text(p["berth"])

            except Exception as e:
                self._log(f"Error filling form for passenger {i+1}: {e}")
                return False

        # Handle booking preferences
        try:
            auto_upgrade_label = self.driver.find_element(By.CSS_SELECTOR, "label[for='autoUpgradation']")
            auto_upgrade_checkbox = self.driver.find_element(By.ID, "autoUpgradation")
            if preferences.get("auto_upgrade", False) != auto_upgrade_checkbox.is_selected():
                auto_upgrade_label.click()
        except Exception as e:
            self._log(f"Warning: Could not set 'Auto Upgradation' preference: {e}")

        # Proceed to the next step
        self._log("Passenger details filled, proceeding to review.")
        continue_btn = self._safe_find(By.XPATH, "//button[contains(., 'Continue')]", timeout=5)
        if continue_btn and continue_btn.is_enabled():
            continue_btn.click()
            return True
        else:
            self._log("Continue button not found or not enabled.")
            return False
