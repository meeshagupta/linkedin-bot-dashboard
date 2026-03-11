"""
app.py — Streamlit dashboard for LinkedIn Bot.
Features: Start button, Stop button (thread-safe), live status display.
"""
import streamlit as st
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")

st.title("🤖 LinkedIn Comment Liker Bot - PRO")
st.markdown("---")

# ── Session state init ────────────────────────────────────────────────────────
if "stop_event"   not in st.session_state:
    st.session_state.stop_event   = threading.Event()
if "bot_running"  not in st.session_state:
    st.session_state.bot_running  = False
if "bot_status"   not in st.session_state:
    st.session_state.bot_status   = "idle"   # idle | running | stopped | done | error
if "status_msg"   not in st.session_state:
    st.session_state.status_msg   = ""

# ── Sidebar ───────────────────────────────────────────────────────────────────
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
        help="Exact company name as shown on LinkedIn",
    )
    if company_name:
        st.sidebar.info(f"🔍 Will switch to: '{company_name}'")
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
st.sidebar.info("🖥️ Browser runs headless (invisible) on Streamlit Cloud automatically.")

email     = st.sidebar.text_input("🔐 LinkedIn Email")
password  = st.sidebar.text_input("🔑 LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("📊 Google Sheet URL")

# ── Status banner ─────────────────────────────────────────────────────────────
status_colors = {
    "idle":    ("⚪", "secondary"),
    "running": ("🟢", "success"),
    "stopped": ("🔴", "error"),
    "done":    ("✅", "success"),
    "error":   ("❌", "error"),
}
icon, _ = status_colors.get(st.session_state.bot_status, ("⚪", "secondary"))
st.markdown(f"**Status:** {icon} `{st.session_state.bot_status.upper()}`"
            + (f" — {st.session_state.status_msg}" if st.session_state.status_msg else ""))

# ── Control buttons ───────────────────────────────────────────────────────────
col_start, col_stop, col_spacer = st.columns([1, 1, 4])

with col_start:
    start_clicked = st.button(
        "🚀 START BOT",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.bot_running,
    )

with col_stop:
    stop_clicked = st.button(
        "⏹ STOP BOT",
        type="secondary",
        use_container_width=True,
        disabled=not st.session_state.bot_running,
    )

# ── Stop handler (immediate) ──────────────────────────────────────────────────
if stop_clicked:
    st.session_state.stop_event.set()
    st.session_state.bot_running = False
    st.session_state.bot_status  = "stopped"
    st.session_state.status_msg  = "Stop signal sent — bot will finish current action then halt"
    st.warning("⏹ Stop signal sent. Bot will stop after current row completes.")
    st.rerun()

# ── Output area ───────────────────────────────────────────────────────────────
output_area = st.empty()

# ── Bot thread function ───────────────────────────────────────────────────────
def run_bot(bot_type, email, password, sheet_url, company_name,
            creds_path, stop_event):
    try:
        if "Profile" in bot_type:
            from profile_bot import Config as BotConfig, LinkedInCommentLiker
        else:
            from company_bot import Config as BotConfig, LinkedInCommentLiker
            BotConfig.COMPANY_NAME = company_name.strip()

        BotConfig.GOOGLE_CREDENTIALS_FILE = creds_path
        BotConfig.GOOGLE_SHEET_URL        = sheet_url
        BotConfig.LINKEDIN_EMAIL          = email
        BotConfig.LINKEDIN_PASSWORD       = password
        BotConfig.HEADLESS_MODE           = True

        bot = LinkedInCommentLiker(BotConfig, stop_event=stop_event)
        bot.initialize()
        bot.run()

        if stop_event.is_set():
            st.session_state.bot_status  = "stopped"
            st.session_state.status_msg  = "Bot stopped by user"
        else:
            st.session_state.bot_status  = "done"
            st.session_state.status_msg  = "All rows processed!"

    except Exception as e:
        st.session_state.bot_status  = "error"
        st.session_state.status_msg  = str(e)

    finally:
        st.session_state.bot_running = False
        if os.path.exists(creds_path):
            os.remove(creds_path)

# ── Start handler ─────────────────────────────────────────────────────────────
if start_clicked:
    # Validate inputs
    if not uploaded_file:
        st.error("❌ Upload Google Service Account JSON first!")
        st.stop()
    if not all([email, password, sheet_url]):
        st.error("❌ Fill in Email, Password and Sheet URL!")
        st.stop()
    if "Company" in bot_type and not company_name.strip():
        st.error("❌ Company name is required for Company Bot!")
        st.stop()

    # Save credentials temporarily
    creds_path = "temp_creds.json"
    with open(creds_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Reset stop event for fresh run
    st.session_state.stop_event  = threading.Event()
    st.session_state.bot_running = True
    st.session_state.bot_status  = "running"
    st.session_state.status_msg  = "Bot is running…"

    thread = threading.Thread(
        target=run_bot,
        args=(bot_type, email, password, sheet_url, company_name,
              creds_path, st.session_state.stop_event),
        daemon=True,
    )
    thread.start()
    st.rerun()

# ── Running indicator ─────────────────────────────────────────────────────────
if st.session_state.bot_running:
    output_area.info(
        "🤖 Bot is running in the background.\n\n"
        "• It will like the post and up to 3 comments for each URL in your sheet.\n"
        "• Status updates appear in your Google Sheet in real time.\n"
        "• Press **⏹ STOP BOT** at any time to halt after the current row."
    )

# ── Help panel ────────────────────────────────────────────────────────────────
st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("""
    **📋 Google Sheet format:**
    | Post Url | Name | Status |
    |----------|------|--------|
    | https://lnkd.in/xyz | John Doe | |
    | https://lnkd.in/abc | Jane Doe | |
    """)

with col_b:
    st.markdown("""
    **🔧 Common fixes if bot shows FAILED:**
    1. Make sure the post URL is a **direct post link** (not a feed URL)
    2. Share the Google Sheet with the `client_email` from your JSON
    3. Sheet columns must be: **Post Url** | **Name** | **Status**
    4. Check LinkedIn credentials are correct
    """)

st.caption("🤖 PRO Edition · Streamlit Cloud Ready · Stop Anytime")
