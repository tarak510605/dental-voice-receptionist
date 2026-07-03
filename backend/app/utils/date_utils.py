"""
Timezone-aware date and time utilities.
All external-facing dates/times are expressed in Asia/Kolkata (IST, UTC+5:30).
"""

from datetime import datetime, date, time, timedelta
from typing import List, Optional
import pytz

from app.config.settings import get_settings
from app.constants.clinic import (
    WORKING_WEEKDAY_INTS,
    WORKING_HOURS_START,
    WORKING_HOURS_END,
)

_settings = get_settings()
SLOT_DURATION_MINUTES: int = _settings.SLOT_DURATION_MINUTES


def get_clinic_timezone() -> pytz.BaseTzInfo:
    """Return the configured clinic timezone (default: Asia/Kolkata)."""
    return pytz.timezone(_settings.TIMEZONE)


def now_in_clinic_tz() -> datetime:
    """Return the current datetime in the clinic's local timezone."""
    return datetime.now(tz=get_clinic_timezone())


def today_in_clinic_tz() -> date:
    """Return today's date in the clinic's local timezone."""
    return now_in_clinic_tz().date()


def parse_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD string into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def parse_time(time_str: str) -> time:
    """Parse HH:MM (or HH:MM:SS) into a time object."""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time string: {time_str!r}")


def is_working_day(d: date) -> bool:
    """Return True if *d* is a weekday the clinic operates (Mon–Sat)."""
    return d.weekday() in WORKING_WEEKDAY_INTS


def is_working_hour(t: time) -> bool:
    """
    Return True if *t* falls within the clinic's appointment window.
    The last bookable slot starts SLOT_DURATION_MINUTES before closing.
    Example: close=18:00, slot=30 min → last slot starts at 17:30.
    """
    from datetime import datetime as _dt

    slot_start = time(WORKING_HOURS_START, 0)
    # Compute last slot start as a timedelta subtraction on a dummy datetime
    closing = _dt.combine(date.today(), time(WORKING_HOURS_END, 0))
    last_slot_dt = closing - timedelta(minutes=SLOT_DURATION_MINUTES)
    last_slot = last_slot_dt.time()
    return slot_start <= t <= last_slot


def is_past_datetime(date_str: str, time_str: str) -> bool:
    """Return True if the given date+time is in the past (clinic timezone)."""
    tz = get_clinic_timezone()
    d = parse_date(date_str)
    t = parse_time(time_str)
    dt = tz.localize(datetime.combine(d, t))
    return dt < now_in_clinic_tz()


def generate_slots(d: date) -> List[str]:
    """
    Generate all 30-minute appointment slots for a given date.
    Returns a list of HH:MM strings from 09:00 to 17:30.
    """
    slots: List[str] = []
    slot_minutes = _settings.SLOT_DURATION_MINUTES
    current = datetime.combine(d, time(WORKING_HOURS_START, 0))
    end = datetime.combine(d, time(WORKING_HOURS_END, 0))
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=slot_minutes)
    return slots


def format_date_human(date_str: str) -> str:
    """Convert YYYY-MM-DD to a human-friendly format: Monday, 15 July 2026."""
    d = parse_date(date_str)
    return d.strftime("%A, %d %B %Y")


def format_time_human(time_str: str) -> str:
    """Convert HH:MM to 12-hour format: 10:30 AM."""
    t = parse_time(time_str)
    return datetime.combine(date.today(), t).strftime("%I:%M %p").lstrip("0")


def get_day_of_week(date_str: str) -> str:
    """Return the full day name for a YYYY-MM-DD string."""
    return parse_date(date_str).strftime("%A")
