import streamlit as st
import time
import os
import json
from bot_core import BotConfig, LinkedInCommentLiker

st.set_page_config(page_title="LinkedIn Bot", layout="wide")

st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .status-box {background: #f0f2f6; padding: 1rem; border-radius: 10px; border-left: 5px solid #1f77b4;}
    .btn-run {background: #10b981; color: white; border-radius: 20px; padding: 0.75rem 2rem; font-size: 1.1rem;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'bot_status' not in st.session_state:
    st.session_state.bot_status = "🟢 Ready"
    st.session_state.logs = []
    st.session_state.running = False

# Sidebar Configuration
st.sidebar.header("🔧 Bot Configuration")
email = st.sidebar.text_input("LinkedIn Email", value="shruti.shar10@gmail.com")
password = st.sidebar.text_input("LinkedIn Password", type="password", value="PSabcD@123456!")
sheet_url = st.sidebar.text_input("Google Sheet URL", value="https://docs.google.com/spreadsheets/d/17bwCB8vbuo96tVHrW6bsBk2sFVd5CSIgYWy1LmofF2k/edit")
company_name = st.sidebar.text_input("Company Page Name", value="Meeshu automation")
creds_file = st.sidebar.file_uploader("Upload Google Service Account JSON", type="json")

# Main interface
st.markdown('<h1 class="main-header">🤖 LinkedIn Automation Bot</h1>', unsafe_allow_html=True)

# Status display
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="status-box">
        <h3>📊 Status</h3>
        <p><strong>{st.session_state.bot_status}</strong></p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🚀 START BOT", use_container_width=True) and creds_file:
            st.session_state.running = True
            st.session_state.bot_status = "🔄 Initializing..."
            st.rerun()
    
    with col_btn2:
        if st.button("🛑 STOP BOT", use_container_width=True):
            st.session_state.running = False
            st.session_state.bot_status = "🛑 Stopped"
            st.rerun()

# Logs display
st.subheader("📋 Live Logs")
log_container = st.container(height=400)
logs_df = None

# Bot execution (NON-THREADED - fixes ScriptRunContext error)
if st.session_state.running and creds_file:
    with log_container:
        try:
            # Save uploaded credentials
            creds_path = "temp_creds.json"
            with open(creds_path, "wb") as f:
                f.write(creds_file.getvalue())
            
            st.session_state.logs.append("📝 Saving credentials...")
            
            # Create bot config
            config = BotConfig(
                linkedin_email=email,
                linkedin_password=password,
                google_sheet_url=sheet_url,
                company_page_name=company_name,
                google_credentials_file=creds_path
            )
            
            st.session_state.logs.append("🤖 Creating bot instance...")
            
            # Initialize bot
            bot = LinkedInCommentLiker(config)
            bot.initialize()
            
            st.session_state.bot_status = "⚡ Running bot..."
            st.session_state.logs.append("✅ Bot initialized successfully!")
            
            # Run bot
            bot.run()
            
            st.session_state.bot_status = "✅ COMPLETED!"
            st.session_state.logs.append("🎉 Bot finished successfully!")
            st.session_state.running = False
            
        except Exception as e:
            st.session_state.bot_status = f"❌ ERROR: {str(e)[:100]}"
            st.session_state.logs.append(f"❌ Error: {str(e)}")
            st.session_state.running = False
        finally:
            st.rerun()

# Display logs
if st.session_state.logs:
    for log in st.session_state.logs[-20:]:
        st.text(log)

# Preview uploaded credentials (for debugging)
if creds_file:
    st.sidebar.success("✅ Credentials uploaded!")
    st.sidebar.json(creds_file.read())

# Instructions
with st.expander("📖 How to use"):
    st.markdown("""
    1. **Fill all fields** (pre-filled with your values)
    2. **Upload** your `Credentials.json` 
    3. **Click START BOT** 
    4. **Watch logs** and check your Google Sheet!
    """)
