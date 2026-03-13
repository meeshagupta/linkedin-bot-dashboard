import streamlit as st
import time
from bot_runner import LinkedInBotRunner
import threading
from datetime import datetime
import json

st.set_page_config(
    page_title="LinkedIn Like Bot",
    page_icon="🔐",
    layout="wide"
)

# Custom CSS for better login styling
st.markdown("""
    <style>
    .main-header {font-size: 3rem; color: #1f77b4; text-align: center; margin-bottom: 2rem;}
    .login-box {max-width: 500px; margin: 0 auto; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'credentials' not in st.session_state:
    st.session_state.credentials = {}

# ===================================
# LOGIN SCREEN (Shows FIRST)
# ===================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="main-header">🤖 LinkedIn Automation Bot</h1>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("🔐 Enter Your Credentials")
        
        with st.form("credentials_form", clear_on_submit=False):
            st.subheader("📧 LinkedIn Account")
            linkedin_email = st.text_input("LinkedIn Email", placeholder="your.email@gmail.com")
            linkedin_password = st.text_input("LinkedIn Password", type="password", placeholder="Your password")
            
            st.subheader("📊 Google Sheets")
            gsheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/YOUR_ID/edit")
            
            st.subheader("🔑 Google Service Account")
            st.info("Paste your **Credentials.json** content below (from Google Cloud Console)")
            google_credentials = st.text_area(
                "Google Service Account JSON", 
                placeholder='{"type": "service_account", "project_id": "..."}',
                height=200,
                help="Download from Google Cloud → IAM → Service Accounts → Keys → JSON"
            )
            
            profile_mode = st.radio("Profile Type", ["Personal Profile", "Company Page"])
            company_name = st.text_input("Company Name (Company mode only)", 
                                       placeholder="Meeshu automation")
            
            submitted = st.form_submit_button("🚀 Connect & Start Bot", use_container_width=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submitted:
            # Validation
            if not all([linkedin_email, linkedin_password, gsheet_url, google_credentials]):
                st.error("❌ Please fill **all fields** above!")
            else:
                try:
                    # Test Google credentials JSON
                    creds_json = json.loads(google_credentials)
                    if creds_json.get("type") != "service_account":
                        st.error("❌ Invalid Google credentials JSON!")
                    else:
                        # Save to session & show dashboard
                        st.session_state.credentials = {
                            "linkedin_email": linkedin_email,
                            "linkedin_password": linkedin_password,
                            "gsheet_url": gsheet_url,
                            "google_credentials": google_credentials,
                            "profile_mode": profile_mode,
                            "company_name": company_name if profile_mode == "Company Page" else None
                        }
                        st.session_state.logged_in = True
                        st.success("✅ Connected! Dashboard loading...")
                        st.rerun()
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in Google credentials!")
                    
    st.markdown("---")
    st.markdown("*Bot will run in background with **your credentials only**. No data saved.*")
    
# ===================================
# BOT DASHBOARD (Shows AFTER LOGIN)
# ===================================
else:
    st.markdown("# 🎛️ Bot Dashboard")
    st.success(f"👋 Welcome! Connected with **{st.session_state.credentials['linkedin_email']}**")
    
    # Logout button
    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("🔐 Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.clear()
            st.rerun()
    
    # Sidebar controls
    st.sidebar.header("⚙️ Bot Controls")
    if st.sidebar.button("🚀 Start Bot", type="primary", use_container_width=True):
        st.sidebar.success("🤖 Bot starting...")
        st.session_state['bot_running'] = True
        
    if st.sidebar.button("⏹️ Stop Bot"):
        st.session_state['bot_running'] = False
        st.sidebar.success("⏹️ Bot stopped!")
    
    # Main metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", st.session_state.get('bot_status', 'Ready'))
    with col2:
        st.metric("Posts Processed", st.session_state.get('processed', 0))
    with col3:
        st.metric("Success Rate", f"{st.session_state.get('success_rate', 0):.1f}%")
    
    # Live logs
    st.header("📋 Live Logs")
    log_placeholder = st.empty()
    
    # Run bot in background
    def run_bot():
        try:
            runner = LinkedInBotRunner(**st.session_state.credentials)
            runner.run_bot(
                log_callback=lambda log: update_logs(log),
                google_credentials=st.session_state.credentials['google_credentials']
            )
        except Exception as e:
            st.session_state['bot_status'] = f"❌ Error: {str(e)}"
            update_logs(f"ERROR: {str(e)}")
    
    def update_logs(message):
        if 'logs' not in st.session_state:
            st.session_state['logs'] = ""
        st.session_state['logs'] += f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        st.rerun()
    
    if st.session_state.get('bot_running', False):
        if 'logs' not in st.session_state:
            st.session_state['logs'] = "🤖 Bot started...\n"
        st.session_state['bot_status'] = "Running..."
        
        log_placeholder.text_area("Live Logs", st.session_state['logs'], height=400)
        
        # Start bot thread
        if 'bot_thread' not in st.session_state:
            thread = threading.Thread(target=run_bot)
            thread.daemon = True
            thread.start()
            st.session_state['bot_thread'] = thread
    else:
        if 'logs' in st.session_state:
            log_placeholder.text_area("Logs", st.session_state['logs'], height=400)
    
    # Download logs
    if 'logs' in st.session_state and st.session_state['logs'].strip():
        st.download_button(
            "📥 Download Logs",
            st.session_state['logs'],
            file_name=f"linkedin_bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
