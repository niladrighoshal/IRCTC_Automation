# This file contains all the CSS selectors used for automating the IRCTC website.
# Centralizing them here makes maintenance easier. If the website structure changes,
# we only need to update the selectors in this file.

# --- Login Page ---
LOGIN_BUTTON_HOME = "a[aria-label='login']"
USERNAME_INPUT = "input[formcontrolname='userid']"
PASSWORD_INPUT = "input[formcontrolname='password']"
CAPTCHA_INPUT_LOGIN = "input[formcontrolname='nlpAnswer']"
SIGN_IN_BUTTON_MODAL = "button[type='submit']"

# --- Journey Planner ---
BOOK_TICKET_HEADING = "h2[class='font-bold sm:text-xl']"
JOURNEY_FROM_INPUT = "p-autocomplete[formcontrolname='jps-origin'] input"
JOURNEY_TO_INPUT = "p-autocomplete[formcontrolname='jps-destination'] input"
DATE_INPUT = "p-calendar[formcontrolname='jps-journey-date'] input"
FIND_TRAINS_BUTTON = "button.train_Search"

# --- Train List Page ---
TRAIN_LIST_ITEM = "div.p-slidetab-content"
REFRESH_BUTTON_BY_TRAIN = "strong.hidden-xs"
QUOTA_TATKAL_RADIO = "p-radiobutton[id='tatkal']"
CLASS_SELECTOR_TEMPLATE = "td[class*='{class_code}']" # e.g., "td[class*='3A']"
BOOK_NOW_BUTTON = "button.btnDefault.train_Search"

# --- Passenger Details Page ---
PASSENGER_NAME_INPUT = "p-autocomplete[formcontrolname='passengerName'] input"
PASSENGER_AGE_INPUT = "input[formcontrolname='passengerAge']"
PASSENGER_GENDER_DROPDOWN = "p-dropdown[formcontrolname='passengerGender']"
PASSENGER_PREFERENCE_DROPDOWN = "p-dropdown[formcontrolname='passengerBerthChoice']"
ADD_PASSENGER_BUTTON = "button.psgn-smry-btn"
PASSENGER_MOBILE_INPUT = "input[formcontrolname='mobileNumber']"
SUBMIT_PASSENGER_DETAILS_BUTTON = "button.train_Search.continue-booking-btn"

# --- Review & Payment Page ---
CAPTCHA_INPUT_REVIEW = "input[formcontrolname='nlpAnswer']"
PROCEED_TO_PAY_BUTTON = "button.train_Search.payment-button"

# --- Payment Gateway ---
# Using a more robust XPath selector that finds the radio button associated with the 'BHIM/ UPI' label.
PAYMENT_METHOD_UPI_RADIO_XPATH = "//div[contains(text(), 'BHIM/ UPI')]/ancestor::div[1]/preceding-sibling::div/p-radiobutton"
PAY_AND_BOOK_BUTTON = "button.btn.btn-primary.btn-lg"

# --- Pop-ups and Alerts ---
PNR_CONFIRMATION_POPUP = "div.p-dialog-content"
LOGOUT_CONFIRMATION_YES_BUTTON = "button.p-confirm-dialog-accept"
SESSION_TIMEOUT_POPUP = "div.p-confirm-dialog-message" # Generic, might need refinement
ADVISORY_POPUP_CLOSE_BUTTON = "button.p-dialog-header-icon"

# --- General ---
SELECTED_DROPDOWN_VALUE = "span.p-dropdown-label" # To check current value
SPINNER_OVERLAY = "div.pre-load-new" # Loading spinner
ERROR_MESSAGE_BOX = "div.p-toast-message-content"
LOGOUT_BUTTON = "a[aria-label='logout']"
