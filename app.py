import streamlit as st
import time
import threading
from bot_core import BotConfig, LinkedInCommentLiker
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="LinkedIn Bot", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .status-box {background: #f0f2f6; padding: 1rem; border-radius: 10px; border-left: 5px solid #1f77b4;}
    .btn-run {background: #10b981; color: white; border-radius: 20px; padding: 0.75rem 2rem; font-size: 1.1rem;}
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("🔧 Bot Configuration")
email = st.sidebar.text_input("LinkedIn Email", type="password")
password = st.sidebar.text_input("LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("Google Sheet URL")
company_name = st.sidebar.text_input("Company Page Name", value="Meeshu automation")
use_company = st.sidebar.checkbox("Use Company Profile", value=True)
headless = st.sidebar.checkbox("Headless Mode", value=False)

# Credentials upload (secure method)
creds_file = st.sidebar.file_uploader("Upload Google Service Account JSON", type="json")

# Main interface
st.markdown('<h1 class="main-header">🤖 LinkedIn Automation Bot</h1>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🚀 Run Bot", key="run", help="Start automation", use_container_width=True):
        st.success("Bot started!")

# Real-time status
if 'bot_status' not in st.session_state:
    st.session_state.bot_status = "Ready"
    st.session_state.log_messages = []

status_col1, status_col2 = st.columns(2)
with status_col1:
    st.markdown(f"""
    <div class="status-box">
        <h3>📊 Status</h3>
        <p><strong>{st.session_state.bot_status}</strong></p>
    </div>
    """, unsafe_allow_html=True)

with status_col2:
    if st.button("🛑 Stop Bot", key="stop"):
        st.session_state.bot_status = "Stopped"

# Live logs
st.subheader("📋 Live Logs")
chat_placeholder = st.empty()
logs_df = None

# Bot execution function
def run_bot():
    try:
        st.session_state.bot_status = "Initializing..."
        
        # Validate inputs
        if not all([email, password, sheet_url, creds_file]):
            st.error("Please fill all required fields")
            return
            
        # Save credentials temporarily
        with open("temp_creds.json", "wb") as f:
            f.write(creds_file.read())
        
        config = BotConfig(
            email=email,
            password=password,
            sheet_url=sheet_url,
            company_name=company_name,
            creds_file="temp_creds.json"
        )
        
        bot = LinkedInCommentLiker(config)
        bot.initialize()
        st.session_state.bot_status = "Running..."
        bot.run()
        st.session_state.bot_status = "Completed!"
        
    except Exception as e:
        st.session_state.bot_status = f"Error: {str(e)}"
        st.error(f"Bot failed: {str(e)}")

# Background thread for bot
if st.sidebar.button("🎯 Start Bot Thread"):
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()

# Preview sheet data
if st.checkbox("📊 Preview Google Sheet"):
    try:
        # Test connection
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file("temp_creds.json", scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).sheet1
        data = sheet.get_all_records()
        st.dataframe(data)
    except:
        st.warning("Upload credentials and enter valid sheet URL to preview")

# Logs display
if st.session_state.log_messages:
    for msg in st.session_state.log_messages[-10:]:
        st.text(msg)
