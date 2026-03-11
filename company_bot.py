"""
company_bot.py — LinkedIn automation for COMPANY page accounts.
Fixes: updated 2025/2026 LinkedIn DOM selectors, working company switcher,
       stop-flag support for the Streamlit stop button.
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
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)

from chrome_utils import get_chrome_driver

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = "temp_creds.json"
    GOOGLE_SHEET_URL        = ""
    LINKEDIN_EMAIL          = ""
    LINKEDIN_PASSWORD       = ""
    COMPANY_NAME            = ""
    MIN_DELAY               = 5     # seconds between posts
    MAX_DELAY               = 8
    COMMENT_MIN_WAIT        = 1     # seconds between comment likes
    COMMENT_MAX_WAIT        = 2
    HEADLESS_MODE           = True
    LOG_FILE                = "bot_logs.txt"

# ==================== LOGGER ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("CompanyBot")

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
    """Scroll into view then JS-click (avoids intercept errors)."""
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
        self.email       = email
        self.password    = password
        self.headless    = headless
        self.stop_event  = stop_event or threading.Event()
        self.driver      = None

    # ── Setup ────────────────────────────────────────────────────────────────
    def setup_driver(self):
        self.driver = get_chrome_driver(headless=self.headless)
        logger.info("🚀 Chrome ready!")

    def stopped(self):
        return self.stop_event.is_set()

    # ── Login ────────────────────────────────────────────────────────────────
    def login(self):
        logger.info("🔐 Logging in…")
        self.driver.get("https://www.linkedin.com/login")
        human_sleep(1, 2)

        email_f = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        human_type(email_f, self.email)

        pw_f = self.driver.find_element(By.ID, "password")
        human_type(pw_f, self.password)

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

        WebDriverWait(self.driver, 40).until(
            EC.any_of(EC.url_contains("feed"), EC.url_contains("checkpoint"))
        )
        if "checkpoint" in self.driver.current_url:
            raise RuntimeError("LinkedIn is asking for verification — please verify manually first.")
        logger.info("✅ Logged in!")
        human_sleep(2, 3)

    # ── Company page switch ──────────────────────────────────────────────────
    def switch_to_company(self, company_name: str) -> bool:
        """
        Switch LinkedIn 'posting identity' to a company page.
        Works with LinkedIn's 2025 nav identity-switcher.
        """
        if not company_name.strip():
            return False

        logger.info(f"🏢 Switching to company page: {company_name}")
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            human_sleep(3, 5)

            # ── Step 1: open the "Me" dropdown ───────────────────────────────
            me_triggers = [
                "//button[contains(@class,'global-nav__primary-link') and .//span[contains(@class,'nav-item__profile-member-photo')]]",
                "//div[contains(@class,'global-nav__me')]//button",
                "//span[text()='Me']/ancestor::button",
                "//li[contains(@class,'global-nav__primary-item')]//button[@aria-label]",
            ]
            me_btn = None
            for sel in me_triggers:
                try:
                    me_btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    break
                except TimeoutException:
                    continue

            if not me_btn:
                logger.warning("⚠️ Could not find Me button — trying alternate switch method")
                return self._switch_via_post_box(company_name)

            safe_click(self.driver, me_btn)
            human_sleep(1, 2)

            # ── Step 2: find company name in the dropdown ─────────────────────
            company_selectors = [
                f"//span[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'{company_name.upper()}')]",
                f"//div[contains(@class,'artdeco-dropdown__content')]//span[contains(text(),'{company_name}')]",
                f"//li[contains(@class,'artdeco-dropdown__item')]//span[contains(text(),'{company_name}')]",
            ]
            company_item = None
            for sel in company_selectors:
                try:
                    company_item = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    break
                except TimeoutException:
                    continue

            if company_item:
                safe_click(self.driver, company_item)
                human_sleep(3, 5)
                logger.info(f"✅ Switched to: {company_name}")
                return True
            else:
                logger.warning(f"⚠️ '{company_name}' not in Me dropdown — trying post-box method")
                return self._switch_via_post_box(company_name)

        except Exception as e:
            logger.warning(f"⚠️ Company switch error: {e}")
            return False

    def _switch_via_post_box(self, company_name: str) -> bool:
        """
        Fallback: use the 'Posting as' selector inside the post creation box.
        LinkedIn shows this when you have company admin access.
        """
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            human_sleep(3, 5)

            # Click "Start a post"
            start_post_sel = [
                "//span[contains(text(),'Start a post')]",
                "//button[contains(@class,'share-box-feed-entry__trigger')]",
            ]
            for sel in start_post_sel:
                try:
                    btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    safe_click(self.driver, btn)
                    human_sleep(2, 3)
                    break
                except TimeoutException:
                    continue

            # Look for identity dropdown
            identity_sel = [
                "//button[contains(@class,'identity-selector')]",
                "//div[contains(@class,'share-creation-state')]//button",
                "//span[contains(@class,'artdeco-dropdown__trigger')]",
            ]
            for sel in identity_sel:
                try:
                    dropdown = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    safe_click(self.driver, dropdown)
                    human_sleep(1, 2)

                    co = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//span[contains(text(),'{company_name}')]")
                        )
                    )
                    safe_click(self.driver, co)
                    human_sleep(2, 3)

                    # Close the post dialog
                    try:
                        close = self.driver.find_element(
                            By.XPATH, "//button[contains(@aria-label,'Dismiss')]"
                        )
                        close.click()
                    except Exception:
                        pass

                    logger.info(f"✅ Switched via post-box to: {company_name}")
                    return True
                except TimeoutException:
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Post-box switch failed: {e}")

        logger.warning("⚠️ Could not switch to company page — continuing as personal profile")
        return False

    # ── Like post ────────────────────────────────────────────────────────────
    def like_post(self) -> bool:
        """
        Like the main post on the current page.
        Uses multiple selector strategies for 2025/2026 LinkedIn DOM.
        """
        logger.info("❤️ Attempting to like post…")
        human_scroll(self.driver, 2)
        human_sleep(2, 4)

        # LinkedIn 2025: like button is a <button> with aria-label like
        # "React to <Name>'s post"  OR  class contains "react-button__trigger"
        selectors = [
            # Most reliable in 2025 — react button trigger
            "//button[contains(@class,'react-button__trigger')]",
            # aria-label pattern: "React to X's post"
            "//button[contains(@aria-label,'React to') and contains(@aria-label,'post')]",
            # Generic Like aria-label (older posts / reshares)
            "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'comment'))]",
            # data-control-name
            "//button[@data-control-name='react_to_post']",
            # span with text Like inside a button (some feed variants)
            "//button[.//span[text()='Like']]",
        ]

        like_btn = None
        for sel in selectors:
            try:
                candidates = self.driver.find_elements(By.XPATH, sel)
                for btn in candidates:
                    # Skip buttons that are already reacted
                    pressed = btn.get_attribute("aria-pressed")
                    if pressed == "true":
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
            # Last resort: find by SVG title or reaction container
            try:
                like_btn = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'social-actions')]//button[1]"
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

    # ── Like comments ────────────────────────────────────────────────────────
    def like_comments(self) -> bool:
        """
        Like ALL comments on the current post page.
        Uses 2025/2026 LinkedIn comment DOM selectors.
        """
        logger.info("💬 Looking for comments to like…")
        human_scroll(self.driver, 3)
        human_sleep(3, 5)

        # Expand comments if needed
        expand_selectors = [
            "//button[contains(@aria-label,'Load previous comments')]",
            "//button[contains(@aria-label,'See more comments')]",
            "//button[contains(text(),'comments')]",
        ]
        for sel in expand_selectors:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                safe_click(self.driver, btn)
                human_sleep(2, 3)
                break
            except Exception:
                pass

        human_scroll(self.driver, 2)
        human_sleep(2, 3)

        # LinkedIn 2025 comment like button selectors
        comment_selectors = [
            # react-button inside a comment item
            "//div[contains(@class,'comment') or contains(@class,'Comment')]"
            "//button[contains(@class,'react-button__trigger')]",
            # aria-label: "React to <Name>'s comment"
            "//button[contains(@aria-label,'React to') and contains(@aria-label,'comment')]",
            # Older pattern
            "//button[contains(@aria-label,'Like') and contains(@aria-label,'comment')]",
            # Generic: all react buttons on the page (post + comments), skip first (post)
            "//button[contains(@class,'react-button__trigger')]",
        ]

        all_btns = []
        for sel in comment_selectors:
            try:
                found = self.driver.find_elements(By.XPATH, sel)
                # Filter out already-liked and the main post like button
                for b in found:
                    if b.get_attribute("aria-pressed") != "true" and b not in all_btns:
                        all_btns.append(b)
                if all_btns:
                    break
            except Exception:
                continue

        # If we got all react-buttons including the post button, skip the first one
        if all_btns and "post" not in (all_btns[0].get_attribute("aria-label") or "").lower():
            pass  # already comment buttons only
        elif len(all_btns) > 1:
            all_btns = all_btns[1:]  # skip post like button

        logger.info(f"📝 Found {len(all_btns)} comment like button(s)")

        liked = 0
        for btn in all_btns:          # ← no limit, like ALL comments
            if self.stopped():
                break
            try:
                safe_click(self.driver, btn)
                human_sleep(
                    Config.COMMENT_MIN_WAIT,
                    Config.COMMENT_MAX_WAIT
                )
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
        self.client.login()

        company = getattr(self.config, "COMPANY_NAME", "").strip()
        if company:
            switched = self.client.switch_to_company(company)
            if not switched:
                logger.warning(f"⚠️ Proceeding as personal profile — '{company}' switch failed")

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
                logger.warning(f"Row {i+1}: No URL found")
                handler.update_status(i, "NO_URL")
                continue

            logger.info(f"\n{'='*55}\n[{i+1}/{len(rows)}] {post_url[:55]}…\n{'='*55}")

            try:
                logger.info(f"🌐 Opening post URL…")
                self.client.driver.get(post_url)
                human_sleep(3, 5)           # was 8-12s

                post_liked     = self.client.like_post()
                human_pause()               # now 1-2s, was 3-7s
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
                logger.info(f"😴 Waiting {delay:.0f}s before next row…")
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
