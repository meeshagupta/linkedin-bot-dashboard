"""
chrome_utils.py — FIXED for Streamlit Cloud crashes during login.
"""
import os
import shutil
import platform
import subprocess
import logging
import tempfile
import stat
import time

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

def _get_chromium_version(binary: str) -> int | None:
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip()  # e.g. "Chromium 146.0.7680.71"
        major = int(version_str.split()[1].split(".")[0])
        logger.info(f"Detected Chromium version: {major}")
        return major
    except Exception as e:
        logger.warning(f"Could not detect Chromium version: {e}")
        return 146  # Default to installed version

def _get_writable_chromedriver() -> str | None:
    original = _find_binary(["chromedriver"])
    if not original:
        logger.warning("chromedriver not found on system!")
        return None

    tmp_driver = os.path.join(tempfile.gettempdir(), "chromedriver_uc")

    if not os.path.exists(tmp_driver):
        shutil.copy2(original, tmp_driver)
        st = os.stat(tmp_driver)
        os.chmod(tmp_driver, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        logger.info(f"✅ Copied chromedriver → {tmp_driver}")

    return tmp_driver

def get_chrome_driver(headless: bool = False):
    import undetected_chromedriver as uc

    force_headless = is_streamlit_cloud()
    use_headless = headless or force_headless

    options = uc.ChromeOptions()

    # ── CRASH-PROOF CONTAINER FLAGS ────────────────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--single-process")
    options.add_argument("--no-zygote")  # ← NEW: Prevent fork crashes
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    # ── Extra stealth (helps bypass detection) ─────────────────
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    system = platform.system()

    if system == "Linux":
        chromium_bin = _find_binary(["chromium", "chromium-browser", "google-chrome"])
        if chromium_bin:
            options.binary_location = chromium_bin
            logger.info(f"Using binary: {chromium_bin}")
        else:
            logger.error("❌ No Chromium binary found! Add to packages.txt")
            raise RuntimeError("Chromium missing")

        driver_path = _get_writable_chromedriver()
        version_main = _get_chromium_version(chromium_bin)

        driver = uc.Chrome(
            options=options,
            driver_executable_path=driver_path,
            headless=use_headless,
            use_subprocess=True,
            version_main=version_main,
        )
    else:
        driver = uc.Chrome(
            options=options,
            headless=use_headless,
            version_main=146,
        )

    driver.implicitly_wait(15)
    driver.set_page_load_timeout(60)  # ← NEW: Prevent hangs

    # ── Extra stealth script ─────────────────
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        '''
    })

    env_label = "Streamlit Cloud" if force_headless else system
    logger.info(f"✅ Chrome ready [{env_label}{' headless' if use_headless else ''}]")
    return driver
