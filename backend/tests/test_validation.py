"""
Tests for the validation service.
All tests are pure-Python (no HTTP calls, no mocking required).
"""

import pytest
from datetime import date, timedelta

from app.services.validation_service import (
    validate_email,
    validate_phone,
    validate_service,
    validate_appointment_date,
    validate_appointment_time,
    validate_booking_request,
)
from app.utils.date_utils import today_in_clinic_tz


# ── Email ─────────────────────────────────────────────────────────────────────

class TestEmailValidation:
    def test_valid_email(self):
        valid, _ = validate_email("user@example.com")
        assert valid is True

    def test_valid_email_with_subdomain(self):
        valid, _ = validate_email("user@mail.example.co.in")
        assert valid is True

    def test_invalid_email_missing_at(self):
        valid, msg = validate_email("userexample.com")
        assert valid is False
        assert msg

    def test_invalid_email_missing_domain(self):
        valid, msg = validate_email("user@")
        assert valid is False

    def test_invalid_email_spaces(self):
        valid, msg = validate_email("user @example.com")
        assert valid is False


# ── Phone ─────────────────────────────────────────────────────────────────────

class TestPhoneValidation:
    def test_valid_10_digit_phone(self):
        valid, result = validate_phone("9876543210")
        assert valid is True
        assert result == "9876543210"

    def test_valid_phone_with_plus91(self):
        valid, result = validate_phone("+919876543210")
        assert valid is True
        assert result == "9876543210"

    def test_valid_phone_with_91_prefix(self):
        valid, result = validate_phone("919876543210")
        assert valid is True
        assert result == "9876543210"

    def test_valid_phone_starting_with_6(self):
        valid, result = validate_phone("6543210987")
        assert valid is True

    def test_invalid_phone_starts_with_5(self):
        valid, msg = validate_phone("5123456789")
        assert valid is False

    def test_invalid_phone_too_short(self):
        valid, msg = validate_phone("98765")
        assert valid is False

    def test_invalid_phone_letters(self):
        valid, msg = validate_phone("98765ABCDE")
        assert valid is False

    def test_phone_with_dashes_normalised(self):
        valid, result = validate_phone("98765-43210")
        assert valid is True
        assert result == "9876543210"


# ── Service ────────────────────────────────────────────────────────────────────

class TestServiceValidation:
    def test_valid_service_exact(self):
        valid, name = validate_service("Dental Cleaning")
        assert valid is True
        assert name == "Dental Cleaning"

    def test_valid_service_case_insensitive(self):
        valid, name = validate_service("dental cleaning")
        assert valid is True
        assert name == "Dental Cleaning"

    def test_valid_service_alias(self):
        valid, name = validate_service("root canal")
        assert valid is True
        assert name == "Root Canal Treatment"

    def test_valid_service_alias_braces(self):
        valid, name = validate_service("braces")
        assert valid is True
        assert name == "Braces Consultation"

    def test_invalid_service(self):
        valid, msg = validate_service("Laser Eye Surgery")
        assert valid is False
        assert "not a recognised service" in msg.lower() or "recognised" in msg.lower()

    def test_all_canonical_services_pass(self):
        from app.constants.clinic import DENTAL_SERVICES
        for svc in DENTAL_SERVICES:
            valid, result = validate_service(svc)
            assert valid is True, f"Service '{svc}' should be valid"
            assert result == svc


# ── Appointment Date ───────────────────────────────────────────────────────────

class TestAppointmentDateValidation:
    def _future_working_day(self) -> str:
        """Find the next Monday–Saturday from today."""
        d = today_in_clinic_tz() + timedelta(days=1)
        while d.weekday() not in {0, 1, 2, 3, 4, 5}:
            d += timedelta(days=1)
        return d.isoformat()

    def test_valid_future_working_day(self):
        d = self._future_working_day()
        valid, msg = validate_appointment_date(d)
        assert valid is True, f"Expected valid but got: {msg}"

    def test_past_date_rejected(self):
        past = (today_in_clinic_tz() - timedelta(days=1)).isoformat()
        valid, msg = validate_appointment_date(past)
        assert valid is False
        assert "past" in msg.lower()

    def test_sunday_rejected(self):
        # Find next Sunday
        d = today_in_clinic_tz() + timedelta(days=1)
        while d.weekday() != 6:
            d += timedelta(days=1)
        valid, msg = validate_appointment_date(d.isoformat())
        assert valid is False
        assert "working day" in msg.lower() or "sunday" in msg.lower() or "monday" in msg.lower()

    def test_invalid_format_rejected(self):
        valid, msg = validate_appointment_date("15-07-2026")
        assert valid is False
        assert "format" in msg.lower() or "YYYY-MM-DD" in msg


# ── Appointment Time ───────────────────────────────────────────────────────────

class TestAppointmentTimeValidation:
    def test_valid_time_within_hours(self):
        valid, msg = validate_appointment_time("10:00")
        assert valid is True

    def test_valid_time_first_slot(self):
        valid, msg = validate_appointment_time("09:00")
        assert valid is True

    def test_valid_time_last_slot(self):
        valid, msg = validate_appointment_time("17:30")
        assert valid is True

    def test_invalid_time_too_early(self):
        valid, msg = validate_appointment_time("07:00")
        assert valid is False

    def test_invalid_time_too_late(self):
        valid, msg = validate_appointment_time("18:00")
        assert valid is False

    def test_invalid_time_format(self):
        valid, msg = validate_appointment_time("10:00 AM")
        assert valid is False

    def test_invalid_time_midnight(self):
        valid, msg = validate_appointment_time("00:00")
        assert valid is False


# ── Full Booking Request Validation ───────────────────────────────────────────

class TestFullBookingValidation:
    def _future_working_day(self) -> str:
        d = today_in_clinic_tz() + timedelta(days=1)
        while d.weekday() not in {0, 1, 2, 3, 4, 5}:
            d += timedelta(days=1)
        return d.isoformat()

    def test_valid_request_passes(self):
        valid, errors, normalised = validate_booking_request(
            full_name="Priya Sharma",
            phone="9876543210",
            email="priya@example.com",
            service="Dental Cleaning",
            preferred_date=self._future_working_day(),
            preferred_time="10:00",
        )
        assert valid is True
        assert errors == {}

    def test_multiple_errors_collected(self):
        valid, errors, _ = validate_booking_request(
            full_name="P",
            phone="123",
            email="bad-email",
            service="Laser Surgery",
            preferred_date="2020-01-01",
            preferred_time="07:00",
        )
        assert valid is False
        assert len(errors) >= 3

    def test_phone_normalised_in_result(self):
        valid, errors, normalised = validate_booking_request(
            full_name="Ravi Kumar",
            phone="+919876543210",
            email="ravi@example.com",
            service="General Dental Consultation",
            preferred_date=self._future_working_day(),
            preferred_time="11:00",
        )
        assert valid is True
        assert normalised["phone"] == "9876543210"
