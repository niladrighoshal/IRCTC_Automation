# IRCTC Tatkal Booking Bot (v3.1 - Intelligent & Performant)

This is a high-performance, multi-threaded application designed to automate the process of booking IRCTC Tatkal tickets. This intelligent version features a sophisticated UI, resilient state-machine architecture, advanced multi-stage timing, and a high-performance, silent-loading architecture for a professional-grade booking experience.

---

## 🌟 Key Features

- **High-Performance Startup:** The application starts instantly. Heavy components like the OCR model and web drivers are loaded silently in the background while you fill out the form.
- **Advanced UI Form:** A rich user interface for creating, saving, and loading detailed booking configurations.
- **State-Machine Core:** The bot is a resilient automaton that understands its current state on the website and can recover from unexpected glitches like being logged out.
- **Advanced Multi-Stage Timing:** For Tatkal bookings, the bot follows a precise sequence: opening the browser 3 minutes before, logging in 1 minute before, and initiating the search at the exact moment the window opens.
- **Intelligent Popup Handling:** A high-speed observer constantly watches for and instantly closes known popups.
- **Full Automation:** End-to-end automation, including OCR-based captcha solving.
- **Live Dashboard:** A real-time dashboard in the UI sidebar shows the live status of each bot and a synchronized IRCTC server clock.
- **Complete Session & Credential Management:** Save/load booking sessions and user accounts.
- **Stealthy & Robust:** Uses `undetected-chromedriver` to avoid bot detection and has long timeouts to handle slow network conditions gracefully.

---

## ⚙️ How It Works: The Intelligent Flow

1.  **Instant Launch:** The user runs `python master.py`. The Streamlit UI starts instantly.
2.  **Silent Background Loading:** As soon as the UI opens, two background threads are started: one to initialize the OCR engine and another to start the headless browser for the "Find Train Name" feature.
3.  **Configuration:** The user fills out the booking form, loads a saved session, and configures runtime settings and accounts in the sidebar. By the time they are done, the background resources are ready.
4.  **Launch Bots:** When "Launch" is clicked, the application starts the bot threads.
5.  **Timed Sequence & State Machine:** The bot executes its timed sequence for Tatkal bookings and then transitions into the resilient state-machine loop to handle the rest of the process robustly, recovering from any glitches.
6.  **Live Monitoring:** The user can monitor the exact status of each bot in real-time via the live dashboard.

---

## 📂 File Architecture & Setup

-   **Run:** `python master.py`
-   **Dependencies:** `pip install -r requirements.txt`
-   **Documentation:** All files are structured and commented. Key files include:
    -   `src/ui/app.py`: The complete Streamlit UI, including background loading logic.
    -   `src/core/bot.py`: The state-machine and timing logic for the bot.
    -   `src/core/ocr_solver.py`: The OCR engine, now loaded in the background.
    -   `src/utils/train_info.py`: The train name fetcher, now loaded in the background.
