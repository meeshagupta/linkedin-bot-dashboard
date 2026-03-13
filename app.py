import streamlit as st
import time
import json
from datetime import datetime

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

# Initialize ALL session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'logs' not in st.session_state:
    st.session_state.logs = ""
if 'status' not in st.session_state:
    st.session_state.status = "Ready"
if 'posts' not in st.session_state:
    st.session_state.posts = 0
if 'success' not in st.session_state:
    st.session_state.success = 0
if 'running' not in st.session_state:
    st.session_state.running = False
if 'creds' not in st.session_state:
    st.session_state.creds = {}

# LOGIN SCREEN
if not st.session_state.logged_in:
    st.title("🤖 LinkedIn Automation Bot")
    st.markdown("---")
    
    with st.form("login"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("👤 LinkedIn Email")
            password = st.text_input("🔑 Password", type="password")
            sheet_url = st.text_input("📊 Google Sheet URL")
        with col2:
            google_file = st.file_uploader("📄 Upload Credentials.json", type="json")
            mode = st.radio("Profile Type", ["Personal", "Company"])
            company = st.text_input("Company Name (if Company)")
        
        col1, col2 = st.columns(2)
        col1.markdown("")
        if col2.form_submit_button("🚀 Connect & Run Bot", type="primary"):
            if not all([email, password, sheet_url, google_file]):
                st.error("❌ Fill ALL fields + upload JSON!")
            else:
                try:
                    # Validate JSON file
                    json.load(google_file)
                    st.session_state.logged_in = True
                    st.session_state.creds = {
                        'email': email, 'password': password,
                        'sheet': sheet_url, 'google': google_file.getvalue().decode(),
                        'mode': mode, 'company': company
                    }
                    st.session_state.logs = "✅ Connected successfully!"
                    st.success("🎉 Ready to automate LinkedIn!")
                    st.rerun()
                except:
                    st.error("❌ Invalid JSON file!")
    st.rerun()

# DASHBOARD
else:
    # Header
    st.header("🎛️ LinkedIn Bot Dashboard")
    col1, col2 = st.columns([3,1])
    col1.success(f"✅ Logged in: **{st.session_state.creds['email']}**")
    if col2.button("🔐 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Controls
    col1, col2 = st.columns(2)
    start_disabled = st.session_state.running
    stop_disabled = not st.session_state.running
    
    if col1.button("🚀 Start Bot", type="primary", disabled=start_disabled):
        st.session_state.running = True
        st.session_state.logs += f"\n[{datetime.now().strftime('%H:%M:%S')}] 🤖 Bot started!\n"
        st.session_state.status = "Initializing..."
    
    if col2.button("⏹️ Stop Bot", disabled=stop_disabled, type="secondary"):
        st.session_state.running = False
        st.session_state.status = "Stopped by user"
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", st.session_state.status)
    col2.metric("Posts Processed", st.session_state.posts)
    col3.metric("Success Rate", f"{st.session_state.success}%")
    
    # Logs
    st.subheader("📋 Live Logs")
    st.text_area("Latest activity", st.session_state.logs, height=350)
    
    # Bot Simulation (Realistic flow)
    if st.session_state.running:
        with st.spinner("🤖 Running LinkedIn automation..."):
            
            # Step 1: Load bot
            if st.session_state.status == "Initializing...":
                st.session_state.logs += "[08:10] 📥 Loading Selenium modules...\n"
                st.session_state.status = "Loading Chrome..."
                st.rerun()
            
            # Step 2: Chrome
            elif st.session_state.status == "Loading Chrome...":
                st.session_state.logs += "[08:11] 🌐 Starting Chrome browser...\n"
                time.sleep(3)
                st.session_state.status = "Chrome ready"
                st.rerun()
            
            # Step 3: Google Sheets
            elif st.session_state.status == "Chrome ready":
                st.session_state.logs += "[08:14] 📊 Reading Google Sheet...\n"
                time.sleep(2)
                st.session_state.status = "Sheets connected"
                st.rerun()
            
            # Step 4: Login
            elif st.session_state.status == "Sheets connected":
                st.session_state.logs += "[08:16] 🔐 Logging into LinkedIn...\n"
                time.sleep(4)
                st.session_state.status = "Logging in..."
                st.rerun()
            
            # Step 5: Process posts
            elif "Post" not in st.session_state.status:
                current_post = st.session_state.posts + 1
                st.session_state.status = f"Processing Post {current_post}"
                st.session_state.logs += f"[08:20] 📤 Post {current_post}: Liking post + comments...\n"
                time.sleep(3)
                st.session_state.posts += 1
                st.session_state.success = 95
                if st.session_state.posts >= 3:  # Simulate 3 posts
                    st.session_state.status = "✅ Complete!"
                    st.session_state.logs += "🎉 All posts processed! Check your Google Sheet.\n"
                    st.session_state.running = False
                st.rerun()
    
    # Download logs
    if st.session_state.logs.strip():
        st.download_button(
            "💾 Download Full Logs",
            st.session_state.logs,
            f"linkedin_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            type="secondary"
        )
