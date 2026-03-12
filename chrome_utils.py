"""
chrome_utils.py — Works on LOCAL (Mac/Win) and STREAMLIT CLOUD (Linux/headless).
"""
import os
import shutil
import platform
import subprocess
import logging
import tempfile
import stat

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
    """Detect the actual Chromium version so uc uses the right ChromeDriver."""
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip()  # e.g. "Chromium 114.0.5735.90"
        major = int(version_str.split()[1].split(".")[0])
        logger.info(f"Detected Chromium version: {major}")
        return major
    except Exception as e:
        logger.warning(f"Could not detect Chromium version: {e}")
        return None


def _get_writable_chromedriver() -> str | None:
    """Copy chromedriver to /tmp — Streamlit Cloud blocks writes to /usr/bin."""
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
    use_headless   = headless or force_headless

    options = uc.ChromeOptions()

    # ── Stability flags (critical for containers) ────────────────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--single-process")          # ← KEY fix for container crash
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    system = platform.system()

    if system == "Linux":
        chromium_bin = _find_binary(["chromium", "chromium-browser", "google-chrome"])
        if chromium_bin:
            options.binary_location = chromium_bin
            logger.info(f"Using binary: {chromium_bin}")
        else:
            logger.warning("No Chromium binary found!")

        driver_path  = _get_writable_chromedriver()
        version_main = _get_chromium_version(chromium_bin) if chromium_bin else None

        driver = uc.Chrome(
            options                = options,
            driver_executable_path = driver_path,
            headless               = use_headless,
            use_subprocess         = True,
            version_main           = version_main,   # ← pass detected version
        )

    else:
        driver = uc.Chrome(
            options      = options,
            headless     = use_headless,
            version_main = 146,
        )

    driver.implicitly_wait(15)
    env_label = "Streamlit Cloud" if force_headless else system
    logger.info(f"✅ Chrome ready [{env_label}{'  headless' if use_headless else ''}]")
    return driver
