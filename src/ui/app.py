import streamlit as st
import src.config as config
from src.core.bot import IRCTCBot
import threading
import json

def run_bot_thread(account, booking_details, instance_id):
    """Function to be executed by each bot thread."""
    bot = IRCTCBot(account, booking_details, instance_id)
    bot.run()

def display_config():
    """Displays the current booking configuration in the UI."""
    st.subheader("Journey & Passenger Details")
    col1, col2, col3 = st.columns(3)
    col1.metric("From", config.STATION_FROM)
    col2.metric("To", config.STATION_TO)
    col3.metric("Date", config.JOURNEY_DATE)

    st.text(f"Train: {config.TRAIN_NUMBER}, Class: {config.TRAVEL_CLASS}")

    with st.expander("See Passenger List"):
        st.json(config.PASSENGERS)

    st.subheader("Technical & Account Settings")
    col1, col2, col3 = st.columns(3)
    col1.metric("Browser Count", config.BROWSER_COUNT)
    col2.metric("Headless Mode", str(config.HEADLESS))
    col3.metric("Payment Method", config.PAYMENT_METHOD)

    with st.expander("See Accounts (Usernames only)"):
        st.json([{"username": acc["username"]} for acc in config.ACCOUNTS])


def run():
    """
    Main function for the Streamlit UI.
    It displays the configuration and provides a button to launch the bots.
    """
    st.set_page_config(layout="wide", page_title="IRCTC Tatkal Bot")
    st.title("🤖 IRCTC Tatkal Booking Bot")
    st.markdown("---")

    st.sidebar.header("Master Controls")

    # --- OCR GPU Toggle ---
    # This toggle directly modifies the config variable.
    # The value it holds when "Launch" is clicked will be used by the bots.
    config.OCR_USE_GPU = st.sidebar.toggle(
        "Enable GPU for OCR",
        value=config.OCR_USE_GPU,
        help="Use GPU for faster captcha solving. Requires a compatible NVIDIA or Apple Silicon GPU."
    )

    st.sidebar.markdown("---")

    # --- Configuration Validation ---
    validation_passed = True
    # Verify that there are enough accounts for the number of browsers specified.
    if len(config.ACCOUNTS) < config.BROWSER_COUNT:
        validation_passed = False
        st.sidebar.error(
            f"Config Error: BROWSER_COUNT ({config.BROWSER_COUNT}) is greater than "
            f"the number of ACCOUNTS ({len(config.ACCOUNTS)})."
        )

    # Verify the Tatkal passenger limit.
    if len(config.PASSENGERS) > 4:
        validation_passed = False
        st.sidebar.error(
            f"Config Error: A maximum of 4 passengers are allowed for Tatkal bookings. "
            f"You have specified {len(config.PASSENGERS)}."
        )

    # The button is disabled if validation fails.
    if st.sidebar.button("🚀 Launch Booking Bots", disabled=not validation_passed):
        st.sidebar.info(f"Launching {config.BROWSER_COUNT} bot(s)...")

        # Prepare booking details from config
        booking_details = {
            "from_station": config.STATION_FROM,
            "to_station": config.STATION_TO,
            "journey_date": config.JOURNEY_DATE,
            "train_number": config.TRAIN_NUMBER,
            "travel_class": config.TRAVEL_CLASS,
            "passengers": config.PASSENGERS
        }

        # --- Multi-Browser Launch Logic ---
        # This loop iterates based on BROWSER_COUNT.
        # For each iteration, it creates and starts a new thread.
        # Each thread runs the `run_bot_thread` function, which creates and runs a new IRCTCBot instance.
        # Each bot instance is given a unique account from the ACCOUNTS list and a unique instance_id.
        # This ensures that each browser operates independently.
        threads = []
        for i in range(config.BROWSER_COUNT):
            if i < len(config.ACCOUNTS):
                account = config.ACCOUNTS[i]
                thread = threading.Thread(
                    target=run_bot_thread,
                    args=(account, booking_details, i + 1)
                )
                threads.append(thread)
                thread.start()
                st.sidebar.write(f"✅ Bot {i+1} for user `{account['username']}` started.")
            else:
                st.sidebar.error(f"❌ Not enough accounts in config.py for Bot {i+1}. Skipping.")

        st.sidebar.success("All bot threads launched.")
        st.info("Monitor the console output to see the real-time status of each bot.")

    st.header("Current Configuration")
    st.info("This configuration is loaded from `src/config.py`. Edit that file to make changes.")
    display_config()


if __name__ == "__main__":
    # To run the UI, execute `streamlit run src/ui/app.py` in your terminal.
    run()
