import streamlit as st
import time
import threading
from datetime import datetime
import json
import tempfile
import os

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
            st.subheader("LinkedIn")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            gsheet_url = st.text_input("Google Sheet URL")
        with col2:
            st.subheader("Google Service Account")
            google_json = st.text_area("JSON Credentials", height=200)
            profile_mode = st.radio("Profile", ["Personal", "Company"])
            company_name = st.text_input("Company Name") if profile_mode == "Company" else ""
        
        if st.form_submit_button("🚀 Connect"):
            if not all([email, password, gsheet_url, google_json]):
                st.error("❌ Fill all fields!")
            else:
                try:
                    json.loads(google_json)
                    st.session_state.logged_in = True
                    st.session_state.creds = {
                        'email': email, 'password': password,
                        'gsheet': gsheet_url, 'google_json': google_json,
                        'mode': profile_mode, 'company': company_name
                    }
                    st.success("✅ Dashboard ready!")
                    st.rerun()
                except:
                    st.error("❌ Invalid JSON!")

# DASHBOARD
else:
    st.success(f"✅ Connected: {st.session_state.creds['email']}")
    if st.button("🔐 Logout"):
        st.session_state.clear()
        st.rerun()
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 Start Bot", type="primary"):
        st.session_state.running = True
        st.session_state.logs = "🤖 Bot starting...\n"
    if col2.button("⏹️ Stop Bot"):
        st.session_state.running = False
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.get('status', 'Ready'))
    col2.metric("Posts", st.session_state.get('posts', 0))
    col3.metric("Success", f"{st.session_state.get('success', 0)}%")
    
    # Logs
    if 'logs' not in st.session_state:
        st.session_state.logs = ""
    
    st.text_area("📋 Live Logs", st.session_state.logs or "Ready to start...", height=300)
    
    # TEST BOT (no selenium yet)
    if st.session_state.get('running', False):
        st.session_state.status = "Running test..."
        st.session_state.logs += f"[{datetime.now().strftime('%H:%M')}] Processing...\n"
        st.session_state.posts = st.session_state.get('posts', 0) + 1
        time.sleep(2)
        st.session_state.logs += "✅ Test complete!\n"
        st.session_state.status = "Test Success"
        st.session_state.running = False
        st.rerun()
