import streamlit as st
import json, os
from datetime import date, datetime, timedelta

# ---------- Styling ----------
st.markdown("""
<style>
.stApp header {background-color: navy !important;}
.stButton>button {background-color: navy; color: white; font-weight:bold;}
.branding {font-size:28px; color: navy; font-weight:bold;}
.delete-btn {margin-top: 27px;}
.warning {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ---------- Branding ----------
st.markdown("<div class='branding'>IRCTC Tatkal Booking Form</div>", unsafe_allow_html=True)
st.markdown("<p style='color: navy; font-weight:bold'>Made by Niladri Ghoshal</p>", unsafe_allow_html=True)

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
username = st.text_input("Username *", placeholder="Enter your IRCTC username")
password = st.text_input("Password *", type="password", placeholder="Enter your IRCTC password", key="pwd")

# ---------- Train Details ----------
st.subheader("Train Details *")

# Line 1: From + To (searchable selectbox)
col1, col2 = st.columns([1,1])
with col1:
    from_station_display = st.selectbox(
        "From Station *",
        options=STATION_DISPLAY_OPTIONS,
        index=0,
        help="Type to search by station code (e.g., BWN) or name",
        placeholder="Select or type to search station"
    )
    from_station = from_station_display.split("(")[-1].split(")")[0] if from_station_display and "(" in from_station_display else ""
with col2:
    to_station_display = st.selectbox(
        "To Station *",
        options=STATION_DISPLAY_OPTIONS,
        index=0,
        help="Type to search by station code (e.g., BWN) or name",
        placeholder="Select or type to search station"
    )
    to_station = to_station_display.split("(")[-1].split(")")[0] if to_station_display and "(" in to_station_display else ""

# Line 2: Date + Train No
col3, col4 = st.columns([1,1])
with col3:
    # Set default to next day
    default_date = date.today() + timedelta(days=1)
    travel_date = st.date_input(
        "Date of Journey *",
        value=default_date,
        min_value=date.today(),
        max_value=date.today() + timedelta(days=60),
        format="DD/MM/YYYY"
    )
with col4:
    train_no = st.text_input("Train Number *", placeholder="Enter train number (e.g., 12301)")

# Line 3: Class + Quota
train_class, quota = st.columns(2)
with train_class:
    train_class_val = st.selectbox("Class *", [""] + [
        "AC 3 Tier (3A)", "AC 3 Economy (3E)", "Sleeper (SL)", "AC 2 Tier (2A)",
        "AC Chair Car (CC)", "Second Sitting (2S)", "First Class (FC)", "Anubhuti Class (EA)",
        "AC First Class (1A)", "Vistadome AC (EV)", "Exec. Chair Car (EC)", "Vistadome Chair Car (VC)",
        "Vistadome Non AC (VS)", "GENERAL"
    ], placeholder="Select travel class")
with quota:
    quota_val = st.selectbox("Quota *", [""] + [
        "TATKAL", "PREMIUM TATKAL", "GENERAL", "LADIES",
        "LOWER BERTH/SR.CITIZEN", "PERSON WITH DISABILITY", "DUTY PASS"
    ], placeholder="Select quota type")

# ---------- Dynamic Passengers ----------
st.subheader("Passenger Details *")

def add_passenger():
    if len(st.session_state.passengers) < 6:
        st.session_state.passengers.append({"name":"", "age": None, "sex": "", "nationality":"Indian", "berth":""})

def delete_passenger(idx):
    if 0 <= idx < len(st.session_state.passengers):
        st.session_state.passengers.pop(idx)
        st.rerun()

for idx, passenger in enumerate(st.session_state.passengers):
    st.markdown(f"### Passenger {idx+1}")

    # Row 1: Name + Age
    row1 = st.columns([3,1])
    passenger["name"] = row1[0].text_input(
        "Name *", max_chars=16, placeholder="Enter passenger name", key=f"name{idx}"
    )
    
    # Age input with blank default
    passenger["age"] = row1[1].number_input(
        "Age *", min_value=1, max_value=99,
        value=None,
        placeholder="Age",
        step=1, key=f"age{idx}"
    )

    # Row 2: Sex + Nationality + Berth + Delete (aligned properly)
    row2 = st.columns([2,2,3,1])
    passenger["sex"] = row2[0].selectbox(
        "Sex *", ["", "Male", "Female", "Transgender"], 
        key=f"sex{idx}", placeholder="Select gender"
    )
    passenger["nationality"] = row2[1].text_input(
        "Nationality *", value=passenger["nationality"], 
        key=f"nat{idx}", placeholder="Enter nationality"
    )
    passenger["berth"] = row2[2].selectbox(
        "Preferred Berth *",
        ["", "No Preference","Lower","Middle","Upper","Side Lower","Side Upper"],
        key=f"berth{idx}", placeholder="Select berth preference"
    )
    
    # Delete button with proper alignment
    with row2[3]:
        if len(st.session_state.passengers) > 1:
            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
            if st.button("🗑️", key=f"del{idx}"):
                delete_passenger(idx)
            st.markdown('</div>', unsafe_allow_html=True)

if len(st.session_state.passengers) < 6:
    st.button("Add Passenger", on_click=add_passenger)

# ---------- Contact Details ----------
st.subheader("Contact Details *")
mobile_number = st.text_input("Mobile Number *", placeholder="Enter 10-digit mobile number to get ticket details", max_chars=10)

# ---------- Booking Preferences ----------
st.subheader("Booking Preferences *")
auto_upgrade = st.checkbox("Consider for Auto Upgradation", value=True)
confirm_only = st.checkbox("Book Only Confirm Berth is Alloted", value=True)

# Payment method with radio buttons
st.subheader("Payment Method *")
payment_method = st.radio(
    "Select payment method:",
    ["Pay through BHIM UPI", "Pay through IRCTC Wallet"],
    index=0,
    horizontal=True
)

if payment_method == "Pay through BHIM UPI":
    upi_id = st.text_input("UPI ID *", placeholder="Enter your UPI ID (e.g., name@upi)")
else:
    st.markdown('<p class="warning">Make sure you have at least 100 rupees extra in wallet than the tatkal fare.</p>', unsafe_allow_html=True)
    upi_id = ""  # Clear UPI ID if not using UPI

# ---------- Helpers ----------
def all_filled():
    if not all([username, password, from_station, to_station, train_no, train_class_val, quota_val, mobile_number]):
        return False
    for p in st.session_state.passengers:
        if not p["name"] or p["age"] is None or not p["sex"] or not p["nationality"] or not p["berth"]:
            return False
    if payment_method == "Pay through BHIM UPI" and not upi_id:
        return False
    return True

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
if st.button("Save Booking Details"):
    if not all_filled():
        st.error("All fields marked * are required.")
    else:
        data = {
            "login": {"username": username, "password": password},
            "contact": {"mobile_number": mobile_number},
            "train": {
                "from_station": from_station,
                "to_station": to_station,
                "date": travel_date.strftime("%d%m%Y"),
                "train_no": train_no,
                "class": train_class_val,
                "quota": quota_val
            },
            "passengers": st.session_state.passengers,
            "preferences": {
                "auto_upgrade": auto_upgrade,
                "confirm_only": confirm_only,
                "payment_method": payment_method,
                "upi_id": upi_id if payment_method == "Pay through BHIM UPI" else ""
            },
            "saved_at": datetime.now().isoformat(timespec="seconds")
        }
        out_path = make_output_name(travel_date, train_no, from_station, to_station)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.success(f"Booking details saved to {out_path}")
        st.json(data)

# ---------- Footer ----------
st.markdown("<p style='color: navy; font-weight:bold'>Powered by Niladri Ghoshal</p>", unsafe_allow_html=True)