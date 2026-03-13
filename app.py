import streamlit as st
import time
import threading
import json
import tempfile
import os
import sys
from datetime import datetime

# Dynamic bot import
def load_bot_module(filename):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bot", filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot"] = module
    spec.loader.exec_module(module)
    return module

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# LOGIN SCREEN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Automation Bot")
    st.markdown("---")
    
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔐 LinkedIn")
            email = st.text_input("Email", placeholder="shruti.shar10@gmail.com")
            password = st.text_input("Password", type="password")
            gsheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/YOUR_ID")
        with col2:
            st.subheader("📄 Google Credentials")
            google_json = st.file_uploader("Upload Credentials.json", type="json")
            profile_mode = st.radio("Profile Mode", ["Personal", "Company"])
            company_name = st.text_input("Company Name") if profile_mode == "Company" else ""
        
        if st.form_submit_button("🚀 Connect"):
            if not all([email, password, gsheet_url, google_json]):
                st.error("❌ Fill all fields!")
            else:
                try:
                    creds_content = json.load(google_json)
                    st.session_state.logged_in = True
                    st.session_state.creds = {
                        'email': email, 'password': password,
                        'gsheet': gsheet_url, 'google_json': google_json.getvalue().decode(),
                        'mode': profile_mode, 'company': company_name
                    }
                    st.success("✅ Connected!")
                    st.rerun()
                except:
                    st.error("❌ Invalid JSON file!")

# DASHBOARD
else:
    st.success(f"✅ Connected: {st.session_state.creds['email']}")
    
    col1, col2 = st.columns(2)
    if col1.button("🔐 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Bot Controls
    col1, col2 = st.columns(2)
    if col1.button("🚀 Start REAL Bot", type="primary"):
        st.session_state.running = True
        st.session_state.logs = "🤖 Starting REAL Selenium bot...\n"
        st.session_state.status = "Initializing Chrome..."
    if col2.button("⏹️ Stop Bot"):
        st.session_state.running = False
        st.session_state.status = "Stopped"
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.get('status', 'Ready'))
    col2.metric("Posts Processed", st.session_state.get('posts', 0))
    col3.metric("Success Rate", f"{st.session_state.get('success', 0)}%")
    
    # Live Logs
    st.subheader("📋 Live Logs")
    if 'logs' not in st.session_state:
        st.session_state.logs = ""
    st.text_area("Logs", st.session_state.logs, height=400)
    
    # REAL BOT EXECUTION
    if st.session_state.get('running', False):
        def run_real_bot():
            try:
                st.session_state.logs += "📥 Loading bot modules...\n"
                
                # Load correct bot based on mode
                if st.session_state.creds['mode'] == 'Company':
                    bot_module = load_bot_module('13.py')
                else:
                    bot_module = load_bot_module('14.py')
                
                st.session_state.logs += "🚀 Initializing Selenium...\n"
                st.session_state.status = "Chrome starting..."
                st.rerun()
                
                # Create temp Google credentials
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    tmp.write(st.session_state.creds['google_json'])
                    tmp_path = tmp.name
                
                # Update config and run
                config = bot_module.Config()
                config.GOOGLE_SHEET_URL = st.session_state.creds['gsheet']
                config.LINKEDIN_EMAIL = st.session_state.creds['email']
                config.LINKEDIN_PASSWORD = st.session_state.creds['password']
                if st.session_state.creds['company']:
                    config.COMPANY_PAGE_NAME = st.session_state.creds['company']
                
                bot = bot_module.LinkedInCommentLiker(config)
                st.session_state.logs += "🔐 Logging into LinkedIn...\n"
                bot.initialize()
                
                st.session_state.logs += "📊 Reading Google Sheet...\n"
                bot.run()
                
                st.session_state.logs += "✅ BOT COMPLETED SUCCESSFULLY!\n"
                st.session_state.status = "Complete"
                
            except Exception as e:
                st.session_state.logs += f"❌ ERROR: {str(e)[:100]}\n"
                st.session_state.status = "Error"
            finally:
                st.session_state.running = False
                os.unlink(tmp_path) if 'tmp_path' in locals() else None
                st.rerun()
        
        # Run in background
        if 'bot_thread' not in st.session_state:
            thread = threading.Thread(target=run_real_bot, daemon=True)
            st.session_state.bot_thread = thread
            thread.start()
