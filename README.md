# IRCTC Tatkal Booking Bot

This is a high-performance, multi-threaded application designed to automate the process of booking IRCTC Tatkal tickets. It uses a modern Streamlit-based UI for configuration and launching, and leverages Selenium for browser automation.

---

## 🌟 Key Features

- **Multi-Browser & Multi-Account:** Run multiple browser instances simultaneously, each with a different IRCTC account, to maximize your booking chances.
- **Precision Timing:** Synchronizes with IRCTC's official servers to start the booking process at the exact moment the Tatkal window opens.
- **Streamlit UI:** A simple and effective web-based UI to configure your journey, manage settings, and launch the bots.
- **Fully Automated Captcha Solving:** Uses the `easyocr` library to automatically read and solve captchas for a "hands-free" booking experience.
- **GPU Acceleration:** Includes a toggle in the UI to enable GPU-powered OCR for significantly faster captcha solving on compatible hardware.
- **Extensible & Modular:** The code is architected with a clean separation of concerns, making it easy to maintain and extend.
- **Packaged for Distribution:** Includes a `build.spec` file to create a single-file executable using PyInstaller.

---

## ⚙️ How It Works: The Application Flow

The application operates in a clear, sequential flow, orchestrated by the Streamlit UI and the core bot logic.

1.  **Launch:** The user starts the application by running `python master.py`. This script launches the Streamlit web server and opens the UI in a browser.
2.  **Configuration:** The UI displays the current booking settings loaded from `src/config.py`. It also performs validation checks, such as ensuring you have enough accounts for the number of browsers and that you haven't exceeded the 4-passenger limit for Tatkal.
3.  **Bot Initialization:** When the "Launch Booking Bots" button is clicked, the UI creates and starts a separate Python thread for each browser instance (`BROWSER_COUNT`). Each thread is assigned a unique IRCTC account and an instance ID.
4.  **Browser Creation:** Each bot thread calls the `webdriver_factory` to create its own independent, sandboxed Selenium WebDriver instance.
5.  **Wait for Tatkal Time:** Each bot then calls the `time_utils` module to synchronize with IRCTC's server time. The bot will pause its execution until the precise, calculated moment the Tatkal window opens.
6.  **Execution Sequence:** Once the time is reached, each bot begins executing the fully automated booking workflow defined in `src/core/bot.py`:
    - **Login:** Navigates to the site, fills credentials, and **automatically solves the captcha using OCR**.
    - **Fill Journey:** Fills the "From", "To", and "Date" details.
    - **Select Train:** Selects the Tatkal quota, finds the correct train and class, and clicks "Book Now".
    - **Fill Passengers:** Fills out the details for all configured passengers.
    - **Final Review:** **Automatically solves the second captcha using OCR**.
    - **Payment:** Selects the UPI payment method and clicks the final "Pay & Book" button.
7.  **Completion:** The bot's automated job is complete. It waits on the final page, and if it detects a PNR confirmation, it saves a screenshot. You just need to complete the payment on your UPI app.

---

## 📂 File Architecture

The project is organized into a modular structure for clarity and maintainability.

-   `master.py`: The main entry point script. You run this to start the application. It simply launches the Streamlit UI.
-   `main.py`: The entry point for the Streamlit application itself.
-   `requirements.txt`: A list of all Python dependencies required for the project.
-   `build.spec`: The configuration file for PyInstaller to build a distributable executable.
-   `README.md`: This file.

### `src/` - The Source Code Directory

-   **`src/config.py`**: **(User-configurable)** This is the most important file for the user. It contains all the settings for the bot, including account credentials, journey details, passenger information, and technical settings like `BROWSER_COUNT`.

-   **`src/ui/app.py`**: This file contains all the code for the Streamlit user interface.
    -   `run()`: The main function that sets up the Streamlit page, displays the configuration, performs validation checks, and contains the "Launch" button logic that starts the bot threads.

-   **`src/core/bot.py`**: The heart of the application. It contains the `IRCTCBot` class which manages a single browser instance and performs the booking.
    -   `IRCTCBot.run()`: The main method that orchestrates the sequence of booking steps.
    -   `IRCTCBot._perform_login()`: Handles the login sequence.
    -   `IRCTCBot._fill_journey_details()`: Fills the main search form.
    -   `IRCTCBot._select_train_and_class()`: Handles the train list page.
    -   `IRCTCBot._fill_passenger_details()`: Handles the passenger details form.
    -   `IRCTCBot._handle_final_review()`: Handles the final review page and the second CAPTCHA.
    -   `IRCTCBot._perform_payment()`: Handles the final payment page.

-   **`src/core/ocr_solver.py`**: This module contains the complete logic for solving captchas. It uses the `easyocr` library, supports GPU acceleration, and includes image preprocessing functions to improve accuracy.

-   **`src/core/selectors.py`**: **(User-configurable)** This file centralizes all the CSS and XPath selectors used to find elements on the IRCTC website. If the website's layout changes in the future, you should only need to update the selectors in this file.

-   **`src/core/webdriver_factory.py`**: A utility module responsible for creating and configuring Selenium WebDriver instances. It reads settings like `HEADLESS` and `USE_GPU` from the config file.

-   **`src/utils/logger.py`**: A utility to set up instance-specific loggers. This ensures that the console output from each bot thread is clearly tagged (e.g., `[Bot 1]`, `[Bot 2]`), which is essential for debugging.

-   **`src/utils/time_utils.py`**: This utility handles the precision timing.
    -   `get_irctc_server_time()`: Fetches the current time directly from IRCTC's API.
    -   `wait_until_tatkal_time()`: Calculates the difference between server time and local time and makes the bot wait until the perfectly synchronized moment to start booking.

---

## 🚀 Setup and Usage

1.  **Prerequisites:**
    -   Python 3.8+
    -   Google Chrome browser installed in the default location.

2.  **Installation:**
    -   Clone the repository.
    -   Install Python dependencies: `pip install -r requirements.txt`
    -   **Note:** You do **not** need to manually download `chromedriver`. The `undetected-chromedriver` library handles this automatically.

3.  **Configuration:**
    -   Open `src/config.py` and carefully fill in all your details (accounts, journey, passengers, etc.).

4.  **Run the Bot:**
    -   Open a terminal in the project's root directory.
    -   Run the command: `python master.py`
    -   A browser tab with the Streamlit UI will open.

5.  **Launch and Operate:**
    -   In the Streamlit UI sidebar, you can optionally **toggle GPU acceleration for OCR**.
    -   Click the **"🚀 Launch Booking Bots"** button.
    -   The bot will open new Chrome windows and proceed with the booking **fully automatically**. There is no need for any further manual intervention.

---

## 📦 Building the Executable

To create a single-file executable for easier distribution:

1.  Install PyInstaller: `pip install pyinstaller`
2.  Run the build command from the root directory: `pyinstaller build.spec`
3.  The final executable will be located in the `dist/` directory.
