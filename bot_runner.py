import logging
from your_selenium_files import Config, LinkedInCommentLiker  # Import your existing bot
import time
import streamlit as st

class LinkedInBotRunner:
    def __init__(self, gsheet_url, email, password, company_name=None, profile_mode="Personal"):
        self.gsheet_url = gsheet_url
        self.email = email
        self.password = password
        self.company_name = company_name
        self.profile_mode = profile_mode
        
        # Update config dynamically
        self.config = Config()
        self.config.GOOGLE_SHEET_URL = gsheet_url
        self.config.LINKEDIN_EMAIL = email
        self.config.LINKEDIN_PASSWORD = password
        if company_name:
            self.config.COMPANY_PAGE_NAME = company_name
    
    def log(self, message):
        """Callback for Streamlit logs"""
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
        return message
    
    def run_bot(self, log_callback=None):
        """Main bot execution with Streamlit integration"""
        try:
            # Override logger for Streamlit
            logging.getLogger("LinkedInBot").handlers = []
            
            bot = LinkedInCommentLiker(self.config)
            bot.initialize()
            
            # Run with custom logging
            original_logger = logging.getLogger("LinkedInBot")
            original_logger.info = lambda msg: log_callback(self.log(msg)) if log_callback else print(msg)
            
            bot.run()
            
        except Exception as e:
            error_msg = f"Bot failed: {str(e)}"
            log_callback(error_msg) if log_callback else print(error_msg)
            raise
