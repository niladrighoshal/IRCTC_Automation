import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import src.config as config
import src.core.selectors as selectors
from src.core.webdriver_factory import create_webdriver
from src.utils.logger import setup_logger
from src.utils.time_utils import wait_until_tatkal_time
from src.core.ocr_solver import solve_captcha


class IRCTCBot:
    """
    The main class for the IRCTC booking bot.
    Each instance of this class will manage one browser and one booking attempt.
    """

    def __init__(self, account_details, booking_details, instance_id=0):
        self.account = account_details
        self.booking_details = booking_details
        self.instance_id = instance_id
        self.logger = setup_logger(self.instance_id)
        self.driver = None
        self.status = "INITIALIZED"
        self.logger.info(f"Bot initialized for user '{self.account['username']}'.")

    def _wait_for_element(self, by, value, timeout=10):
        """A helper function for explicit waits of elements."""
        self.logger.debug(f"Waiting for element: {by}='{value}'")
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception as e:
            self.logger.error(f"Element {by}='{value}' not found after {timeout} seconds.")
            raise e

    def run(self):
        """The main execution method for the bot."""
        self.status = "STARTING"
        self.logger.info("Starting bot run...")
        self.driver = create_webdriver()

        if not self.driver:
            self.status = "FAILED: WebDriver creation failed."
            self.logger.error("WebDriver creation failed. Aborting run.")
            return

        try:
            self.status = "NAVIGATING"
            self.logger.info("Navigating to IRCTC website.")
            self.driver.get("https://www.irctc.co.in/nget/train-search")

            self.status = "WAITING FOR TATKAL"
            wait_until_tatkal_time(
                hour=config.TATKAL_HOUR,
                minute=config.TATKAL_MINUTE,
                offset_seconds=config.BOOKING_TIME_OFFSET_SECONDS,
                logger=self.logger,
            )

            # --- Start of the booking workflow ---
            self._perform_login()
            self._fill_journey_details()
            self._select_train_and_class()
            self._fill_passenger_details()
            self._handle_final_review()
            self._perform_payment()
            # --- End of workflow ---

            self.status = "BOOKING SUCCESSFUL (Placeholder)"
            self.logger.info("Booking process completed successfully (Placeholder).")
            time.sleep(10) # Keep browser open for a bit

        except Exception as e:
            self.status = f"ERROR: {e}"
            self.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        finally:
            if self.driver:
                self.logger.info("Closing browser.")
                self.driver.quit()
            self.status = "FINISHED"
            self.logger.info("Bot run finished.")

    def _perform_login(self):
        """Finds and clicks the login button, fills credentials, and solves captcha."""
        self.status = "LOGGING IN"
        self.logger.info("Executing login sequence...")

        login_home_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.LOGIN_BUTTON_HOME)
        login_home_btn.click()
        self.logger.info("Login modal opened.")

        username_field = self._wait_for_element(By.CSS_SELECTOR, selectors.USERNAME_INPUT)
        username_field.send_keys(self.account["username"])

        password_field = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSWORD_INPUT)
        password_field.send_keys(self.account["password"])
        self.logger.info("Username and password entered.")

        # --- Automated Captcha Solving ---
        self.logger.info("Attempting to solve login captcha...")
        captcha_img = self._wait_for_element(By.CSS_SELECTOR, "img.captcha-img")
        captcha_src = captcha_img.get_attribute("src")

        solved_text = solve_captcha(captcha_src, use_gpu=config.OCR_USE_GPU, logger=self.logger)

        if solved_text:
            captcha_input = self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_LOGIN)
            captcha_input.send_keys(solved_text)
            self.logger.info(f"Entered solved captcha: '{solved_text}'")
        else:
            self.logger.error("Failed to solve captcha. Manual intervention may be required.")
            # As a fallback, we could re-introduce the input() here, but for now we'll let it fail.
            raise Exception("Captcha solving failed.")

        sign_in_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL)
        sign_in_btn.click()

        self.logger.info("Waiting for login to complete...")
        WebDriverWait(self.driver, 15).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, selectors.SIGN_IN_BUTTON_MODAL))
        )
        self.logger.info("Login successful.")

    def _fill_journey_details(self):
        """Fills the 'From', 'To', and 'Date' fields and clicks 'Find Trains'."""
        self.status = "FILLING JOURNEY"
        self.logger.info("Starting to fill journey details...")

        # Fill "From" station
        from_station_input = self._wait_for_element(By.CSS_SELECTOR, selectors.JOURNEY_FROM_INPUT)
        from_station_input.send_keys(config.STATION_FROM)
        self.logger.info(f"Entered 'From' station: {config.STATION_FROM}")
        # Wait for autocomplete and click the first option
        from_station_option = self._wait_for_element(By.CSS_SELECTOR, "li[role='option']")
        from_station_option.click()

        # Fill "To" station
        to_station_input = self._wait_for_element(By.CSS_SELECTOR, selectors.JOURNEY_TO_INPUT)
        to_station_input.send_keys(config.STATION_TO)
        self.logger.info(f"Entered 'To' station: {config.STATION_TO}")
        # Wait for autocomplete and click the first option
        to_station_option = self._wait_for_element(By.CSS_SELECTOR, "li[role='option']")
        to_station_option.click()

        # Fill Date - Using JavaScript to bypass the calendar widget
        self.logger.info(f"Setting date to: {config.JOURNEY_DATE}")
        date_input_element = self._wait_for_element(By.CSS_SELECTOR, selectors.DATE_INPUT)
        self.driver.execute_script(f"arguments[0].value = '{config.JOURNEY_DATE}';", date_input_element)
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input'))", date_input_element);
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", date_input_element);


        # Click "Find Trains"
        find_trains_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.FIND_TRAINS_BUTTON)
        find_trains_btn.click()
        self.logger.info("Clicked 'Find Trains'. Waiting for train list to load.")

        # Wait for the train list to appear to confirm page load
        self._wait_for_element(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM, timeout=20)
        self.logger.info("Train list page loaded successfully.")

    def _select_train_and_class(self):
        """Selects Tatkal quota, finds the train, and selects the class."""
        self.status = "SELECTING TRAIN"
        self.logger.info("Searching for train and selecting class...")

        # Select "Tatkal" quota
        tatkal_radio = self._wait_for_element(By.CSS_SELECTOR, selectors.QUOTA_TATKAL_RADIO)
        tatkal_radio.click()
        self.logger.info("Selected 'Tatkal' quota. Waiting for list to refresh.")
        # It's good practice to wait for a spinner to disappear, but a short sleep is a simpler placeholder
        time.sleep(1.5)

        # Find the specific train
        train_found = False
        all_trains = self.driver.find_elements(By.CSS_SELECTOR, selectors.TRAIN_LIST_ITEM)
        self.logger.info(f"Found {len(all_trains)} trains on the page. Searching for {config.TRAIN_NUMBER}.")

        for train_element in all_trains:
            try:
                # Check if the train number exists within this train's element
                train_number_element = train_element.find_element(By.XPATH, f".//*[contains(text(), '{config.TRAIN_NUMBER}')]")
                if train_number_element:
                    self.logger.info(f"Found train {config.TRAIN_NUMBER}.")
                    train_found = True

                    # Find and click the specified travel class within the correct train's element
                    self.logger.info(f"Attempting to find and click class '{config.TRAVEL_CLASS}' for this train.")
                    class_selector = selectors.CLASS_SELECTOR_TEMPLATE.format(class_code=config.TRAVEL_CLASS)
                    class_element = train_element.find_element(By.CSS_SELECTOR, class_selector)
                    class_element.click()
                    self.logger.info(f"Clicked on class '{config.TRAVEL_CLASS}'.")
                    time.sleep(1) # Wait for availability to show

                    # Find and click the "Book Now" button within the correct train's element
                    self.logger.info("Attempting to find and click 'Book Now' for this train.")
                    book_now_btn = train_element.find_element(By.CSS_SELECTOR, selectors.BOOK_NOW_BUTTON)
                    book_now_btn.click()
                    self.logger.info("Clicked 'Book Now'.")

                    # Wait for passenger page to load by looking for the 'Add Passenger' button
                    self._wait_for_element(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON, timeout=20)
                    self.logger.info("Passenger details page loaded successfully.")
                    break # Exit the loop once the train is found and booked
            except Exception:
                # This train is not the one we're looking for, continue to the next
                continue

        if not train_found:
            self.logger.error(f"Train {config.TRAIN_NUMBER} not found on the page.")
            raise Exception(f"Train {config.TRAIN_NUMBER} not found.")

    def _fill_passenger_details(self):
        """Fills out the passenger details form."""
        self.status = "FILLING PASSENGERS"
        self.logger.info("Starting to fill passenger details...")

        for i, passenger in enumerate(config.PASSENGERS):
            self.logger.info(f"Adding passenger {i+1}: {passenger['name']}")

            # Fill passenger name
            name_input = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSENGER_NAME_INPUT)
            name_input.send_keys(passenger["name"])

            # Fill age
            age_input = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSENGER_AGE_INPUT)
            age_input.send_keys(passenger["age"])

            # Select gender
            gender_dropdown = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSENGER_GENDER_DROPDOWN)
            gender_dropdown.click()
            gender_option = self._wait_for_element(By.XPATH, f"//span[contains(text(),'{passenger['gender']}')]")
            gender_option.click()

            # Select berth preference
            berth_dropdown = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSENGER_PREFERENCE_DROPDOWN)
            berth_dropdown.click()
            berth_option = self._wait_for_element(By.XPATH, f"//span[contains(text(),'{passenger['preference']}')]")
            berth_option.click()

            # If not the last passenger, click "Add Passenger"
            if i < len(config.PASSENGERS) - 1:
                self.logger.info("Adding another passenger.")
                add_passenger_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.ADD_PASSENGER_BUTTON)
                add_passenger_btn.click()

        # Fill mobile number
        mobile_input = self._wait_for_element(By.CSS_SELECTOR, selectors.PASSENGER_MOBILE_INPUT)
        mobile_input.send_keys(self.account["mobile_number"])
        self.logger.info(f"Entered mobile number: {self.account['mobile_number']}")

        # Submit passenger details
        submit_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.SUBMIT_PASSENGER_DETAILS_BUTTON)
        submit_btn.click()
        self.logger.info("Submitted passenger details. Proceeding to review page.")

        # Wait for the review page to load by looking for the second captcha input
        self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW, timeout=20)
        self.logger.info("Review page loaded successfully.")

    def _handle_final_review(self):
        """Handles the review page, including solving the second captcha."""
        self.status = "REVIEWING"
        self.logger.info("Handling final review page...")

        # --- Automated Captcha Solving ---
        self.logger.info("Attempting to solve review page captcha...")
        captcha_img = self._wait_for_element(By.CSS_SELECTOR, "img.captcha-img")
        captcha_src = captcha_img.get_attribute("src")

        solved_text = solve_captcha(captcha_src, use_gpu=config.OCR_USE_GPU, logger=self.logger)

        if solved_text:
            captcha_input = self._wait_for_element(By.CSS_SELECTOR, selectors.CAPTCHA_INPUT_REVIEW)
            captcha_input.send_keys(solved_text)
            self.logger.info(f"Entered solved captcha: '{solved_text}'")
        else:
            self.logger.error("Failed to solve review page captcha.")
            raise Exception("Review page captcha solving failed.")

        proceed_btn = self._wait_for_element(By.CSS_SELECTOR, selectors.PROCEED_TO_PAY_BUTTON)
        proceed_btn.click()
        self.logger.info("Clicked 'Proceed to Pay'. Waiting for payment page.")

        # Wait for the payment page to load by looking for a payment method
        self._wait_for_element(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH, timeout=20)
        self.logger.info("Payment page loaded successfully.")

    def _take_screenshot(self):
        """Takes a screenshot and saves it with a timestamp."""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"booking_success_{self.account['username']}_{timestamp}.png"
            filepath = os.path.join(config.SUCCESS_SCREENSHOT_DIR, filename)
            self.driver.save_screenshot(filepath)
            self.logger.info(f"Successfully saved screenshot to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")

    def _perform_payment(self):
        """Selects the payment method and clicks Pay."""
        self.status = "PAYING"
        self.logger.info(f"Handling payment via {config.PAYMENT_METHOD}...")

        if config.PAYMENT_METHOD == "UPI":
            self.logger.info("Selecting UPI as payment method.")
            upi_radio = self._wait_for_element(By.XPATH, selectors.PAYMENT_METHOD_UPI_RADIO_XPATH)
            # The radio button is sometimes obscured, so we click using JavaScript
            self.driver.execute_script("arguments[0].click();", upi_radio)

            pay_button = self._wait_for_element(By.CSS_SELECTOR, selectors.PAY_AND_BOOK_BUTTON)
            self.driver.execute_script("arguments[0].click();", pay_button)

            self.logger.info("Clicked 'Pay & Book'. The bot's main job is done.")
            self.logger.info("Please complete the payment on your UPI app.")

            # The bot will now wait for a potential confirmation page.
            try:
                self.logger.info("Waiting for PNR confirmation popup (up to 2 minutes)...")
                self._wait_for_element(By.CSS_SELECTOR, selectors.PNR_CONFIRMATION_POPUP, timeout=120)
                self.logger.info("SUCCESS! PNR confirmation detected.")
                self.status = "BOOKING SUCCESSFUL"
                self._take_screenshot()
            except Exception:
                self.logger.warning("Did not detect PNR confirmation page within 2 minutes.")
                self.logger.warning("Please check the IRCTC website and your messages manually.")
                self.status = "PAYMENT INITIATED"

        elif config.PAYMENT_METHOD in ["CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]:
            self.logger.error(f"Payment method '{config.PAYMENT_METHOD}' is not yet implemented.")
            raise NotImplementedError(f"Payment logic for {config.PAYMENT_METHOD} is a placeholder.")
        else:
            self.logger.error(f"Unknown payment method: '{config.PAYMENT_METHOD}'")
            raise ValueError(f"Unknown payment method: '{config.PAYMENT_METHOD}'")


if __name__ == "__main__":
    if config.ACCOUNTS:
        bot = IRCTCBot(config.ACCOUNTS[0], {}, instance_id=99)
        bot.run()
    else:
        print("No accounts configured in src/config.py. Cannot run test.")
