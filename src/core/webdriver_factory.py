import undetected_chromedriver as uc
import sys
import os
from selenium.common.exceptions import WebDriverException

def create_webdriver(instance_id, is_headless=False, use_gpu=True):
    """
    Creates a robust webdriver instance that attempts to launch automatically,
    but falls back to a manual driver if a version mismatch occurs.
    """
    options = uc.ChromeOptions()

    # --- Base Options ---
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument('--disable-blink-features=AutomationControlled')

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # --- Profile Path ---
    profile_dir = os.path.join(os.getcwd(), "chromeprofile", str(instance_id))
    os.makedirs(profile_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")
    print(f"[WebDriverFactory] Using profile path: {profile_dir}")

    # --- Primary Automatic Launch Attempt ---
    try:
        print("[WebDriverFactory] Attempting automatic driver detection...")
        driver = uc.Chrome(options=options)
        print("[WebDriverFactory] Automatic driver detection successful.")
        return driver
    except WebDriverException as e:
        # Check if the error is the specific version mismatch error
        if "session not created" in str(e) and "This version of ChromeDriver only supports" in str(e):
            print("[WebDriverFactory] Automatic detection failed due to version mismatch. Falling back to manual driver.")

            # --- Manual Driver Fallback ---
            manual_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
            if os.path.exists(manual_driver_path):
                print(f"[WebDriverFactory] Found manual driver at: {manual_driver_path}")
                try:
                    driver = uc.Chrome(driver_executable_path=manual_driver_path, options=options)
                    print("[WebDriverFactory] Manual driver launch successful.")
                    return driver
                except Exception as manual_e:
                    print(f"[WebDriverFactory] Manual driver launch also failed: {manual_e}")
                    return None
            else:
                # --- User Guidance ---
                print("\n" + "="*80)
                print("!!! CRITICAL ERROR: AUTOMATIC BROWSER DRIVER DETECTION FAILED !!!")
                print("="*80)
                print("This usually means your installed Chrome/Chromium version is very new or very old.")
                print("\n--- HOW TO FIX ---")
                print("1. Go to: https://googlechromelabs.github.io/chrome-for-testing/")
                print("2. Find the 'Stable' version that most closely matches your installed browser version.")
                print("3. Download the 'chromedriver' for your platform (e.g., 'win64').")
                print("4. Unzip the file and place 'chromedriver.exe' in the project's root folder.")
                print(f"   (The same folder as '{os.path.basename(sys.argv[0])}')")
                print("5. Rerun the bot.")
                print("="*80 + "\n")
                return None
        else:
            # It was a different WebDriver error, so re-raise it
            print(f"An unexpected WebDriver error occurred: {e}")
            return None

    except Exception as e:
        print(f"An unexpected error occurred during webdriver creation: {e}")
        return None
