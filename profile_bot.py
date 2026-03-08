import pandas as pd
import time
import random
import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import json

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = r"C:\\Users\\priyanka\\.ipython\\Credentials.json"
    GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DJBkhAtRePpmQHC2oYZV_0J5lzdnSuXklRLYMBbUMf4/edit"
    LINKEDIN_EMAIL = "shruti.shar10@gmail.com"
    LINKEDIN_PASSWORD = "PSabcD@123456!"
    MIN_DELAY = 25
    MAX_DELAY = 50
    COMMENT_MIN_WAIT = 12
    COMMENT_MAX_WAIT = 25
    HEADLESS_MODE = False
    LOG_FILE = "bot_logs.txt"
    TARGET_NAMES = [
        "Bim Sphere", "Anuj Kumar Gupta", "Glaztower", "Ayush Nagar Koti", 
        "BrikAtrium", "Coolrise", "Structoria", "Design Veil", "PLENORISE", 
        "AXIALITH", "SILLTRACE", "Nitin Gupta", "Vimal Yadav", "Sagar Rawat"
    ]

# ==================== LOGGER ====================
def setup_logger(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("LinkedInBot")

logger = setup_logger(Config.LOG_FILE)

# ==================== STEALTH HELPERS ====================
def human_sleep(a=1, b=3):
    time.sleep(random.uniform(a, b))

def human_pause():
    pause = random.uniform(4, 15)
    logger.info(f"⏳ Human pause... {pause:.1f}s")
    time.sleep(pause)

def human_scroll(driver):
    scrolls = random.randint(2, 5)
    for _ in range(scrolls):
        scroll_amount = random.randint(200, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        human_sleep(0.5, 1.5)

def human_mouse_move(driver, element):
    ActionChains(driver).move_to_element(element).perform()
    human_sleep(0.3, 0.8)

def human_type(element, text):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(0.08, 0.25))
    human_sleep(1, 3)

def human_comment_wait():
    wait_time = random.uniform(Config.COMMENT_MIN_WAIT, Config.COMMENT_MAX_WAIT)
    logger.info(f"📖 Reading comment... {wait_time:.1f}s")
    time.sleep(wait_time)

# ==================== GOOGLE SHEET HANDLER ====================
class GoogleSheetHandler:
    def __init__(self, credentials_file, sheet_url):
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_url(sheet_url).sheet1
    
    def read_file(self):
        records = self.sheet.get_all_records()
        logger.info(f"✅ Loaded {len(records)} rows from Google Sheets")
        return records
    
    def update_status(self, row_index, status):
        try:
            headers = self.sheet.row_values(1)
            status_col = None
            for col_num, header in enumerate(headers, 1):
                if "status" in header.lower().strip():
                    status_col = col_num
                    break
        
            if not status_col:
                logger.error("❌ 'Status' header not found!")
                return
            
            row_num = row_index + 2
            self.sheet.update_cell(row_num, status_col, f"{status} @ {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"📝 Updated Row {row_num}: {status}")
        except Exception as e:
            logger.error(f"❌ Status update failed: {e}")

    def is_row_done(self, row_index):
        try:
            headers = self.sheet.row_values(1)
            status_col = None
            for col_num, header in enumerate(headers, 1):
                if "status" in header.lower().strip():
                    status_col = col_num
                    break
            if not status_col:
                return False
            row_num = row_index + 2
            current_status = self.sheet.cell(row_num, status_col).value or ""
            return "done" in current_status.lower()
        except:
            return False

# ==================== SELENIUM CLIENT (2026 FIXED) ====================
class LinkedInSeleniumClient:
    def __init__(self, email, password, headless=False):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        options = Options()
        
        # ✅ STREAMLIT CLOUD FLAGS (SINGLE BLOCK - NO DUPLICATES)
        options.add_argument('--headless=new') if self.headless else None
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-zygote')
        options.add_argument('--single-process')
        
        # ✅ ELITE STEALTH 2026
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        
        # ✅ CHROMIUM FIX
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # ✅ ULTRA STEALTH SCRIPTS
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            '''
        })
        
        self.driver.implicitly_wait(15)
        logger.info("🚀 2026 ELITE STEALTH Chrome ready!")

    def login(self):
        try:
            logger.info("🔐 Logging into LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            human_sleep(5, 8)
            
            # ENTER CREDENTIALS
            email_el = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "username")))
            human_type(email_el, self.email)
            
            password_el = self.driver.find_element(By.ID, "password")
            human_type(password_el, self.password)
            
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
            
            # WAIT FOR FEED OR CHECKPOINT
            WebDriverWait(self.driver, 60).until(
                EC.any_of(EC.url_contains("feed"), EC.url_contains("checkpoint"))
            )
            logger.info("✅ LOGIN SUCCESSFUL!")
            human_sleep(5, 8)
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            self.driver.save_screenshot("login_error.png")
            raise

    def like_post(self):
        """🔥 2026 WORKING POST LIKE METHOD"""
        try:
            logger.info("❤️ Hunting post like button...")
            human_scroll(self.driver)
            human_sleep(3, 5)
            
            # 2026 LINKEDIN SELECTORS (PROVEN)
            selectors = [
                "//button[contains(@aria-label,'Like') or contains(@aria-label,'like')]",
                "//div[@role='button' and contains(@aria-label,'Like')]",
                "//button[contains(@data-control-name,'like')]",
                "//*[contains(@class,'like') and contains(@class,'button')]",
                "//button[.//*[name()='svg' and contains(@aria-hidden,'true')]]"  # Heart icon
            ]
            
            post_btn = None
            for selector in selectors:
                try:
                    post_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    logger.info(f"✅ Post button found: {selector[:40]}")
                    break
                except:
                    continue
            
            if not post_btn:
                logger.warning("❌ No post like button found")
                self.driver.save_screenshot("no_post_like.png")
                return False
            
            # CHECK IF ALREADY LIKED
            if post_btn.get_attribute("aria-pressed") == "true":
                logger.info("ℹ️ Post already liked")
                return True
            
            # HUMAN-LIKE CLICK
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", post_btn)
            human_sleep(2, 4)
            ActionChains(self.driver).move_to_element(post_btn).click().perform()
            human_sleep(4, 7)
            
            logger.info("✅ POST LIKED SUCCESSFULLY!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Post like error: {str(e)[:60]}")
            return False

    def like_comment(self):
        """🔥 2026 WORKING COMMENT LIKE METHOD"""
        try:
            logger.info("💬 Hunting comment likes...")
            human_scroll(self.driver)
            human_sleep(5, 8)
            
            # 2026 COMMENT SELECTORS
            comment_selectors = [
                "//button[contains(@aria-label,'Like')]",
                "//button[contains(@aria-label,'react')]",
                "//div[@role='button' and contains(@aria-label,'Like')]"
            ]
            
            comment_buttons = []
            for selector in comment_selectors:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    aria = btn.get_attribute("aria-label") or ""
                    if "like" in aria.lower() and btn.get_attribute("aria-pressed") != "true":
                        comment_buttons.append(btn)
            
            logger.info(f"📝 Found {len(comment_buttons)} comment buttons")
            
            if not comment_buttons:
                logger.warning("❌ No comment buttons found")
                return False
            
            # LIKE FIRST 3 COMMENTS (HUMAN BEHAVIOR)
            for i, btn in enumerate(comment_buttons[:3]):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    ActionChains(self.driver).move_to_element(btn).click().perform()
                    human_comment_wait()
                    logger.info(f"✅ Comment {i+1}/3 LIKED")
                except:
                    continue
            
            logger.info("✅ Comments liked successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Comment like error: {str(e)[:60]}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")

# ==================== MAIN BOT ====================
class LinkedInCommentLiker:
    def __init__(self, config):
        self.config = config
        self.selenium = None

    def initialize(self):
        self.selenium = LinkedInSeleniumClient(
            self.config.LINKEDIN_EMAIL,
            self.config.LINKEDIN_PASSWORD,
            self.config.HEADLESS_MODE
        )
        self.selenium.login()

    def run(self):
        handler = GoogleSheetHandler(self.config.GOOGLE_CREDENTIALS_FILE, self.config.GOOGLE_SHEET_URL)
        rows = handler.read_file()

        if not rows:
            logger.error("❌ No data found!")
            return
        
        processed = 0
        for i, row in enumerate(rows):
            # ✅ CHECK IF ROW ALREADY DONE
            if handler.is_row_done(i):
                logger.info(f"⏭️ Row {i}: Already DONE - skipping")
                continue
                
            post_url = str(row.get("Post Url") or row.get("Comment URL") or "").strip()
            target_name = str(row.get("Name") or "").strip()
        
            if not post_url or post_url == "nan":
                logger.warning(f"Row {i}: Missing URL - skipping")
                handler.update_status(i, "MISSING_URL")
                continue

            logger.info(f"\n{'='*80}")
            logger.info(f"[{i+1}/{len(rows)}] 🎯 {target_name}")
            logger.info(f"🔗 {post_url[:70]}...")
            logger.info(f"{'='*80}")

            try:
                # 1. NAVIGATE TO POST
                self.selenium.driver.get(post_url)
                human_sleep(10, 15)
                
                # DEBUG SCREENSHOT
                self.selenium.driver.save_screenshot(f"debug_row_{i}.png")
                logger.info(f"📸 Screenshot: debug_row_{i}.png")
                
                # 2. LIKE POST
                post_liked = self.selenium.like_post()
                human_pause()
                
                # 3. LIKE COMMENTS
                target_liked = self.selenium.like_comment()
                
                # 4. UPDATE STATUS
                if post_liked and target_liked:
                    status = f"DONE:{target_name}"
                elif post_liked:
                    status = "POST_ONLY"
                else:
                    status = "FAILED"
                
                handler.update_status(i, status)
                logger.info(f"✅ RESULT: {status}")
                processed += 1

            except Exception as e:
                logger.error(f"❌ Row {i} failed: {str(e)[:60]}")
                handler.update_status(i, f"ERROR")
            
            # STEALTH WAIT
            if processed < len(rows):
                delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
                logger.info(f"😴 Stealth wait: {delay:.1f}s")
                time.sleep(delay)

        logger.info(f"\n🎉 MISSION COMPLETE! {processed}/{len(rows)} processed")

if __name__ == "__main__":
    bot = LinkedInCommentLiker(Config)
    try:
        bot.initialize()
        bot.run()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
    finally:
        if bot.selenium:
            bot.selenium.close()
