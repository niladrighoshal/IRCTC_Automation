import streamlit as st
import sys
import os

# This needs to be imported from the new location
from src.ui.app import run_app

def main():
    """
    Main function to run the application.
    """
    # Adjust CWD for PyInstaller
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)

    run_app()

if __name__ == "__main__":
    main()
