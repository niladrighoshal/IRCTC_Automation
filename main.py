import streamlit as st
from src.ui.app import run_app
import os
import sys

def main():
    """
    Main function to run the IRCTC Booking Bot application.
    """
    # When running as a PyInstaller executable, the CWD needs to be adjusted.
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)

    run_app()

if __name__ == "__main__":
    main()
