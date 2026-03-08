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
from selenium.webdriver.common.action_chains import ActionChains
import json

# ==================== CONFIG ====================
class Config:
    GOOGLE_CREDENTIALS_FILE = r"C:\Users\priyanka\.ipython\Credentials.json"
    GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DJBkhAtRePpmQHC2oYZV_0J5lzdnSuXklRLYMBbUMf4/edit"
    LINKEDIN_EMAIL = "shruti.shar10@gmail.com"
    LINKEDIN_PASSWORD = "PSabcD@123456!"
    MIN_DELAY = 25      # Between posts
    MAX_DELAY = 50      # Between posts
    COMMENT_MIN_WAIT = 12  # Between comments (NEW!)
    COMMENT_MAX_WAIT = 25  # Between comments (NEW!)
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

# ==================== ULTIMATE STEALTH HELPERS ====================
def human_sleep(a=1, b=3):
    time.sleep(random.uniform(a, b))

def human_pause():
    pause = random.uniform(4, 15)
    logger.info(f" Human thinking... {pause:.1f}s")
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
    """ NEW: Human-like wait BETWEEN comments (12-25s)"""
    wait_time = random.uniform(Config.COMMENT_MIN_WAIT, Config.COMMENT_MAX_WAIT)
    logger.info(f" Human reading comment... {wait_time:.1f}s")
    time.sleep(wait_time)

def human_random_actions(driver):
    if random.random() < 0.3:
        actions = [
            lambda: driver.execute_script("window.scrollBy(0, " + str(random.randint(-100, 100)) + ");"),
            lambda: time.sleep(random.uniform(0.5, 2)),
            lambda: driver.execute_script("document.body.click();")
        ]
        random.choice(actions)()

# ==================== GOOGLE SHEET HANDLER ====================
class GoogleSheetHandler:
    def __init__(self, credentials_file, sheet_url):
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_url(sheet_url).sheet1  # First sheet tab
    
    def read_file(self):
        records = self.sheet.get_all_records()  # Same format as pandas!
        logger.info(f" Loaded {len(records)} rows from Google Sheets [web:220]")
        return records
    
    def update_status(self, row_index, status):
        """Finds 'Status' header automatically & updates there!"""
        try:
            # Get headers from Row 1
            headers = self.sheet.row_values(1)
            logger.info(f"Headers found: {headers}")
        
            # Find "Status" column
            status_col = None
            for col_num, header in enumerate(headers, 1):
                if "status" in header.lower().strip():  # Case-insensitive
                    status_col = col_num
                    logger.info(f"Status column found at #{status_col}: '{header}'")
                    break
        
            if not status_col:
                logger.error(" 'Status' header not found! Add 'Status' to Row 1")
                return
        
            # Update the Status cell
            row_num = row_index + 2  # Skip header row
            self.sheet.update_cell(row_num, status_col, f"{status} @ {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f" Updated Row {row_num}, Col{status_col} ({chr(64+status_col)}): {status}")
        
        except Exception as e:
            logger.error(f"Status update failed: {e}")

     
    def is_row_done(self, row_index):
        """Check if row already has DONE status"""
        try:
            headers = self.sheet.row_values(1)
            status_col = None
            for col_num, header in enumerate(headers, 1):
                if "status" in header.lower().strip():
                    status_col = col_num
                    break
        
            if not status_col:
                return False
        
            row_num = row_index + 2  # Skip header
            current_status = self.sheet.cell(row_num, status_col).value or ""
        
            # Check if contains "DONE" (case-insensitive)
            return "done" in current_status.lower()
    
        except Exception as e:
            logger.warning(f"Could not check row {row_index} status: {e}") 
            return False


# ==================== SELENIUM CLIENT ====================
class LinkedInSeleniumClient:
    def __init__(self, email, password, headless=False):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()

    #  CLOUD DEVTOOLSPORT FIX (ADD THESE 4 LINES!)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-pipe')  #  KEY FIX!
    options.add_argument('--disable-gpu')

    # YOUR 2026 ELITE STEALTH (KEEP ALL!)
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logger"])
    options.add_experimental_option('useAutomationExtension', False)

    # BANNER KILLER (Chrome 120+)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")  # Legacy support

    # NO "NEW DEVICE" EMAILS
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")

    # HUMAN CHROME PROFILE
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")  # Linux UA!
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    if self.headless:
        options.add_argument("--headless=new")  # Modern headless

    # Create driver
    service = Service(ChromeDriverManager().install())
    self.driver = webdriver.Chrome(service=service, options=options)

    # YOUR ULTRA STEALTH SCRIPTS (KEEP!)
    self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // Block ALL webdriver detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        
            // Fake Chrome object
            window.chrome = {
                runtime: {
                    PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros' },
                    PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                },
            };
        
            // Fake plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        
            // Block automation flags
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        
            // Permissions API spoofing
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        '''
    })

    # Extra stealth
    self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined,});")

    self.driver.implicitly_wait(15)
    logger.info(" CLOUD DEVTOOLSPORT FIXED - ELITE STEALTH Chrome ready!")




    def login(self):
        try:
            logger.info(" Logging in...")
            self.driver.get("https://www.linkedin.com/login")
            human_sleep(4, 7)
            human_scroll(self.driver)

            email_el = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_mouse_move(self.driver, email_el)
            human_type(email_el, self.email)
            human_pause()

            password_el = self.driver.find_element(By.ID, "password")
            human_mouse_move(self.driver, password_el)
            human_type(password_el, self.password)
            human_pause()
            
            #  IDEA: UNCHECK "Keep me logged in"
            try:
                remember_checkbox = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and (@name='remember' or contains(@aria-label,'Remember') or contains(@id,'remember'))]"))
                )
                if remember_checkbox.is_selected():
                    logger.info(" Unchecking 'Keep me logged in'...")
                    self.driver.execute_script("arguments[0].click();", remember_checkbox)
                    human_sleep(1, 2)
                else:
                    logger.info(" 'Keep me logged in' already unchecked")
            except:
                logger.info(" No 'Keep me logged in' checkbox found")

            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            human_mouse_move(self.driver, login_btn)
            human_sleep(2, 4)
            login_btn.click()
            
            human_pause()
            WebDriverWait(self.driver, 60).until(
                EC.any_of(EC.url_contains("feed"), EC.url_contains("checkpoint"))
            )
            logger.info("LOGIN SUCCESSFUL")
            human_pause()
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise

    def like_post(self):
        try:
            logger.info(" Hunting post like...")
            human_pause()
            human_scroll(self.driver)
            
            selectors = [
                "//button[contains(@aria-label,'Like')]",
                "//button[contains(@aria-label,'React Like')]",
                "//button[@data-control-name*='like']"
            ]
        
            post_btn = None
            for selector in selectors:
                try:
                    post_btn = WebDriverWait(self.driver, 12).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    logger.info(" Post button found")
                    break
                except:
                    continue
        
            if not post_btn:
                logger.warning(" No post like button")
                return False
            
            if post_btn.get_attribute("aria-pressed") == "true":
                logger.info(" Post already liked")
                return True
            
            human_mouse_move(self.driver, post_btn)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", post_btn)
            human_pause()
            self.driver.execute_script("arguments[0].click();", post_btn)
            human_sleep(3, 5)
            logger.info(" POST LIKED!")
            human_random_actions(self.driver)
            return True
        except Exception as e:
            logger.warning(f"Post like failed: {str(e)[:50]}")
            return False

    def like_comment(self):
        """ FIXED TARGET LIKING + HUMAN WAITS BETWEEN COMMENTS!"""
        try:
            logger.info(" Hunting TARGET comments...")
            human_pause()
        
            # Aggressive human scrolling to load ALL comments
            for _ in range(4):
                human_scroll(self.driver)
                human_sleep(3, 5)

            #  ULTRA-STRICT SELECTOR - ONLY "React Like" buttons
            like_selectors = [
                "//button[contains(@aria-label,'React Like') and not(contains(@aria-label,'Unreact'))]"
            ]
        
            all_like_buttons = []
            seen_elements = set()
        
            for selector in like_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    logger.info(f" Found {len(buttons)} React Like buttons")
                    
                    for btn in buttons:
                        try:
                            btn_id = f"{id(btn)}_{btn.location['x']}_{btn.location['y']}"
                            if btn_id in seen_elements:
                                continue
                                
                            aria_label = btn.get_attribute("aria-label") or ""
                            aria_lower = aria_label.lower()
                            pressed = btn.get_attribute("aria-pressed")
                            
                            #  PERFECT FILTER
                            if (pressed != "true" and 
                                "react like" in aria_lower and 
                                "unreact" not in aria_lower and
                                any(name.lower() in aria_lower for name in Config.TARGET_NAMES)):
                                
                                all_like_buttons.append(btn)
                                seen_elements.add(btn_id)
                                logger.info(f" TARGET KEPT: '{aria_label[:50]}'")
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Selector failed: {str(e)[:40]}")
                    continue
        
            logger.info(f" {len(all_like_buttons)} CLEAN TARGETS READY!")
        
            if not all_like_buttons:
                logger.info(" No new targets found")
                return True
        
            #  EXECUTE LIKES WITH HUMAN-LIKE WAITS BETWEEN EACH!
            liked_count = 0
            for i, target_btn in enumerate(all_like_buttons):
                try:
                    aria = target_btn.get_attribute("aria-label") or "Target"
                    logger.info(f" #{i+1}/{len(all_like_buttons)} → '{aria[:40]}'")
                
                    # Human behavior BEFORE clicking
                    human_mouse_move(self.driver, target_btn)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_btn)
                    human_sleep(2, 4)
                
                    #  HUMAN WAIT BEFORE CLICK (like reading comment)
                    human_comment_wait()
                
                    # SINGLE CLICK + VERIFICATION
                    self.driver.execute_script("arguments[0].click();", target_btn)
                    human_sleep(5, 8)
                
                    #  FINAL STATE CHECK
                    final_aria = target_btn.get_attribute("aria-label") or ""
                    final_pressed = target_btn.get_attribute("aria-pressed")
                    
                    if ("unlike" in final_aria.lower() or 
                        final_pressed == "true"):
                        logger.info(f" #{i+1} LIKED  (aria='{final_aria[:30]}')")
                        liked_count += 1
                    else:
                        logger.warning(f" #{i+1} UNCERTAIN (aria='{final_aria[:30]}')")
                
                    human_random_actions(self.driver)
                    
                    #  CRITICAL: HUMAN WAIT BETWEEN COMMENTS!
                    if i < len(all_like_buttons) - 1:
                        logger.info(f" Moving to next comment... (human pattern)")
                        human_comment_wait()
                    
                except Exception as e:
                    logger.warning(f"#{i+1} error: {str(e)[:40]}")
                    # Still wait even if error
                    if i < len(all_like_buttons) - 1:
                        human_comment_wait()
                    continue
        
            logger.info(f" FINAL: {liked_count}/{len(all_like_buttons)} TARGETS LIKED!")
            return liked_count > 0

        except Exception as e:
            logger.error(f"Comments error: {str(e)[:80]}")
            return False

    def close(self):
        human_sleep(2, 4)
        if self.driver:
            self.driver.quit()
            logger.info(" Session closed")

# ==================== MAIN BOT ====================
class LinkedInCommentLiker:
    def __init__(self, config):
        self.config = config
        self.selenium = None

    def initialize(self):
        try:
            self.selenium = LinkedInSeleniumClient(
                self.config.LINKEDIN_EMAIL,
                self.config.LINKEDIN_PASSWORD,
                self.config.HEADLESS_MODE
            )
            self.selenium.login()
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise

    def run(self):
        handler = GoogleSheetHandler(self.config.GOOGLE_CREDENTIALS_FILE, self.config.GOOGLE_SHEET_URL)
        rows = handler.read_file()

        if not rows:
            logger.error("No data found!")
            return
    
        processed = 0
        for i, row in enumerate(rows):
            if handler.is_row_done(i):
                logger.info(f"Row {i}: Already DONE - skipping")
                continue
        # YOUR PRIORITY: Post → Comment URL → Name
            post_url = str(row.get("Post Url") or row.get("Comment URL") or "").strip()
            target_name = str(row.get("Name") or "").strip()
        
            if not post_url or not target_name or post_url == "nan":
                logger.warning(f"Row {i}: Missing Post/Name - skipping")
                handler.update_status(i, "MISSING_DATA")
                continue

            logger.info(f"\n{'='*90}")
            logger.info(f" [{i+1}/{len(rows)}] POST → TARGET: {target_name}")
            logger.info(f" URL: {post_url[:80]}...")
            logger.info(f"{'='*90}")

            try:
                # 1. Go to post URL (YOUR PRIORITY)
                self.selenium.driver.get(post_url)
                human_sleep(10, 15)

                # 2. SCROLL TO social actions (12.py PROVEN method)
                self.selenium.driver.execute_script("""
                document.querySelectorAll('.feed-shared-social-actions, [role="group"], .social-details__action-list')
                .forEach(el => el.scrollIntoView({block: 'center'}));
                """)
                human_sleep(4, 6)

                # 3. Like post  
                post_liked = self.selenium.like_post()
                human_pause()

                # 4. Like TARGET comment (use like_comment method)
                target_liked = self.selenium.like_comment()

                # 5. Status (SIMPLE - personal profile only)
                if target_liked and post_liked:
                    status = f"DONE:{target_name}"
                elif post_liked:
                    status = "POST_ONLY"
                elif target_liked:
                    status = "COMMENTSONLY"
                else:
                    status = "FAILED"
    
                handler.update_status(i, status)
                logger.info(f" RESULT: {status}")
                processed += 1

            except Exception as e:
                logger.error(f"Row {i} failed: {str(e)[:80]}")
                handler.update_status(i, f"ERROR:{str(e)[:20]}")


            # Stealth wait (12.py style)
            if processed < len(rows):
                delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
                logger.info(f" Stealth wait: {delay:.1f}s")
                time.sleep(delay)

        logger.info(f"\n MISSION COMPLETE! {processed}/{len(rows)} processed")

if __name__ == "__main__":
    bot = LinkedInCommentLiker(Config)
    try:
        bot.initialize()
        bot.run()
    except KeyboardInterrupt:
        logger.info(" Bot stopped by user")
    except Exception as e:
        logger.error(f" Fatal error: {e}")
    finally:
        if bot.selenium:
            bot.selenium.close()

