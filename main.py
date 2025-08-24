import streamlit as st
from src.ui.app import run as run_app

def main():
    """
    Main function to run the IRCTC Booking Bot application.
    This launches the Streamlit UI, which serves as the control panel.
    """
    run_app()

if __name__ == "__main__":
    # To run the application:
    # 1. Make sure you have all dependencies installed (e.g., streamlit, selenium).
    # 2. Open your terminal in the project root directory.
    # 3. Run the command: streamlit run main.py
    main()
