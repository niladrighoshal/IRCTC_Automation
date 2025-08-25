from enum import Enum, auto

class BotState(Enum):
    """
    Defines the comprehensive states of the IRCTC booking bot.
    The states are designed to be granular to allow for precise control and logging.
    """

    # Initialization States
    INITIALIZED = auto()            # Bot object created, not yet started.
    STARTING = auto()               # Webdriver is being created.
    STOPPED = auto()                # Bot has been gracefully stopped.

    # Pre-Login States
    IDLE = auto()                   # Browser is open, at the homepage, ready for action.
    LOGGED_OUT = auto()             # Specifically at the homepage, not logged in.

    # Login States
    LOGIN_STARTED = auto()          # Login button clicked, modal should be visible.
    LOGIN_ENTERING_CREDENTIALS = auto() # Typing username/password.
    LOGIN_SOLVING_CAPTCHA = auto()  # OCR in progress for login captcha.
    LOGIN_SUBMITTING = auto()       # "Sign In" button clicked, awaiting result.
    LOGIN_SUCCESSFUL = auto()       # Login confirmed, usually leads to AT_DASHBOARD.
    LOGIN_FAILED = auto()           # Login failed (e.g., bad credentials, captcha fail).

    # Main Dashboard & Journey Planning
    AT_DASHBOARD = auto()           # Logged in, on the main "Book Ticket" page.
    FILLING_JOURNEY_DETAILS = auto() # Entering From, To, Date.
    SUBMITTING_JOURNEY = auto()     # "Find Trains" button clicked.

    # Train Selection
    TRAIN_LIST_PAGE = auto()        # On the page with the list of available trains.
    SELECTING_QUOTA = auto()        # Clicking the desired quota (General, Tatkal).
    SELECTING_CLASS = auto()        # Clicking the desired class (SL, 3A, etc.).
    CLICKING_BOOK_NOW = auto()      # Clicking the "Book Now" button for the selected train.

    # Passenger Details
    PASSENGER_DETAILS_PAGE = auto() # On the page to enter passenger information.
    FILLING_PASSENGER_DETAILS = auto() # Typing passenger names, ages, etc.
    SUBMITTING_PASSENGERS = auto()  # Clicking "Continue" after filling details.

    # Final Review & Pre-Payment
    REVIEW_PAGE = auto()            # On the final review page before payment.
    REVIEW_SOLVING_CAPTCHA = auto() # OCR in progress for the review page captcha.
    PROCEEDING_TO_PAYMENT = auto()  # "Proceed to Pay" button clicked.

    # Payment States
    PAYMENT_PAGE = auto()           # On the payment gateway selection page.
    SELECTING_PAYMENT_METHOD = auto() # Choosing UPI/Netbanking etc.
    INITIATING_PAYMENT = auto()     # Clicking the final "Pay & Book" button.
    WAITING_FOR_UPI_MANDATE = auto() # Payment initiated, waiting for user phone approval.

    # Outcome States
    BOOKING_CONFIRMED = auto()      # PNR generated, booking is successful.
    BOOKING_FAILED = auto()         # Booking failed for any reason after payment.

    # Generic/Error States
    UNKNOWN = auto()                # The Supervisor cannot determine the page/state.
    FATAL_ERROR = auto()            # An unrecoverable error occurred.
    RECOVERING = auto()             # Attempting to recover from a minor error.
