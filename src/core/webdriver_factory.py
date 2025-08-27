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
    options = uc.ChromeOptions()

    if is_headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    if not use_gpu:
        options.add_argument("--disable-gpu")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # Select a random user-agent for each browser instance
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")

    # --- Options based on user's proven working code ---
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")

    # This is a standard stealth flag that is safe to keep.
    options.add_argument('--disable-blink-features=AutomationControlled')

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    browser_path = None

    if sys.platform == "win32":
        # User-provided path for Windows and Chromium
        chromium_path = r"C:\Users\Niladri_Ghoshal\AppData\Local\Chromium\Application\chrome.exe"

        # Create a unique, persistent profile for each bot instance.
        base_profile_path = os.path.join(os.getcwd(), "chromium_profiles")
        profile_path = os.path.join(base_profile_path, f"bot_{instance_id}")

        os.makedirs(profile_path, exist_ok=True)
        print(f"[WebDriverFactory] Using profile path: {profile_path}")
        options.add_argument(f'--user-data-dir={profile_path}')

        if os.path.exists(chromium_path):
            browser_path = chromium_path
        else:
            print(f"[WebDriverFactory] Chromium not found at specified path: {chromium_path}. Falling back to default.")

    elif sys.platform == "linux":
        # Path discovered during smoke testing in the cloud environment
        linux_path = "/home/jules/.cache/ms-playwright/chromium-1181/chrome-linux/chrome"
        if os.path.exists(linux_path):
            browser_path = linux_path
        else:
            print("[WebDriverFactory] Chromium not found at specified path. Falling back to default.")

    try:
        driver = None
        # The user's browser is v109. We will use a manually downloaded chromedriver
        # to ensure perfect version compatibility.
        kwargs = {'options': options}

        # Path to the manually downloaded chromedriver.exe
        manual_driver_path = r"C:\Users\Niladri_Ghoshal\chromedriver.exe"

        if os.path.exists(manual_driver_path):
            print(f"[WebDriverFactory] Using manually specified driver: {manual_driver_path}")
            kwargs['driver_executable_path'] = manual_driver_path
        else:
            # Fallback to forcing version if manual driver not found
            print(f"[WebDriverFactory] Manual driver not found at {manual_driver_path}. Falling back to version_main.")
            kwargs['version_main'] = 109

        if browser_path:
            print(f"[WebDriverFactory] Using browser executable: {browser_path}")
            kwargs['browser_executable_path'] = browser_path
        else:
            print("[WebDriverFactory] Using default browser executable path.")

        driver = uc.Chrome(**kwargs)

        # The driver is returned immediately. Any post-launch handling is the responsibility of the caller.
        return driver

    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        return None
