# =====================================================
# ENVIRONMENT & COOKIE MANAGEMENT
# =====================================================

import os
import time


def is_local_desktop():
    """
    Detect if app is running locally on a desktop machine.
    Streamlit Cloud / mobile = False
    """
    return os.path.exists("data") and os.path.isdir("data")


COOKIE_PATH = "data/nse_cookies.json"

COOKIE_STALE_HOURS = 12
COOKIE_EXPIRE_HOURS = 36


def get_cookie_age_hours():
    if not os.path.exists(COOKIE_PATH):
        return None
    mtime = os.path.getmtime(COOKIE_PATH)
    age_seconds = time.time() - mtime
    return round(age_seconds / 3600, 1)


def get_cookie_status():
    """
    Returns: (status, age_hours)

    status ∈ {"MISSING", "FRESH", "STALE", "EXPIRED"}
    """
    age = get_cookie_age_hours()

    if age is None:
        return "MISSING", None
    if age >= COOKIE_EXPIRE_HOURS:
        return "EXPIRED", age
    if age >= COOKIE_STALE_HOURS:
        return "STALE", age
    return "FRESH", age