import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging

class LinkedInBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LinkedIn Bot - STOP Anytime!")
        self.root.geometry("900x700")
        
        self.bot_running = False
        self.bot_thread = None
        self.driver = None
        self.sheet = None
        
        self.setup_logging()
        self.create_widgets()
        self.load_sheet()
    
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
        self.logger = logging.getLogger("BotGUI")
    
    def create_widgets(self):
        # Title
        title = tk.Label(self.root, text="🚀 LinkedIn Post & Comment Liker", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Status Frame
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(status_frame, text="Status:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                   fg="green", font=("Arial", 10))
        self.status_label.pack(anchor="w")
        
        # Progress
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(progress_frame, text="Progress:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.progress_var = tk.StringVar(value="0/0")
        tk.Label(progress_frame, textvariable=self.progress_var, font=("Arial", 12, "bold")).pack(anchor="w")
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(5,0))
        
        # Control Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.start_btn = tk.Button(button_frame, text="▶️ START BOT", command=self.start_bot,
                                 bg="green", fg="white", font=("Arial", 12, "bold"),
                                 width=15, height=2)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(button_frame, text="⏹️ STOP BOT", command=self.stop_bot,
                                bg="red", fg="white", font=("Arial", 12, "bold"),
                                width=15, height=2, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        
        # Logs
        log_frame = tk.LabelFrame(self.root, text="Live Logs", font=("Arial", 10, "bold"))
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def log(self, message):
        self.logger.info(message)
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def load_sheet(self):
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(
                r"C:\Users\priyanka\.ipython\Credentials.json", scopes=scope)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_url(
                "https://docs.google.com/spreadsheets/d/1DJBkhAtRePpmQHC2oYZV_0J5lzdnSuXklRLYMBbUMf4/edit").sheet1
            self.log("✅ Google Sheet loaded")
        except Exception as e:
            self.log(f"❌ Sheet error: {e}")
    
    def setup_driver(self):
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--window-size=1920,1080')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
        })
    
    def login(self):
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(3)
        
        email = self.driver.find_element(By.ID, "username")
        password = self.driver.find_element(By.ID, "password")
        login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        
        for char in "shruti.shar10@gmail.com":
            if not self.bot_running:
                return False
            email.send_keys(char)
            time.sleep(0.1)
        
        for char in "PSabcD@123456!":
            if not self.bot_running:
                return False
            password.send_keys(char)
            time.sleep(0.1)
        
        login_btn.click()
        time.sleep(10)
        return "feed" in self.driver.current_url
    
    def process_row(self, row_index):
        if not self.bot_running:
            return False
        
        row = self.sheet.row_values(row_index + 2)
        post_url = row[0] if row else ""  # Assuming URL in column A
        
        if not post_url or post_url == "nan":
            self.update_status(row_index, "NO_URL")
            return True
        
        self.status_var.set(f"Row {row_index + 1}: {post_url[:50]}...")
        self.root.update()
        
        self.driver.get(post_url)
        time.sleep(8)
        
        # Like post
        try:
            like_btn = self.driver.find_element(By.XPATH, 
                "//button[contains(@aria-label,'Like')]")
            if like_btn.get_attribute("aria-pressed") != "true":
                like_btn.click()
                self.log(f"✅ Row {row_index + 1}: Post liked")
        except:
            self.log(f"⚠️ Row {row_index + 1}: No post like button")
        
        time.sleep(5)
        
        # Like comments
        comments_liked = 0
        try:
            comments = self.driver.find_elements(By.XPATH, 
                "//button[contains(@aria-label,'Like') and not(contains(@aria-label,'Unlike'))]")
            for comment in comments[:3]:
                if not self.bot_running:
                    break
                comment.click()
                comments_liked += 1
                time.sleep(3)
        except:
            pass
        
        status = "DONE" if comments_liked > 0 else "POST_ONLY"
        self.update_status(row_index, status)
        return True
    
    def update_status(self, row_index, status):
        headers = self.sheet.row_values(1)
        status_col = next((i+1 for i, h in enumerate(headers) if 'status' in h.lower()), None)
        if status_col:
            self.sheet.update_cell(row_index + 2, status_col, 
                                 f"{status} @ {datetime.now().strftime('%H:%M')}")
    
    def bot_loop(self):
        self.log("🚀 Bot started!")
        self.setup_driver()
        
        if not self.login():
            self.log("❌ Login failed")
            self.stop_bot()
            return
        
        self.log("✅ Login successful")
        rows = len(self.sheet.get_all_values()) - 1
        processed = 0
        
        for i in range(rows):
            if not self.bot_running:
                self.log("⏹️ Bot stopped by user")
                break
            
            if self.is_row_done(i):
                continue
            
            self.progress_bar['maximum'] = rows
            self.progress_bar['value'] = processed
            self.progress_var.set(f"{processed}/{rows}")
            
            if self.process_row(i):
                processed += 1
            
            if self.bot_running:
                delay = random.uniform(20, 35)
                self.status_var.set(f"Waiting {delay:.0f}s...")
                for _ in range(int(delay)):
                    if not self.bot_running:
                        break
                    time.sleep(1)
        
        self.log(f"🎉 Complete! {processed}/{rows}")
        self.stop_bot()
    
    def is_row_done(self, row_index):
        headers = self.sheet.row_values(1)
        status_col = next((i+1 for i, h in enumerate(headers) if 'status' in h.lower()), None)
        if status_col:
            status = self.sheet.cell(row_index + 2, status_col).value or ""
            return 'done' in status.lower()
        return False
    
    def start_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_var.set("Starting...")
            self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
            self.bot_thread.start()
    
    def stop_bot(self):
        self.bot_running = False
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        self.status_var.set("Stopping...")
        if self.driver:
            self.driver.quit()
        self.log("🛑 Bot stopped safely")
    
    def on_closing(self):
        self.stop_bot()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkedInBotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
