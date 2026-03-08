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

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = r"C:\\Users\\priyanka\\.ipython\\Credentials.json"
    GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DJBkhAtRePpmQHC2oYZV_0J5lzdnSuXklRLYMBbUMf4/edit"
    LINKEDIN_EMAIL = "shruti.shar10@gmail.com"
    LINKEDIN_PASSWORD = "PSabcD@123456!"
    MIN_DELAY = 20
    MAX_DELAY = 35
    COMMENT_MIN_WAIT = 10
    COMMENT_MAX_WAIT = 20
    HEADLESS_MODE = False
    LOG_FILE = "bot_logs.txt"

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
    pause = random.uniform(3, 8)
    logger.info(f"⏳ Human pause... {pause:.1f}s")
    time.sleep(pause)

def human_scroll(driver):
    for _ in range(random.randint(2, 4)):
        scroll = random.randint(200, 600)
        driver.execute_script(f"window.scrollBy(0, {scroll});")
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
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_url(sheet_url).sheet1
    
    def read_file(self):
        records = self.sheet.get_all_records()
        logger.info(f"✅ Loaded {len(records)} rows")
        return records
    
    def update_status(self, row_index, status):
        try:
            headers = self.sheet.row_values(1)
            status_col = None
            for col, header in enumerate(headers, 1):
                if 'status' in header.lower():
                    status_col = col
                    break
            
            if status_col:
                row_num = row_index + 2
                self.sheet.update_cell(row_num, status_col, f"{status} @ {datetime.now().strftime('%H:%M')}")
                logger.info(f"📝 Row {row_num}: {status}")
        except Exception as e:
            logger.error(f"Sheet update failed: {e}")
    
    def is_row_done(self, row_index):
        try:
            headers = self.sheet.row_values(1)
            status_col = None
            for col, header in enumerate(headers, 1):
                if 'status' in header.lower():
                    status_col = col
                    break
            if status_col:
                row_num = row_index + 2
                status = self.sheet.cell(row_num, status_col).value or ""
                return 'done' in status.lower()
            return False
        except:
            return False

# ==================== SELENIUM CLIENT (2026 PROVEN) ====================
class LinkedInClient:
    def __init__(self, email, password, headless=False):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        options = Options()
        
        # CLEAN FLAGS - NO DUPLICATES
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--window-size=1920,1080')
        
        # 2026 STEALTH
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # ULTRA STEALTH
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            '''
        })
        self.driver.implicitly_wait(15)
        logger.info("🚀 2026 STEALTH Chrome ready!")
    
    def login(self):
        try:
            logger.info("🔐 Logging in...")
            self.driver.get("https://www.linkedin.com/login")
            human_sleep(4, 6)
            
            # Login fields
            email_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_type(email_field, self.email)
            
            password_field = self.driver.find_element(By.ID, "password")
            human_type(password_field, self.password)
            
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
            
            # Wait for feed or checkpoint
            WebDriverWait(self.driver, 40).until(
                EC.any_of(
                    EC.url_contains("feed"),
                    EC.url_contains("checkpoint")
                )
            )
            logger.info("✅ LOGIN SUCCESS!")
            human_sleep(5, 8)
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            self.driver.save_screenshot("login_error.png")
            raise
    
    def like_post(self):
        try:
            logger.info("❤️ Finding post like...")
            human_scroll(self.driver)
            human_sleep(3, 5)
            
            # 2026 WORKING SELECTORS
            selectors = [
                "//button[contains(@aria-label,'Like') or contains(@aria-label,'like')]",
                "//div[@role='button' and contains(@aria-label,'Like')]",
                "//button[contains(@data-control-name,'like')]",
                "//*[name()='button' and .//*[name()='svg' and contains(@aria-label,'Like')]]"
            ]
            
            like_btn = None
            for selector in selectors:
                try:
                    like_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not like_btn:
                logger.warning("❌ No like button found")
                self.driver.save_screenshot("no_like.png")
                return False
            
            # Skip if already liked
            if like_btn.get_attribute("aria-pressed") == "true":
                logger.info("ℹ️ Already liked")
                return True
            
            # Human click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_btn)
            human_sleep(2, 3)
            ActionChains(self.driver).move_to_element(like_btn).click().perform()
            human_sleep(3, 5)
            
            logger.info("✅ POST LIKED!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Post like failed: {e}")
            return False
    
    def like_comments(self):
        try:
            logger.info("💬 Finding comments...")
            human_scroll(self.driver)
            human_sleep(4, 6)
            
            # Load more comments
            try:
                more_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label,'See more comments')]")
                more_btn.click()
                human_sleep(3, 5)
            except:
                pass
            
            # 2026 comment selectors
            comment_selectors = [
                "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'Unlike'))]",
                "//div[@role='button' and contains(@aria-label,'Like comment')]"
            ]
            
            all_comments = []
            for selector in comment_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    all_comments.extend([b for b in buttons if b.get_attribute("aria-pressed") != "true"])
                except:
                    continue
            
            logger.info(f"📝 Found {len(all_comments)} comments")
            
            # Like first 3 (human behavior)
            liked = 0
            for i, comment in enumerate(all_comments[:3]):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", comment)
                    ActionChains(self.driver).move_to_element(comment).click().perform()
                    human_comment_wait()
                    logger.info(f"✅ Comment {i+1}/3 liked")
                    liked += 1
                except:
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

# ==================== MAIN BOT ====================
class LinkedInBot:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.sheet_handler = GoogleSheetHandler(config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SHEET_URL)
    
    def run(self):
        try:
            # Initialize
            self.client = LinkedInClient(
                self.config.LINKEDIN_EMAIL,
                self.config.LINKEDIN_PASSWORD,
                self.config.HEADLESS_MODE
            )
            self.client.login()
            
            # Process rows
            rows = self.sheet_handler.read_file()
            if not rows:
                logger.error("❌ No data in sheet")
                return
            
            processed = 0
            for i, row in enumerate(rows):
                if self.sheet_handler.is_row_done(i):
                    logger.info(f"⏭️ Row {i+1}: Already done")
                    continue
                
                post_url = str(row.get("Post Url") or row.get("Comment URL") or "").strip()
                if not post_url or post_url == "nan":
                    logger.warning(f"Row {i+1}: No URL")
                    self.sheet_handler.update_status(i, "NO_URL")
                    continue
                
                logger.info(f"\n{'='*60}")
                logger.info(f"[{i+1}/{len(rows)}] {post_url[:60]}...")
                logger.info(f"{'='*60}")
                
                try:
                    # Visit post
                    self.client.driver.get(post_url)
                    human_sleep(8, 12)
                    
                    # Take screenshot
                    self.client.driver.save_screenshot(f"debug_row_{i+1}.png")
                    
                    # Like post + comments
                    post_liked = self.client.like_post()
                    human_pause()
                    comments_liked = self.client.like_comments()
                    
                    # Update status
                    if post_liked and comments_liked:
                        status = "DONE"
                    elif post_liked:
                        status = "POST_ONLY"
                    else:
                        status = "FAILED"
                    
                    self.sheet_handler.update_status(i, status)
                    logger.info(f"✅ RESULT: {status}")
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"❌ Row {i+1} failed: {e}")
                    self.sheet_handler.update_status(i, "ERROR")
                
                # Stealth delay
                if processed < len(rows):
                    delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
                    logger.info(f"😴 Next in {delay:.1f}s")
                    time.sleep(delay)
            
            logger.info(f"\n🎉 COMPLETE! {processed}/{len(rows)} processed")
            
        except KeyboardInterrupt:
            logger.info("⏹️ Stopped by user")
        except Exception as e:
            logger.error(f"💥 Fatal: {e}")
        finally:
            if self.client:
                self.client.close()

if __name__ == "__main__":
    bot = LinkedInBot(Config)
    bot.run()
