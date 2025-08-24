import undetected_chromedriver as uc
import src.config as config

def create_webdriver():
    """
    Creates and configures a new undetected_chromedriver instance based on settings in config.py.
    This version is patched to be less detectable by services like IRCTC.

    Returns:
        A configured instance of undetected_chromedriver.
    """
    options = uc.ChromeOptions()

    # Headless mode - Note: Undetected-chromedriver's headless mode can sometimes be less stable/stealthy.
    if config.HEADLESS:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")

    # GPU settings
    if not config.USE_GPU:
        options.add_argument("--disable-gpu")

    # Other useful arguments for stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    # User agent can still be useful
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/536.36")

    try:
        # undetected_chromedriver automatically downloads and manages the driver executable.
        driver = uc.Chrome(options=options)
    except Exception as e:
        print(f"Error creating undetected WebDriver: {e}")
        print("Please ensure Google Chrome is installed correctly.")
        return None

    return driver

if __name__ == '__main__':
    # A simple test to verify the webdriver_factory is working
    print("Attempting to create a WebDriver instance...")
    driver = create_webdriver()
    if driver:
        print("WebDriver created successfully.")
        driver.get("https://www.google.com")
        print(f"Page title: {driver.title}")
        driver.quit()
        print("WebDriver closed.")
    else:
        print("Failed to create WebDriver.")
