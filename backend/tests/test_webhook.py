"""
Tests for POST /retell/webhook endpoint.
"""

import pytest
from datetime import timedelta
from app.utils.date_utils import today_in_clinic_tz


def _next_working_day() -> str:
    d = today_in_clinic_tz() + timedelta(days=1)
    while d.weekday() not in {0, 1, 2, 3, 4, 5}:
        d += timedelta(days=1)
    return d.isoformat()


def _make_payload(event: str, tool_call: dict | None = None) -> dict:
    payload = {
        "event": event,
        "call": {
            "call_id": "test-call-abc123",
            "agent_id": "test-agent",
            "call_status": "ongoing",
            "from_number": "+919876543210",
            "to_number": "+918765432109",
        },
    }
    if tool_call:
        payload["tool_call"] = tool_call
    return payload


class TestWebhookCallEvents:
    def test_call_started_returns_200(self, client):
        response = client.post("/retell/webhook", json=_make_payload("call_started"))
        assert response.status_code == 200

    def test_call_ended_returns_200(self, client):
        response = client.post("/retell/webhook", json=_make_payload("call_ended"))
        assert response.status_code == 200

    def test_call_analyzed_returns_200(self, client):
        response = client.post("/retell/webhook", json=_make_payload("call_analyzed"))
        assert response.status_code == 200

    def test_unknown_event_returns_200(self, client):
        response = client.post("/retell/webhook", json=_make_payload("some_unknown_event"))
        assert response.status_code == 200

    def test_invalid_json_returns_400(self, client):
        response = client.post(
            "/retell/webhook",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)


class TestWebhookBookAppointment:
    def test_book_appointment_tool_call_returns_200(self, client, mock_sheets, mock_email):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-001",
                "name": "book_appointment",
                "arguments": {
                    "full_name": "Arjun Mehta",
                    "phone": "9876543210",
                    "email": "arjun@example.com",
                    "service": "Dental Cleaning",
                    "preferred_date": _next_working_day(),
                    "preferred_time": "11:00",
                    "reason": "First visit",
                },
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200

    def test_book_appointment_response_has_tool_call_id(self, client, mock_sheets, mock_email):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-002",
                "name": "book_appointment",
                "arguments": {
                    "full_name": "Sita Ram",
                    "phone": "9876543211",
                    "email": "sita@example.com",
                    "service": "Root Canal Treatment",
                    "preferred_date": _next_working_day(),
                    "preferred_time": "14:00",
                },
            },
        )
        response = client.post("/retell/webhook", json=payload)
        data = response.json()
        assert "tool_call_id" in data
        assert data["tool_call_id"] == "tc-002"

    def test_book_appointment_response_has_result(self, client, mock_sheets, mock_email):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-003",
                "name": "book_appointment",
                "arguments": {
                    "full_name": "Maya Patel",
                    "phone": "8765432109",
                    "email": "maya@example.com",
                    "service": "Teeth Whitening",
                    "preferred_date": _next_working_day(),
                    "preferred_time": "15:30",
                },
            },
        )
        response = client.post("/retell/webhook", json=payload)
        data = response.json()
        assert "result" in data
        assert isinstance(data["result"], str)
        assert len(data["result"]) > 0


class TestWebhookCheckAvailability:
    def test_check_availability_tool_call(self, client, mock_sheets):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-004",
                "name": "check_availability",
                "arguments": {"date": _next_working_day()},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_check_availability_sunday_response(self, client, mock_sheets):
        d = today_in_clinic_tz() + timedelta(days=1)
        while d.weekday() != 6:
            d += timedelta(days=1)
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-005",
                "name": "check_availability",
                "arguments": {"date": d.isoformat()},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        data = response.json()
        assert "Sunday" in data["result"] or "not open" in data["result"].lower() or "working day" in data["result"].lower()


class TestWebhookFAQ:
    def test_faq_timings(self, client):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-006",
                "name": "get_faq_answer",
                "arguments": {"topic": "timings"},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "Monday" in data["result"] or "9" in data["result"]

    def test_faq_unknown_topic_returns_fallback(self, client):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-007",
                "name": "get_faq_answer",
                "arguments": {"topic": "something completely unknown xyz"},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]) > 0


class TestWebhookTransferToHuman:
    def test_transfer_tool_call(self, client):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-008",
                "name": "transfer_to_human",
                "arguments": {"reason": "Patient requested human agent"},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "transferring" in data["result"].lower() or "team" in data["result"].lower()


class TestWebhookUnknownTool:
    def test_unknown_tool_returns_graceful_response(self, client):
        payload = _make_payload(
            "tool_call",
            tool_call={
                "tool_call_id": "tc-009",
                "name": "nonexistent_tool",
                "arguments": {},
            },
        )
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data


class TestWebhookMissingToolCall:
    def test_tool_call_event_without_tool_call_object_returns_422(self, client):
        payload = _make_payload("tool_call")   # No tool_call key
        response = client.post("/retell/webhook", json=payload)
        assert response.status_code == 422
