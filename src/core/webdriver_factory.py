import undetected_chromedriver as uc
import sys
import os
import random

def create_webdriver(instance_id, is_headless=False, use_gpu=True):
    """
    Creates a webdriver instance with a unique, persistent profile for each bot.
    """
    options = uc.ChromeOptions()

    # --- Base Options ---
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # --- Paths ---
    # Use the user-provided Chromium path.
    chromium_path = r"C:\Users\Niladri_Ghoshal\AppData\Local\Chromium\Application\chrome.exe"

    # --- Scalable, Persistent Profile Creation ---
    base_profile_dir = os.path.join(os.getcwd(), "chromeprofile")
    os.makedirs(base_profile_dir, exist_ok=True)
    profile_path = os.path.join(base_profile_dir, str(instance_id))
    os.makedirs(profile_path, exist_ok=True)

    # Set the binary location if the executable exists.
    if os.path.exists(chromium_path):
        options.binary_location = chromium_path
    else:
        print(f"[WebDriverFactory] WARNING: Chromium not found at '{chromium_path}'. Relying on default path.")

    # Always use the dedicated profile path.
    options.add_argument(f"--user-data-dir={profile_path}")
    print(f"[WebDriverFactory] Using persistent profile for instance {instance_id}: {profile_path}")

    try:
        # Force driver version 109 to match the user's browser and prevent crashes.
        driver = uc.Chrome(options=options, version_main=109)
        return driver

    except Exception as e:
        print(f"Error creating undetected WebDriver for instance {instance_id}: {e}")
        return None
