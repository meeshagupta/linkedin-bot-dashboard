"""
company_bot.py — LinkedIn automation for COMPANY page accounts.
Uses chrome_utils.py for cross-platform Chrome setup.
"""
import time
import random
import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from chrome_utils import get_chrome_driver   # ← shared, cloud-safe driver

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = "temp_creds.json"
    GOOGLE_SHEET_URL = ""
    LINKEDIN_EMAIL = ""
    LINKEDIN_PASSWORD = ""
    COMPANY_NAME = ""
    MIN_DELAY = 20
    MAX_DELAY = 35
    COMMENT_MIN_WAIT = 10
    COMMENT_MAX_WAIT = 20
    HEADLESS_MODE = True     # always True on Streamlit Cloud (chrome_utils handles it)
    LOG_FILE = "bot_logs.txt"

# ==================== LOGGER ====================
def setup_logger(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("LinkedInBot")

logger = setup_logger(Config.LOG_FILE)

# ==================== STEALTH HELPERS ====================
def human_sleep(a=1, b=3):
    time.sleep(random.uniform(a, b))

def human_pause():
    pause = random.uniform(3, 8)
    logger.info(f"⏳ Human pause... {pause:.1f}s")
    time.sleep(pause)

def human_scroll(driver):
    for _ in range(random.randint(2, 4)):
        driver.execute_script(f"window.scrollBy(0, {random.randint(200, 600)});")
        human_sleep(0.5, 1.2)

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
    human_sleep(1, 2)

def human_comment_wait():
    wait = random.uniform(Config.COMMENT_MIN_WAIT, Config.COMMENT_MAX_WAIT)
    logger.info(f"📖 Reading... {wait:.1f}s")
    time.sleep(wait)

# ==================== GOOGLE SHEET ====================
class GoogleSheetHandler:
    def __init__(self, credentials_file, sheet_url):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_url(sheet_url).sheet1

    def read_file(self):
        records = self.sheet.get_all_records()
        logger.info(f"✅ Loaded {len(records)} rows")
        return records

    def _get_status_col(self):
        headers = self.sheet.row_values(1)
        for col, header in enumerate(headers, 1):
            if "status" in header.lower():
                return col
        return None

    def update_status(self, row_index, status):
        try:
            status_col = self._get_status_col()
            if status_col:
                self.sheet.update_cell(
                    row_index + 2, status_col,
                    f"{status} @ {datetime.now().strftime('%H:%M')}"
                )
                logger.info(f"📝 Row {row_index + 2}: {status}")
        except Exception as e:
            logger.error(f"Sheet update failed: {e}")

    def is_row_done(self, row_index):
        try:
            status_col = self._get_status_col()
            if status_col:
                status = self.sheet.cell(row_index + 2, status_col).value or ""
                return "done" in status.lower()
        except Exception:
            pass
        return False

# ==================== SELENIUM CLIENT ====================
class LinkedInClient:
    def __init__(self, email, password, headless=True):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Use shared cloud-safe driver from chrome_utils."""
        self.driver = get_chrome_driver(headless=self.headless)
        logger.info("🚀 Chrome ready!")

    def login(self):
        try:
            logger.info("🔐 Logging in...")
            self.driver.get("https://www.linkedin.com/login")
            human_sleep(4, 6)

            email_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_type(email_field, self.email)

            password_field = self.driver.find_element(By.ID, "password")
            human_type(password_field, self.password)

            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

            WebDriverWait(self.driver, 40).until(
                EC.any_of(
                    EC.url_contains("feed"),
                    EC.url_contains("checkpoint"),
                )
            )
            logger.info("✅ Login success!")
            human_sleep(5, 8)
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            raise

    def switch_to_company(self, company_name: str):
        """Switch LinkedIn identity to the specified company page."""
        try:
            logger.info(f"🏢 Switching to company: {company_name}")
            self.driver.get("https://www.linkedin.com/feed/")
            human_sleep(3, 5)

            # Click "Me" / identity switcher
            me_menu = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class,'global-nav__primary-link')]"
                               "[.//*[contains(@class,'nav-item__profile-member')]]")
                )
            )
            me_menu.click()
            human_sleep(1, 2)

            # Look for company in dropdown
            company_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//span[contains(text(), '{company_name}')]")
                )
            )
            company_option.click()
            human_sleep(3, 5)
            logger.info(f"✅ Switched to: {company_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not switch to company '{company_name}': {e}")

    def like_post(self):
        try:
            logger.info("❤️ Liking post...")
            human_scroll(self.driver)
            human_sleep(3, 5)

            selectors = [
                "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'Unlike'))]",
                "//div[@role='button' and contains(@aria-label,'Like')]",
                "//button[contains(@data-control-name,'like')]",
            ]

            like_btn = None
            for sel in selectors:
                try:
                    like_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    break
                except Exception:
                    continue

            if not like_btn:
                logger.warning("❌ No like button found")
                return False

            if like_btn.get_attribute("aria-pressed") == "true":
                logger.info("ℹ️ Already liked")
                return True

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", like_btn
            )
            human_sleep(2, 3)
            ActionChains(self.driver).move_to_element(like_btn).click().perform()
            human_sleep(3, 5)
            logger.info("✅ Post liked!")
            return True

        except Exception as e:
            logger.error(f"❌ Like failed: {e}")
            return False

    def like_comments(self):
        try:
            logger.info("💬 Liking comments...")
            human_scroll(self.driver)
            human_sleep(4, 6)

            # Load more comments if available
            try:
                more_btn = self.driver.find_element(
                    By.XPATH, "//button[contains(@aria-label,'See more comments')]"
                )
                more_btn.click()
                human_sleep(3, 5)
            except Exception:
                pass

            selectors = [
                "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'Unlike'))]",
                "//div[@role='button' and contains(@aria-label,'Like comment')]",
            ]

            all_btns = []
            for sel in selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, sel)
                    all_btns.extend(
                        [b for b in btns if b.get_attribute("aria-pressed") != "true"]
                    )
                except Exception:
                    continue

            logger.info(f"📝 Found {len(all_btns)} likeable comments")

            liked = 0
            for btn in all_btns[:3]:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    ActionChains(self.driver).move_to_element(btn).click().perform()
                    human_comment_wait()
                    liked += 1
                    logger.info(f"✅ Comment {liked}/3 liked")
                except Exception:
                    continue

            logger.info(f"✅ {liked} comments liked")
            return liked > 0

        except Exception as e:
            logger.error(f"❌ Comments failed: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")

# ==================== MAIN BOT (used by app.py) ====================
class LinkedInCommentLiker:
    def __init__(self, config):
        self.config = config
        self.client = None

    def initialize(self):
        self.client = LinkedInClient(
            self.config.LINKEDIN_EMAIL,
            self.config.LINKEDIN_PASSWORD,
            headless=self.config.HEADLESS_MODE,
        )
        self.client.setup_driver()
        self.client.login()

        if getattr(self.config, "COMPANY_NAME", "").strip():
            self.client.switch_to_company(self.config.COMPANY_NAME)

    def run(self):
        handler = GoogleSheetHandler(
            self.config.GOOGLE_CREDENTIALS_FILE,
            self.config.GOOGLE_SHEET_URL,
        )
        rows = handler.read_file()
        if not rows:
            logger.error("❌ No data in sheet")
            return

        processed = 0
        for i, row in enumerate(rows):
            if handler.is_row_done(i):
                logger.info(f"⏭️ Row {i+1}: Already done")
                continue

            post_url = str(
                row.get("Post Url") or row.get("Comment URL") or ""
            ).strip()
            if not post_url or post_url == "nan":
                logger.warning(f"Row {i+1}: No URL")
                handler.update_status(i, "NO_URL")
                continue

            logger.info(f"\n{'='*60}\n[{i+1}/{len(rows)}] {post_url[:60]}...\n{'='*60}")

            try:
                self.client.driver.get(post_url)
                human_sleep(8, 12)

                post_liked     = self.client.like_post()
                human_pause()
                comments_liked = self.client.like_comments()

                status = (
                    "DONE"      if post_liked and comments_liked else
                    "POST_ONLY" if post_liked else
                    "FAILED"
                )
                handler.update_status(i, status)
                logger.info(f"✅ Result: {status}")
                processed += 1

            except Exception as e:
                logger.error(f"❌ Row {i+1} failed: {e}")
                handler.update_status(i, "ERROR")

            delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
            logger.info(f"😴 Next in {delay:.1f}s")
            time.sleep(delay)

        logger.info(f"\n🎉 Complete! {processed}/{len(rows)} processed")
        if self.client:
            self.client.close()

if __name__ == "__main__":
    bot = LinkedInCommentLiker(Config)
    bot.initialize()
    bot.run()
