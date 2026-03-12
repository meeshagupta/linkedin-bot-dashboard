import streamlit as st
import threading
import queue
import os
import sys
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="LinkedIn Bot", page_icon="🤖", layout="wide")
st.title("🤖 LinkedIn Comment Liker Bot - PRO")
st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "stop_event":          threading.Event(),
    "bot_running":         False,
    "bot_status":          "idle",
    "status_msg":          "",
    "log_lines":           [],
    "log_queue":           queue.Queue(),
    "saved_cookie_bytes":  None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("🔧 Bot Configuration")
bot_type = st.sidebar.selectbox("Choose Bot:", ["Profile (profile_bot.py)", "Company (company_bot.py)"])

if "Company" in bot_type:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Company Page")
    company_name = st.sidebar.text_input("Company Name", placeholder="e.g. Microsoft, Google")
    if company_name:
        st.sidebar.info(f"🔍 Will switch to: '{company_name}'")
else:
    company_name = ""

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Credentials")
uploaded_file = st.sidebar.file_uploader("📄 Google Service Account JSON", type="json")
if uploaded_file:
    st.sidebar.success(f"✅ {uploaded_file.name} loaded!")
else:
    st.sidebar.warning("❌ Upload JSON file first!")

st.sidebar.markdown("---")
st.sidebar.subheader("🍪 Session Cookie (Recommended)")
cookie_file_upload = st.sidebar.file_uploader(
    "Upload linkedin_session.pkl",
    type=["pkl"],
    help="Upload a saved session file to skip login and avoid verification challenges. "
         "Generate this once by running locally — see instructions below."
)
if cookie_file_upload:
    st.sidebar.success("✅ Session cookie loaded — will skip login page!")
else:
    st.sidebar.info(
        "ℹ️ No session file — bot will log in fresh. "
        "If you get a verification error, follow the local-run instructions below."
    )

st.sidebar.markdown("---")
st.sidebar.info("🖥️ Browser runs headless (invisible) on Streamlit Cloud automatically.")
email     = st.sidebar.text_input("🔐 LinkedIn Email")
password  = st.sidebar.text_input("🔑 LinkedIn Password", type="password")
sheet_url = st.sidebar.text_input("📊 Google Sheet URL")

# ── Status ────────────────────────────────────────────────────────────────────
icons = {"idle":"⚪","running":"🟢","stopped":"🔴","done":"✅","error":"❌"}
icon  = icons.get(st.session_state.bot_status, "⚪")
st.markdown(f"**Status:** {icon} `{st.session_state.bot_status.upper()}`"
            + (f" — {st.session_state.status_msg}" if st.session_state.status_msg else ""))

# ── Buttons ───────────────────────────────────────────────────────────────────
c1, c2, _ = st.columns([1, 1, 4])
with c1:
    start_clicked = st.button("🚀 START BOT", type="primary",
                               use_container_width=True,
                               disabled=st.session_state.bot_running)
with c2:
    stop_clicked = st.button("⏹ STOP BOT", type="secondary",
                              use_container_width=True,
                              disabled=not st.session_state.bot_running)

# ── Live log ──────────────────────────────────────────────────────────────────
st.markdown("#### 📋 Live Log")

# Drain queue into log_lines
while not st.session_state.log_queue.empty():
    try:
        st.session_state.log_lines.append(st.session_state.log_queue.get_nowait())
    except queue.Empty:
        break

log_text = "\n".join(st.session_state.log_lines[-40:]) or "Waiting for bot to start…"
st.code(log_text, language=None)

if st.button("🗑 Clear log"):
    st.session_state.log_lines = []
    st.rerun()

# ── Stop ──────────────────────────────────────────────────────────────────────
if stop_clicked:
    st.session_state.stop_event.set()
    st.session_state.bot_running = False
    st.session_state.bot_status  = "stopped"
    st.session_state.status_msg  = "Stop signal sent"
    st.warning("⏹ Bot will stop after completing current action.")
    st.rerun()

# ── Thread helpers ────────────────────────────────────────────────────────────
def attach_queue_handler(log_queue, logger_name):
    class QH(logging.Handler):
        def emit(self, r):
            log_queue.put(self.format(r))
    h = QH()
    h.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    lg = logging.getLogger(logger_name)
    lg.handlers = [x for x in lg.handlers if not isinstance(x, QH)]
    lg.addHandler(h)
    lg.setLevel(logging.INFO)

def run_bot(bot_type, email, password, sheet_url, company_name,
            creds_path, cookie_path, stop_event, log_queue):
    try:
        if "Profile" in bot_type:
            import profile_bot as mod
            attach_queue_handler(log_queue, "ProfileBot")
        else:
            import company_bot as mod
            attach_queue_handler(log_queue, "CompanyBot")
            mod.Config.COMPANY_NAME = company_name.strip()

        mod.Config.GOOGLE_CREDENTIALS_FILE = creds_path
        mod.Config.GOOGLE_SHEET_URL        = sheet_url
        mod.Config.LINKEDIN_EMAIL          = email
        mod.Config.LINKEDIN_PASSWORD       = password
        mod.Config.HEADLESS_MODE           = True
        mod.Config.COOKIE_FILE             = cookie_path   # ← NEW

        log_queue.put("⏳ Starting Chrome and logging in…")
        bot = mod.LinkedInCommentLiker(mod.Config, stop_event=stop_event)
        bot.initialize()
        log_queue.put("✅ Logged in! Processing posts now…")
        bot.run()

        # If a new session was saved (fresh login), make it downloadable
        if os.path.exists(cookie_path):
            with open(cookie_path, "rb") as f:
                st.session_state["saved_cookie_bytes"] = f.read()

        st.session_state.bot_status = "stopped" if stop_event.is_set() else "done"
        st.session_state.status_msg = "Stopped by user" if stop_event.is_set() else "All rows done!"

    except Exception as e:
        st.session_state.bot_status = "error"
        st.session_state.status_msg = str(e)
        log_queue.put(f"❌ ERROR: {e}")
    finally:
        st.session_state.bot_running = False
        if os.path.exists(creds_path):
            os.remove(creds_path)

# ── Start ─────────────────────────────────────────────────────────────────────
if start_clicked:
    if not uploaded_file:
        st.error("❌ Upload Google Service Account JSON first!"); st.stop()
    if not all([email, password, sheet_url]):
        st.error("❌ Fill in Email, Password and Sheet URL!"); st.stop()
    if "Company" in bot_type and not company_name.strip():
        st.error("❌ Company name required for Company Bot!"); st.stop()

    creds_path  = "temp_creds.json"
    cookie_path = "linkedin_session.pkl"

    with open(creds_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Write uploaded session cookie file if provided
    if cookie_file_upload:
        with open(cookie_path, "wb") as f:
            f.write(cookie_file_upload.getvalue())

    st.session_state.stop_event         = threading.Event()
    st.session_state.log_queue          = queue.Queue()
    st.session_state.log_lines          = []
    st.session_state.bot_running        = True
    st.session_state.bot_status         = "running"
    st.session_state.status_msg         = "Bot is running…"
    st.session_state.saved_cookie_bytes = None

    threading.Thread(
        target=run_bot,
        args=(bot_type, email, password, sheet_url, company_name,
              creds_path, cookie_path,
              st.session_state.stop_event, st.session_state.log_queue),
        daemon=True,
    ).start()
    st.rerun()

# ── Download saved session cookie after first login ───────────────────────────
if st.session_state.saved_cookie_bytes:
    st.success("🍪 New session saved! Download and re-upload next time to skip login:")
    st.download_button(
        "⬇️ Download linkedin_session.pkl",
        data     = st.session_state.saved_cookie_bytes,
        file_name= "linkedin_session.pkl",
        mime     = "application/octet-stream",
    )

# ── Auto-refresh while running ────────────────────────────────────────────────
if st.session_state.bot_running:
    time.sleep(2)
    st.rerun()

# ── Help ──────────────────────────────────────────────────────────────────────
st.markdown("---")
ca, cb = st.columns(2)
with ca:
    st.markdown("**📋 Sheet format:** `Post Url | Name | Status`")
with cb:
    st.markdown("**🔧 If FAILED:** Use direct post URLs, not feed URLs")

with st.expander("🔑 First-time setup: How to generate linkedin_session.pkl"):
    st.markdown("""
**You only need to do this once when running on Streamlit Cloud.**

1. **On your own PC**, install the requirements:
   ```
   pip install selenium undetected-chromedriver
   ```

2. **Run this one-time script** (saves `linkedin_session.pkl` to your folder):
   ```python
   import time, pickle
   import undetected_chromedriver as uc

   driver = uc.Chrome(headless=False)          # visible window
   driver.get("https://www.linkedin.com/login")
   input("Log in manually in the browser, complete any verification, "
         "then press ENTER here...")
   pickle.dump(driver.get_cookies(), open("linkedin_session.pkl","wb"))
   print("Saved! Upload this file to Streamlit.")
   driver.quit()
   ```

3. **Upload `linkedin_session.pkl`** via the sidebar on Streamlit Cloud.

4. The bot will now skip the login page entirely — no more verification challenges! ✅
    """)

st.caption("🤖 PRO Edition · Streamlit Cloud Ready · Stop Anytime")
