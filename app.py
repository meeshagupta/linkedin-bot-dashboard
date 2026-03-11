import streamlit as st
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

st.title("🤖 LinkedIn Comment Liker Bot - PRO")
st.markdown("---")

st.sidebar.header("🔧 Bot Configuration")
bot_type = st.sidebar.selectbox(
    "Choose Bot:", ["Profile (profile_bot.py)", "Company (company_bot.py)"]
)

if "Company" in bot_type:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Company Page")
    company_name = st.sidebar.text_input(
        "Company Name",
        placeholder="e.g. Microsoft, Google",
        help="Full company name as shown on LinkedIn",
    )
    if company_name:
        st.sidebar.info(f"🔍 Bot will switch to: '{company_name}'")
else:
    company_name = ""

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Credentials")
uploaded_file = st.sidebar.file_uploader(
    "📄 Google Service Account JSON",
    type="json",
    help="Upload your credentials.json file",
)
if uploaded_file:
    st.sidebar.success(f"✅ {uploaded_file.name} loaded!")
else:
    st.sidebar.warning("❌ Upload JSON file first!")

st.sidebar.markdown("---")
st.sidebar.info(
    "🖥️ **Headless mode** is automatically enabled on Streamlit Cloud. "
    "The browser runs invisibly in the background."
)

email     = st.sidebar.text_input("🔐 LinkedIn Email")
password  = st.sidebar.text_input("🔑 LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("📊 Google Sheet URL")

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 START BOT", type="primary", use_container_width=True):

        if not uploaded_file:
            st.error("❌ Upload Google Service Account JSON first!")
            st.stop()
        if not all([email, password, sheet_url]):
            st.error("❌ Fill in Email, Password and Sheet URL!")
            st.stop()
        if "Company" in bot_type and not company_name.strip():
            st.error("❌ Company name is required for Company Bot!")
            st.stop()

        creds_path = "temp_creds.json"
        with open(creds_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.success(f"✅ {uploaded_file.name} saved temporarily")

        progress = st.progress(0)
        logs     = st.empty()
        logs.info("🔄 Importing bot module...")

        try:
            if "Profile" in bot_type:
                from profile_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
            else:
                from company_bot import Config as BotConfig, LinkedInCommentLiker, GoogleSheetHandler
                BotConfig.COMPANY_NAME = company_name.strip()

            BotConfig.GOOGLE_CREDENTIALS_FILE = creds_path
            BotConfig.GOOGLE_SHEET_URL        = sheet_url
            BotConfig.LINKEDIN_EMAIL          = email
            BotConfig.LINKEDIN_PASSWORD       = password
            BotConfig.HEADLESS_MODE           = True

            logs.info("🔄 Connecting to Google Sheets...")
            handler = GoogleSheetHandler(creds_path, sheet_url)
            data    = handler.read_file()

            if not data:
                st.error("❌ Sheet is empty or missing columns. Required: Post Url | Name | Status")
                st.stop()

            logs.success(f"✅ Loaded {len(data)} rows from sheet")
            logs.info("🔄 Starting Chrome and logging in to LinkedIn...")

            bot = LinkedInCommentLiker(BotConfig)
            bot.initialize()
            logs.success("✅ LinkedIn logged in!")

            logs.info("🎯 Running bot — skipping rows already marked DONE...")
            bot.run()

            progress.progress(1.0)
            st.balloons()
            st.success("🎉 Mission complete! Check your Google Sheet for results.")

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info(
                "**🔧 Common fixes:**\n"
                "1. Share the Google Sheet with the `client_email` from your JSON\n"
                "2. Sheet must have columns: Post Url | Name | Status\n"
                "3. Check LinkedIn email/password are correct\n"
                "4. Make sure `packages.txt` is in your repo root (installs Chromium)"
            )

        finally:
            if os.path.exists("temp_creds.json"):
                os.remove("temp_creds.json")

with col2:
    st.markdown("""
    **📋 Google Sheet format:**
    ```
    Post Url          | Name       | Status
    https://lnkd.in/x | Bim Sphere | 
    https://lnkd.in/y | Anuj Kumar | 
    ```

    **✅ Features:**
    - 📤 Upload JSON only
    - ☁️ Auto headless on cloud
    - ⏭️ Skip DONE rows
    - 🏢 Company page switch

    **⏱️ ~2–5 min per row**
    """)

st.markdown("---")
st.caption("🤖 PRO Edition · Upload Only · Streamlit Cloud Ready")
