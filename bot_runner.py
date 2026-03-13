import tempfile
import os
import logging
from 13 import Config as ConfigCompany, LinkedInCommentLiker as BotCompany
from 14 import Config as ConfigPersonal, LinkedInCommentLiker as BotPersonal

class LinkedInBotRunner:
    def __init__(self, linkedin_email, linkedin_password, gsheet_url, profile_mode="Personal", 
                 company_name=None, google_credentials=None):
        self.linkedin_email = linkedin_email
        self.linkedin_password = linkedin_password
        self.gsheet_url = gsheet_url
        self.profile_mode = profile_mode
        self.company_name = company_name
        self.google_credentials_json = google_credentials
        
        # Create temporary credentials file
        self._create_temp_credentials()
        
        # Choose correct config
        if self.profile_mode == "Company Page" and company_name:
            self.config = ConfigCompany()
            self.config.COMPANY_PAGE_NAME = company_name
            self.BotClass = BotCompany
        else:
            self.config = ConfigPersonal()
            self.BotClass = BotPersonal
            
        self.config.GOOGLE_SHEET_URL = gsheet_url
        self.config.GOOGLE_CREDENTIALS_FILE = self.temp_credentials_path
        self.config.LINKEDIN_EMAIL = linkedin_email
        self.config.LINKEDIN_PASSWORD = linkedin_password
    
    def _create_temp_credentials(self):
        """Save Google credentials to temp file"""
        fd, self.temp_credentials_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(self.temp_credentials_path, 'w') as f:
            f.write(self.google_credentials_json)
    
    def run_bot(self, log_callback=None):
        try:
            bot = self.BotClass(self.config)
            bot.initialize()
            bot.run()
            if log_callback:
                log_callback("✅ Bot completed successfully!")
        except Exception as e:
            error_msg = f"Bot failed: {str(e)}"
            if log_callback:
                log_callback(error_msg)
            raise
        finally:
            # Cleanup temp file
            if hasattr(self, 'temp_credentials_path'):
                os.unlink(self.temp_credentials_path)
