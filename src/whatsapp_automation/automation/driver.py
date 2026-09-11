from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import settings


def get_chrome_options(user_data_dir: str | None = None, headless: bool = False) -> Options:
    options = Options()

    profile_dir = user_data_dir or settings.chrome_profile_dir
    profile_path = Path(profile_dir).expanduser().resolve()
    profile_path.mkdir(parents=True, exist_ok=True)

    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    if headless or settings.headless:
        options.add_argument("--headless=new")

    return options

def init_driver(user_data_dir: str | None = None, headless: bool = False) -> webdriver.Chrome:
    options = get_chrome_options(user_data_dir=user_data_dir, headless=headless)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def check_session_health(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """
    Checks if WhatsApp Web is logged in.
    Looks for the main search input element or chat list side pane.
    """
    try:
        if "web.whatsapp.com" not in driver.current_url:
            driver.get(settings.whatsapp_web_url)

        # Look for search input or left panel indicative of active session
        search_selectors = [
            "//div[@contenteditable='true'][@data-tab='3']",
            "//div[@contenteditable='true'][contains(@aria-label, 'Search')]",
            "//div[@id='pane-side']",
        ]
        combined_xpath = " | ".join(search_selectors)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, combined_xpath))
        )
        return True
    except Exception:
        return False

def close_driver(driver: webdriver.Chrome | None) -> None:
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
