import undetected_chromedriver as uc

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
    try:
        # The browser in this environment is a self-contained Playwright binary.
        # Pointing directly to this executable.
        return uc.Chrome(browser_executable_path="/home/jules/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", options=options)
    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        return None
