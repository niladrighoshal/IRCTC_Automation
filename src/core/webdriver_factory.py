import undetected_chromedriver as uc
import sys
import os

def create_webdriver(is_headless=False, use_gpu=True):
    options = uc.ChromeOptions()

    if is_headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    if not use_gpu:
        options.add_argument("--disable-gpu")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/536.36")
    options.add_experimental_option("prefs", {"credentials_enable_service": False, "profile.password_manager_enabled": False})

    browser_path = None

    if sys.platform == "win32":
        # User-provided paths for Windows and Brave
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        profile_path = r"G:\Project\IRCTC_Tatkal\Automation\BraveProfile"

        if os.path.exists(brave_path):
            browser_path = brave_path
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
