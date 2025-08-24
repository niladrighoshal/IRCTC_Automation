import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def init_persistent_driver():
    """Initializes a single, persistent, headless Chrome driver."""
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)
    return driver

def fetch_train_name(driver, train_no: str):
    """
    Uses the provided driver instance to fetch the train name from a third-party site.
    """
    url = f"https://www.railyatri.in/time-table/{train_no}"
    try:
        driver.get(url)
        heading = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.timetable_lts_timeline_title__7Patt h1")
            )
        )
        text = heading.text.strip()
        match = re.match(r"(.+?\(\d+\))", text)
        if match:
            return match.group(1).strip()
        else:
            return text.replace("Train Time Table", "").strip()
    except Exception as e:
        return f"Error fetching train name."
