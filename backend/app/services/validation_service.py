"""
Input validation service.
All business-rule checks (dates, times, services, holidays) are centralised here.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.constants.clinic import (
    DENTAL_SERVICES,
    SERVICE_ALIASES,
)
from app.utils.date_utils import (
    is_working_day,
    is_working_hour,
    is_past_datetime,
    parse_date,
    parse_time,
    today_in_clinic_tz,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Path to the holidays configuration file (relative to backend/ root)
# __file__ = backend/app/services/validation_service.py
# parents[2] = backend/
HOLIDAYS_FILE = Path(__file__).resolve().parents[2] / "holidays.json"


def _load_holidays() -> Dict[str, str]:
    """Load holidays from holidays.json. Returns {YYYY-MM-DD: holiday_name}."""
    if not HOLIDAYS_FILE.exists():
        logger.warning("holidays.json not found at %s — no holidays configured.", HOLIDAYS_FILE)
        return {}
    try:
        with open(HOLIDAYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("holidays", {})
    except Exception as exc:
        logger.error("Failed to load holidays.json: %s", exc)
        return {}


def get_holiday_name(date_str: str) -> Optional[str]:
    """Return the holiday name for the given date, or None if it's not a holiday."""
    holidays = _load_holidays()
    return holidays.get(date_str)


def is_holiday(date_str: str) -> bool:
    """Return True if the given date is configured as a public holiday."""
    return date_str in _load_holidays()


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format. Returns (is_valid, error_message)."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email.strip()):
        return False, "Please provide a valid email address."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Validate and normalise an Indian mobile number.
    Returns (is_valid, error_message_or_normalised_number).
    """
    # Strip ALL non-digit characters (handles spaces, dashes, dots the AI may include)
    cleaned = re.sub(r"\D", "", phone)
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    if not re.fullmatch(r"[6-9]\d{9}", cleaned):
        return False, "Phone number must be a valid 10-digit Indian mobile number (starting with 6, 7, 8, or 9)."
    return True, cleaned


def validate_service(service: str) -> Tuple[bool, str]:
    """
    Validate the requested dental service.
    Performs case-insensitive matching against canonical names and aliases.
    Returns (is_valid, canonical_service_name_or_error).
    """
    normalised = service.strip().lower()

    # Try direct match (case-insensitive)
    for canonical in DENTAL_SERVICES:
        if canonical.lower() == normalised:
            return True, canonical

    # Try alias match
    if normalised in SERVICE_ALIASES:
        return True, SERVICE_ALIASES[normalised].value

    return (
        False,
        f"'{service}' is not a recognised service. "
        f"Available services: {', '.join(DENTAL_SERVICES)}.",
    )


def validate_appointment_date(date_str: str) -> Tuple[bool, str]:
    """
    Validate appointment date against:
    - Correct format (YYYY-MM-DD)
    - Not in the past
    - Is a working day (Mon–Sat)
    - Is not a holiday
    Returns (is_valid, error_message).
    """
    # Format check
    try:
        d = parse_date(date_str)
    except ValueError:
        return False, "Please provide the date in YYYY-MM-DD format."

    # Past check
    today = today_in_clinic_tz()
    if d < today:
        return False, "The appointment date cannot be in the past."

    # Working day check
    if not is_working_day(d):
        day_name = d.strftime("%A")
        return (
            False,
            f"{day_name} is not a working day. We operate Monday to Saturday.",
        )

    # Holiday check
    holiday_name = get_holiday_name(date_str)
    if holiday_name:
        return (
            False,
            f"{date_str} is a public holiday ({holiday_name}). Please choose another date.",
        )

    return True, ""


def validate_appointment_time(time_str: str, date_str: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate appointment time against:
    - Correct format (HH:MM)
    - Within working hours (09:00–17:30)
    - Not in the past (if date is today)
    Returns (is_valid, error_message).
    """
    try:
        t = parse_time(time_str)
    except ValueError:
        return False, "Please provide the time in HH:MM format."

    if not is_working_hour(t):
        return (
            False,
            f"Appointments are available between 9:00 AM and 5:30 PM "
            f"(last slot). Please choose a time within working hours.",
        )

    if date_str:
        try:
            if is_past_datetime(date_str, time_str):
                return False, "The selected appointment slot is in the past. Please choose a future time."
        except Exception:
            pass  # Non-fatal; date validation handles format errors

    return True, ""


def validate_booking_request(
    full_name: str,
    phone: str,
    email: str,
    service: str,
    preferred_date: str,
    preferred_time: str,
) -> Tuple[bool, Dict[str, str], Dict[str, str]]:
    """
    Run all validations for a booking request.

    Returns:
        (all_valid, errors_dict, normalised_values_dict)
        - errors_dict maps field → error message
        - normalised_values_dict maps field → cleaned value (phone, service)
    """
    errors: Dict[str, str] = {}
    normalised: Dict[str, str] = {}

    # Name
    if not full_name or len(full_name.strip()) < 2:
        errors["full_name"] = "Please provide your full name (at least 2 characters)."

    # Phone
    phone_valid, phone_result = validate_phone(phone)
    if phone_valid:
        normalised["phone"] = phone_result
    else:
        errors["phone"] = phone_result

    # Email
    email_valid, email_error = validate_email(email)
    if not email_valid:
        errors["email"] = email_error

    # Service
    service_valid, service_result = validate_service(service)
    if service_valid:
        normalised["service"] = service_result
    else:
        errors["service"] = service_result

    # Date
    date_valid, date_error = validate_appointment_date(preferred_date)
    if not date_valid:
        errors["preferred_date"] = date_error

    # Time (only fully validate if date is valid, to avoid misleading past-slot errors)
    time_valid, time_error = validate_appointment_time(
        preferred_time, preferred_date if date_valid else None
    )
    if not time_valid:
        errors["preferred_time"] = time_error

    all_valid = len(errors) == 0
    logger.debug("Validation result for '%s': valid=%s errors=%s", full_name, all_valid, errors)
    return all_valid, errors, normalised
