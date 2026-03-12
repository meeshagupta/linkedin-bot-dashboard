"""
session_manager.py — Save and restore LinkedIn session cookies.
Handles www vs non-www domain mismatch between PC-generated and cloud-loaded cookies.
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
            logger.info(f"Session saved -> {path}  ({len(cookies)} cookies)")
            return True
        except Exception as e:
            logger.error(f"Session save failed: {e}")
            return False

    @staticmethod
    def load(driver, path: str = COOKIE_FILE_DEFAULT) -> bool:
        if not os.path.exists(path):
            logger.info("No saved session found - will do fresh login.")
            return False

        try:
            with open(path, "rb") as f:
                cookies = pickle.load(f)

            logger.info(f"Loaded {len(cookies)} cookies from file")

            # Set cookies on BOTH domains to handle www vs non-www mismatch
            # LinkedIn uses both linkedin.com and www.linkedin.com
            for base_url in [
                "https://www.linkedin.com",
                "https://linkedin.com",
            ]:
                try:
                    driver.get(base_url)
                    time.sleep(2)

                    for cookie in cookies:
                        c = cookie.copy()
                        c.pop("expiry", None)
                        # Force domain to match current base_url
                        if "linkedin.com" in c.get("domain", ""):
                            c["domain"] = ".linkedin.com"  # dot prefix = all subdomains
                        try:
                            driver.add_cookie(c)
                        except Exception:
                            pass
                except Exception:
                    pass

            # Now navigate to feed and check if truly logged in
            driver.get("https://www.linkedin.com/feed/")
            time.sleep(5)

            # Check URL first
            url = driver.current_url
            if "login" in url or "checkpoint" in url or "authwall" in url:
                logger.warning("Session load: redirected to login page - session expired")
                return False

            # Check for actual logged-in page elements (not just URL)
            # LinkedIn feed shows a nav bar with user profile when logged in
            page_source = driver.page_source
            logged_in_indicators = [
                "feed-identity-module",     # profile card on feed
                "global-nav__me",           # nav bar profile icon
                "ember-view",               # LinkedIn's Ember app (only loads when logged in)
                "mynetwork",                # network tab only visible logged in
            ]

            for indicator in logged_in_indicators:
                if indicator in page_source:
                    logger.info(f"Session confirmed logged in (found: {indicator})")
                    return True

            # If none found but URL looks ok, check one more time after extra wait
            if "feed" in url:
                time.sleep(5)
                page_source = driver.page_source
                for indicator in logged_in_indicators:
                    if indicator in page_source:
                        logger.info(f"Session confirmed on second check (found: {indicator})")
                        return True

            logger.warning(f"Session loaded but page indicators not found. URL: {url}")
            logger.warning("Cookies may be expired - will attempt fresh login")
            return False

        except Exception as e:
            logger.error(f"Session load failed: {e}")
            return False

    @staticmethod
    def delete(path: str = COOKIE_FILE_DEFAULT):
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Session file deleted: {path}")
