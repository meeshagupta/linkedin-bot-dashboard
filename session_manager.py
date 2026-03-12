"""
session_manager.py — Save and restore LinkedIn session cookies.

WHY THIS EXISTS:
  LinkedIn triggers verification (email/phone OTP) when it sees a
  fresh login from a cloud/data-centre IP.  Once you have logged in
  once (even manually), saving and re-using the cookies lets the bot
  skip the login page entirely on every subsequent run — no fresh
  credentials, no OTP challenge.

USAGE:
  # After a successful login:
  SessionManager.save(driver, "linkedin_session.pkl")

  # On the next run, BEFORE navigating to any page:
  ok = SessionManager.load(driver, "linkedin_session.pkl")
  if not ok:
      # fall back to normal email/password login
      ...
"""

import os
import pickle
import logging
import time

logger = logging.getLogger("SessionManager")

COOKIE_FILE_DEFAULT = "linkedin_session.pkl"


class SessionManager:

    @staticmethod
    def save(driver, path: str = COOKIE_FILE_DEFAULT) -> bool:
        """Persist all current browser cookies to disk."""
        try:
            cookies = driver.get_cookies()
            with open(path, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"💾 Session saved → {path}  ({len(cookies)} cookies)")
            return True
        except Exception as e:
            logger.error(f"Session save failed: {e}")
            return False

    @staticmethod
    def load(driver, path: str = COOKIE_FILE_DEFAULT) -> bool:
        """
        Inject saved cookies into the browser.
        Must call driver.get("https://www.linkedin.com") first so the
        domain matches, then reload after injecting.
        Returns True if cookies were loaded successfully.
        """
        if not os.path.exists(path):
            logger.info("No saved session found — will do fresh login.")
            return False

        try:
            # Navigate to LinkedIn domain so cookies can be set
            driver.get("https://www.linkedin.com")
            time.sleep(2)

            with open(path, "rb") as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                # Selenium doesn't accept 'expiry' as a float on some versions
                cookie.pop("expiry", None)
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass  # some cookies may be rejected; that's fine

            driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)

            # Check if we're actually logged in
            if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                logger.info("✅ Session restored from cookies — skipped login page!")
                return True
            else:
                logger.warning("⚠️ Cookies loaded but session expired — need fresh login.")
                return False

        except Exception as e:
            logger.error(f"Session load failed: {e}")
            return False

    @staticmethod
    def delete(path: str = COOKIE_FILE_DEFAULT):
        """Remove a saved session (e.g. after a verified logout)."""
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"🗑 Session file deleted: {path}")
