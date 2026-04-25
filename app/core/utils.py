from datetime import datetime, timezone, timedelta

BOLIVIA_TIMEZONE = timezone(timedelta(hours=-4))

def now_bolivia() -> datetime:
    return datetime.now(BOLIVIA_TIMEZONE)

def utc_now() -> datetime:
    return datetime.now(BOLIVIA_TIMEZONE)