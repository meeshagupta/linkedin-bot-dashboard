"""
chrome_utils.py — Works on LOCAL (Mac/Win) and STREAMLIT CLOUD (Linux/headless).
Import this in both profile_bot.py and company_bot.py.
"""
import os
import platform
import subprocess
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger("ChromeUtils")


def is_streamlit_cloud() -> bool:
    """Detect if we're running inside Streamlit Cloud (headless Linux container)."""
    return (
        platform.system() == "Linux"
        and os.environ.get("HOME", "") in ("/home/appuser", "/root")
        or os.path.exists("/etc/streamlit")          # Streamlit Cloud marker
        or os.environ.get("STREAMLIT_SHARING_MODE")  # another env var it sets
    )


def _find_binary(names: list[str]) -> str | None:
    for name in names:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        path = result.stdout.strip()
        if path:
            return path
        # Also check common fixed paths
        for prefix in ["/usr/bin", "/usr/local/bin", "/snap/bin"]:
            full = f"{prefix}/{name}"
            if os.path.exists(full):
                return full
    return None


def get_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Return a configured Chrome WebDriver.

    On Streamlit Cloud → always headless + system Chromium.
    On local           → respects `headless` param + webdriver-manager.
    """
    options = Options()

    # ── Force headless on cloud, respect flag locally ────────────────────────
    force_headless = is_streamlit_cloud()
    if headless or force_headless:
        options.add_argument("--headless=new")   # Chrome 112+ headless

    # ── Required flags for containerised / CI environments ───────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")

    # ── Stealth / anti-bot-detection ─────────────────────────────────────────
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # ── Choose binary & driver based on platform ─────────────────────────────
    system = platform.system()

    if system == "Linux":
        # Streamlit Cloud / Ubuntu: packages.txt installs chromium + chromium-driver
        chromium_bin = _find_binary(["chromium", "chromium-browser"])
        chromedriver_bin = _find_binary(["chromedriver"])

        if chromium_bin:
            options.binary_location = chromium_bin
            logger.info(f"Using Chromium binary: {chromium_bin}")
        else:
            logger.warning("Chromium binary not found — Chrome may fail to start.")

        if chromedriver_bin:
            service = Service(executable_path=chromedriver_bin)
        else:
            # Last resort: webdriver-manager with CHROMIUM type
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())

    else:
        # Mac / Windows local dev — auto-download matching ChromeDriver
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)

    # Remove navigator.webdriver fingerprint
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
            window.chrome = {runtime: {}};
        """
    })

    driver.implicitly_wait(15)
    env_label = "Streamlit Cloud" if force_headless else system
    logger.info(f"✅ Chrome ready [{env_label}{'  headless' if headless or force_headless else ''}]")
    return driver
