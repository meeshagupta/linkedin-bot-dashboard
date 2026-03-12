"""
profile_bot.py — LinkedIn automation for PERSONAL profile accounts.
Fixes: updated 2025/2026 LinkedIn DOM selectors, stop-flag support.
"""
import time
import random
import logging
import threading
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException
)

from chrome_utils import get_chrome_driver
from session_manager import SessionManager

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = "temp_creds.json"
    GOOGLE_SHEET_URL        = ""
    LINKEDIN_EMAIL          = ""
    LINKEDIN_PASSWORD       = ""
    MIN_DELAY               = 5
    MAX_DELAY               = 8
    COMMENT_MIN_WAIT        = 1
    COMMENT_MAX_WAIT        = 2
    HEADLESS_MODE           = True
    LOG_FILE                = "bot_logs.txt"
    COOKIE_FILE             = "linkedin_session.pkl"   # ← NEW: session persistence

# ==================== LOGGER ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ProfileBot")

# ==================== STEALTH HELPERS ====================
def human_sleep(a=0.3, b=0.8):
    time.sleep(random.uniform(a, b))

def human_pause():
    t = random.uniform(1, 2)
    logger.info(f"⏳ Pause {t:.1f}s")
    time.sleep(t)

def human_scroll(driver, times=2):
    for _ in range(times):
        driver.execute_script(f"window.scrollBy(0, {random.randint(200,500)});")
        time.sleep(random.uniform(0.2, 0.5))

def human_type(element, text):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(0.03, 0.08))
    time.sleep(0.3)

def safe_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'smooth'});", element)
    human_sleep(0.5, 1.0)
    try:
        ActionChains(driver).move_to_element(element).click().perform()
    except Exception:
        driver.execute_script("arguments[0].click();", element)

# ==================== GOOGLE SHEET ====================
class GoogleSheetHandler:
    def __init__(self, credentials_file, sheet_url):
        scope  = ["https://www.googleapis.com/auth/spreadsheets"]
        creds  = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_url(sheet_url).sheet1

    def read_file(self):
        records = self.sheet.get_all_records()
        logger.info(f"✅ Loaded {len(records)} rows")
        return records

    def _status_col(self):
        headers = self.sheet.row_values(1)
        for i, h in enumerate(headers, 1):
            if "status" in h.lower():
                return i
        return None

    def update_status(self, row_index, status):
        try:
            col = self._status_col()
            if col:
                self.sheet.update_cell(
                    row_index + 2, col,
                    f"{status} @ {datetime.now().strftime('%H:%M')}"
                )
                logger.info(f"📝 Row {row_index+2}: {status}")
        except Exception as e:
            logger.error(f"Sheet update error: {e}")

    def is_row_done(self, row_index):
        try:
            col = self._status_col()
            if col:
                val = self.sheet.cell(row_index + 2, col).value or ""
                return "done" in val.lower()
        except Exception:
            pass
        return False

# ==================== LINKEDIN CLIENT ====================
class LinkedInClient:
    def __init__(self, email, password, headless=True, stop_event: threading.Event = None):
        self.email      = email
        self.password   = password
        self.headless   = headless
        self.stop_event = stop_event or threading.Event()
        self.driver     = None

    def setup_driver(self):
        self.driver = get_chrome_driver(headless=self.headless)
        logger.info("🚀 Chrome ready!")

    def stopped(self):
        return self.stop_event.is_set()

    def login(self, cookie_file: str = "linkedin_session.pkl"):
        # ── Step 1: try to restore a saved session (no login page hit) ──────
        logger.info("🍪 Checking for saved session…")
        if SessionManager.load(self.driver, cookie_file):
            logger.info("✅ Resumed from saved session — no login needed!")
            return

        # ── Step 2: fresh email/password login ───────────────────────────────
        logger.info("🔐 No saved session — logging in with credentials…")
        self.driver.get("https://www.linkedin.com/login")
        human_sleep(2, 4)   # longer wait mimics a human arriving at the page

        email_f = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        human_type(email_f, self.email)
        human_sleep(0.5, 1.0)

        pw_f = self.driver.find_element(By.ID, "password")
        human_type(pw_f, self.password)
        human_sleep(0.5, 1.2)

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

        WebDriverWait(self.driver, 40).until(
            EC.any_of(EC.url_contains("feed"), EC.url_contains("checkpoint"))
        )
        if "checkpoint" in self.driver.current_url:
            raise RuntimeError(
                "LinkedIn sent a verification challenge.\n"
                "FIX: Run the bot ONCE locally (non-headless) on your own PC, "
                "complete the verification manually, then the bot will save the "
                "session cookies automatically.  After that, upload the saved "
                "linkedin_session.pkl file via the sidebar and cloud runs will "
                "skip the login page entirely."
            )

        logger.info("✅ Logged in!")
        human_sleep(2, 3)

        # Save cookies so the next run skips the login page
        SessionManager.save(self.driver, cookie_file)
        logger.info("💾 Session cookies saved for future runs")

    def like_post(self) -> bool:
        logger.info("❤️ Attempting to like post…")
        human_scroll(self.driver, 2)
        human_sleep(1, 2)

        selectors = [
            "//button[contains(@class,'react-button__trigger')]",
            "//button[contains(@aria-label,'React to') and contains(@aria-label,'post')]",
            "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'comment'))]",
            "//button[@data-control-name='react_to_post']",
            "//button[.//span[text()='Like']]",
        ]

        like_btn = None
        for sel in selectors:
            try:
                candidates = self.driver.find_elements(By.XPATH, sel)
                for btn in candidates:
                    if btn.get_attribute("aria-pressed") == "true":
                        logger.info("ℹ️ Post already liked")
                        return True
                    like_btn = btn
                    break
                if like_btn:
                    break
            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        if not like_btn:
            try:
                like_btn = self.driver.find_element(
                    By.XPATH, "//div[contains(@class,'social-actions')]//button[1]"
                )
            except Exception:
                pass

        if not like_btn:
            logger.warning("❌ No like button found on this page")
            return False

        try:
            safe_click(self.driver, like_btn)
            human_sleep(2, 4)
            logger.info("✅ Post liked!")
            return True
        except Exception as e:
            logger.error(f"❌ Click failed: {e}")
            return False

    def like_comments(self) -> bool:
        logger.info("💬 Looking for comments to like…")
        human_scroll(self.driver, 3)
        human_sleep(3, 5)

        for sel in [
            "//button[contains(@aria-label,'Load previous comments')]",
            "//button[contains(@aria-label,'See more comments')]",
        ]:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                safe_click(self.driver, btn)
                human_sleep(2, 3)
                break
            except Exception:
                pass

        human_scroll(self.driver, 2)
        human_sleep(2, 3)

        comment_selectors = [
            "//div[contains(@class,'comment') or contains(@class,'Comment')]"
            "//button[contains(@class,'react-button__trigger')]",
            "//button[contains(@aria-label,'React to') and contains(@aria-label,'comment')]",
            "//button[contains(@aria-label,'Like') and contains(@aria-label,'comment')]",
            "//button[contains(@class,'react-button__trigger')]",
        ]

        all_btns = []
        for sel in comment_selectors:
            try:
                found = self.driver.find_elements(By.XPATH, sel)
                for b in found:
                    if b.get_attribute("aria-pressed") != "true" and b not in all_btns:
                        all_btns.append(b)
                if all_btns:
                    break
            except Exception:
                continue

        if all_btns and len(all_btns) > 1:
            label = all_btns[0].get_attribute("aria-label") or ""
            if "post" in label.lower() or "React to" in label:
                all_btns = all_btns[1:]

        logger.info(f"📝 Found {len(all_btns)} comment like button(s)")

        liked = 0
        for btn in all_btns:          # ← no limit, like ALL comments
            if self.stopped():
                break
            try:
                safe_click(self.driver, btn)
                human_sleep(Config.COMMENT_MIN_WAIT, Config.COMMENT_MAX_WAIT)
                liked += 1
                logger.info(f"✅ Comment {liked}/{len(all_btns)} liked")
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.warning(f"⚠️ Comment like failed: {e}")
                continue

        logger.info(f"✅ {liked} comment(s) liked")
        return liked > 0

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")

# ==================== MAIN BOT (called by app.py) ====================
class LinkedInCommentLiker:
    def __init__(self, config, stop_event: threading.Event = None):
        self.config     = config
        self.client     = None
        self.stop_event = stop_event or threading.Event()

    def initialize(self):
        self.client = LinkedInClient(
            self.config.LINKEDIN_EMAIL,
            self.config.LINKEDIN_PASSWORD,
            headless   = self.config.HEADLESS_MODE,
            stop_event = self.stop_event,
        )
        self.client.setup_driver()
        self.client.login(cookie_file=getattr(self.config, "COOKIE_FILE", "linkedin_session.pkl"))

    def run(self):
        handler = GoogleSheetHandler(
            self.config.GOOGLE_CREDENTIALS_FILE,
            self.config.GOOGLE_SHEET_URL,
        )
        rows = handler.read_file()
        if not rows:
            logger.error("❌ No rows found in sheet")
            return

        processed = 0
        for i, row in enumerate(rows):

            if self.stop_event.is_set():
                logger.info("⛔ Stopped by user")
                break

            if handler.is_row_done(i):
                logger.info(f"⏭️ Row {i+1}: Already DONE — skipping")
                continue

            post_url = str(
                row.get("Post Url") or row.get("Comment URL") or ""
            ).strip()

            if not post_url or post_url.lower() == "nan":
                logger.warning(f"Row {i+1}: No URL")
                handler.update_status(i, "NO_URL")
                continue

            logger.info(f"\n{'='*55}\n[{i+1}/{len(rows)}] {post_url[:55]}…\n{'='*55}")

            try:
                logger.info(f"🌐 Opening post URL…")
                self.client.driver.get(post_url)
                human_sleep(3, 5)           # was 8-12s

                post_liked     = self.client.like_post()
                human_pause()               # now 1-2s
                comments_liked = self.client.like_comments()

                status = (
                    "DONE"      if post_liked and comments_liked else
                    "POST_ONLY" if post_liked                    else
                    "FAILED"
                )
                handler.update_status(i, status)
                processed += 1

            except Exception as e:
                logger.error(f"❌ Row {i+1} error: {e}")
                handler.update_status(i, "ERROR")

            if not self.stop_event.is_set() and i < len(rows) - 1:
                delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
                logger.info(f"😴 Waiting {delay:.0f}s…")
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)

        logger.info(f"\n🎉 Finished! {processed}/{len(rows)} processed")
        if self.client:
            self.client.close()

if __name__ == "__main__":
    bot = LinkedInCommentLiker(Config)
    bot.initialize()
    bot.run()
