import streamlit as st
import json
import os
from datetime import date, datetime, timedelta
import re
import threading
import time
import requests

# Import project modules
import src.config as config
from src.utils.status_server import start_server_in_thread
from src.utils.time_utils import get_irctc_server_time
from src.core.bot_runner import run_bot_thread
from src.utils.train_info import init_persistent_driver, fetch_train_name

from src.core.ocr_solver import initialize_ocr_model

# --- Initialize Session State on first run ---
def init_session_state():
    if "server_started" not in st.session_state:
        st.session_state.server_started = True
        start_server_in_thread()

    if "background_loaders_started" not in st.session_state:
        st.session_state.info_driver = None
        st.session_state.background_loaders_started = True

        def _load_driver():
            st.session_state.info_driver = init_persistent_driver()
        threading.Thread(target=_load_driver, daemon=True).start()

        threading.Thread(target=initialize_ocr_model, args=(config.USE_GPU,), daemon=True).start()

    if "passengers" not in st.session_state:
        st.session_state.passengers = [{"name":"", "age": None, "sex": "", "berth":""}]

    if "credentials" not in st.session_state:
        CRED_FILE = "credentials.json"
        if os.path.exists(CRED_FILE):
            try:
                with open(CRED_FILE, "r") as f:
                    # Handle case where file is empty
                    content = f.read()
                    if content:
                        st.session_state.credentials = json.loads(content)
                    else:
                        st.session_state.credentials = []
            except (json.JSONDecodeError, FileNotFoundError):
                st.session_state.credentials = [] # Default to empty list if corrupt or missing
        else:
            st.session_state.credentials = []

def run_app():
    st.set_page_config(layout="wide", page_title="IRCTC Tatkal Bot")
    init_session_state()

    # ---------- Styling ----------
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(to right, #e0eafc, #cfdef3); }
    .stApp header { background-color: transparent; }
    .stButton>button { background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; font-weight: bold; border-radius: 8px; }
    .branding { font-size: 28px; color: #1e3c72; font-weight: bold; }
    input[type="text"] { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    # ---------- Branding ----------
    st.markdown("<div class='branding'>IRCTC Tatkal Booking Form</div>", unsafe_allow_html=True)
    st.markdown("---")

    # ---------- Sidebar ---
    st.sidebar.title("Controls")

    config.TIMED_BOOKING = st.sidebar.toggle("Timed (Tatkal) Booking", value=config.TIMED_BOOKING, help="Enable for Tatkal timing logic.")
    if config.TIMED_BOOKING:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            config.IS_AC = st.toggle("AC (10 AM)", value=config.IS_AC)
        with col2:
            config.IS_SL = st.toggle("SL (11 AM)", value=config.IS_SL)

    st.sidebar.markdown("---")
    config.HEADLESS = st.sidebar.toggle("Run Headless", value=config.HEADLESS)
    config.USE_GPU = st.sidebar.toggle("Enable GPU for OCR", value=config.USE_GPU)

    max_browsers = 25 if config.HEADLESS else 8
    browser_count = st.sidebar.slider("Number of Browsers", 1, max_browsers, config.DEFAULT_BROWSER_COUNT)

    st.sidebar.markdown("---")
    st.sidebar.subheader("User Accounts")

    # Ensure credentials list in session state is long enough
    while len(st.session_state.credentials) < browser_count:
        st.session_state.credentials.append({"username": "", "password": ""})

    # Display input fields for the number of browsers
    for i in range(browser_count):
        with st.sidebar.expander(f"Account {i+1}", expanded=i==0):
            cred = st.session_state.credentials[i]
            cred["username"] = st.text_input(f"Username {i+1}", value=cred.get("username", ""), key=f"user{i}")
            cred["password"] = st.text_input(f"Password {i+1}", value=cred.get("password", ""), type="password", key=f"pass{i}")

    if st.sidebar.button("Save Credentials"):
        with open("credentials.json", "w") as f:
            json.dump(st.session_state.credentials[:browser_count], f, indent=2)
        st.sidebar.success("Credentials saved!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Saved Bookings")
    saved_files = [f for f in os.listdir("saved_details") if f.endswith(".json")]

    if not saved_files:
        st.sidebar.write("No saved bookings found.")
    else:
        selected_file = st.sidebar.selectbox("Load a saved booking", [""] + saved_files)
        if st.sidebar.button("Load Selected"):
            if selected_file:
                filepath = os.path.join("saved_details", selected_file)
                with open(filepath, "r") as f:
                    st.session_state.loaded_data = json.load(f)
                st.info(f"Loaded data from `{selected_file}`.")

    if "loaded_data" in st.session_state:
        with st.expander("View Loaded Booking Data", expanded=True):
            st.json(st.session_state.loaded_data)

    st.sidebar.markdown("---")
    # Launch button is now here
    if st.sidebar.button("🚀 Launch Booking Bots", use_container_width=True):
        try: requests.post("http://localhost:8000/clear", timeout=1)
        except: pass

        from_station = from_station_display.split('(')[-1][:-1]
        to_station = to_station_display.split('(')[-1][:-1]
        class_code_match = re.search(r'\((\w+)\)', train_class_val)
        class_code = class_code_match.group(1) if class_code_match else "CLASS"
        tatkal_hour = 11 if config.IS_SL else 10

        booking_data = {
            "train": {"from_station": from_station, "to_station": to_station, "date": travel_date.strftime("%d/%m/%Y"), "train_no": train_no_input, "class": class_code, "quota": quota_val, "tatkal_hour": tatkal_hour, "tatkal_minute": 0},
            "passengers": st.session_state.passengers,
            "preferences": {"payment_method": payment_method, "upi_id": upi_id}
        }

        active_accounts = [c for c in st.session_state.credentials[:browser_count] if c.get("username")]

        if not active_accounts:
            st.sidebar.error("No valid accounts entered.")
        else:
            st.sidebar.info(f"Launching {len(active_accounts)} bot(s)...")
            for i, account in enumerate(active_accounts):
                thread = threading.Thread(target=run_bot_thread, args=(account, booking_data, i + 1))
                thread.daemon = True
                thread.start()
            st.sidebar.success("All bots launched!")

    # ---------- Main Form ----------
    try:
        with open("src/ui/railwayStationsList.json", "r", encoding="utf-8") as f:
            stations_data = json.load(f)["stations"]
        STATION_OPTIONS = [""] + [f"{s['stnName']} ({s['stnCode']})" for s in stations_data]
    except FileNotFoundError:
        st.error("Error: `railwayStationsList.json` not found.")
        return

    st.subheader("Train Details *")
    col1, col2 = st.columns(2)
    with col1:
        from_station_display = st.selectbox("From Station *", options=STATION_OPTIONS, index=0)
    with col2:
        to_station_display = st.selectbox("To Station *", options=STATION_OPTIONS, index=0)

    col3, col4 = st.columns(2)
    with col3:
        travel_date = st.date_input("Date of Journey *", value=date.today() + timedelta(days=1), min_value=date.today(), format="DD/MM/YYYY")
    with col4:
        train_no_input = st.text_input("Train Number *", placeholder="e.g., 12301")
        if st.button("Find Train Name"):
            if train_no_input:
                with st.spinner("Fetching train name..."):
                    wait_start = time.time()
                    while st.session_state.info_driver is None and time.time() - wait_start < 20:
                        time.sleep(0.2)

                    if st.session_state.info_driver:
                        train_name = fetch_train_name(st.session_state.info_driver, train_no_input)
                        st.info(f"Train Name: {train_name}")
                    else:
                        st.error("Info driver failed to initialize in time.")
            else:
                st.error("Please enter a train number.")

    col5, col6 = st.columns(2)
    with col5:
        train_class_val = st.selectbox("Class *", ["", "AC 3 Tier (3A)", "Sleeper (SL)", "AC 2 Tier (2A)"], placeholder="Select travel class")
    with col6:
        quota_val = st.selectbox("Quota *", ["", "TATKAL", "PREMIUM TATKAL", "GENERAL"], index=1)

    st.subheader("Passenger Details *")

    max_passengers = 4 if config.TIMED_BOOKING else 6
    st.caption(f"A maximum of {max_passengers} passengers are allowed for the selected booking type.")

    def add_passenger():
        if len(st.session_state.passengers) < max_passengers:
            st.session_state.passengers.append({"name":"", "age": None, "sex": "", "berth":""})

    def delete_passenger(idx):
        if len(st.session_state.passengers) > 1:
            st.session_state.passengers.pop(idx)

    for idx, p in enumerate(st.session_state.passengers):
        st.markdown(f"**Passenger {idx+1}**")
        r1, r2 = st.columns([3, 1])
        p['name'] = r1.text_input("Name *", value=p.get('name', ''), key=f"name{idx}").title()
        p['age'] = r2.number_input("Age *", min_value=1, max_value=99, value=p.get('age'), key=f"age{idx}", placeholder="Age", step=1)

        r3, r4, r5 = st.columns([2, 3, 1])
        p['sex'] = r3.selectbox("Sex *", ["", "Male", "Female", "Transgender"], key=f"sex{idx}")
        p['berth'] = r4.selectbox("Berth Preference", ["", "Lower", "Middle", "Upper", "Side Lower", "Side Upper"], key=f"berth{idx}")
        if len(st.session_state.passengers) > 1:
            with r5:
                if st.button("🗑️", key=f"del{idx}", help="Delete this passenger"):
                    delete_passenger(idx)
                    st.rerun()

    if len(st.session_state.passengers) < max_passengers:
        st.button("Add Passenger", on_click=add_passenger)

    st.subheader("Payment & Preferences *")
    payment_method = st.radio("Payment Method", ["Pay through BHIM UPI"], index=0, horizontal=True)
    if payment_method == "Pay through BHIM UPI":
        upi_id = st.text_input("UPI ID *", placeholder="Enter your UPI ID")
    else:
        upi_id = ""

    # ---------- Save Logic ----------
    def all_filled():
        if not all([from_station_display, to_station_display, train_no_input, train_class_val, quota_val]): return False
        for p in st.session_state.passengers:
            if not p['name'] or not p['age'] or not p['sex']: return False
        if payment_method == "Pay through BHIM UPI" and not upi_id: return False
        return True

    if st.button("Save Booking Details"):
        if not all_filled():
            st.error("Please fill all required (*) fields.")
        else:
            from_station = from_station_display.split('(')[-1][:-1]
            to_station = to_station_display.split('(')[-1][:-1]
            class_code_match = re.search(r'\((\w+)\)', train_class_val)
            class_code = class_code_match.group(1) if class_code_match else "CLASS"
            filename = f"{travel_date.strftime('%d%m%y')}_{train_no_input}_{from_station}_{to_station}_{class_code}.json"
            filepath = os.path.join("saved_details", filename)

            tatkal_hour = 11 if config.IS_SL else 10

            data_to_save = {
                "train": {"from_station": from_station, "to_station": to_station, "date": travel_date.strftime("%d/%m/%Y"), "train_no": train_no_input, "class": class_code, "quota": quota_val, "tatkal_hour": tatkal_hour, "tatkal_minute": 0},
                "passengers": st.session_state.passengers,
                "preferences": {"payment_method": payment_method, "upi_id": upi_id}
            }
            with open(filepath, "w") as f:
                json.dump(data_to_save, f, indent=2)
            st.success(f"Booking details saved to `{filepath}`")


    # ---------- Live Dashboard & Clock ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("Live Dashboard")
    clock_placeholder = st.sidebar.empty()
    status_placeholder = st.sidebar.empty()

    # ---------- Live Update Loop (at the end of the script) ----------
    while True:
        irctc_time = get_irctc_server_time()
        if irctc_time:
            clock_placeholder.markdown(f"**IRCTC Time:** `{irctc_time.strftime('%H:%M:%S.%f')[:-3]}`")
        else:
            clock_placeholder.markdown("**IRCTC Time:** `N/A`")

        try:
            response = requests.get("http://localhost:8000/status", timeout=0.5)
            if response.ok:
                statuses = response.json()
                status_md = ""
                for bot_id, status in sorted(statuses.items()):
                    status_md += f"**Bot {bot_id}:** `{status}`\n\n"
                status_placeholder.markdown(status_md if statuses else "`No bots running.`")
        except requests.exceptions.RequestException:
            status_placeholder.markdown("`Connecting...`")

        time.sleep(1)

if __name__ == "__main__":
    run_app()
