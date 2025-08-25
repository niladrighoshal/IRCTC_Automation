# Intelligent IRCTC Booking Bot

This project is a sophisticated, automated bot for booking train tickets on the Indian Railway Catering and Tourism Corporation (IRCTC) website. It features a robust, state-driven architecture, a multi-threaded design to run multiple booking instances in parallel, and a real-time monitoring dashboard.

## Key Features

- **Intelligent State Machine:** The bot is not a simple script. It operates on a state machine, allowing it to understand its context on the website and recover from unexpected errors.
- **Supervisor/Worker Architecture:** Each bot instance uses a two-thread model for maximum resilience. The "Supervisor" observes the browser and identifies the state, while the "Worker" performs actions. This prevents the bot from getting stuck or performing incorrect actions.
- **Multi-Browser Support:** Run multiple booking sessions simultaneously, each with its own credentials and configuration, to maximize booking chances.
- **Timed (Tatkal) Booking:** Precisely schedules login and booking actions for the Tatkal window (10:00 AM for AC, 11:00 AM for SL).
- **Real-Time UI Dashboard:** A Streamlit-based web UI allows you to configure the bot, start the process, and monitor the real-time status of each bot instance.
- **Hyper-Detailed Logging:** The live dashboard shows every micro-action the bot takes, from state changes to clicks and typing, giving you a clear window into its operations.
- **Stealth Features:** The bot mimics human behavior by using randomized typing speeds and rotating user-agent strings to reduce the chance of detection.

## How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure the Bot:**
    Edit the `config.json` file to set up your booking details. See the section below for a detailed explanation of all configuration options.

3.  **Launch the Application:**
    ```bash
    python3 master.py
    ```
    This will start the Streamlit web server. Open the displayed URL in your browser to access the UI.

## Configuration (`config.json`)

The `config.json` file is the heart of the bot's setup. Here is a detailed breakdown of each section:

```json
{
  "preferences": {
    "browser_count": 1,
    "timed": false,
    "ac": false,
    "sl": false,
    "headless": false,
    "ocr_cpu": true,
    "payment": "Pay through BHIM UPI"
  },
  "logins": [
    {
      "username": "YOUR_USERNAME_1",
      "password": "YOUR_PASSWORD_1"
    }
  ],
  "train": {
    "from_code": "SBC",
    "from_station": "KSR BENGALURU",
    "to_code": "MDU",
    "to_station": "MADURAI JN",
    "date": "25122025",
    "train_no": "12637",
    "class": "AC 3 Tier (3A)",
    "quota": "TATKAL"
  },
  "passengers": [
    {
      "name": "Passenger One",
      "age": "30",
      "sex": "Male",
      "berth": "LOWER"
    }
  ],
  "contact": {
    "phone": "9876543210"
  }
}
```

- **`preferences`**:
  - `browser_count`: The number of simultaneous browser instances to launch. Must be less than or equal to the number of entries in `logins`.
  - `timed`: `true` for a timed (Tatkal) booking, `false` for a normal booking.
  - `ac` / `sl`: For timed bookings, set one to `true` to target the correct Tatkal window (10 AM for AC, 11 AM for SL).
  - `headless`: `true` to run browsers in the background without a visible UI.
  - `ocr_cpu`: `true` to force captcha solving on the CPU (recommended for systems without a powerful NVIDIA GPU).
  - `payment`: The payment method to select. Currently, only `"Pay through BHIM UPI"` is supported.
- **`logins`**: A list of IRCTC account credentials. The bot will launch one browser per entry, up to the `browser_count` limit.
- **`train`**:
  - `from_code` / `to_code`: Station codes for the journey.
  - `from_station` / `to_station`: Full station names (for display, not used by the bot).
  - `date`: Journey date in `DDMMYYYY` format.
  - `train_no`: The target train number.
  - `class`: The exact text of the travel class, e.g., `"AC 3 Tier (3A)"`, `"Sleeper (SL)"`.
  - `quota`: The booking quota, e.g., `"GENERAL"`, `"TATKAL"`.
- **`passengers`**: A list of passenger details.
  - `berth`: Berth preference (e.g., `"LOWER"`, `"UPPER"`).
- **`contact`**:
  - `phone`: The mobile number to be filled in on the passenger details page.

## Architecture Deep Dive

The bot's intelligence comes from its modern, multi-threaded architecture.

### The State Machine

The core of the bot is a state machine defined in `src/core/state.py`. Instead of blindly executing a script, the bot always knows what "state" it is in (e.g., `LOGGED_OUT`, `TRAIN_LIST_PAGE`, `PAYMENT_PAGE`). This allows it to make intelligent decisions about what to do next.

### The Supervisor/Worker Model

For each browser, the bot runs two threads that work together:

1.  **The Supervisor (The "Eyes")**: This thread's only job is to **observe** the browser. It constantly scans the page for key elements to determine the current state. For example, if it sees the main "Login" button, it sets the state to `LOGGED_OUT`. If it sees the passenger name input field, it sets the state to `PASSENGER_DETAILS_PAGE`. It is also responsible for immediately closing any popups that appear.

2.  **The Worker (The "Hands")**: This thread's only job is to **act**. It reads the state that the Supervisor has set and executes the corresponding action. If the state is `LOGGED_OUT`, the worker clicks the login button. If the state is `PASSENGER_DETAILS_PAGE`, the worker starts filling in passenger information.

This separation is crucial for stability. The Worker never acts blindly; it only does what the Supervisor has confirmed is the correct action for the current page. This prevents the bot from getting stuck or crashing due to unexpected delays or UI changes.

### The Live Bot Status Dashboard

The UI provides a dashboard that shows a real-time log of each bot's actions. This is not just a simple status update; it is a detailed, granular feed of every single state change and browser interaction. This visibility allows you to monitor the bot's progress precisely and diagnose any issues immediately.
