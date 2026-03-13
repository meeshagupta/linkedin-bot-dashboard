import streamlit as st
import time
import subprocess
import json
import os
from datetime import datetime

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

# Initialize ALL session state
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'status' not in st.session_state: st.session_state.status = "Ready"
if 'posts' not in st.session_state: st.session_state.posts = 0
if 'success' not in st.session_state: st.session_state.success = 0
if 'running' not in st.session_state: st.session_state.running = False
if 'step' not in st.session_state: st.session_state.step = 0
if 'creds' not in st.session_state: st.session_state.creds = {}
if 'email' not in st.session_state: st.session_state.email = ""
if 'process' not in st.session_state: st.session_state.process = None

# LOGIN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Bot - REAL EXECUTION")
    with st.form("login"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("LinkedIn Email")
            password = st.text_input("Password", type="password")
            sheet_url = st.text_input("Google Sheet URL")
        with col2:
            creds_json = st.text_area("Paste credentials.json content", height=150)
            mode = st.radio("Mode", ["Personal", "Company"])
            company = st.text_input("Company Name") if mode == "Company" else ""
        
        if st.form_submit_button("🚀 Start Bot"):
            if not all([email, password, sheet_url, creds_json]):
                st.error("❌ Fill ALL fields!")
            else:
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.creds = {
                    'email': email, 'password': password, 'sheet': sheet_url,
                    'google': creds_json, 'mode': mode, 'company': company
                }
                st.session_state.logs = "✅ Login successful!"
                st.rerun()

# DASHBOARD + REAL BOT
else:
    st.success(f"✅ Logged in: {st.session_state.email}")
    
    # Controls
    col1, col2 = st.columns([1,1])
    if col1.button("🔐 Logout", use_container_width=True):
        if st.session_state.process:
            st.session_state.process.terminate()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    col1, col2 = st.columns([1,1])
    start_disabled = st.session_state.running
    if col1.button("🚀 START REAL BOT", disabled=start_disabled, use_container_width=True):
        st.session_state.running = True
        st.session_state.step = 0
        st.session_state.logs += f"\n[{datetime.now().strftime('%H:%M')}] 🔥 REAL BOT EXECUTION STARTED\n"
        st.rerun()
    
    if col2.button("⏹️ STOP BOT", disabled=not st.session_state.running, use_container_width=True):
        if st.session_state.process:
            st.session_state.process.terminate()
        st.session_state.running = False
        st.session_state.status = "⏹️ STOPPED"
        st.rerun()
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.status)
    col2.metric("Posts Processed", st.session_state.posts)
    col3.metric("Success Rate", f"{st.session_state.success}%")
    
    # Progress bar
    if st.session_state.running:
        progress = min(1.0, st.session_state.step / 30.0)
        st.progress(progress)
    
    st.text_area("📋 Live Logs", st.session_state.logs, height=350)
    
    # 🔥 REAL BOT EXECUTION
    if st.session_state.running and st.session_state.step == 0:
        st.session_state.step = 1
        st.session_state.status = "📦 Creating bot config..."
        st.session_state.logs += "[09:25] 📦 Creating real bot config...\n"
        st.rerun()
    
    elif st.session_state.running and st.session_state.step == 1:
        # Create REAL credentials file
        creds_file = "temp_creds.json"
        with open(creds_file, 'w') as f:
            json.dump(st.session_state.creds, f)
        
        st.session_state.status = "🚀 Launching REAL 14.py..."
        st.session_state.logs += "[09:26] 🚀 Executing REAL Selenium bot...\n"
        st.session_state.step = 2
        st.rerun()
    
    elif st.session_state.running and st.session_state.step == 2:
        # EXECUTE REAL BOT via subprocess (BYPASSES Streamlit threading issues)
        bot_file = "14.py" if st.session_state.creds['mode'] == "Personal" else "13.py"
        st.session_state.status = f"⚡ Running {bot_file} (check Chrome!)"
        
        # Run REAL bot in subprocess
        cmd = [
            "python", bot_file,
            "--sheet", st.session_state.creds['sheet'],
            "--email", st.session_state.creds['email'],
            "--password", st.session_state.creds['password']
        ]
        if st.session_state.creds.get('company'):
            cmd.extend(["--company", st.session_state.creds['company']])
        
        st.session_state.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        st.session_state.logs += f"[09:27] ✅ {bot_file} EXECUTING NOW - Chrome should open!\n"
        st.session_state.logs += "📱 Check your Google Sheet for LIVE updates!\n"
        st.session_state.step = 3
        st.rerun()
    
    elif st.session_state.running and st.session_state.step >= 3:
        # Monitor real bot process
        if st.session_state.process:
            try:
                output, error = st.session_state.process.communicate(timeout=1)
                if output: st.session_state.logs += output
                if error: st.session_state.logs += f"⚠️ {error}\n"
            except subprocess.TimeoutExpired:
                pass  # Still running
        
        # Check if process finished
        if st.session_state.process.poll() is not None:
            st.session_state.running = False
            st.session_state.status = "✅ REAL BOT COMPLETED!"
            st.session_state.logs += "[09:35] 🎉 REAL BOT FINISHED - Check LinkedIn + Sheet!\n"
        
        st.rerun()
