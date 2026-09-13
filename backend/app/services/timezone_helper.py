from datetime import date, datetime
from typing import Any, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_user_today(user_or_tz: Any) -> Tuple[date, int]:
    """
    Returns (today_date, day_of_week) computed in the user's timezone using:
    datetime.now(ZoneInfo(user.timezone))
    If timezone is NULL or invalid, falls back to Europe/London (or UTC).
    day_of_week matches SyncShift calendar standard:
    0 = Sunday, 1 = Monday, 2 = Tuesday, 3 = Wednesday, 4 = Thursday, 5 = Friday, 6 = Saturday.
    """
    tz_str = None
    if isinstance(user_or_tz, str):
        tz_str = user_or_tz
    elif user_or_tz is not None:
        if isinstance(user_or_tz, dict):
            tz_str = user_or_tz.get("timezone")
        else:
            tz_str = getattr(user_or_tz, "timezone", None)

    tz = None
    if tz_str:
        try:
            tz = ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError, Exception):
            tz = None

    if tz is None:
        try:
            tz = ZoneInfo("Europe/London")
        except Exception:
            tz = ZoneInfo("UTC")

    now_tz = datetime.now(tz)
    today_date = now_tz.date()
    # Convert Python weekday (0=Mon..6=Sun) to SyncShift day_of_week (0=Sun, 1=Mon..6=Sat)
    today_dow = (today_date.weekday() + 1) % 7
    return today_date, today_dow
