"""
Booking router.
Exposes:
  POST /book               – create a new appointment
  GET  /availability       – check available slots for a date
  POST /send-confirmation  – re-send a confirmation email
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.booking import (
    AvailabilityResponse,
    BookingRequest,
    BookingResponse,
    ConfirmationRequest,
    ConfirmationResponse,
    ErrorResponse,
)
from app.services import booking_service, availability_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Booking"])


@router.post(
    "/book",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation or business-rule failure"},
        409: {"model": ErrorResponse, "description": "Slot already booked (conflict)"},
        503: {"model": ErrorResponse, "description": "Upstream dependency failure"},
    },
    summary="Book an Appointment",
    description=(
        "Creates a new dental appointment. "
        "Validates inputs, checks slot availability, persists to Google Sheets, "
        "and sends a confirmation email."
    ),
)
async def book_appointment(request: BookingRequest) -> BookingResponse:
    logger.info("POST /book — patient='%s'", request.full_name)
    try:
        response = booking_service.create_booking(request)
        return response

    except ValueError as exc:
        # Validation or conflict errors are 400/409
        error_msg = str(exc)
        if "already booked" in error_msg.lower() or "unavailable" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    except RuntimeError as exc:
        # Downstream dependency failures (Google Sheets retries exhausted)
        logger.error("Booking service runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save appointment right now. Please try again in a moment.",
        )


@router.get(
    "/availability",
    response_model=AvailabilityResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date format"},
    },
    summary="Check Appointment Availability",
    description=(
        "Returns a list of all 30-minute appointment slots for the requested date "
        "with their availability status."
    ),
)
async def get_availability(
    date: str = Query(
        ...,
        description="Date in YYYY-MM-DD format",
        example="2026-07-15",
    )
) -> AvailabilityResponse:
    logger.info("GET /availability — date='%s'", date)
    try:
        return availability_service.get_availability(date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/send-confirmation",
    response_model=ConfirmationResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Booking ID not found"},
        502: {"model": ErrorResponse, "description": "Email delivery failed"},
    },
    summary="Re-send Confirmation Email",
    description="Manually trigger a confirmation email for an existing booking.",
)
async def send_confirmation(request: ConfirmationRequest) -> ConfirmationResponse:
    logger.info(
        "POST /send-confirmation — booking_id='%s' email='%s'",
        request.booking_id,
        request.email,
    )
    success, message = booking_service.resend_confirmation(
        booking_id=request.booking_id,
        email=str(request.email),
    )

    if not success:
        if "not found" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        )

    return ConfirmationResponse(
        success=True,
        message=message,
        booking_id=request.booking_id,
    )
