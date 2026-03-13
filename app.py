import streamlit as st
import time
import json
import tempfile
import os
import sys
import importlib.util
from datetime import datetime

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

# Initialize session state
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'status' not in st.session_state: st.session_state.status = "Ready"
if 'posts' not in st.session_state: st.session_state.posts = 0
if 'success' not in st.session_state: st.session_state.success = 0
if 'running' not in st.session_state: st.session_state.running = False
if 'creds' not in st.session_state: st.session_state.creds = {}

def load_module(filename):
    spec = importlib.util.spec_from_file_location("bot", filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot"] = module
    spec.loader.exec_module(module)
    return module

# LOGIN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Bot")
    with st.form("login"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("LinkedIn Email")
            password = st.text_input("Password", type="password")
            sheet_url = st.text_input("Google Sheet URL")
        with col2:
            google_file = st.file_uploader("Credentials.json", type="json")
            mode = st.radio("Mode", ["Personal", "Company"])
            company = st.text_input("Company Name") if mode == "Company" else ""
        
        if st.form_submit_button("🚀 Start Real Bot"):
            if not all([email, password, sheet_url, google_file]):
                st.error("Fill all fields!")
            else:
                try:
                    json.load(google_file)
                    st.session_state.logged_in = True
                    st.session_state.creds = {
                        'email': email, 'password': password, 'sheet': sheet_url,
                        'google': google_file.getvalue().decode(), 'mode': mode, 'company': company
                    }
                    st.session_state.logs = "✅ Ready for REAL automation!"
                    st.rerun()
                except: st.error("Invalid JSON!")

# DASHBOARD + REAL BOT
else:
    st.success(f"✅ {st.session_state.creds['email']}")
    
    col1, col2 = st.columns(2)
    if col1.button("🔐 Logout"): 
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 REAL BOT", disabled=st.session_state.running):
        st.session_state.running = True
        st.session_state.logs += f"\n[{datetime.now().strftime('%H:%M')}] 🔥 REAL SELENIUM START\n"
    
    if col2.button("⏹️ Stop", disabled=not st.session_state.running):
        st.session_state.running = False
    
    col1.metric("Status", st.session_state.status)
    col2.metric("Posts", st.session_state.posts)
    col3.metric("Success", f"{st.session_state.success}%")
    
    st.text_area("Live Logs", st.session_state.logs, height=300)
    
    # 🔥 REAL SELENIUM BOT
    if st.session_state.running:
        st.session_state.logs += "🔄 Loading your bot modules...\n"
        st.rerun()
        
        try:
            # Load REAL bot (13.py or 14.py)
            bot_file = '13.py' if st.session_state.creds['mode'] == 'Company' else '14.py'
            bot_module = load_module(bot_file)
            
            # Create temp Google credentials
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(st.session_state.creds['google'])
                creds_path = f.name
            
            st.session_state.logs += f"✅ Loaded {bot_file} - Chrome starting...\n"
            st.rerun()
            
            # Initialize REAL bot
            config = bot_module.Config()
            config.GOOGLE_SHEET_URL = st.session_state.creds['sheet']
            config.LINKEDIN_EMAIL = st.session_state.creds['email']
            config.LINKEDIN_PASSWORD = st.session_state.creds['password']
            if st.session_state.creds['company']: config.COMPANY_PAGE_NAME = st.session_state.creds['company']
            
            bot = bot_module.LinkedInCommentLiker(config)
            bot.initialize()
            
            st.session_state.logs += "🚀 Bot running - check your Google Sheet for updates!\n"
            st.session_state.status = "🤖 LIVE - Processing sheet rows..."
            
            # Run REAL bot
            bot.run()
            
            st.session_state.logs += "🎉 REAL BOT FINISHED!\n"
            st.session_state.status = "✅ Complete"
            st.session_state.running = False
            
        except Exception as e:
            st.session_state.logs += f"❌ Error: {str(e)[:100]}\n"
            st.session_state.status = "❌ Error"
            st.session_state.running = False
        
        try: os.unlink(creds_path)
        except: pass
        
        st.rerun()
