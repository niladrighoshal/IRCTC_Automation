import undetected_chromedriver as uc
import sys
import os
import random

# List of common, recent user-agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def create_webdriver(instance_id, is_headless=False, use_gpu=True):
    """
    Creates a webdriver instance based on the user's proven-working configuration.
    This uses a single, persistent user profile to appear more human.
    """
    options = uc.ChromeOptions()

    # --- Base Options from User's Working Code ---
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # --- Paths from User's Working Code ---
    # Using a single, persistent profile is key to avoiding bot detection.
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    profile_path = r"G:\Project\IRCTC_BOT_GOOGLE\BraveProfile"

    if os.path.exists(brave_path):
        options.binary_location = brave_path
    else:
        print(f"[WebDriverFactory] WARNING: Brave browser not found at '{brave_path}'. Relying on default.")

    # Always use the same profile path.
    options.add_argument(f"--user-data-dir={profile_path}")
    print(f"[WebDriverFactory] Using persistent profile path: {profile_path}")

    try:
        # We force the driver version to 109 to match the user's last known working setup.
        # This avoids the `session not created` error.
        driver = uc.Chrome(options=options, version_main=109)
        return driver

    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        return None
