import streamlit as st
import pandas as pd
import time
from bot_runner import LinkedInBotRunner
import threading
from datetime import datetime

st.set_page_config(
    page_title="LinkedIn Like Bot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 LinkedIn Post & Comment Liker")
st.markdown("---")

# Sidebar for configuration
st.sidebar.header("Bot Configuration")
profile_mode = st.sidebar.radio(
    "Profile Type",
    ["Personal Profile", "Company Page"],
    key="profile_mode"
)

gsheet_url = st.sidebar.text_input(
    "Google Sheet URL",
    value="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    help="Paste your Google Sheets URL here"
)

linkedin_email = st.sidebar.text_input("LinkedIn Email", type="password")
linkedin_password = st.sidebar.text_input("LinkedIn Password", type="password")
company_name = st.sidebar.text_input("Company Name (for company mode)", 
                                   value="Meeshu automation")

# Bot controls
if st.sidebar.button("🚀 Start Bot", type="primary"):
    if not all([gsheet_url, linkedin_email, linkedin_password]):
        st.sidebar.error("Please fill all required fields!")
    else:
        st.sidebar.success("Bot starting...")
        st.session_state['bot_running'] = True

if st.sidebar.button("⏹️ Stop Bot"):
    st.session_state['bot_running'] = False
    st.sidebar.success("Bot stopped!")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Bot Status")
    if 'bot_status' in st.session_state:
        st.metric("Status", st.session_state['bot_status'])
    st.metric("Posts Processed", st.session_state.get('processed', 0))
    st.metric("Success Rate", f"{st.session_state.get('success_rate', 0):.1f}%")

with col2:
    st.header("⚙️ Quick Actions")
    if st.button("🔄 Refresh Status"):
        st.rerun()
    
    st.header("📈 Logs")
    if st.button("📥 Download Logs"):
        st.download_button("Download bot_logs.txt", "logs content")

# Real-time log display
st.header("📋 Live Logs")
log_placeholder = st.empty()
if 'logs' in st.session_state:
    log_placeholder.text_area("Logs", st.session_state['logs'], height=300)

# Run bot in background thread
def run_bot():
    try:
        runner = LinkedInBotRunner(
            gsheet_url=gsheet_url,
            email=linkedin_email,
            password=linkedin_password,
            company_name=company_name if profile_mode == "Company Page" else None,
            profile_mode=profile_mode
        )
        runner.run_bot(log_callback=lambda log: update_logs(log))
    except Exception as e:
        st.session_state['bot_status'] = f"Error: {str(e)}"
        st.session_state['logs'] += f"ERROR: {str(e)}\n"

def update_logs(log_message):
    st.session_state['logs'] += f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}\n"
    st.rerun()

if st.session_state.get('bot_running', False):
    if 'logs' not in st.session_state:
        st.session_state['logs'] = ""
    if 'processed' not in st.session_state:
        st.session_state['processed'] = 0
    
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    st.session_state['bot_status'] = "Running..."
