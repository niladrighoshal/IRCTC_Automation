import undetected_chromedriver as uc
import sys
import os
import random

# List of common, recent user-agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def create_webdriver(instance_id, is_headless=False, use_gpu=True):
    """
    Creates a webdriver instance with a unique, persistent profile for each bot,
    based on the user's proven-working configuration.
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
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

    # --- Scalable, Persistent Profile Creation ---
    # Create a master profile directory if it doesn't exist
    base_profile_dir = os.path.join(os.getcwd(), "BraveProfile")
    os.makedirs(base_profile_dir, exist_ok=True)

    # Create a path for the specific bot instance (e.g., BraveProfile/bot_1)
    profile_path = os.path.join(base_profile_dir, f"bot_{instance_id}")
    os.makedirs(profile_path, exist_ok=True) # This ensures the profile is created if new, or reused if it exists

    if os.path.exists(brave_path):
        options.binary_location = brave_path
    else:
        print(f"[WebDriverFactory] WARNING: Brave browser not found at '{brave_path}'. Relying on default.")

    options.add_argument(f"--user-data-dir={profile_path}")
    print(f"[WebDriverFactory] Using persistent profile for instance {instance_id}: {profile_path}")

    try:
        # Force driver version 109 to match the user's browser and prevent crashes.
        driver = uc.Chrome(options=options, version_main=109)
        return driver

    except Exception as e:
        print(f"Error creating undetected WebDriver for instance {instance_id}: {e}")
        return None
