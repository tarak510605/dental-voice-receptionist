"""
Tests for the availability service and GET /availability endpoint.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.utils.date_utils import today_in_clinic_tz


def _next_working_day() -> str:
    d = today_in_clinic_tz() + timedelta(days=1)
    while d.weekday() not in {0, 1, 2, 3, 4, 5}:
        d += timedelta(days=1)
    return d.isoformat()


def _next_sunday() -> str:
    d = today_in_clinic_tz() + timedelta(days=1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d.isoformat()


# ── Endpoint tests ─────────────────────────────────────────────────────────────

class TestAvailabilityEndpoint:
    def test_availability_returns_200_for_working_day(self, client, mock_sheets):
        response = client.get(f"/availability?date={_next_working_day()}")
        assert response.status_code == 200

    def test_availability_body_has_slots(self, client, mock_sheets):
        response = client.get(f"/availability?date={_next_working_day()}")
        data = response.json()
        assert "available_slots" in data
        assert isinstance(data["available_slots"], list)

    def test_availability_sunday_no_slots(self, client, mock_sheets):
        sunday = _next_sunday()
        response = client.get(f"/availability?date={sunday}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_working_day"] is False
        assert data["available_slots"] == []

    def test_availability_invalid_date_format(self, client):
        response = client.get("/availability?date=not-a-date")
        assert response.status_code in (400, 422)

    def test_availability_missing_date_param(self, client):
        response = client.get("/availability")
        assert response.status_code == 422

    def test_availability_slots_are_30_min_apart(self, client, mock_sheets):
        response = client.get(f"/availability?date={_next_working_day()}")
        data = response.json()
        slots = [s["time"] for s in data["available_slots"]]
        if len(slots) >= 2:
            from datetime import datetime
            t1 = datetime.strptime(slots[0], "%H:%M")
            t2 = datetime.strptime(slots[1], "%H:%M")
            diff_minutes = (t2 - t1).seconds // 60
            assert diff_minutes == 30

    def test_availability_first_slot_is_nine_am(self, client, mock_sheets):
        response = client.get(f"/availability?date={_next_working_day()}")
        data = response.json()
        slots = data["available_slots"]
        assert len(slots) > 0
        assert slots[0]["time"] == "09:00"

    def test_availability_last_slot_is_1730(self, client, mock_sheets):
        response = client.get(f"/availability?date={_next_working_day()}")
        data = response.json()
        slots = data["available_slots"]
        assert slots[-1]["time"] == "17:30"

    def test_booked_slot_marked_unavailable(self, client, mock_sheets):
        from app.models.booking import BookingRecord
        from app.constants.clinic import BookingStatus

        working_day = _next_working_day()
        booked = BookingRecord(
            booking_id="QDC-TEST-001",
            customer_name="Test Patient",
            phone="9876543210",
            email="test@test.com",
            service="Dental Cleaning",
            appointment_date=working_day,
            appointment_time="10:00",
            reason=None,
            status=BookingStatus.CONFIRMED.value,
        )
        mock_sheets["get_bookings_for_date"].return_value = [booked]

        response = client.get(f"/availability?date={working_day}")
        data = response.json()
        slot_map = {s["time"]: s["available"] for s in data["available_slots"]}
        assert slot_map.get("10:00") is False


# ── Service-level tests ────────────────────────────────────────────────────────

class TestIsSlotAvailable:
    def test_available_slot(self, mock_sheets):
        mock_sheets["is_slot_taken"].return_value = False
        from app.services.availability_service import is_slot_available
        available, reason = is_slot_available(_next_working_day(), "10:00")
        assert available is True

    def test_taken_slot(self, mock_sheets):
        mock_sheets["is_slot_taken"].return_value = True
        from app.services.availability_service import is_slot_available
        available, reason = is_slot_available(_next_working_day(), "10:00")
        assert available is False
        assert "already booked" in reason.lower() or "booked" in reason.lower()

    def test_sunday_not_available(self, mock_sheets):
        from app.services.availability_service import is_slot_available
        available, reason = is_slot_available(_next_sunday(), "10:00")
        assert available is False
