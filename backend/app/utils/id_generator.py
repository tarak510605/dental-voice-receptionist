"""
Booking ID generator.
Format: QDC-YYYYMMDD-NNN   (e.g. QDC-20260702-001)
The sequence is derived from the current count of bookings for that date
as read from Google Sheets, so no local state is required.
"""

from datetime import datetime
from app.constants.clinic import BOOKING_ID_PREFIX


def generate_booking_id(date_str: str, daily_count: int) -> str:
    """
    Generate a unique booking ID.

    Args:
        date_str:    Appointment date in YYYY-MM-DD format.
        daily_count: Number of existing bookings already stored for this date.
                     The new booking will be daily_count + 1.

    Returns:
        Booking ID string, e.g. 'QDC-20260702-001'.
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_part = date_obj.strftime("%Y%m%d")
    except ValueError:
        # Fallback: use today's date if parsing fails
        date_part = datetime.utcnow().strftime("%Y%m%d")

    sequence = str(daily_count + 1).zfill(3)
    return f"{BOOKING_ID_PREFIX}-{date_part}-{sequence}"


def parse_booking_id_date(booking_id: str) -> str:
    """
    Extract the date portion from a booking ID.

    Args:
        booking_id: e.g. 'QDC-20260702-001'

    Returns:
        Date string in YYYY-MM-DD format, e.g. '2026-07-02'.
    """
    parts = booking_id.split("-")
    if len(parts) < 3:
        raise ValueError(f"Invalid booking ID format: {booking_id}")
    raw_date = parts[1]
    return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
