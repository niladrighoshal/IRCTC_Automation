import os

# --- Essential User Configuration ---

# Set the number of concurrent browser instances you want to run.
# Each browser will attempt to book a ticket using a separate account.
BROWSER_COUNT = 2

# List of user accounts. The number of accounts should be equal to or greater than BROWSER_COUNT.
# Each dictionary represents one account.
# Format: {"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD", "mobile_number": "YOUR_REGISTERED_MOBILE"}
ACCOUNTS = [
    {"username": "USER1", "password": "PASSWORD1", "mobile_number": "1234567890"},
    {"username": "USER2", "password": "PASSWORD2", "mobile_number": "0987654321"},
    # Add more accounts here if BROWSER_COUNT > 2
]

# --- Booking Details ---

# Journey details
STATION_FROM = "HWH"  # Station code, e.g., "NDLS" for New Delhi
STATION_TO = "ADI"  # Station code, e.g., "BCT" for Mumbai Central
JOURNEY_DATE = "30/09/2025"  # DD/MM/YYYY format

# Train and class details
TRAIN_NUMBER = "12834"  # Train number as a string
TRAVEL_CLASS = "3A"  # Travel class code, e.g., "SL", "3A", "2A", "1A"

# List of passenger details. Add one dictionary for each passenger.
PASSENGERS = [
    {
        "name": "Passenger One",
        "age": "30",
        "gender": "Male",  # Male, Female, or Transgender
        "preference": "LB",  # LB, MB, UB, SL, SU
    },
    {
        "name": "Passenger Two",
        "age": "28",
        "gender": "Female",
        "preference": "LB",
    },
]


# --- Payment Details ---

# Set your preferred payment method.
# Options: "UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"
PAYMENT_METHOD = "UPI"

# Your UPI ID
UPI_ID = "your_upi_id@oksbi"


# --- Tatkal Timing Settings ---

# The hour and minute for the Tatkal booking window opening.
# For AC classes (2A, 3A, etc.), this is 10:00 AM.
# For Sleeper class (SL), this is 11:00 AM.
TATKAL_HOUR = 10  # 24-hour format
TATKAL_MINUTE = 0

# A small offset in seconds to start the process slightly before the official time.
# This can help account for network latency. Use with caution.
# A value of -1.5 means the bot will spring into action 1.5 seconds *before* the Tatkal time.
BOOKING_TIME_OFFSET_SECONDS = -1.5


# --- Technical Settings ---

# Set to True to run browsers in headless mode (no GUI).
# Set to False to watch the automation in real-time.
HEADLESS = False

# Enable or disable GPU acceleration for the browser.
# May improve performance on some systems, but can cause issues on others.
USE_GPU = False

# Path to your chromedriver executable.
# If chromedriver is in your system's PATH, you can leave this as "chromedriver".
# Otherwise, provide the full path, e.g., "/path/to/your/chromedriver".
CHROMEDRIVER_PATH = "chromedriver"

# --- OCR Settings ---

# Set to True to use GPU for captcha solving (if a compatible GPU is available).
# Set to False to force CPU. This can be toggled from the UI.
OCR_USE_GPU = True


# --- Internal Paths (Do not change) ---

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path for storing logs
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Path for storing screenshots of successful bookings
SUCCESS_SCREENSHOT_DIR = os.path.join(BASE_DIR, "successful_bookings")

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SUCCESS_SCREENSHOT_DIR, exist_ok=True)
