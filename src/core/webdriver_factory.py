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
    options.add_argument("--no-first-run") # Suppress the "Welcome to Brave" screen
    options.add_argument('--disable-blink-features=AutomationControlled') # The classic

    # The following experimental options were found to be unstable and are disabled
    # to prevent the browser from crashing on launch.
    # options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # options.add_experimental_option('useAutomationExtension', False)

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2 # 1:allow, 2:block
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
        if browser_path:
            print(f"[WebDriverFactory] Using browser executable: {browser_path}")
            driver = uc.Chrome(browser_executable_path=browser_path, options=options)
        else:
            print("[WebDriverFactory] Using default browser executable path.")
            driver = uc.Chrome(options=options)

        # --- Post-launch popup handling ---
        # After launch, Brave may show a "private analytics" popup. We need to dismiss it.
        print("[WebDriverFactory] Checking for initial Brave popups...")
        from selenium.webdriver.common.by import By
        import time

        end_time = time.time() + 10 # Check for 10 seconds
        popup_found_and_clicked = False
        while time.time() < end_time and not popup_found_and_clicked:
            try:
                # This selector is specific to the "Got it" button on the analytics popup
                got_it_button = driver.find_element(By.XPATH, "//button[normalize-space()='Got it']")
                if got_it_button.is_displayed() and got_it_button.is_enabled():
                    print("[WebDriverFactory] Found 'Got it' popup. Clicking to dismiss...")
                    got_it_button.click()
                    popup_found_and_clicked = True
                    print("[WebDriverFactory] 'Got it' popup dismissed.")
            except Exception:
                # Button not found, which is the normal case after the first run.
                time.sleep(0.5)

        if not popup_found_and_clicked:
            print("[WebDriverFactory] No initial popups found, or could not dismiss in time.")

        return driver

    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        return None
