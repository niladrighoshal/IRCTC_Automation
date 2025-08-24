from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import src.config as config

def create_webdriver():
    """
    Creates and configures a new Selenium Chrome WebDriver instance based on settings in config.py.

    Returns:
        A configured instance of selenium.webdriver.chrome.webdriver.WebDriver.
    """
    chrome_options = Options()

    # Headless mode
    if config.HEADLESS:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080") # Recommended for headless

    # GPU settings
    if not config.USE_GPU:
        chrome_options.add_argument("--disable-gpu")

    # Other useful arguments for stability and to avoid detection
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/536.36")

    # Exclude automation switches to prevent detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Set up the service
    try:
        service = Service(executable_path=config.CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Error creating WebDriver: {e}")
        print("Please ensure that chromedriver is installed and that the 'CHROMEDRIVER_PATH' in 'src/config.py' is correct.")
        return None

    # This helps in preventing detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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
