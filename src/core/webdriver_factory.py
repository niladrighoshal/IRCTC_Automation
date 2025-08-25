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

    # --- Options to disable browser popups and infobars ---
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    # --- Deep Stealth Options ---
    # These are critical for avoiding detection.
    options.add_argument("--no-first-run") # Suppress the "Welcome to Brave" screen
    options.add_argument("--disable-default-apps") # Disables installation of default apps on first run
    options.add_argument('--disable-blink-features=AutomationControlled') # The classic

    # Re-enable these critical experimental options for maximum stealth
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2 # 1:allow, 2:block
    }
    options.add_experimental_option("prefs", prefs)

    browser_path = None

    if sys.platform == "win32":
        # User-provided paths for Windows and Brave
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        # Create a unique, persistent profile for each bot instance to avoid detection
        # and ensure separate browser windows.
        base_profile_path = os.path.join(os.getcwd(), "brave_profiles")
        profile_path = os.path.join(base_profile_path, f"bot_{instance_id}")

        # Ensure the directory for the profile exists before launching
        os.makedirs(profile_path, exist_ok=True)
        print(f"[WebDriverFactory] Using profile path: {profile_path}")

        if os.path.exists(brave_path):
            browser_path = brave_path
            # This is the critical argument for using a dedicated profile
            options.add_argument(f'--user-data-dir={profile_path}')
        else:
            print("[WebDriverFactory] Brave browser not found at specified path. Falling back to default.")

    elif sys.platform == "linux":
        # Path discovered during smoke testing in the cloud environment
        linux_path = "/home/jules/.cache/ms-playwright/chromium-1181/chrome-linux/chrome"
        if os.path.exists(linux_path):
            browser_path = linux_path
        else:
            print("[WebDriverFactory] Chromium not found at specified path. Falling back to default.")

    try:
        if browser_path:
            print(f"[WebDriverFactory] Using browser executable: {browser_path}")
            return uc.Chrome(browser_executable_path=browser_path, options=options)
        else:
            # Fallback to default behavior if no specific path is found
            print("[WebDriverFactory] Using default browser executable path.")
            return uc.Chrome(options=options)

    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        return None
