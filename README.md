# IRCTC Tatkal Booking Bot (v3 - Intelligent Automaton)

This is a high-performance, multi-threaded application designed to automate the process of booking IRCTC Tatkal tickets. This intelligent version features a sophisticated UI, resilient state-machine architecture, and advanced multi-stage timing for a professional-grade booking experience.

---

## 🌟 Key Features

- **Advanced UI Form:** A rich user interface for creating, saving, and loading detailed booking configurations.
- **State-Machine Core:** The bot is no longer a simple script. It's a resilient automaton that understands its current state on the website and can recover from unexpected glitches like being logged out.
- **Advanced Multi-Stage Timing:** For Tatkal bookings, the bot follows a precise sequence: opening the browser 3 minutes before, logging in 1 minute before, and initiating the search at the exact moment the window opens.
- **Intelligent Popup Handling:** A high-speed observer constantly watches for and instantly closes known popups (like Aadhaar or Disha banners) without interrupting the main workflow.
- **Full Automation:** End-to-end automation, including OCR-based captcha solving.
- **Live Dashboard:** A real-time dashboard in the UI sidebar shows the live status of each bot and a synchronized IRCTC server clock.
- **Complete Session & Credential Management:** Save/load booking sessions and user accounts.
- **Stealthy & Robust:** Uses `undetected-chromedriver` to avoid bot detection and has long timeouts to handle slow network conditions gracefully.

---

## ⚙️ How It Works: The Intelligent Flow

1.  **Configuration:** The user configures a booking using the advanced UI, then configures runtime settings (Tatkal mode, browser count, etc.) in the sidebar.
2.  **Launch:** When "Launch" is clicked, the UI starts a new thread for each bot.
3.  **Timed Sequence (for Tatkal):**
    -   **T-3 Minutes:** The bot calculates the synchronized time and waits. At T-3m, it opens a browser window and navigates to the IRCTC homepage.
    -   **T-1 Minute:** The bot waits again. At T-1m, it performs the login (solving the captcha automatically) and fills in all the journey details on the main page.
    -   The bot now waits, poised for the exact Tatkal opening time.
4.  **State-Machine Execution:**
    -   At the moment the Tatkal window opens, the bot clicks "Find Trains".
    -   From this point forward, it enters a **resilient state-machine loop**.
    -   In the loop, it constantly checks: "What page am I on?" (`_get_current_state`) and "Are there any popups?" (`_handle_popups`).
    -   Based on the state, it executes the correct action (e.g., `_select_train_and_class`, `_fill_passenger_details`).
    -   **If it's unexpectedly logged out, the state check will detect this, and the bot will automatically try to log back in and continue.**
5.  **Completion:** The process finishes after payment is initiated. The live dashboard will show the final status.

---

## 📂 File Architecture

The project uses a highly modular structure. Key files include:
-   `master.py`: The main script to run the application.
-   `src/ui/app.py`: The complete Streamlit UI, including the form, sidebar, and live dashboard client.
-   `src/core/bot.py`: The heart of the application. Contains the state-machine logic, the timed sequence, and all booking action methods.
-   `src/utils/status_server.py`: The background server that powers the live dashboard.
-   `credentials.json` & `saved_details/`: Directories for storing user data.

---

## 🚀 Setup and Usage

1.  **Prerequisites:** Python 3.8+, Google Chrome.
2.  **Installation:** `pip install -r requirements.txt`.
3.  **Run:** `python master.py`.
4.  **First-Time Use:** Configure your accounts in the sidebar and click "Save Credentials".
5.  **Operation:** Fill out the booking form (or load a saved session), configure the sidebar toggles, and click "🚀 Launch Booking Bots". The process is fully automated.
