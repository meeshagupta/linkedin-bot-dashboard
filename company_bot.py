"""
company_bot.py — LinkedIn automation for COMPANY page accounts.
Selectors, click logic and company switcher taken from proven working local scripts (13.py).
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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from chrome_utils import get_chrome_driver
from session_manager import SessionManager

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = "temp_creds.json"
    GOOGLE_SHEET_URL        = ""
    LINKEDIN_EMAIL          = ""
    LINKEDIN_PASSWORD       = ""
    COMPANY_NAME            = ""
    MIN_DELAY               = 5
    MAX_DELAY               = 8
    COMMENT_MIN_WAIT        = 1
    COMMENT_MAX_WAIT        = 2
    HEADLESS_MODE           = True
    LOG_FILE                = "bot_logs.txt"
    COOKIE_FILE             = "linkedin_session.pkl"

# ==================== LOGGER ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("CompanyBot")

# ==================== STEALTH HELPERS ====================
def human_sleep(a=0.5, b=1.5):
    time.sleep(random.uniform(a, b))

def human_pause(a=2, b=5):
    t = random.uniform(a, b)
    logger.info(f"Pause {t:.1f}s")
    time.sleep(t)

def human_scroll(driver, times=3):
    for _ in range(times):
        driver.execute_script(f"window.scrollBy(0, {random.randint(200, 600)});")
        time.sleep(random.uniform(0.3, 0.8))

def human_type(element, text):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(0.05, 0.15))
    time.sleep(0.5)

def js_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(random.uniform(0.3, 0.7))
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
        logger.info(f"Loaded {len(records)} rows")
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
                logger.info(f"Row {row_index+2}: {status}")
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
    def __init__(self, email, password, headless=True, stop_event=None):
        self.email      = email
        self.password   = password
        self.headless   = headless
        self.stop_event = stop_event or threading.Event()
        self.driver     = None

    def setup_driver(self):
        self.driver = get_chrome_driver(headless=self.headless)
        logger.info("Chrome ready!")

    def stopped(self):
        return self.stop_event.is_set()

    def login(self, cookie_file="linkedin_session.pkl"):
        logger.info("Checking for saved session...")
        if SessionManager.load(self.driver, cookie_file):
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(5)
            url = self.driver.current_url
            if "feed" in url or "mynetwork" in url:
                logger.info("Resumed from saved session - no login needed!")
                return
            logger.warning("Session cookie expired - doing fresh login...")

        logger.info("Logging in with credentials...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(random.uniform(3, 5))

        email_f = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        human_type(email_f, self.email)
        time.sleep(random.uniform(1, 2))

        pw_f = self.driver.find_element(By.ID, "password")
        human_type(pw_f, self.password)
        time.sleep(random.uniform(1, 2))

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

        WebDriverWait(self.driver, 60).until(
            EC.any_of(EC.url_contains("feed"), EC.url_contains("checkpoint"))
        )
        if "checkpoint" in self.driver.current_url:
            raise RuntimeError(
                "LinkedIn verification required. "
                "Run generate_session.py on your PC, complete verification, "
                "then upload linkedin_session.pkl via the sidebar."
            )

        logger.info("Logged in!")
        time.sleep(random.uniform(3, 5))
        SessionManager.save(self.driver, cookie_file)
        logger.info("Session saved for next run")

    def switch_to_company(self, company_name: str) -> bool:
        """
        Switch LinkedIn posting identity to a company page.
        Logic taken directly from proven working script (13.py).
        """
        if not company_name.strip():
            return False

        try:
            logger.info(f"Opening company switcher for: '{company_name}'")
            time.sleep(random.uniform(8, 12))

            # Open the identity switcher dropdown
            circle_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(@aria-label,'switching identity') or "
                    "contains(@aria-label,'Open menu for switching')]"
                ))
            )
            self.driver.execute_script("arguments[0].click();", circle_btn)
            time.sleep(random.uniform(4, 6))

            logger.info(f"Looking for exact match: '{company_name}'")

            # Exact match selectors (from proven 13.py)
            exact_selectors = [
                f"//li[.//text()[normalize-space()='{company_name}']]",
                f"//div[.//text()[normalize-space()='{company_name}']]",
                f"//li[contains(@role,'option') or @role='menuitem'][normalize-space(.//text())='{company_name}']",
                f"//div[contains(@role,'option') or @role='menuitem'][normalize-space(.//text())='{company_name}']",
                f"//*[@aria-label='{company_name}' or @aria-labelledby='{company_name}']",
                f"//*[normalize-space(text())='{company_name}' or normalize-space()='{company_name}']",
            ]

            company_el = None
            for i, selector in enumerate(exact_selectors, 1):
                try:
                    company_el = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    logger.info(f"Exact match found (selector #{i}): '{company_el.text.strip()}'")
                    break
                except Exception:
                    continue

            if not company_el:
                # Strict fallback: all words must appear
                words = company_name.split()
                conditions = [
                    f'contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{w.lower()}")'
                    for w in words
                ]
                fuzzy_xpath = (
                    f"//li[{' and '.join(conditions)}]"
                    f"[string-length(normalize-space(.)) > {len(company_name) - 3}]"
                )
                try:
                    company_el = self.driver.find_element(By.XPATH, fuzzy_xpath)
                    logger.info(f"Fuzzy match: '{company_el.text.strip()[:50]}'")
                except Exception:
                    logger.warning(f"Company '{company_name}' not found in switcher")
                    return False

            # Human click
            logger.info(f"Clicking: '{company_el.text.strip()}'")
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", company_el)
            time.sleep(random.uniform(1, 2))
            ActionChains(self.driver).move_to_element(company_el).click().perform()
            time.sleep(random.uniform(3, 5))

            # Click Save button
            try:
                save_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[(contains(text(),'Save') or contains(@aria-label,'Save')) "
                        "and not(contains(@disabled,'true'))]"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", save_btn)
                logger.info("Saved! Company switch successful!")
                time.sleep(random.uniform(3, 5))
                return True
            except Exception:
                logger.warning("No Save button found - may have auto-switched")
                return True

        except Exception as e:
            logger.error(f"Company switch failed: {str(e)[:100]}")
            return False

    def like_post(self) -> bool:
        logger.info("Attempting to like post...")

        human_scroll(self.driver, 3)
        time.sleep(random.uniform(2, 4))

        self.driver.execute_script("""
            document.querySelectorAll(
                '.feed-shared-social-actions, [role="group"], .social-details__action-list,
                 .main-feed-activity-card__social-actions'
            ).forEach(el => el.scrollIntoView({block: 'center'}));
        """)
        time.sleep(random.uniform(2, 3))

        selectors = [
            "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'comment')) and not(contains(@aria-label,'Comment'))]",
            "//button[contains(@aria-label,'React Like')]",
            "//button[@data-control-name='react_to_post']",
        ]

        post_btn = None
        for selector in selectors:
            try:
                post_btn = WebDriverWait(self.driver, 12).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                logger.info("Like button found")
                break
            except TimeoutException:
                continue
            except Exception:
                continue

        if not post_btn:
            logger.warning("No post like button found")
            return False

        pressed = post_btn.get_attribute("aria-pressed") or ""
        label   = (post_btn.get_attribute("aria-label") or "").lower()
        if pressed == "true" or "unlike" in label:
            logger.info("Post already liked")
            return True

        try:
            js_click(self.driver, post_btn)
            time.sleep(random.uniform(3, 5))
            logger.info("POST LIKED!")
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False

    def like_comments(self) -> bool:
        logger.info("Looking for comments to like...")
        human_pause(2, 4)

        for _ in range(4):
            human_scroll(self.driver, 2)
            time.sleep(random.uniform(2, 4))

        for sel in [
            "//button[contains(@aria-label,'Load previous comments')]",
            "//button[contains(@aria-label,'See more comments')]",
            "//button[contains(@aria-label,'View more comments')]",
        ]:
            try:
                btn = self.driver.find_element(By.XPATH, sel)
                js_click(self.driver, btn)
                time.sleep(random.uniform(2, 3))
                break
            except Exception:
                pass

        human_scroll(self.driver, 2)
        time.sleep(random.uniform(2, 3))

        like_selectors = [
            "//button[contains(@aria-label,'React Like') and not(contains(@aria-label,'Unreact'))]",
            "//button[contains(@aria-label,'Like') and contains(@aria-label,'comment') and not(contains(@aria-label,'Unlike'))]",
        ]

        all_btns = []
        seen = set()

        for selector in like_selectors:
            try:
                buttons = self.driver.find_elements(By.XPATH, selector)
                logger.info(f"Found {len(buttons)} buttons via selector")

                for btn in buttons:
                    try:
                        btn_id = f"{btn.location['x']}_{btn.location['y']}"
                        if btn_id in seen:
                            continue
                        if not btn.is_displayed():
                            continue
                        aria   = (btn.get_attribute("aria-label") or "").lower()
                        pressed = btn.get_attribute("aria-pressed")
                        if pressed == "true" or "unreact" in aria or "unlike" in aria:
                            continue
                        all_btns.append(btn)
                        seen.add(btn_id)
                        logger.info(f"Target: '{btn.get_attribute('aria-label')[:60]}'")
                    except Exception:
                        continue

                if all_btns:
                    break
            except Exception:
                continue

        logger.info(f"Found {len(all_btns)} comment like button(s)")

        liked = 0
        for i, btn in enumerate(all_btns):
            if self.stopped():
                break
            try:
                js_click(self.driver, btn)
                time.sleep(random.uniform(Config.COMMENT_MIN_WAIT, Config.COMMENT_MAX_WAIT))
                liked += 1
                logger.info(f"Comment {liked}/{len(all_btns)} liked")
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.warning(f"Comment like failed: {e}")
                continue

        logger.info(f"{liked} comment(s) liked")
        return liked > 0

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

# ==================== MAIN BOT ====================
class LinkedInCommentLiker:
    def __init__(self, config, stop_event=None):
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
            logger.error("No rows found in sheet")
            return

        company = getattr(self.config, "COMPANY_NAME", "").strip()
        processed = 0

        for i, row in enumerate(rows):

            if self.stop_event.is_set():
                logger.info("Stopped by user")
                break

            if handler.is_row_done(i):
                logger.info(f"Row {i+1}: Already DONE - skipping")
                continue

            post_url = str(
                row.get("Post Url") or row.get("Comment URL") or ""
            ).strip()

            if not post_url or post_url.lower() == "nan":
                logger.warning(f"Row {i+1}: No URL")
                handler.update_status(i, "NO_URL")
                continue

            logger.info(f"\n{'='*55}\n[{i+1}/{len(rows)}] {post_url[:55]}\n{'='*55}")

            try:
                # Go to feed first (prevents public/cold-join view on post URL)
                logger.info("Navigating to feed first...")
                self.client.driver.get("https://www.linkedin.com/feed/")
                time.sleep(random.uniform(3, 5))

                logger.info("Opening post URL...")
                self.client.driver.get(post_url)
                time.sleep(random.uniform(8, 12))

                # Safety check
                current_url = self.client.driver.current_url
                if any(x in current_url for x in ["signup", "login", "cold-join", "authwall"]):
                    logger.warning(f"Redirected to: {current_url} - session may have expired")
                    handler.update_status(i, "SESSION_EXPIRED")
                    continue

                # Scroll social bar into view
                self.client.driver.execute_script("""
                    document.querySelectorAll(
                        '.feed-shared-social-actions, [role="group"],
                         .social-details__action-list,
                         .main-feed-activity-card__social-actions'
                    ).forEach(el => el.scrollIntoView({block: 'center'}));
                """)
                time.sleep(random.uniform(2, 3))

                # Switch to company page if configured
                profile_type = "PERSONAL"
                if company:
                    switched = self.client.switch_to_company(company)
                    profile_type = "COMPANY" if switched else "PERSONAL"
                    logger.info(f"Using {profile_type} profile")

                post_liked     = self.client.like_post()
                human_pause(2, 4)
                comments_liked = self.client.like_comments()

                status = (
                    f"{profile_type}:DONE"      if post_liked and comments_liked else
                    f"{profile_type}:POST_ONLY" if post_liked                    else
                    f"{profile_type}:FAILED"
                )
                handler.update_status(i, status)
                processed += 1

            except Exception as e:
                logger.error(f"Row {i+1} error: {e}")
                handler.update_status(i, "ERROR")

            if not self.stop_event.is_set() and i < len(rows) - 1:
                delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
                logger.info(f"Waiting {delay:.0f}s...")
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)

        logger.info(f"Finished! {processed}/{len(rows)} processed")
        if self.client:
            self.client.close()

if __name__ == "__main__":
    bot = LinkedInCommentLiker(Config)
    bot.initialize()
    bot.run()
