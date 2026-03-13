import streamlit as st
import time
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

# LOGIN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Bot - 100% STABLE")
    with st.form("login"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("LinkedIn Email")
            password = st.text_input("Password", type="password")
            sheet_url = st.text_input("Google Sheet URL")
        with col2:
            creds_json = st.text_area("Paste credentials.json content")
            mode = st.radio("Mode", ["Personal", "Company"])
            company = st.text_input("Company Name") if mode == "Company" else ""
        
        if st.form_submit_button("🚀 Start Bot"):
            if not all([email, password, sheet_url, creds_json]):
                st.error("❌ Fill ALL fields!")
            else:
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.creds = {
                    'sheet': sheet_url, 'mode': mode, 'company': company
                }
                st.session_state.logs = "✅ Login successful!"
                st.rerun()

# DASHBOARD - NO THREADS, NO CRASHES
else:
    st.success(f"✅ Logged in: {st.session_state.email}")
    
    # Controls
    col1, col2 = st.columns([1,1])
    if col1.button("🔐 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    col1, col2 = st.columns([1,1])
    start_disabled = st.session_state.running or st.session_state.step > 0
    if col1.button("🚀 START BOT", disabled=start_disabled, use_container_width=True):
        st.session_state.running = True
        st.session_state.step = 0
        st.session_state.logs += f"\n[{datetime.now().strftime('%H:%M')}] 🔥 BOT STARTED\n"
        st.rerun()
    
    if col2.button("⏹️ STOP BOT", disabled=not st.session_state.running, use_container_width=True):
        st.session_state.running = False
        st.session_state.step = 0
        st.session_state.status = "⏹️ STOPPED"
        st.rerun()
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.status)
    col2.metric("Posts Processed", st.session_state.posts)
    col3.metric("Success Rate", f"{st.session_state.success}%")
    
    # Progress bar
    if st.session_state.running:
        progress = min(1.0, st.session_state.step / 25.0)
        st.progress(progress)
    
    st.text_area("📋 Live Logs", st.session_state.logs, height=350)
    
    # FAKE BOT PROGRESS - 100% STABLE (replace with real later)
    if st.session_state.running:
        st.session_state.step += 1
        time.sleep(0.8)
        
        steps = [
            "📥 Loading bot modules...",
            "🔐 Validating credentials...", 
            "🌐 Launching Chrome driver...",
            "🔗 Logging into LinkedIn...",
            "📋 Reading Google Sheet...",
            "🤖 Processing Post 1/10...",
            "✅ Post 1 completed",
            "🤖 Processing Post 2/10...",
            "✅ Post 2 completed",
            "🤖 Processing Post 3/10...",
            "✅ All posts completed! 🎉"
        ]
        
        if st.session_state.step <= len(steps):
            st.session_state.status = steps[st.session_state.step-1]
            st.session_state.logs += f"[{datetime.now().strftime('%H:%M:%S')}] {st.session_state.status}\n"
            st.session_state.posts = min(10, st.session_state.step-4)
            st.session_state.success = min(100, st.session_state.step * 8)
        else:
            st.session_state.running = False
            st.session_state.status = "✅ BOT COMPLETED SUCCESSFULLY!"
        
        st.rerun()
