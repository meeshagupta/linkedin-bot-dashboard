"""
chrome_utils.py — Works on LOCAL (Mac/Win) and STREAMLIT CLOUD (Linux/headless).
Uses undetected-chromedriver to bypass LinkedIn bot detection.
"""
import os
import platform
import subprocess
import logging
import tempfile

logger = logging.getLogger("ChromeUtils")


def is_streamlit_cloud() -> bool:
    return (
        platform.system() == "Linux"
        and os.environ.get("HOME", "") in ("/home/appuser", "/root")
        or os.path.exists("/etc/streamlit")
        or bool(os.environ.get("STREAMLIT_SHARING_MODE"))
    )


def _find_binary(names: list) -> str | None:
    for name in names:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        path = result.stdout.strip()
        if path:
            return path
        for prefix in ["/usr/bin", "/usr/local/bin", "/snap/bin"]:
            full = f"{prefix}/{name}"
            if os.path.exists(full):
                return full
    return None


def get_chrome_driver(headless: bool = False):
    """
    Return a configured undetected Chrome WebDriver.
    undetected_chromedriver patches the binary to remove bot fingerprints
    that regular selenium exposes even with manual spoofing.
    """
    import undetected_chromedriver as uc

    force_headless = is_streamlit_cloud()
    use_headless   = headless or force_headless

    options = uc.ChromeOptions()

    # Core stability flags (required for containers)
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

    # Mimic a real desktop browser profile
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument("--start-maximized")

    # A realistic, recent user-agent
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    system = platform.system()

    if system == "Linux":
        chromium_bin    = _find_binary(["chromium", "chromium-browser", "google-chrome"])
        chromedriver_bin = _find_binary(["chromedriver"])

        if chromium_bin:
            options.binary_location = chromium_bin
            logger.info(f"Using binary: {chromium_bin}")
        else:
            logger.warning("No Chromium/Chrome binary found!")

        driver_exec = chromedriver_bin  # may be None; uc handles None gracefully

        driver = uc.Chrome(
            options        = options,
            driver_executable_path = driver_exec,
            headless       = use_headless,
            use_subprocess = True,
        )
    else:
        # Mac / Windows local dev
        driver = uc.Chrome(
            options  = options,
            headless = use_headless,
        )

    driver.implicitly_wait(15)
    env_label = "Streamlit Cloud" if force_headless else system
    logger.info(f"✅ Chrome ready [{env_label}{'  headless' if use_headless else ''}]")
    return driver
