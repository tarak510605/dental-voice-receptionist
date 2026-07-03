"""
Pydantic schemas for the booking API layer.
Used for request validation, response serialisation, and OpenAPI documentation.
"""

import re
from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request Schemas ────────────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    """Payload for POST /book."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Patient's full name",
        examples=["Priya Sharma"],
    )
    phone: str = Field(
        ...,
        description="10-digit Indian mobile number (with or without +91/0 prefix)",
        examples=["9876543210"],
    )
    email: EmailStr = Field(
        ...,
        description="Patient's email address for confirmation",
        examples=["priya.sharma@example.com"],
    )
    service: str = Field(
        ...,
        description="Dental service requested",
        examples=["Dental Cleaning"],
    )
    preferred_date: str = Field(
        ...,
        description="Appointment date in YYYY-MM-DD format",
        examples=["2026-07-15"],
    )
    preferred_time: str = Field(
        ...,
        description="Appointment time in HH:MM (24-hour) format",
        examples=["10:30"],
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for visit",
        examples=["Routine check-up"],
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip common prefix variants
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:]
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        elif cleaned.startswith("0"):
            cleaned = cleaned[1:]

        if not re.fullmatch(r"[6-9]\d{9}", cleaned):
            raise ValueError(
                "Phone number must be a valid 10-digit Indian mobile number starting with 6–9."
            )
        return cleaned

    @field_validator("preferred_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return v

    @field_validator("preferred_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        try:
            time.fromisoformat(v)
        except ValueError:
            raise ValueError("Time must be in HH:MM format.")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not re.match(r"^[A-Za-z\s\.\'\-]+$", stripped):
            raise ValueError("Name must contain only letters, spaces, dots, apostrophes, or hyphens.")
        return stripped


class ConfirmationRequest(BaseModel):
    """Payload for POST /send-confirmation (manual re-send)."""

    booking_id: str = Field(..., description="Booking ID to re-send confirmation for", examples=["QDC-20260702-001"])
    email: EmailStr = Field(..., description="Recipient email address")


# ── Response Schemas ───────────────────────────────────────────────────────────

class BookingResponse(BaseModel):
    """Response returned after a successful booking."""

    success: bool
    booking_id: str
    message: str
    customer_name: str
    service: str
    appointment_date: str
    appointment_time: str
    email_sent: bool


class AvailabilitySlot(BaseModel):
    """A single available time slot."""

    time: str        # HH:MM
    available: bool


class AvailabilityResponse(BaseModel):
    """Response for GET /availability."""

    date: str
    day_of_week: str
    is_working_day: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    available_slots: List[AvailabilitySlot]


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str
    version: str
    service: str


class ErrorResponse(BaseModel):
    """Standard error response body."""

    success: bool = False
    error: str
    detail: Optional[str] = None


class ConfirmationResponse(BaseModel):
    """Response for POST /send-confirmation."""

    success: bool
    message: str
    booking_id: str
