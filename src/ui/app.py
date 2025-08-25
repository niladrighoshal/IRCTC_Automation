import streamlit as st
import json, os, re, sys, subprocess
from datetime import date, datetime, timedelta

# Selenium imports are moved into the functions that use them to speed up UI loading.

# ---------- Directories ----------
BASE_DIR = os.getcwd()
SAVE_DIR = os.path.join(BASE_DIR, "saved_details")
LOGIN_DIR = os.path.join(BASE_DIR, "saved_logins")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(LOGIN_DIR, exist_ok=True)
LOGIN_FILE = os.path.join(LOGIN_DIR, "user_credentials.json")

# ---------- Styling & Branding ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to bottom, #e0f7fa, #80deea);
    background-attachment: fixed;
}
.stApp header {background-color: navy !important;}
.stButton>button {background-color: navy; color: white; font-weight:bold;}
.branding {font-size:28px; color: navy; font-weight:bold;}
.delete-btn {margin-top: 27px;}
.sidebar-scroll {max-height: 320px; overflow-y: auto;}
.file-row {display:flex; justify-content:space-between; align-items:center;}
.file-name {font-size:14px; margin-right:8px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='branding'>IRCTC Tatkal Booking Form</div>", unsafe_allow_html=True)
st.markdown("<p style='color: navy; font-weight:bold'>Made by Niladri Ghoshal</p>", unsafe_allow_html=True)

# ---------- Load station list ----------
with open("src/ui/railwayStationsList.json", "r", encoding="utf-8") as f:
    stations_data = json.load(f)["stations"]

STATION_OPTIONS = []
for station in stations_data:
    code = station['stnCode'].upper()
    name = station['stnName']
    display_text = f"{name} ({code})"
    search_text = f"{code} {name}".lower()
    STATION_OPTIONS.append({"display": display_text, "search": search_text, "code": code})

STATION_OPTIONS.sort(key=lambda x: x["code"])
STATION_DISPLAY_OPTIONS = [""] + [s["display"] for s in STATION_OPTIONS]

# ---------- Session defaults ----------
st.session_state.setdefault("passengers", [{"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""}])
st.session_state.setdefault("loaded_file", None)

# ---------- If a load request exists from previous run, apply BEFORE widget creation ----------
if "_loaded_data" in st.session_state:
    _ld = st.session_state.pop("_loaded_data")
    data = _ld.get("data", {})
    filename = _ld.get("filename")
    train = data.get("train", {})
    # apply defaults so later widgets pick them up
    st.session_state["from_station_display"] = train.get("from_input", "")
    st.session_state["to_station_display"] = train.get("to_input", "")
    try:
        st.session_state["travel_date"] = datetime.strptime(train.get("date",""), "%d%m%Y").date()
    except Exception:
        st.session_state["travel_date"] = date.today() + timedelta(days=1)
    st.session_state["train_no_input"] = train.get("train_no", "")
    st.session_state["train_name"] = train.get("train_name", "")
    st.session_state["train_class_val"] = train.get("class", "")
    st.session_state["quota_val"] = train.get("quota", "")
    st.session_state["passengers"] = data.get("passengers", [{"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""}])
    st.session_state["phone_no"] = data.get("contact", {}).get("phone", "")
    prefs = data.get("preferences", {})
    st.session_state["auto_upgrade"] = prefs.get("auto_upgrade", True)
    st.session_state["confirm_only"] = prefs.get("confirm_only", True)
    st.session_state["payment_method"] = prefs.get("payment", "Pay through BHIM UPI")
    st.session_state["upi_id"] = prefs.get("upi_id", "")
    st.session_state["timed"] = prefs.get("timed", False)
    st.session_state["ac_toggle"] = prefs.get("ac", False)
    st.session_state["sl_toggle"] = prefs.get("sl", False)
    st.session_state["ocr_cpu"] = prefs.get("ocr_cpu", True)
    st.session_state["headless"] = prefs.get("headless", False)
    st.session_state["browser_count"] = prefs.get("browser_count", 1)
    st.session_state["loaded_file"] = filename

# ---------- Sidebar: Bot Controls ----------
st.sidebar.header("Bot Controls")
timed = st.sidebar.checkbox("TIMED", value=st.session_state.get("timed", False), key="timed")
ac_toggle = sl_toggle = False
if timed:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        ac_toggle = st.sidebar.checkbox("AC", value=st.session_state.get("ac_toggle", False), key="ac_toggle")
    with col2:
        sl_toggle = st.sidebar.checkbox("SL", value=st.session_state.get("sl_toggle", False), key="sl_toggle")

# ensure ocr_cpu default exists before widget creation
st.session_state.setdefault("ocr_cpu", True)
ocr_cpu = st.sidebar.checkbox("OCR CPU", value=st.session_state["ocr_cpu"], key="ocr_cpu")

st.session_state.setdefault("headless", False)
headless = st.sidebar.checkbox("HEADLESS", value=st.session_state["headless"], key="headless")

# ensure browser_count default before slider
st.session_state.setdefault("browser_count", 1)
browser_count = st.sidebar.slider("Browser Count", min_value=1, max_value=(8 if not headless else 24), value=st.session_state["browser_count"], key="browser_count")

# ---------- Sidebar: Saved details list with ↪ and 🗑 ----------
st.sidebar.subheader("Saved Booking Files")
saved_files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith(".json")], reverse=True)
with st.sidebar:
    st.markdown('<div class="sidebar-scroll">', unsafe_allow_html=True)
    for sf in saved_files:
        cols = st.columns([0.65, 0.15, 0.2])
        cols[0].markdown(f"<div class='file-name'>{sf}</div>", unsafe_allow_html=True)
        if cols[1].button("↪", key=f"load_{sf}"):
            with open(os.path.join(SAVE_DIR, sf), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # store loaded data for next run (so assignment happens before widgets)
            st.session_state["_loaded_data"] = {"data": data, "filename": sf}
            st.rerun()
        if cols[2].button("🗑", key=f"del_{sf}"):
            os.remove(os.path.join(SAVE_DIR, sf))
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Sidebar: User Credentials (multi-browser) ----------
st.sidebar.subheader("User Credentials")
saved_logins = []
if os.path.exists(LOGIN_FILE):
    try:
        with open(LOGIN_FILE, "r", encoding="utf-8") as fh:
            saved_logins = json.load(fh)
    except Exception:
        saved_logins = []

# ensure session_state.logins length matches browser_count
if "logins" not in st.session_state:
    st.session_state.logins = [{} for _ in range(browser_count)]
elif len(st.session_state.logins) < browser_count:
    st.session_state.logins.extend({} for _ in range(browser_count - len(st.session_state.logins)))
elif len(st.session_state.logins) > browser_count:
    st.session_state.logins = st.session_state.logins[:browser_count]

for i in range(browser_count):
    if i < len(saved_logins) and not st.session_state.logins[i]:
        st.session_state.logins[i] = saved_logins[i]

for i in range(browser_count):
    with st.sidebar.expander(f"Browser {i+1} Login", expanded=False):
        u = st.text_input("Username", value=st.session_state.logins[i].get("username",""), key=f"uname{i}")
        p = st.text_input("Password", value=st.session_state.logins[i].get("password",""), type="password", key=f"pwd{i}")
        st.session_state.logins[i] = {"username": u, "password": p}

if st.sidebar.button("Save Credentials"):
    with open(LOGIN_FILE, "w", encoding="utf-8") as fh:
        json.dump(st.session_state.logins, fh, indent=2, ensure_ascii=False)
    st.sidebar.success("Saved credentials to saved_logins/user_credentials.json")

# ---------- Selenium for train name ----------
def init_driver():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return uc.Chrome(options=options)

if "driver" not in st.session_state:
    try:
        st.session_state.driver = init_driver()
    except Exception:
        st.session_state.driver = None

def cb_fetch_train_name():
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    tn = st.session_state.get("train_no_input","")
    if tn and tn.isdigit() and st.session_state.get("driver"):
        try:
            url = f"https://www.railyatri.in/time-table/{tn}"
            d = st.session_state.driver
            d.get(url)
            heading = WebDriverWait(d, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.timetable_lts_timeline_title__7Patt h1"))
            )
            text = heading.text.strip()
            m = re.match(r"(.+?\(\d+\))", text)
            st.session_state["train_name"] = (m.group(1).strip() if m else text.replace("Train Time Table","").strip())
        except Exception:
            st.session_state["train_name"] = "Error fetching train name."

# ---------- Helper callbacks ----------
def cb_titlecase(idx_field):
    # idx_field format "name{idx}"
    key = idx_field
    val = st.session_state.get(key, "")
    st.session_state[key] = " ".join(w.capitalize() for w in val.split())
    # update passenger list entry
    m = re.match(r'([a-zA-Z_]*?)(\d+)$', key)
    if m:
        prefix, idx = m.group(1), int(m.group(2))
        field = prefix.rstrip(''.join('0123456789'))
        # we used 'name{idx}', so set passengers[idx]['name']
        if 0 <= idx < len(st.session_state.passengers):
            st.session_state.passengers[idx]["name"] = st.session_state[key]

def cb_age(idx_field):
    key = idx_field
    val = st.session_state.get(key, "")
    digits = re.sub(r"\D", "", val)
    if digits == "":
        st.session_state[key] = ""
        parsed = None
    else:
        n = int(digits)
        if n < 1: n = 1
        if n > 99: n = 99
        st.session_state[key] = str(n)
        parsed = n
    # update passenger dict
    m = re.match(r'age(\d+)$', key)
    if m:
        idx = int(m.group(1))
        if 0 <= idx < len(st.session_state.passengers):
            st.session_state.passengers[idx]["age"] = parsed

def cb_phone(key):
    val = st.session_state.get(key, "")
    digits = re.sub(r"\D", "", val)
    if len(digits) > 10:
        digits = digits[-10:]
    st.session_state[key] = digits
    st.session_state["phone_no"] = digits

# ---------- Main form ----------
st.subheader("Train Details *")

# From + To (selectbox from JSON)
col1, col2 = st.columns([1,1])
with col1:
    default_from = st.session_state.get("from_station_display", STATION_DISPLAY_OPTIONS[0])
    try:
        idx = STATION_DISPLAY_OPTIONS.index(default_from) if default_from in STATION_DISPLAY_OPTIONS else 0
    except Exception:
        idx = 0
    from_station_display = st.selectbox("From Station *", options=STATION_DISPLAY_OPTIONS, index=idx, key="from_station_display")
    from_station = from_station_display.split("(")[-1].split(")")[0] if "(" in from_station_display else ""
with col2:
    default_to = st.session_state.get("to_station_display", STATION_DISPLAY_OPTIONS[0])
    try:
        idx2 = STATION_DISPLAY_OPTIONS.index(default_to) if default_to in STATION_DISPLAY_OPTIONS else 0
    except Exception:
        idx2 = 0
    to_station_display = st.selectbox("To Station *", options=STATION_DISPLAY_OPTIONS, index=idx2, key="to_station_display")
    to_station = to_station_display.split("(")[-1].split(")")[0] if "(" in to_station_display else ""

# Date + Train No
col3, col4 = st.columns(2)
with col3:
    default_date = st.session_state.get("travel_date", date.today() + timedelta(days=1))
    travel_date = st.date_input("Date of Journey *", value=default_date, min_value=date.today(), max_value=date.today()+timedelta(days=60), format="DD/MM/YYYY", key="travel_date")
with col4:
    default_train_no = st.session_state.get("train_no_input", "")
    st.text_input("Train Number *", value=default_train_no, key="train_no_input", placeholder="e.g., 12301", on_change=cb_fetch_train_name)
    train_no = st.session_state.get("train_no_input", "")

train_name_display = st.session_state.get("train_name", "")
if train_name_display:
    st.success(f"Selected Train: {train_name_display}")

# Class + Quota
train_class_choices = ["", "AC 3 Tier (3A)", "AC 3 Economy (3E)", "Sleeper (SL)", "AC 2 Tier (2A)",
    "AC Chair Car (CC)", "Second Sitting (2S)", "First Class (FC)", "Anubhuti Class (EA)",
    "AC First Class (1A)", "Vistadome AC (EV)", "Exec. Chair Car (EC)", "Vistadome Chair Car (VC)",
    "Vistadome Non AC (VS)", "GENERAL"]
default_class = st.session_state.get("train_class_val", "")
train_class, quota = st.columns(2)
with train_class:
    train_class_val = st.selectbox("Class *", train_class_choices, index=(train_class_choices.index(default_class) if default_class in train_class_choices else 0), key="train_class_val")
with quota:
    quota_choices = ["", "TATKAL", "PREMIUM TATKAL", "GENERAL", "LADIES", "LOWER BERTH/SR.CITIZEN", "PERSON WITH DISABILITY", "DUTY PASS"]
    default_quota = st.session_state.get("quota_val", "")
    quota_val = st.selectbox("Quota *", quota_choices, index=(quota_choices.index(default_quota) if default_quota in quota_choices else 0), key="quota_val")

# ---------- Passenger Details ----------
st.subheader("Passenger Details *")

# Ensure widget keys exist for each passenger before rendering
for idx, p in enumerate(st.session_state.passengers):
    st.session_state.setdefault(f"name{idx}", p.get("name",""))
    st.session_state.setdefault(f"age{idx}", "" if p.get("age") is None else str(p.get("age")))
    st.session_state.setdefault(f"sex{idx}", p.get("sex",""))
    st.session_state.setdefault(f"nat{idx}", p.get("nationality","Indian"))
    st.session_state.setdefault(f"berth{idx}", p.get("berth",""))

def add_passenger():
    if len(st.session_state.passengers) < 6:
        st.session_state.passengers.append({"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""})
        st.rerun()

def delete_passenger(idx):
    if "passengers" in st.session_state and 0 <= idx < len(st.session_state.passengers):
        st.session_state.passengers.pop(idx)
        # also remove associated widget keys if present
        for k in [f"name{idx}", f"age{idx}", f"sex{idx}", f"nat{idx}", f"berth{idx}"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

for idx, passenger in enumerate(st.session_state.passengers):
    st.markdown(f"### Passenger {idx+1}")
    row1 = st.columns([3,1])
    # Name: titlecase on Enter (on_change)
    row1[0].text_input("Name *", value=st.session_state.get(f"name{idx}",""), max_chars=16, key=f"name{idx}", on_change=cb_titlecase, args=(f"name{idx}",))
    # Age: use text_input with placeholder instead of number_input default
    row1[1].text_input("Age *", value=st.session_state.get(f"age{idx}",""), placeholder="Enter age (1-99)", key=f"age{idx}", on_change=cb_age, args=(f"age{idx}",))
    row2 = st.columns([2,2,3,1])
    # Sex and nationality and berth: update passenger dict after widget change by reading keys
    sex_val = row2[0].selectbox("Sex *", ["", "Male", "Female", "Transgender"], index=(["", "Male", "Female", "Transgender"].index(st.session_state.get(f"sex{idx}","")) if st.session_state.get(f"sex{idx}","") in ["", "Male", "Female", "Transgender"] else 0), key=f"sex{idx}")
    nat_val = row2[1].text_input("Nationality *", value=st.session_state.get(f"nat{idx}","Indian"), key=f"nat{idx}")
    berth_val = row2[2].selectbox("Preferred Berth *", ["", "No Preference","Lower","Middle","Upper","Side Lower","Side Upper"], index=(["", "No Preference","Lower","Middle","Upper","Side Lower","Side Upper"].index(st.session_state.get(f"berth{idx}","")) if st.session_state.get(f"berth{idx}","") in ["", "No Preference","Lower","Middle","Upper","Side Lower","Side Upper"] else 0), key=f"berth{idx}")
    # sync back into passenger dict
    # Name and age were already synced by callbacks cb_titlecase/cb_age
    # Ensure passenger dict exists at idx
    if 0 <= idx < len(st.session_state.passengers):
        st.session_state.passengers[idx]["sex"] = sex_val
        st.session_state.passengers[idx]["nationality"] = nat_val
        st.session_state.passengers[idx]["berth"] = berth_val
        # also update name/age from widget keys if not already
        name_k = st.session_state.get(f"name{idx}", "")
        age_k = st.session_state.get(f"age{idx}", "")
        st.session_state.passengers[idx]["name"] = " ".join(w.capitalize() for w in name_k.split()) if name_k else ""
        st.session_state.passengers[idx]["age"] = (int(re.sub(r"\D","", age_k)) if age_k and re.sub(r"\D","", age_k) else None)

    with row2[3]:
        if len(st.session_state.passengers) > 1:
            if st.button("🗑️", key=f"del{idx}"):
                delete_passenger(idx)

# --- Add Passenger Button with Quota Logic ---
max_passengers = 4 if quota_val in ["TATKAL", "PREMIUM TATKAL"] else 6

# Display a warning if the current number of passengers exceeds the limit for the selected quota.
if len(st.session_state.passengers) > max_passengers:
    st.warning(f"⚠️ {quota_val} quota allows a maximum of {max_passengers} passengers. Please remove the extra passenger(s).")

# Display the "Add Passenger" button only if below the max limit.
if len(st.session_state.passengers) < max_passengers:
    if st.button("Add Passenger"):
        add_passenger()
else:
    # Inform the user that they have reached the maximum limit.
    st.info(f"Maximum of {max_passengers} passengers reached for {quota_val} quota.")

# ---------- Contact Details ----------
st.subheader("Contact Details *")
# phone with normalization on change
st.text_input("Mobile Number *", value=st.session_state.get("phone_no",""), placeholder="Enter 10-digit phone number", key="phone_no", on_change=cb_phone, args=("phone_no",))
phone_no = st.session_state.get("phone_no","")
if phone_no:
    if not phone_no.isdigit() or len(phone_no) != 10:
        st.error("Phone number must be exactly 10 digits. Non-digits removed. If you pasted +91..., last 10 digits are used.")
    else:
        st.success("Phone validated.")

# ---------- Booking Preferences ----------
st.subheader("Booking Preferences *")
auto_upgrade = st.checkbox("Consider for Auto Upgradation", value=st.session_state.get("auto_upgrade", True), key="auto_upgrade")
confirm_only = st.checkbox("Book Only Confirm Berth is Alloted", value=st.session_state.get("confirm_only", True), key="confirm_only")

# ---------- Payment Method ----------
st.subheader("Payment Method *")
payment_method = st.radio("Select payment method:", ["Pay through BHIM UPI", "Pay through IRCTC Wallet"], index=(0 if st.session_state.get("payment_method","Pay through BHIM UPI")== "Pay through BHIM UPI" else 1), key="payment_method", horizontal=True)
upi_id = st.text_input("UPI ID *", value=st.session_state.get("upi_id",""), placeholder="name@upi", key="upi_id") if payment_method=="Pay through BHIM UPI" else ""

# ---------- Save / Clear Buttons ----------
col_save = st.columns([1,1,1])
with col_save[0]:
    if st.button("Save Travel Details"):
        # validate required fields
        if not from_station or not to_station:
            st.error("From and To stations required.")
        elif not train_no:
            st.error("Train number required.")
        elif not train_class_val or not quota_val:
            st.error("Class and Quota required.")
        elif not phone_no or not phone_no.isdigit() or len(phone_no) != 10:
            st.error("Valid 10-digit phone required.")
        else:
            booking_data = {
                "train": {
                    "from_input": st.session_state.get("from_station_display",""),
                    "from_code": from_station,
                    "to_input": st.session_state.get("to_station_display",""),
                    "to_code": to_station,
                    "date": travel_date.strftime("%d%m%Y"),
                    "train_no": st.session_state.get("train_no_input",""),
                    "train_name": st.session_state.get("train_name",""),
                    "class": st.session_state.get("train_class_val", train_class_val),
                    "quota": st.session_state.get("quota_val", quota_val)
                },
                "passengers": st.session_state.passengers,
                "contact": {"phone": st.session_state.get("phone_no","")},
                "preferences": {
                    "auto_upgrade": st.session_state.get("auto_upgrade", True),
                    "confirm_only": st.session_state.get("confirm_only", True),
                    "payment": st.session_state.get("payment_method", payment_method),
                    "upi_id": st.session_state.get("upi_id", ""),
                    "timed": st.session_state.get("timed", timed),
                    "ac": st.session_state.get("ac_toggle", ac_toggle),
                    "sl": st.session_state.get("sl_toggle", sl_toggle),
                    "ocr_cpu": st.session_state.get("ocr_cpu", ocr_cpu),
                    "headless": st.session_state.get("headless", headless),
                    "browser_count": st.session_state.get("browser_count", browser_count)
                },
                "saved_at": datetime.now().isoformat(timespec="seconds")
            }
            if st.session_state.get("loaded_file"):
                out_path = os.path.join(SAVE_DIR, st.session_state.loaded_file)
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(booking_data, fh, indent=2, ensure_ascii=False)
                st.success(f"Overwrote {st.session_state.loaded_file}")
            else:
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_booking.json"
                out_path = os.path.join(SAVE_DIR, filename)
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(booking_data, fh, indent=2, ensure_ascii=False)
                st.success(f"Saved {filename}")
                st.session_state.loaded_file = filename
            st.rerun()

with col_save[1]:
    # Save credentials only in sidebar (already implemented). Do not show here.
    st.write("")

with col_save[2]:
    if st.button("Clear Loaded File"):
        st.session_state.loaded_file = None
        st.success("Cleared loaded file (new Save will create a new file)")
        st.rerun()

# ---------- Start BOT (sidebar) ----------
if st.sidebar.button("Start BOT", use_container_width=True):
    # First, ensure the latest details are saved, so the bot uses the most recent info.
    # This re-uses the validation and save logic from the main "Save" button.
    required_ok = all([
        from_station, to_station, st.session_state.get("train_no_input",""),
        st.session_state.get("train_class_val", ""), st.session_state.get("quota_val", ""),
        st.session_state.get("phone_no","") and st.session_state.get("phone_no","").isdigit() and len(st.session_state.get("phone_no",""))==10
    ])

    if not required_ok:
        st.sidebar.error("Please fill all required (*) fields with valid values before starting the bot.")
    else:
        # --- Save the current state to a file ---
        # This block is similar to the main "Save" button logic
        booking_data = {
            "train": {
                "from_input": st.session_state.get("from_station_display",""), "from_code": from_station,
                "to_input": st.session_state.get("to_station_display",""), "to_code": to_station,
                "date": travel_date.strftime("%d%m%Y"), "train_no": st.session_state.get("train_no_input",""),
                "train_name": st.session_state.get("train_name",""), "class": st.session_state.get("train_class_val", train_class_val),
                "quota": st.session_state.get("quota_val", quota_val)
            },
            "passengers": st.session_state.passengers,
            "contact": {"phone": st.session_state.get("phone_no","")},
            "logins": st.session_state.get("logins", []),
            "preferences": {
                "auto_upgrade": st.session_state.get("auto_upgrade", True), "confirm_only": st.session_state.get("confirm_only", True),
                "payment": st.session_state.get("payment_method", payment_method), "upi_id": st.session_state.get("upi_id", ""),
                "timed": st.session_state.get("timed", timed), "ac": st.session_state.get("ac_toggle", ac_toggle),
                "sl": st.session_state.get("sl_toggle", sl_toggle), "ocr_cpu": st.session_state.get("ocr_cpu", ocr_cpu),
                "headless": st.session_state.get("headless", headless), "browser_count": st.session_state.get("browser_count", browser_count)
            },
            "saved_at": datetime.now().isoformat(timespec="seconds")
        }
        # Always save to a consistent filename for the bot to pick up, overwriting the latest.
        # The `run_bot.py` script is designed to find the latest file, but saving to a consistent
        # name like 'latest_run.json' can also be a robust strategy. We'll stick to the
        # "latest by timestamp" strategy for now.
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_booking.json"
        out_path = os.path.join(SAVE_DIR, filename)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(booking_data, fh, indent=2, ensure_ascii=False)
        st.sidebar.info(f"Saved current settings to {filename}")

        # --- Launch the bot script as a background process ---
        try:
            bot_script_path = os.path.join(BASE_DIR, 'run_bot.py')
            # Use sys.executable to ensure it runs with the same python interpreter
            subprocess.Popen([sys.executable, bot_script_path])
            st.sidebar.success("✅ Bot started in the background! Monitor 'irctc_booking_log.xlsx' for progress.")
        except FileNotFoundError:
            st.sidebar.error("Error: 'run_bot.py' not found. Cannot start the bot.")
        except Exception as e:
            st.sidebar.error(f"An error occurred while starting the bot: {e}")

# ---------- Footer ----------
st.markdown("<p style='color: navy; font-weight:bold'>Powered by Niladri Ghoshal</p>", unsafe_allow_html=True)
