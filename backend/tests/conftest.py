"""
pytest configuration and shared fixtures.
All external dependencies (Google Sheets, Gmail) are mocked so tests run offline.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Set minimal environment variables before importing the app ────────────────
os.environ.setdefault("GOOGLE_SHEETS_SPREADSHEET_ID", "test-sheet-id")
os.environ.setdefault("GMAIL_SENDER_EMAIL", "test@example.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "test-password")
os.environ.setdefault("RETELL_API_KEY", "test-retell-key")


@pytest.fixture(scope="session")
def app():
    """Create the FastAPI app once per test session."""
    from app.main import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_sheets(monkeypatch):
    """
    Patch all Google Sheets calls so tests never hit the real API.
    Returns a dict of mocked functions for assertions.
    """
    mocks = {
        "append_booking": MagicMock(return_value=True),
        "get_all_bookings": MagicMock(return_value=[]),
        "get_bookings_for_date": MagicMock(return_value=[]),
        "count_bookings_for_date": MagicMock(return_value=0),
        "is_slot_taken": MagicMock(return_value=False),
        "get_booking_by_id": MagicMock(return_value=None),
        "update_booking_status": MagicMock(return_value=True),
    }
    import app.services.sheets_service as ss
    for name, mock in mocks.items():
        monkeypatch.setattr(ss, name, mock)
    return mocks


@pytest.fixture
def mock_email(monkeypatch):
    """Patch email sending so tests never open SMTP connections."""
    mock = MagicMock(return_value=(True, "Email sent (mocked)."))
    import app.services.email_service as es
    monkeypatch.setattr(es, "send_confirmation_email", mock)
    return mock


@pytest.fixture
def valid_booking_payload():
    """A fully valid booking request body."""
    return {
        "full_name": "Priya Sharma",
        "phone": "9876543210",
        "email": "priya.sharma@example.com",
        "service": "Dental Cleaning",
        "preferred_date": "2026-08-01",   # Saturday – a working day
        "preferred_time": "10:00",
        "reason": "Routine check-up",
    }
