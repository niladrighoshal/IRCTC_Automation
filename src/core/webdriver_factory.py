import undetected_chromedriver as uc
import src.config as config

def create_webdriver():
    """
    Creates and configures a new undetected_chromedriver instance.
    """
    options = uc.ChromeOptions()

    if config.HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    if not config.USE_GPU:
        options.add_argument("--disable-gpu")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/536.36")

    options.add_experimental_option(
        "prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
    )

    try:
        driver = uc.Chrome(options=options)
    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        print("Please ensure Google Chrome is installed correctly.")
        return None

    return driver
