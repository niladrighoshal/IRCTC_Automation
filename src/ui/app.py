import streamlit as st
import os
import json

def run_app():
    # --- Setup Directories & Files to prevent crashes ---
    os.makedirs("saved_details", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    if not os.path.exists("credentials.json"):
        with open("credentials.json", "w") as f:
            json.dump([], f)

    # --- UI ---
    st.set_page_config(layout="wide", page_title="IRCTC Bot")
    st.markdown("<div class='branding'>IRCTC Tatkal Booking Form</div>", unsafe_allow_html=True)

    # --- Load station list ---
    with open("src/ui/railwayStationsList.json", "r", encoding="utf-8") as f:
        stations_data = json.load(f)["stations"]
    STATION_DISPLAY_OPTIONS = [""] + [f"{s['stnName']} ({s['stnCode']})" for s in stations_data]

    if "passengers" not in st.session_state:
        st.session_state.passengers = [{"name":"", "age": None, "sex": ""}]

    st.subheader("Train Details *")
    c1, c2 = st.columns(2)
    c1.selectbox("From Station *", options=STATION_DISPLAY_OPTIONS)
    c2.selectbox("To Station *", options=STATION_DISPLAY_OPTIONS)

    st.subheader("Passenger Details *")
    st.info("Passenger form will be implemented here.")

    if st.button("Save Booking Details"):
        st.info("Save logic to be implemented.")

if __name__ == "__main__":
    run_app()
