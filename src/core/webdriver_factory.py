import sys
import os
from selenium import webdriver
from selenium_stealth import stealth

def create_webdriver(instance_id, is_headless=False, use_gpu=True):
    """
    Creates a stealthy webdriver instance using selenium-stealth.
    """
    options = webdriver.ChromeOptions()

    # --- Base Options ---
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")

    # These are the most important stealth options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # --- Paths ---
    chromium_path = os.path.join(os.getcwd(), "chrome-win32", "chrome.exe")
    driver_path = os.path.join(os.getcwd(), "chromedriver.exe")

    # --- Profile Path ---
    profile_dir = os.path.join(os.getcwd(), "chromeprofile", str(instance_id))
    os.makedirs(profile_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")
    print(f"[WebDriverFactory] Using profile path: {profile_dir}")

    # --- Service Setup ---
    # selenium-stealth uses a Service object to manage the driver
    service = webdriver.ChromeService(executable_path=driver_path)

    if os.path.exists(chromium_path):
        options.binary_location = chromium_path
    else:
        print(f"[WebDriverFactory] WARNING: Chromium not found at '{chromium_path}'.")

    try:
        print("[WebDriverFactory] Creating standard Selenium driver...")
        driver = webdriver.Chrome(service=service, options=options)
        print("[WebDriverFactory] Driver created. Applying stealth patches...")

        # --- Apply Stealth Patches ---
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        print("[WebDriverFactory] Stealth patches applied successfully.")
        return driver

    except Exception as e:
        print(f"Error creating stealth WebDriver for instance {instance_id}: {e}")
        return None
