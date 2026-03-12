"""
session_manager.py — Save and restore LinkedIn session cookies.
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
        if not os.path.exists(path):
            logger.info("No saved session found — will do fresh login.")
            return False

        try:
            driver.get("https://www.linkedin.com")
            time.sleep(3)   # wait for page to settle before adding cookies

            with open(path, "rb") as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                cookie.pop("expiry", None)
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

            driver.get("https://www.linkedin.com/feed/")
            
            # Wait longer — LinkedIn feed can be slow to load on cloud
            for _ in range(15):   # up to 15 seconds
                time.sleep(1)
                url = driver.current_url
                if "feed" in url or "mynetwork" in url or "in/" in url:
                    logger.info("✅ Session restored from cookies — skipped login page!")
                    return True
                if "login" in url or "checkpoint" in url:
                    logger.warning("⚠️ Cookies loaded but LinkedIn redirected to login — session expired.")
                    return False

            # Final check after waiting
            url = driver.current_url
            if "feed" in url or "mynetwork" in url:
                logger.info("✅ Session restored from cookies!")
                return True
            else:
                logger.warning(f"⚠️ Session check failed — current URL: {url}")
                return False

        except Exception as e:
            logger.error(f"Session load failed: {e}")
            return False

    @staticmethod
    def delete(path: str = COOKIE_FILE_DEFAULT):
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"🗑 Session file deleted: {path}")
