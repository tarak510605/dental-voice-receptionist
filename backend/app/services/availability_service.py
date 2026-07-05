"""
Availability service.
Determines which time slots are free on a given date by cross-referencing
existing bookings in Google Sheets.
"""

from typing import List, Optional, Set, Tuple

from app.schemas.booking import AvailabilityResponse, AvailabilitySlot
from app.services import sheets_service
from app.services.validation_service import get_holiday_name, is_holiday
from app.utils.date_utils import (
    generate_slots,
    get_clinic_timezone,
    get_day_of_week,
    is_working_day,
    now_in_clinic_tz,
    parse_date,
    parse_time,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_availability(date_str: str) -> AvailabilityResponse:
    """
    Return the full availability picture for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        AvailabilityResponse with slot-by-slot availability.
    """
    d = parse_date(date_str)
    day_of_week = get_day_of_week(date_str)
    working = is_working_day(d)
    holiday = is_holiday(date_str)
    holiday_name = get_holiday_name(date_str)

    if not working or holiday:
        logger.info(
            "Availability check for %s: not a working day (working=%s, holiday=%s).",
            date_str,
            working,
            holiday,
        )
        return AvailabilityResponse(
            date=date_str,
            day_of_week=day_of_week,
            is_working_day=working,
            is_holiday=holiday,
            holiday_name=holiday_name,
            available_slots=[],
        )

    # Fetch existing bookings for the date once
    try:
        existing_bookings = sheets_service.get_bookings_for_date(date_str)
        booked_times: Set[str] = {
            b.appointment_time
            for b in existing_bookings
            if b.status not in ("Cancelled",)
        }
    except Exception as exc:
        logger.error("Failed to fetch bookings for %s: %s", date_str, exc)
        booked_times = set()

    now = now_in_clinic_tz()
    all_slots = generate_slots(d)
    result_slots: List[AvailabilitySlot] = []

    tz = get_clinic_timezone()
    from datetime import datetime as _dt

    for slot_time_str in all_slots:
        # Mark past slots as unavailable
        try:
            slot_dt = parse_time(slot_time_str)
            slot_datetime = tz.localize(_dt.combine(d, slot_dt))
            is_past = slot_datetime < now
        except Exception:
            is_past = False

        available = not is_past and (slot_time_str not in booked_times)
        result_slots.append(AvailabilitySlot(time=slot_time_str, available=available))

    available_count = sum(1 for s in result_slots if s.available)
    logger.info(
        "Availability for %s: %d/%d slots available.",
        date_str,
        available_count,
        len(result_slots),
    )

    return AvailabilityResponse(
        date=date_str,
        day_of_week=day_of_week,
        is_working_day=working,
        is_holiday=holiday,
        holiday_name=holiday_name,
        available_slots=result_slots,
    )


def is_slot_available(date_str: str, time_str: str) -> Tuple[bool, str]:
    """
    Check whether a specific date+time slot is available.

    Returns:
        (available: bool, reason: str)
    """
    d = parse_date(date_str)

    if not is_working_day(d):
        return False, f"{get_day_of_week(date_str)} is not a working day."

    if is_holiday(date_str):
        holiday_name = get_holiday_name(date_str)
        return False, f"{date_str} is a public holiday ({holiday_name})."

    # Normalise time to HH:MM 24-hour before comparing against stored bookings
    try:
        normalised_time = parse_time(time_str).strftime("%H:%M")
    except ValueError:
        return False, f"Cannot parse time '{time_str}'. Please use HH:MM or H:MM AM/PM format."

    try:
        taken = sheets_service.is_slot_taken(date_str, normalised_time)
    except Exception as exc:
        logger.error("Slot conflict check failed: %s", exc)
        return False, "Unable to verify slot availability right now. Please try again."

    if taken:
        return False, f"The {time_str} slot on {date_str} is already booked. Please choose a different time."

    return True, "Slot is available."
