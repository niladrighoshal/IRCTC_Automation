import os
import sys
import glob
import json
from src.core.bot_runner import BotRunner

# --- Constants ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "saved_details")

def find_latest_booking_file():
    """Finds the most recently created .json file in the saved_details directory."""
    if not os.path.isdir(SAVE_DIR):
        print(f"Error: The directory '{SAVE_DIR}' does not exist. Please save a booking from the UI first.")
        return None

    list_of_files = glob.glob(os.path.join(SAVE_DIR, '*.json'))
    if not list_of_files:
        print(f"Error: No booking files found in '{SAVE_DIR}'. Please save a booking from the UI first.")
        return None

    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def main():
    """
    Main function to find the latest booking config and run the bot.
    """
    print("--- IRCTC Bot Backend ---")

    # Add src to python path to allow for absolute imports
    sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

    config_file = find_latest_booking_file()

    if not config_file:
        sys.exit(1)

    print(f"[*] Using configuration from: {os.path.basename(config_file)}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    try:
        runner = BotRunner(config)
        runner.start()
        print("[*] Bot run finished.")
    except Exception as e:
        print(f"\n[FATAL] An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        print("[*] Script finished.")

if __name__ == "__main__":
    main()
