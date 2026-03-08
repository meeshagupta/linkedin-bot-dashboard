import streamlit as st
import time
import os
import sys
import tempfile
import json

# ✅ FIX: Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

st.title("🤖 LinkedIn Comment Liker Bot - PRO")
st.markdown("---")

# Sidebar - ULTIMATE CONFIG
st.sidebar.header("🔧 Bot Configuration")
bot_type = st.sidebar.selectbox("Choose Bot:", ["Profile (profile_bot.py)", "Company (company_bot.py)"])

# ✅ DYNAMIC COMPANY FIELD - ONLY SHOWS FOR COMPANY BOT
if "Company" in bot_type:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Company Page")
    company_name = st.sidebar.text_input(
        "Company Name", 
        placeholder="Meeshu automation, Microsoft, Google",
        help="Full company name as shown on LinkedIn"
    )
    if company_name:
        st.sidebar.info(f"🔍 Bot will search & switch to: '{company_name}'")
else:
    company_name = ""


# ✅ AUTO-CREDENTIALS
creds_option = st.sidebar.radio("📄 Credentials:", [
    "📁 Auto: credentials.json (same folder)",
    "📤 Upload JSON file"
])

# Headless toggle
headless_mode = st.sidebar.checkbox("🫥 Headless Mode (Hide Browser)", value=False)

# Manual inputs
email = st.sidebar.text_input("🔐 LinkedIn Email", type="password")
password = st.sidebar.text_input("🔑 LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("📊 Google Sheet URL")


# ✅ AUTO-DETECT credentials.json
@st.cache_data
def load_auto_creds():
    creds_path = "credentials.json"
    if os.path.exists(creds_path):
        try:
            with open(creds_path, 'r') as f:
                return json.load(f), creds_path
        except:
            return None, None
    return None, None

auto_creds, auto_creds_path = load_auto_creds()

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 START BOT", type="primary", use_container_width=True):
        # ✅ SMART CREDENTIALS LOGIC
        creds_file_path = None
        
        if creds_option == "📁 Auto: credentials.json (same folder)":
            if auto_creds and auto_creds_path:
                st.success(f"✅ Auto-loaded {auto_creds_path}")
                creds_file_path = auto_creds_path
            else:
                st.error("❌ credentials.json not found! Add it to same folder as app.py")
                st.stop()
        else:  # Upload option
            uploaded_file = st.sidebar.file_uploader("📄 Google Service Account JSON", type="json")
            if uploaded_file:
                creds_file_path = "temp_creds.json"
                with open(creds_file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                st.success("✅ Uploaded credentials saved")
            else:
                st.error("❌ Please upload JSON or add credentials.json")
                st.stop()
        
        # Validate all inputs
        if not all([email, password, sheet_url]):
            st.error("❌ Fill Email, Password, Sheet URL!")
            st.stop()

        st.success("✅ Bot launching...")
        progress = st.progress(0)
        logs = st.empty()  # ✅ logs created FIRST
        
        try:
            # ✅ DYNAMIC BOT IMPORT + COMPANY NAME
            if "Profile" in bot_type:
                from profile_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
            else:
                from company_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
                if company_name:
                    BotConfig.COMPANY_NAME = company_name.strip()  # ✅ Changed to COMPANY_NAME
                    logs.info(f"🏢 Company mode: '{company_name}'")
                else:
                    st.error("❌ Company name required for Company Bot!")
                    st.stop()
            
            # ✅ SET CONFIG (overrides your hardcoded paths!)
            BotConfig.GOOGLE_CREDENTIALS_FILE = creds_file_path
            BotConfig.GOOGLE_SHEET_URL = sheet_url
            BotConfig.LINKEDIN_EMAIL = email
            BotConfig.LINKEDIN_PASSWORD = password
            BotConfig.HEADLESS_MODE = headless_mode
            
            logs.info("🔄 Loading Google Sheets...")
            handler = GoogleSheetHandler(creds_file_path, sheet_url)
            data = handler.read_file()
            
            logs.success(f"✅ Loaded {len(data)} rows ({data[0] if data else 'No data'})")
            
            if not data:
                st.error("❌ Empty sheet! Add Post Url + Name + Status columns")
                st.stop()
            
            # 🔥 RUN YOUR ELITE BOT (skips done rows automatically!)
            bot = LinkedInCommentLiker(BotConfig)
            logs.info("🔄 Initializing LinkedIn..." + (" (Headless)" if headless_mode else ""))
            bot.initialize()
            logs.success("✅ LinkedIn ready! 🚀 Starting automation...")
            
            logs.info("🎯 Running FULL BOT (skips already DONE rows)...")
            bot.run()
            
            progress.progress(1.0)
            st.balloons()
            st.success("🎉 MISSION COMPLETE! Check Google Sheet Status column!")
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Bot crashed: {str(e)}")
            st.info("""
            **🔧 Quick Debug:**
            1. ✅ Sheet shared with service account email (from JSON)
            2. ✅ JSON has `client_email` field
            3. ✅ Columns: "Post Url" | "Name" | "Status" 
            4. ✅ LinkedIn credentials valid
            """)
        
        finally:
            # Cleanup
            if os.path.exists("temp_creds.json"):
                os.remove("temp_creds.json")

with col2:
    st.markdown("""
    **📋 Your Google Sheet MUST have:**
    ```
    Post Url          | Name       | Status
    https://lnkd.in/x | Bim Sphere | 
    https://lnkd.in/y | Anuj Kumar | DONE:Bim
    ```
    
    **✅ Features:**
    - 🧠 Auto credentials.json
    - 🫥 Headless toggle  
    - ⏭️ Skips DONE rows
    - 📊 Live logs + progress
    - 🏢 Dynamic Company field
    
    **⏱️ Timing:** 2-5min/row (25-50s stealth delays)
    """)

st.markdown("---")
st.caption("🤖 PRO: Auto-creds + Headless + Dynamic Company + Skip DONE rows!")
