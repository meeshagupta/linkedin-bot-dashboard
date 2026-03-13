import streamlit as st
import time
import threading
from datetime import datetime
import json
import tempfile
import os
import sys
import importlib.util

# Dynamic import for bot_runner (FIXES import error)
def load_bot_runner():
    spec = importlib.util.spec_from_file_location("bot_runner", "bot_runner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_runner"] = module
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
            linkedin_email = st.text_input("LinkedIn Email")
            linkedin_password = st.text_input("LinkedIn Password", type="password")
            gsheet_url = st.text_input("Google Sheet URL")
        with col2:
            google_creds = st.text_area("Google Service Account JSON", height=150)
            profile_mode = st.radio("Profile Mode", ["Personal", "Company"])
            company_name = st.text_input("Company Name", disabled=profile_mode=="Personal")
        
        submit = st.form_submit_button("🚀 Start Bot")
        
        if submit:
            if not all([linkedin_email, linkedin_password, gsheet_url, google_creds]):
                st.error("❌ Fill all fields!")
            else:
                try:
                    json.loads(google_creds)
                    st.session_state.logged_in = True
                    st.session_state.creds = {
                        'email': linkedin_email, 'password': linkedin_password,
                        'gsheet': gsheet_url, 'google_json': google_creds,
                        'mode': profile_mode, 'company': company_name
                    }
                    st.success("✅ Dashboard loading...")
                    st.rerun()
                except:
                    st.error("❌ Invalid JSON!")

# DASHBOARD  
else:
    st.success(f"Connected: {st.session_state.creds['email']}")
    
    # Controls
    col1, col2 = st.columns(2)
    if col1.button("🚀 Run Bot"):
        st.session_state.bot_running = True
    if col2.button("⏹️ Stop"):
        st.session_state.bot_running = False
    
    # Status
    st.metric("Status", st.session_state.get('status', 'Ready'))
    st.metric("Processed", st.session_state.get('count', 0))
    
    # Logs
    if 'logs' not in st.session_state:
        st.session_state.logs = ""
    
    st.text_area("Live Logs", st.session_state.logs, height=300)
    
    # Bot runner
    if st.session_state.get('bot_running', False):
        def run_bot():
            try:
                bot_runner = load_bot_runner()
                runner = bot_runner.LinkedInBotRunner(**st.session_state.creds)
                st.session_state.status = "Running..."
                st.session_state.logs += "Bot started...\n"
                # Simulate bot (replace with real call)
                time.sleep(2)
                st.session_state.logs += "✅ Test complete!\n"
                st.session_state.status = "Complete"
            except Exception as e:
                st.session_state.logs += f"ERROR: {str(e)}\n"
                st.session_state.status = "Error"
        
        thread = threading.Thread(target=run_bot)
        thread.start()
        st.rerun()
