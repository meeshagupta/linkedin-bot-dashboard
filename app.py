import streamlit as st
import time
import os
import sys
import tempfile

# ✅ Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

st.title("🤖 LinkedIn Comment Liker Bot - PRO")
st.markdown("---")

# Sidebar - CLEAN & SIMPLE
st.sidebar.header("🔧 Bot Configuration")
bot_type = st.sidebar.selectbox("Choose Bot:", ["Profile (profile_bot.py)", "Company (company_bot.py)"])

# ✅ DYNAMIC COMPANY FIELD
if "Company" in bot_type:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Company Page")
    company_name = st.sidebar.text_input(
        "Company Name", 
        placeholder="Meeshu automation, Microsoft, Google",
        help="Full company name as shown on LinkedIn"
    )
    if company_name:
        st.sidebar.info(f"🔍 Bot will auto-switch to: '{company_name}'")
else:
    company_name = ""

# ✅ ONLY UPLOAD JSON - NO AUTO OPTION!
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Credentials")
uploaded_file = st.sidebar.file_uploader(
    "📄 Google Service Account JSON", 
    type="json",
    help="Upload your credentials.json file"
)

if uploaded_file:
    st.sidebar.success(f"✅ {uploaded_file.name} loaded!")
else:
    st.sidebar.warning("❌ Upload JSON file first!")

# Headless toggle
st.sidebar.markdown("---")
headless_mode = st.sidebar.checkbox("🫥 Headless Mode (Hide Browser)", value=False)

# Manual inputs
email = st.sidebar.text_input("🔐 LinkedIn Email", type="password")
password = st.sidebar.text_input("🔑 LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("📊 Google Sheet URL")

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 START BOT", type="primary", use_container_width=True):
        # ✅ SIMPLE VALIDATION
        if not uploaded_file:
            st.error("❌ Upload Google Service Account JSON first!")
            st.stop()
        
        if not all([email, password, sheet_url]):
            st.error("❌ Fill Email, Password, Sheet URL!")
            st.stop()

        # ✅ SAVE UPLOADED FILE
        creds_file_path = "temp_creds.json"
        with open(creds_file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.success(f"✅ {uploaded_file.name} ready!")

        st.success("✅ Bot launching...")
        progress = st.progress(0)
        logs = st.empty()
        
        try:
            # Dynamic bot import
            if "Profile" in bot_type:
                from profile_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
            else:
                from company_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
                if company_name:
                    BotConfig.COMPANY_NAME = company_name.strip()
                    logs.info(f"🏢 Company: '{company_name}'")
                else:
                    st.error("❌ Company name required for Company Bot!")
                    st.stop()
            
            # Set config
            BotConfig.GOOGLE_CREDENTIALS_FILE = creds_file_path
            BotConfig.GOOGLE_SHEET_URL = sheet_url
            BotConfig.LINKEDIN_EMAIL = email
            BotConfig.LINKEDIN_PASSWORD = password
            BotConfig.HEADLESS_MODE = headless_mode
            
            logs.info("🔄 Loading Google Sheets...")
            handler = GoogleSheetHandler(creds_file_path, sheet_url)
            data = handler.read_file()
            logs.success(f"✅ Loaded {len(data)} rows")
            
            if not data:
                st.error("❌ Empty sheet! Need 'Post Url', 'Name', 'Status' columns")
                st.stop()
            
            bot = LinkedInCommentLiker(BotConfig)
            logs.info("🔄 Initializing LinkedIn...")
            bot.initialize()
            logs.success("✅ LinkedIn ready!")
            
            logs.info("🎯 Running bot (skips DONE rows)...")
            bot.run()
            
            progress.progress(1.0)
            st.balloons()
            st.success("🎉 MISSION COMPLETE! Check Google Sheet!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("""
            **🔧 Debug:**
            1. Share sheet with service account email (from JSON)
            2. JSON must have `client_email` field
            3. Sheet columns: Post Url | Name | Status
            """)
        
        finally:
            if os.path.exists("temp_creds.json"):
                os.remove("temp_creds.json")

with col2:
    st.markdown("""
    **📋 Google Sheet Format:**
    ```
    Post Url          | Name       | Status
    https://lnkd.in/x | Bim Sphere | 
    https://lnkd.in/y | Anuj Kumar | 
    ```
    
    **✅ Features:**
    • 📤 Upload JSON only
    • 🫥 Headless mode
    • ⏭️ Skip DONE rows  
    • 🏢 Company switch (Company Bot)
    
    **⏱️ 2-5min per row**
    """)

st.markdown("---")
st.caption("🤖 PRO: Upload Only + Cloud Ready!")

