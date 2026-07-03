"""
Tests for POST /book and POST /send-confirmation endpoints.
"""

import pytest
from datetime import timedelta
from app.utils.date_utils import today_in_clinic_tz


def _next_working_day() -> str:
    d = today_in_clinic_tz() + timedelta(days=1)
    while d.weekday() not in {0, 1, 2, 3, 4, 5}:
        d += timedelta(days=1)
    return d.isoformat()


# ── POST /book ─────────────────────────────────────────────────────────────────

class TestBookEndpoint:
    def test_successful_booking_returns_201(self, client, mock_sheets, mock_email, valid_booking_payload):
        valid_booking_payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=valid_booking_payload)
        assert response.status_code == 201

    def test_successful_booking_body_structure(self, client, mock_sheets, mock_email, valid_booking_payload):
        valid_booking_payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=valid_booking_payload)
        data = response.json()
        assert data["success"] is True
        assert data["booking_id"].startswith("QDC-")
        assert "customer_name" in data
        assert "service" in data
        assert "appointment_date" in data
        assert "appointment_time" in data

    def test_booking_id_format(self, client, mock_sheets, mock_email, valid_booking_payload):
        valid_booking_payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=valid_booking_payload)
        data = response.json()
        parts = data["booking_id"].split("-")
        assert len(parts) == 3
        assert parts[0] == "QDC"
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 3   # 001

    def test_booking_calls_sheets_append(self, client, mock_sheets, mock_email, valid_booking_payload):
        valid_booking_payload["preferred_date"] = _next_working_day()
        client.post("/book", json=valid_booking_payload)
        mock_sheets["append_booking"].assert_called_once()

    def test_booking_calls_email(self, client, mock_sheets, mock_email, valid_booking_payload):
        valid_booking_payload["preferred_date"] = _next_working_day()
        client.post("/book", json=valid_booking_payload)
        mock_email.assert_called_once()

    def test_missing_required_field_returns_422(self, client, valid_booking_payload):
        payload = dict(valid_booking_payload)
        del payload["email"]
        response = client.post("/book", json=payload)
        assert response.status_code == 422

    def test_invalid_email_returns_422(self, client, valid_booking_payload):
        payload = dict(valid_booking_payload)
        payload["email"] = "not-an-email"
        response = client.post("/book", json=payload)
        assert response.status_code == 422

    def test_invalid_phone_returns_400(self, client, mock_sheets, mock_email, valid_booking_payload):
        payload = dict(valid_booking_payload)
        payload["phone"] = "12345"
        payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=payload)
        assert response.status_code in (400, 422)

    def test_sunday_booking_rejected(self, client, mock_sheets, mock_email, valid_booking_payload):
        d = today_in_clinic_tz() + timedelta(days=1)
        while d.weekday() != 6:
            d += timedelta(days=1)
        payload = dict(valid_booking_payload)
        payload["preferred_date"] = d.isoformat()
        response = client.post("/book", json=payload)
        assert response.status_code == 400

    def test_past_date_rejected(self, client, mock_sheets, mock_email, valid_booking_payload):
        payload = dict(valid_booking_payload)
        payload["preferred_date"] = "2020-01-01"
        response = client.post("/book", json=payload)
        assert response.status_code == 400

    def test_outside_working_hours_rejected(self, client, mock_sheets, mock_email, valid_booking_payload):
        payload = dict(valid_booking_payload)
        payload["preferred_date"] = _next_working_day()
        payload["preferred_time"] = "07:00"
        response = client.post("/book", json=payload)
        assert response.status_code == 400

    def test_slot_conflict_returns_409(self, client, mock_sheets, mock_email, valid_booking_payload):
        mock_sheets["is_slot_taken"].return_value = True
        payload = dict(valid_booking_payload)
        payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=payload)
        assert response.status_code == 409
        # Restore for subsequent tests
        mock_sheets["is_slot_taken"].return_value = False

    def test_invalid_service_returns_400(self, client, mock_sheets, mock_email, valid_booking_payload):
        payload = dict(valid_booking_payload)
        payload["service"] = "Laser Eye Surgery"
        payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=payload)
        assert response.status_code == 400

    def test_email_failure_still_returns_201(self, client, mock_sheets, valid_booking_payload):
        """Booking should succeed even if email fails (partial success)."""
        from unittest.mock import MagicMock
        import app.services.email_service as es
        original = es.send_confirmation_email
        es.send_confirmation_email = MagicMock(return_value=(False, "SMTP error"))

        valid_booking_payload["preferred_date"] = _next_working_day()
        response = client.post("/book", json=valid_booking_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["email_sent"] is False

        es.send_confirmation_email = original


# ── POST /send-confirmation ────────────────────────────────────────────────────

class TestSendConfirmationEndpoint:
    def test_not_found_booking_returns_404(self, client, mock_sheets):
        mock_sheets["get_booking_by_id"].return_value = None
        response = client.post(
            "/send-confirmation",
            json={"booking_id": "QDC-99999999-999", "email": "test@example.com"},
        )
        assert response.status_code == 404

    def test_existing_booking_sends_email(self, client, mock_sheets, mock_email):
        from app.models.booking import BookingRecord
        from app.constants.clinic import BookingStatus

        record = BookingRecord(
            booking_id="QDC-20260801-001",
            customer_name="Test Patient",
            phone="9876543210",
            email="test@example.com",
            service="Dental Cleaning",
            appointment_date="2026-08-01",
            appointment_time="10:00",
            reason=None,
            status=BookingStatus.CONFIRMED.value,
        )
        mock_sheets["get_booking_by_id"].return_value = record

        response = client.post(
            "/send-confirmation",
            json={"booking_id": "QDC-20260801-001", "email": "test@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
