"""
Core booking orchestration service.
Coordinates validation → conflict detection → persistence → email confirmation.
This is the single entry point for all booking operations.
"""

from typing import Any, Dict, Optional, Tuple

from app.constants.clinic import BookingStatus
from app.models.booking import BookingRecord
from app.schemas.booking import BookingRequest, BookingResponse
from app.services import sheets_service, email_service
from app.services.availability_service import is_slot_available
from app.services.validation_service import validate_booking_request
from app.utils.date_utils import now_in_clinic_tz
from app.utils.id_generator import generate_booking_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_booking(request: BookingRequest) -> BookingResponse:
    """
    End-to-end booking flow:
      1. Validate all fields (format + business rules)
      2. Check slot availability (conflict detection)
      3. Generate unique booking ID
      4. Persist to Google Sheets
      5. Send confirmation email (non-blocking failure)

    Args:
        request: Validated BookingRequest schema.

    Returns:
        BookingResponse indicating success or the reason for failure.

    Raises:
        ValueError: If validation fails — callers should catch and surface to the user.
        RuntimeError: If persistence to Google Sheets fails after retries.
    """
    logger.info(
        "Processing booking request for '%s' — service='%s' date='%s' time='%s'.",
        request.full_name,
        request.service,
        request.preferred_date,
        request.preferred_time,
    )

    # ── Step 1: Deep validation ────────────────────────────────────────────────
    all_valid, errors, normalised = validate_booking_request(
        full_name=request.full_name,
        phone=request.phone,
        email=str(request.email),
        service=request.service,
        preferred_date=request.preferred_date,
        preferred_time=request.preferred_time,
    )

    if not all_valid:
        error_summary = "; ".join(f"{k}: {v}" for k, v in errors.items())
        logger.warning("Booking validation failed for '%s': %s", request.full_name, error_summary)
        raise ValueError(f"Validation failed — {error_summary}")

    # Use normalised values (cleaned phone, canonical service name)
    phone = normalised.get("phone", request.phone)
    service = normalised.get("service", request.service)

    # ── Step 2: Conflict detection ─────────────────────────────────────────────
    available, reason = is_slot_available(request.preferred_date, request.preferred_time)
    if not available:
        logger.warning(
            "Slot %s %s unavailable for '%s': %s",
            request.preferred_date,
            request.preferred_time,
            request.full_name,
            reason,
        )
        raise ValueError(reason)

    # ── Step 3: Generate booking ID ────────────────────────────────────────────
    try:
        daily_count = sheets_service.count_bookings_for_date(request.preferred_date)
    except Exception as exc:
        logger.warning("Could not fetch daily count (defaulting to 0): %s", exc)
        daily_count = 0

    booking_id = generate_booking_id(request.preferred_date, daily_count)

    # ── Step 4: Build record & persist ─────────────────────────────────────────
    record = BookingRecord(
        booking_id=booking_id,
        customer_name=request.full_name.strip(),
        phone=phone,
        email=str(request.email),
        service=service,
        appointment_date=request.preferred_date,
        appointment_time=request.preferred_time,
        reason=request.reason,
        status=BookingStatus.CONFIRMED.value,
        timestamp=now_in_clinic_tz().isoformat(),
    )

    sheets_service.append_booking(record)
    logger.info("Booking %s saved to Google Sheets.", booking_id)

    # ── Step 5: Send confirmation email (partial-success tolerant) ─────────────
    email_sent, email_message = email_service.send_confirmation_email(record)
    if not email_sent:
        logger.error("Email failed for booking %s: %s", booking_id, email_message)

    return BookingResponse(
        success=True,
        booking_id=booking_id,
        message=(
            f"Appointment confirmed! Your booking ID is {booking_id}. "
            f"A confirmation email has{'  been sent' if email_sent else ' NOT been sent'} "
            f"to {record.email}."
        ),
        customer_name=record.customer_name,
        service=service,
        appointment_date=request.preferred_date,
        appointment_time=request.preferred_time,
        email_sent=email_sent,
    )


def create_booking_from_dict(data: Dict[str, Any]) -> BookingResponse:
    """
    Convenience wrapper to create a booking from a raw dictionary.
    Used by the RetellAI webhook handler when parsing tool-call arguments.
    """
    request = BookingRequest(**data)
    return create_booking(request)


def resend_confirmation(booking_id: str, email: str) -> Tuple[bool, str]:
    """
    Re-send a confirmation email for an existing booking.

    Returns:
        (success: bool, message: str)
    """
    record = sheets_service.get_booking_by_id(booking_id)
    if not record:
        return False, f"Booking ID {booking_id} was not found."

    # Override email address if caller provided a different one
    if email and email != record.email:
        record.email = email

    success, msg = email_service.send_confirmation_email(record)
    return success, msg
