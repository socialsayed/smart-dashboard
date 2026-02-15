import datetime
from config import IST


def now_ist():
    return datetime.datetime.now(IST)


def market_status():
    now = now_ist()
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if now.weekday() >= 5:  # Saturday / Sunday
        next_open = open_t + datetime.timedelta(days=(7 - now.weekday()))
        return False, next_open

    if open_t <= now <= close_t:
        return True, None

    if now < open_t:
        return False, open_t

    return False, open_t + datetime.timedelta(days=1)


def countdown(target_time):
    delta = target_time - now_ist()
    if delta.total_seconds() <= 0:
        return "00:00:00"

    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
