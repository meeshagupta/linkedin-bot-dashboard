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
if 'step' not in st.session_state: st.session_state.step = 0
if 'creds' not in st.session_state: st.session_state.creds = {}

def load_module(filename):
    try:
        spec = importlib.util.spec_from_file_location("bot", filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules["bot"] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        st.session_state.logs += f"❌ Failed to load {filename}: {str(e)}\n"
        return None

# LOGIN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Bot - STABLE VERSION")
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
        
        if st.form_submit_button("🚀 Start Bot"):
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
                    st.session_state.logs = "✅ Ready!"
                    st.rerun()
                except: st.error("Invalid JSON!")

# DASHBOARD
else:
    st.success(f"✅ {st.session_state.creds['email']}")
    
    col1, col2 = st.columns(2)
    if col1.button("🔐 Logout"): 
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 START BOT", disabled=st.session_state.running):
        st.session_state.running = True
        st.session_state.step = 0
        st.session_state.logs += f"\n[{datetime.now().strftime('%H:%M')}] 🔥 BOT START\n"
        st.rerun()
    
    if col2.button("⏹️ STOP", disabled=not st.session_state.running):
        st.session_state.running = False
        st.session_state.step = 0
        st.rerun()
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.status)
    col2.metric("Posts", st.session_state.posts)
    col3.metric("Success", f"{st.session_state.success}%")
    
    st.text_area("Live Logs", st.session_state.logs, height=300)
    
    # SIMULATED BOT PROGRESS (Replace with real bot later)
    if st.session_state.running:
        st.session_state.step += 1
        
        if st.session_state.step == 1:
            st.session_state.status = "📥 Loading bot module..."
            st.session_state.logs += "🔄 Loading 14.py...\n"
            
        elif st.session_state.step == 2:
            st.session_state.status = "🔐 Setting up credentials..."
            st.session_state.logs += "✅ Credentials loaded\n"
            
        elif st.session_state.step == 3:
            st.session_state.status = "🌐 Starting Chrome..."
            st.session_state.logs += "🚀 Chrome launching...\n"
            
        elif st.session_state.step == 4:
            st.session_state.status = "🔗 Logging into LinkedIn..."
            st.session_state.logs += "✅ LinkedIn login successful\n"
            
        elif st.session_state.step > 4 and st.session_state.step < 20:
            st.session_state.posts = st.session_state.step - 4
            st.session_state.success = min(95, st.session_state.step * 5)
            st.session_state.status = f"🤖 Processing post {st.session_state.posts}"
            st.session_state.logs += f"✅ Post {st.session_state.posts} completed\n"
            
        elif st.session_state.step >= 20:
            st.session_state.status = "✅ FINISHED!"
            st.session_state.logs += "🎉 All posts processed!\n"
            st.session_state.running = False
            
        time.sleep(1)
        st.rerun()
