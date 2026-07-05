"""
RetellAI webhook router.
POST /retell/webhook — receives all RetellAI events:
  - call_started      → log inbound call
  - call_ended        → log call summary
  - call_analyzed     → log post-call analysis
  - tool_call         → dispatch to appropriate business-logic handler

Tool names the AI can invoke:
  - book_appointment       → full booking flow
  - check_availability     → slot availability for a date
  - get_faq_answer         → answer a clinic FAQ
  - transfer_to_human      → escalate call to a human agent
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status

from app.constants.clinic import FAQS, HUMAN_TRANSFER_NUMBER
from app.schemas.booking import BookingRequest
from app.schemas.webhook import (
    BookAppointmentArgs,
    CheckAvailabilityArgs,
    GetFAQArgs,
    RetellWebhookPayload,
    ToolCallResponse,
    TransferToHumanArgs,
)
from app.services import booking_service
from app.services.availability_service import get_availability, is_slot_available
from app.utils.date_utils import format_date_human, format_time_human
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["RetellAI Webhook"])


# ── Tool handlers ──────────────────────────────────────────────────────────────

def _handle_book_appointment(arguments: Dict[str, Any]) -> str:
    """
    Handle the 'book_appointment' tool call from RetellAI.
    Returns a plain-text result string the LLM will read aloud.
    """
    try:
        args = BookAppointmentArgs(**arguments)
    except Exception as exc:
        logger.warning("book_appointment: invalid arguments: %s", exc)
        return f"I'm sorry, I couldn't capture all the details needed. {exc}"

    try:
        request = BookingRequest(
            full_name=args.full_name,
            phone=args.phone,
            email=args.email,
            service=args.service,
            preferred_date=args.preferred_date,
            preferred_time=args.preferred_time,
            reason=args.reason,
        )
    except Exception as exc:
        logger.warning("book_appointment: Pydantic validation failed: %s", exc)
        # Extract human-friendly message from pydantic error
        return f"There was an issue with the information provided: {exc}"

    try:
        response = booking_service.create_booking(request)
        human_date = format_date_human(args.preferred_date)
        human_time = format_time_human(args.preferred_time)
        result = (
            f"Great news! Your appointment has been confirmed. "
            f"Your booking ID is {response.booking_id}. "
            f"You are booked for {args.service} on {human_date} at {human_time}. "
        )
        result += f"A confirmation email has been sent to {args.email}."
        return result

    except ValueError as exc:
        logger.warning("book_appointment: business rule violation: %s", exc)
        return str(exc)

    except RuntimeError as exc:
        logger.error("book_appointment: persistence failure: %s", exc)
        return (
            "I'm sorry, I was unable to save your appointment due to a technical issue. "
            "Please call us directly at our clinic number and we will book it for you."
        )


def _handle_check_availability(arguments: Dict[str, Any]) -> str:
    """Handle the 'check_availability' tool call."""
    try:
        args = CheckAvailabilityArgs(**arguments)
    except Exception as exc:
        return f"I couldn't understand the date or time requested: {exc}"

    # If a specific time was requested, check that slot
    if args.time:
        available, reason = is_slot_available(args.date, args.time)
        human_date = format_date_human(args.date)
        human_time = format_time_human(args.time)
        if available:
            return (
                f"Yes, {human_time} on {human_date} is available. "
                "Would you like me to book that slot for you?"
            )
        # Slot is taken — fetch remaining available slots for the day
        try:
            avail = get_availability(args.date)
            open_slots = [s.time for s in avail.available_slots if s.available]
        except Exception:
            open_slots = []

        if not open_slots:
            return (
                f"I'm sorry, {human_time} on {human_date} is already booked, "
                "and unfortunately there are no other slots available that day. "
                "Would you like to try a different date?"
            )

        readable_slots = [format_time_human(t) for t in open_slots[:5]]
        slots_text = ", ".join(readable_slots[:-1]) + (
            f" and {readable_slots[-1]}" if len(readable_slots) > 1 else readable_slots[0]
        )
        return (
            f"I'm sorry, {human_time} on {human_date} is already booked. "
            f"However, we still have {len(open_slots)} available slot{'s' if len(open_slots) > 1 else ''} that day: "
            f"{slots_text}. Which of these works for you?"
        )

    # Return a summary of the day's availability
    try:
        avail = get_availability(args.date)
    except Exception as exc:
        logger.error("check_availability error: %s", exc)
        return "I'm sorry, I couldn't check availability right now. Please try again."

    human_date = format_date_human(args.date)

    if not avail.is_working_day:
        return f"I'm afraid we are not open on {avail.day_of_week}s. We operate Monday to Saturday."

    if avail.is_holiday:
        return (
            f"{human_date} is a public holiday ({avail.holiday_name}). "
            "We are closed on that day. May I suggest an alternative date?"
        )

    open_slots = [s.time for s in avail.available_slots if s.available]
    if not open_slots:
        return f"Unfortunately we have no available slots on {human_date}. Shall I check another date?"

    # Read out up to 5 slots naturally
    readable_slots = [format_time_human(t) for t in open_slots[:5]]
    slots_text = ", ".join(readable_slots[:-1]) + (
        f", and {readable_slots[-1]}" if len(readable_slots) > 1 else readable_slots[0]
    )
    return (
        f"On {human_date} we have {len(open_slots)} available slots. "
        f"Some options are: {slots_text}. "
        "Which time works best for you?"
    )


def _handle_get_faq(arguments: Dict[str, Any]) -> str:
    """Handle the 'get_faq_answer' tool call."""
    try:
        args = GetFAQArgs(**arguments)
    except Exception as exc:
        return f"I couldn't understand the topic requested: {exc}"

    topic_lower = args.topic.lower()

    # Find the best matching FAQ key
    for key, answer in FAQS.items():
        if key in topic_lower or topic_lower in key:
            return answer

    # Partial keyword matching
    keyword_map = {
        "time": "timings", "hour": "timings", "open": "timings", "close": "timings",
        "fee": "fee", "cost": "fee", "price": "fee", "charge": "fee", "rate": "fee",
        "walk": "walk_ins", "walkin": "walk_ins", "without appointment": "walk_ins",
        "emergency": "emergency", "urgent": "emergency", "pain": "emergency",
        "location": "location", "address": "location", "where": "location", "direction": "location",
        "pay": "payment", "payment": "payment", "card": "payment", "cash": "payment", "upi": "payment",
        "park": "parking",
        "cancel": "cancellation",
        "reschedule": "rescheduling", "change appointment": "rescheduling",
        "insurance": "insurance",
    }

    for keyword, faq_key in keyword_map.items():
        if keyword in topic_lower:
            return FAQS.get(faq_key, "")

    return (
        "That's a great question! For detailed information, I recommend calling our clinic "
        "directly at our reception number, or I can help you book an appointment with our team "
        "who will be happy to answer all your questions in person."
    )


def _handle_transfer_to_human(arguments: Dict[str, Any]) -> str:
    """Handle the 'transfer_to_human' tool call."""
    try:
        args = TransferToHumanArgs(**arguments)
    except Exception:
        args = TransferToHumanArgs()

    reason = args.reason or "the caller's request"
    logger.info("Human transfer requested. Reason: %s", reason)
    return (
        f"Of course! I am transferring you to one of our team members right away. "
        f"Please hold for just a moment."
    )


# ── Event dispatcher ───────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "book_appointment": _handle_book_appointment,
    "check_availability": _handle_check_availability,
    "get_faq_answer": _handle_get_faq,
    "transfer_to_human": _handle_transfer_to_human,
}


@router.post(
    "/retell/webhook",
    summary="RetellAI Webhook",
    description=(
        "Receives all RetellAI webhook events. "
        "Handles tool calls from the conversational flow and returns results "
        "in the format RetellAI expects."
    ),
    status_code=status.HTTP_200_OK,
)
async def retell_webhook(request: Request) -> Dict[str, Any]:
    # Parse raw body first for logging
    try:
        body = await request.json()
    except Exception:
        logger.error("RetellAI webhook: could not parse JSON body.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    logger.info("RetellAI webhook event: %s", body.get("event", "unknown"))

    try:
        payload = RetellWebhookPayload(**body)
    except Exception as exc:
        logger.error("RetellAI webhook: payload validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Payload structure error: {exc}",
        )

    event = payload.event

    # ── call_started ───────────────────────────────────────────────────────────
    if event == "call_started":
        logger.info(
            "Call started — call_id=%s from=%s",
            payload.call.call_id,
            payload.call.from_number or "unknown",
        )
        return {"status": "received"}

    # ── call_ended ─────────────────────────────────────────────────────────────
    if event == "call_ended":
        logger.info(
            "Call ended — call_id=%s duration=%s status=%s",
            payload.call.call_id,
            payload.call.end_timestamp,
            payload.call.call_status,
        )
        return {"status": "received"}

    # ── call_analyzed ──────────────────────────────────────────────────────────
    if event == "call_analyzed":
        logger.info(
            "Call analysed — call_id=%s analysis=%s",
            payload.call.call_id,
            json.dumps(payload.call.call_analysis or {}, indent=2),
        )
        return {"status": "received"}

    # ── tool_call ──────────────────────────────────────────────────────────────
    if event == "tool_call":
        if not payload.tool_call:
            logger.error("tool_call event missing 'tool_call' object.")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tool_call event must include a tool_call object.",
            )

        tool_name = payload.tool_call.name
        tool_call_id = payload.tool_call.tool_call_id
        arguments = payload.tool_call.arguments

        logger.info(
            "Tool call — call_id=%s tool=%s args=%s",
            payload.call.call_id,
            tool_name,
            json.dumps(arguments),
        )

        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            logger.warning("Unknown tool called: '%s'", tool_name)
            result = (
                f"I'm sorry, I don't have that capability right now. "
                "Would you like me to connect you with a team member who can help?"
            )
        else:
            result = handler(arguments)

        logger.info("Tool '%s' result: %s", tool_name, result[:120])

        return ToolCallResponse(
            tool_call_id=tool_call_id,
            result=result,
        ).model_dump()

    # ── Unknown event ──────────────────────────────────────────────────────────
    logger.warning("Unknown RetellAI event type: '%s'", event)
    return {"status": "ignored", "event": event}


# ── Direct tool endpoints (RetellAI Conductor Function nodes) ──────────────────
# Conductor sends parameters directly as JSON body, not wrapped in event format.

@router.post(
    "/retell/tool/{tool_name}",
    summary="RetellAI Conductor Direct Tool Call",
    status_code=status.HTTP_200_OK,
)
async def retell_tool_direct(tool_name: str, request: Request) -> Dict[str, Any]:
    """
    Handles direct function calls from RetellAI Conductor flow nodes.
    Conductor sends: { "call": {...}, "param1": "val1", ... }
    We strip the "call" wrapper and normalise field names before dispatching.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    # RetellAI Conductor wraps args as {"name": "...", "args": {...}}
    # Fall back to flat body for other formats
    if "args" in body and isinstance(body["args"], dict):
        arguments = body["args"]
    else:
        arguments = {k: v for k, v in body.items() if k not in ("call", "name")}

    # Normalise field name differences between Conductor and our schemas
    if tool_name == "book_appointment":
        if "date" in arguments and "preferred_date" not in arguments:
            arguments["preferred_date"] = arguments.pop("date")
        if "time" in arguments and "preferred_time" not in arguments:
            arguments["preferred_time"] = arguments.pop("time")

    logger.info("Conductor tool call — tool=%s args=%s", tool_name, json.dumps(arguments))

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        logger.warning("Unknown tool called: '%s'", tool_name)
        return {"result": "I'm sorry, I don't have that capability right now."}

    result = handler(arguments)
    logger.info("Tool '%s' result: %s", tool_name, result[:120])
    return {"result": result}
