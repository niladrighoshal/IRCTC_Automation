import streamlit as st
import json, os, sys, subprocess, re
from datetime import date, datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Headless Driver for Train Name Fetching ---
if "train_name_driver" not in st.session_state:
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        st.session_state.train_name_driver = uc.Chrome(options=options)
    except Exception as e:
        st.error(f"Could not initialize headless browser: {e}")
        st.stop()

from status_server import run_server
from streamlit.components.v1 import html

# --- Main App Setup ---
if 'server' not in st.session_state:
    st.session_state.server = run_server()

# Cache the train name fetching function to avoid repeated slow lookups
@st.cache_data
def fetch_train_name(train_no: str):
    if not train_no or not train_no.isdigit() or len(train_no) != 5:
        return "Invalid Train Number"
    url = f"https://www.railyatri.in/time-table/{train_no}"
    try:
        driver = st.session_state.train_name_driver
        driver.get(url)
        heading = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.timetable_lts_timeline_title__7Patt h1"))
        )
        text = heading.text.strip()
        match = re.match(r"(.+?\(\d+\))", text)
        return match.group(1).strip() if match else text.replace("Train Time Table", "").strip()
    except Exception:
        return "Could not fetch train name"

# ---------- Credential Management ----------
CRED_FILE = "credentials.json"

def load_credentials():
    if not os.path.exists(CRED_FILE):
        return {}
    try:
        with open(CRED_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_credentials(creds):
    with open(CRED_FILE, "w") as f:
        json.dump(creds, f, indent=2)

# ---------- Styling and Component Functions ----------
def load_session_state(data):
    """Loads data from a dictionary into the session state."""
    # Load run_config
    if 'run_config' in data:
        for key, value in data['run_config'].items():
            st.session_state[key] = value

    # Load login
    if 'login' in data:
        st.session_state.username = data['login'].get('username', '')
        st.session_state.password = data['login'].get('password', '')

    # Load train details
    if 'train' in data:
        st.session_state.from_station_display = STATION_MAP.get(data['train'].get('from_station', ''))
        st.session_state.to_station_display = STATION_MAP.get(data['train'].get('to_station', ''))
        st.session_state.travel_date = datetime.strptime(data['train']['date'], "%d%m%Y").date() if data['train'].get('date') else date.today()
        st.session_state.train_no = data['train'].get('train_no', '')
        st.session_state.train_name = data['train'].get('train_name', '')
        st.session_state.train_class_val = data['train'].get('class', '')
        st.session_state.quota_val = data['train'].get('quota', '')

    # Load passengers
    if 'passengers' in data:
        st.session_state.passengers = data['passengers']

    # Load contact and preferences
    if 'contact' in data:
        st.session_state.mobile_number = data['contact'].get('mobile_number', '')
    if 'preferences' in data:
        st.session_state.auto_upgrade = data['preferences'].get('auto_upgrade', True)
        st.session_state.confirm_only = data['preferences'].get('confirm_only', True)
        st.session_state.payment_method = data['preferences'].get('payment_method', 'Pay through BHIM UPI')
        st.session_state.upi_id = data['preferences'].get('upi_id', '')

st.markdown("""
<style>
.header { background: linear-gradient(90deg,#00c6ff,#0072ff);padding:15px;border-radius:8px;
text-align:center;color:white;font-size:28px;font-weight:bold; }
div.stButton > button:first-child { background: linear-gradient(90deg,#1e3c72,#2a5298);
color:white;border:none;padding:.6em 2em;font-size:16px;border-radius:8px;transition:all .3s ease; }
div.stButton > button:first-child:hover { transform:scale(1.05);background:linear-gradient(90deg,#2a5298,#1e3c72);}
div.stButton > button:first-child:active { transform:scale(0.95); }
.st-emotion-cache-1jicfl2 { background: linear-gradient(180deg, #89f7fe 0%, #66a6ff 100%); }
.delete-btn {margin-top: 27px;}
.warning {color: red; font-weight: bold;}
.branding {font-size:28px; color: navy; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

def name_capper(key):
    """Callback to capitalize names in session state."""
    try:
        # Capitalize first letter of each word
        st.session_state[key] = st.session_state[key].title()
    except:
        pass # Ignore errors if key doesn't exist yet

# ---------- Sidebar Controls ----------
with st.sidebar:
    st.title("⚙️ Bot Configuration")

    def create_toggle(label, key, default, help_text=""):
        """Creates a toggle switch with a text status indicator."""
        if key not in st.session_state:
            st.session_state[key] = default

        col1, col2 = st.columns([3, 2])
        st.session_state[key] = col1.toggle(label, value=st.session_state[key], help=help_text)
        status_text = "🟢 On" if st.session_state[key] else "⚪ Off"
        col2.markdown(f"**{status_text}**")

    create_toggle("Timed (Tatkal)", 'timed_booking', False, "Enable for Tatkal bookings.")
    create_toggle("Use GPU", 'use_gpu', False, "Use GPU for faster captcha solving.")
    create_toggle("AC Classes", 'ac_booking', True, "For AC Tatkal at 10:00 AM.")
    create_toggle("Sleeper Classes", 'sl_booking', True, "For Sleeper Tatkal at 11:00 AM.")
    create_toggle("Headless Mode", 'headless_mode', False, "Run browsers in the background without a visible UI.")

    max_browsers = 25 if st.session_state.headless_mode else 8
    st.session_state.browser_count = st.slider("Browser Count", min_value=1, max_value=max_browsers, value=st.session_state.get('browser_count', 1), help="Number of parallel browsers to launch.")
    st.caption(f"Max browsers in headless mode: 25. In normal mode: 8.")

    st.markdown("---")

    # --- Saved Sessions Loader ---
    st.subheader("Saved Sessions")

    saved_files_path = os.path.join(os.path.dirname(__file__), "Saved_Details")
    if os.path.exists(saved_files_path) and os.path.isdir(saved_files_path):
        files = sorted(
            [f for f in os.listdir(saved_files_path) if f.endswith('.json')],
            key=lambda f: os.path.getmtime(os.path.join(saved_files_path, f)),
            reverse=True
        )

        with st.container(height=200):
            for f in files:
                col1, col2 = st.columns([3, 1])
                col1.text(f, help=f)
                if col2.button("Load", key=f"load_{f}", use_container_width=True):
                    with open(os.path.join(saved_files_path, f), "r") as file:
                        loaded_data = json.load(file)
                        load_session_state(loaded_data)
                        st.rerun()

# ---------- Branding ----------
st.markdown('<div class="header">IRCTC Booking Bot Control Panel</div>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: navy; font-weight:bold'>Made by Niladri Ghoshal</p>", unsafe_allow_html=True)

# ---------- Load station list ----------
with open("railwayStationsList.json", "r", encoding="utf-8") as f:
    stations_data = json.load(f)["stations"]

# Create a searchable list of stations with both code and name
STATION_OPTIONS = []
for station in stations_data:
    display_text = f"{station['stnName']} ({station['stnCode']})"
    search_text = f"{station['stnCode']} {station['stnName']}".lower()
    STATION_OPTIONS.append({
        "display": display_text,
        "search": search_text,
        "code": station['stnCode']
    })

# Sort by station code for better search
STATION_OPTIONS.sort(key=lambda x: x["code"])

# Create a list of display texts for the selectbox
STATION_DISPLAY_OPTIONS = [""] + [station["display"] for station in STATION_OPTIONS]

# Map stnCode -> stnName (stnCode)
STATION_MAP = {s['stnCode']: f"{s['stnName']} ({s['stnCode']})" for s in stations_data}

# ---------- Session init ----------
if "passengers" not in st.session_state:
    st.session_state.passengers = [{"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""}]

# ---------- IRCTC Login ----------
st.subheader("IRCTC Login *")

credentials = load_credentials()
user_list = [""] + list(credentials.keys()) + ["+ Add New User"]

# Use a key to prevent widget duplication issues
if 'selected_user' not in st.session_state:
    st.session_state.selected_user = ""

selected_user = st.selectbox("Select User or Add New", options=user_list, key="sb_user")

if selected_user == "+ Add New User":
    st.session_state.username = st.text_input("New Username *", value="", autocomplete="off")
    st.session_state.password = st.text_input("New Password *", value="", type="password", autocomplete="new-password")
elif selected_user:
    st.session_state.username = selected_user
    st.session_state.password = credentials[selected_user]
    # Display the selected user's credentials, disabled
    st.text_input("Username *", value=st.session_state.username, disabled=True)
    st.text_input("Password *", value=st.session_state.password, type="password", disabled=True, autocomplete="new-password")
else:
    # Clear fields if no user is selected
    st.session_state.username = ""
    st.session_state.password = ""

# ---------- Train Details ----------
st.subheader("Train Details *")
col1, col2 = st.columns([1,1])
st.session_state.from_station_display = col1.selectbox("From Station *", options=STATION_DISPLAY_OPTIONS, index=STATION_DISPLAY_OPTIONS.index(st.session_state.get('from_station_display', '')) if st.session_state.get('from_station_display') in STATION_DISPLAY_OPTIONS else 0, placeholder="Type to search...")
st.session_state.to_station_display = col2.selectbox("To Station *", options=STATION_DISPLAY_OPTIONS, index=STATION_DISPLAY_OPTIONS.index(st.session_state.get('to_station_display', '')) if st.session_state.get('to_station_display') in STATION_DISPLAY_OPTIONS else 0, placeholder="Type to search...")

col3, col4 = st.columns([1,1])
st.session_state.travel_date = col3.date_input("Date of Journey *", value=st.session_state.get('travel_date', date.today() + timedelta(days=1)), min_value=date.today(), max_value=date.today() + timedelta(days=60), format="DD/MM/YYYY")
st.session_state.train_no = col4.text_input("Train Number *", value=st.session_state.get('train_no', ''), placeholder="5-digit no. & press Enter", autocomplete="off")

# Live train name fetcher logic
if st.session_state.train_no != st.session_state.get('last_train_no', ''):
    st.session_state.last_train_no = st.session_state.train_no
    if len(st.session_state.train_no) == 5 and st.session_state.train_no.isdigit():
        with st.spinner("Fetching train name..."):
            st.session_state.train_name = fetch_train_name(st.session_state.train_no)
    else:
        st.session_state.train_name = ""

if 'train_name' in st.session_state and st.session_state.train_name:
    if "Could not fetch" in st.session_state.train_name or "Invalid" in st.session_state.train_name:
        st.warning(st.session_state.train_name)
    else:
        st.success(st.session_state.train_name)

# Class and Quota
train_class_options = ["", "AC 3 Tier (3A)", "Sleeper (SL)", "AC 2 Tier (2A)", "AC 3 Economy (3E)"]
quota_options = ["", "TATKAL", "PREMIUM TATKAL", "GENERAL"]
c5, c6 = st.columns(2)
st.session_state.train_class_val = c5.selectbox("Class *", options=train_class_options, index=train_class_options.index(st.session_state.get('train_class_val', '')) if st.session_state.get('train_class_val') in train_class_options else 0)
st.session_state.quota_val = c6.selectbox("Quota *", options=quota_options, index=quota_options.index(st.session_state.get('quota_val', '')) if st.session_state.get('quota_val') in quota_options else 0)

# ---------- Dynamic Passengers ----------
st.subheader("Passenger Details *")

def add_passenger():
    if len(st.session_state.passengers) < 6:
        st.session_state.passengers.append({"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""})

def delete_passenger(idx):
    if len(st.session_state.passengers) > idx:
        st.session_state.passengers.pop(idx)

for idx, p in enumerate(st.session_state.passengers):
    st.markdown(f"### Passenger {idx+1}")
    cols = st.columns([3, 1, 2, 2, 3, 1])
    
    # Use a unique key for the name widget for the callback
    name_key = f"passenger_name_{idx}"
    p["name"] = cols[0].text_input("Name *", value=p["name"], key=name_key, on_change=name_capper, args=(name_key,), autocomplete="off")

    # For number_input, value must be None if empty, not an empty string
    age_val = p.get("age")
    p["age"] = cols[1].number_input("Age *", min_value=1, max_value=99, value=age_val, placeholder="Age", key=f"age_{idx}")
    
    sex_options = ["", "Male", "Female", "Transgender"]
    p["sex"] = cols[2].selectbox("Sex *", options=sex_options, index=sex_options.index(p["sex"]) if p["sex"] in sex_options else 0, key=f"sex_{idx}")

    p["nationality"] = cols[3].text_input("Nationality *", value=p["nationality"], key=f"nat_{idx}", autocomplete="off")

    berth_options = ["", "No Preference","Lower","Middle","Upper","Side Lower","Side Upper"]
    p["berth"] = cols[4].selectbox("Berth *", options=berth_options, index=berth_options.index(p["berth"]) if p["berth"] in berth_options else 0, key=f"berth_{idx}")

    if len(st.session_state.passengers) > 1:
        cols[5].button("🗑️", key=f"del_{idx}", on_click=delete_passenger, args=(idx,))

st.button("Add Passenger", on_click=add_passenger)

# ---------- Contact Details ----------
st.subheader("Contact Details *")
st.session_state.mobile_number = st.text_input("Mobile Number *", value=st.session_state.get('mobile_number', ''), max_chars=10, autocomplete="off")
is_mobile_valid = len(st.session_state.mobile_number) == 10 and st.session_state.mobile_number.isdigit()
if st.session_state.mobile_number and not is_mobile_valid:
    st.error("Please enter a valid 10-digit mobile number.")

# ---------- Booking Preferences ----------
st.subheader("Booking Preferences *")
st.session_state.auto_upgrade = st.checkbox("Consider for Auto Upgradation", value=st.session_state.get('auto_upgrade', True))
st.session_state.confirm_only = st.checkbox("Book Only Confirm Berth is Alloted", value=st.session_state.get('confirm_only', True))

# ---------- Payment Method ----------
st.subheader("Payment Method *")
st.session_state.payment_method = st.radio("Select payment method:", ["Pay through BHIM UPI", "Pay through IRCTC Wallet"], index=["Pay through BHIM UPI", "Pay through IRCTC Wallet"].index(st.session_state.get('payment_method', "Pay through BHIM UPI")), horizontal=True)
if st.session_state.payment_method == "Pay through BHIM UPI":
    st.session_state.upi_id = st.text_input("UPI ID *", value=st.session_state.get('upi_id', ''), autocomplete="off")
else:
    st.markdown('<p class="warning">Wallet balance must be sufficient.</p>', unsafe_allow_html=True)
    st.session_state.upi_id = ""

# ---------- Helpers ----------
def all_filled():
    # Read all values from session_state for validation
    form_values = [
        st.session_state.get('username'),
        st.session_state.get('password'),
        st.session_state.get('from_station_display'),
        st.session_state.get('to_station_display'),
        st.session_state.get('train_no'),
        st.session_state.get('train_class_val'),
        st.session_state.get('quota_val'),
        st.session_state.get('mobile_number')
    ]
    if not all(form_values):
        return False

    # Check mobile number validity
    if not (len(st.session_state.get('mobile_number', '')) == 10 and st.session_state.get('mobile_number', '').isdigit()):
        return False

    # Check passenger details
    if not st.session_state.get('passengers'): return False
    for p in st.session_state.passengers:
        if not all(p.get(key) for key in ["name", "age", "sex", "nationality", "berth"]):
            return False

    if st.session_state.get('payment_method') == "Pay through BHIM UPI" and not st.session_state.get('upi_id'):
        return False

    return True

def save_data(is_booking_run: bool):
    """Saves the form data and optionally launches the bot."""
    if not all_filled():
        st.error("Cannot proceed: All fields marked * are required and must be valid.")
        return

    # Update credentials if they are new or changed
    if st.session_state.username and st.session_state.password:
        creds = load_credentials()
        if creds.get(st.session_state.username) != st.session_state.password:
            creds[st.session_state.username] = st.session_state.password
            save_credentials(creds)
            st.toast(f"Saved credentials for user: {st.session_state.username}")

    # Reconstruct the station codes from the display values
    from_station_code = st.session_state.from_station_display.split("(")[-1].split(")")[0].upper() if st.session_state.get('from_station_display') else ""
    to_station_code = st.session_state.to_station_display.split("(")[-1].split(")")[0].upper() if st.session_state.get('to_station_display') else ""

    # Gather all data from session_state
    data = {
        "login": {"username": st.session_state.username, "password": st.session_state.password},
        "contact": {"mobile_number": st.session_state.mobile_number},
        "train": {
            "from_station": from_station_code,
            "to_station": to_station_code,
            "date": st.session_state.travel_date.strftime("%d%m%Y"),
            "train_no": st.session_state.train_no,
            "train_name": st.session_state.get('train_name', ''),
            "class": st.session_state.train_class_val,
            "quota": st.session_state.quota_val
        },
        "passengers": st.session_state.passengers,
        "preferences": {
            "auto_upgrade": st.session_state.auto_upgrade,
            "confirm_only": st.session_state.confirm_only,
            "payment_method": st.session_state.payment_method,
            "upi_id": st.session_state.get('upi_id', '')
        },
        "run_config": {
            "timed_booking": st.session_state.timed_booking,
            "ac_booking": st.session_state.ac_booking,
            "sl_booking": st.session_state.sl_booking,
            "use_gpu": st.session_state.use_gpu,
            "headless_mode": st.session_state.headless_mode,
            "browser_count": st.session_state.browser_count
        },
        "saved_at": datetime.now().isoformat(timespec="seconds")
    }

    if is_booking_run:
        # Save to a single config file for the bot to read
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        st.sidebar.success("Configuration saved. Starting bot...")

        main_script_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
        python_executable = sys.executable # Gets the path to the python interpreter running streamlit

        # This command starts the bot logic in a new process
        # For the PyInstaller .exe, this might need adjustment. The .spec file is configured
        # to bundle main.py, and this Popen call attempts to run it.
        cmd = [python_executable, "-u", main_script_path]
        subprocess.Popen(cmd)

        st.toast(f"Launching {data['run_config']['browser_count']} browser(s) in background...")
    else:
        out_path = make_output_name(st.session_state.travel_date, st.session_state.train_no, from_station_code, to_station_code)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.sidebar.success(f"Details saved to {os.path.basename(out_path)}")

# Corrected save directory to match automation script's expectation
SAVE_DIR_NAME = "Saved_Details"
# Get the directory of the current script, which is 'Form/'
script_dir = os.path.dirname(__file__)
# Create the full path to the save directory, e.g., 'Form/Saved_Details'
SAVE_DIR = os.path.join(script_dir, SAVE_DIR_NAME)
os.makedirs(SAVE_DIR, exist_ok=True)  # Create folder if not exists

def next_available_filename(base_name: str) -> str:
    name, ext = os.path.splitext(base_name)
    # Use the full path for checking existence
    candidate_path = os.path.join(SAVE_DIR, base_name)
    if not os.path.exists(candidate_path):
        return candidate_path
    i = 1
    while True:
        # Use the full path for checking existence
        candidate_path = os.path.join(SAVE_DIR, f"{name}_{i}{ext}")
        if not os.path.exists(candidate_path):
            return candidate_path
        i += 1

def make_output_name(dt: date, train_no: str, from_opt: str, to_opt: str) -> str:
    ddmmyy = dt.strftime("%d%m%y")
    base = f"{ddmmyy}_{train_no}_{from_opt}_{to_opt}.json"
    return next_available_filename(base)

# ---------- Submit ----------
st.sidebar.markdown("---")
book_now_btn = st.sidebar.button("🚀 Book Now", use_container_width=True, type="primary", disabled=not all_filled())
save_for_later_btn = st.sidebar.button("💾 Save Details for Later", use_container_width=True, disabled=not all_filled())

if book_now_btn:
    save_data(is_booking_run=True)

if save_for_later_btn:
    save_data(is_booking_run=False)

# ---------- Live Dashboard Column ----------
# This will appear to the side if there's enough space, or below on mobile.
# A better implementation would use a two-column layout from the start.
st.markdown("---")
st.subheader("Live Bot Status")
dashboard_html = """
    <div id="live-dashboard" style="border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
        <h4>Master Clock</h4>
        <div id="master-time" style="font-family: monospace; font-size: 1.5em; color: lime; background: black; padding: 5px; border-radius: 5px; text-align: center;">--:--:--.---</div>
        <hr>
        <h4>Bot Statuses</h4>
        <div id="bot-statuses" style="font-family: monospace; height: 300px; overflow-y: scroll; background: #f5f5f5; padding: 5px; border: 1px solid #ccc;">Loading...</div>
    </div>

    <script>
        // Ensure this script doesn't run multiple times and create multiple intervals
        if (!window.statusInterval) {
            function updateDashboard() {
                fetch('http://localhost:8000/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('master-time').innerText = data.time || '--:--:--.---';

                        const statusDiv = document.getElementById('bot-statuses');
                        let botHtml = '';
                        if (data.bots && Object.keys(data.bots).length > 0) {
                            for (const bot_id of Object.keys(data.bots).sort()) {
                                botHtml += `<div style="white-space: nowrap;">${data.bots[bot_id]}</div>`;
                            }
                        } else {
                            botHtml = 'No active bots.';
                        }
                        statusDiv.innerHTML = botHtml;
                        // Auto-scroll to bottom
                        statusDiv.scrollTop = statusDiv.scrollHeight;
                    })
                    .catch(error => {
                        // Don't log error continuously, just show a static message
                        const statusDiv = document.getElementById('bot-statuses');
                        if (statusDiv.innerText !== 'Status server offline.') {
                           statusDiv.innerText = 'Status server offline.';
                        }
                    });
            }

            window.statusInterval = setInterval(updateDashboard, 1000);
            updateDashboard(); // Initial call
        }
    </script>
"""
html(dashboard_html, height=450)


# ---------- Footer ----------
st.markdown("<p style='color: navy; font-weight:bold'>Powered by Niladri Ghoshal</p>", unsafe_allow_html=True)