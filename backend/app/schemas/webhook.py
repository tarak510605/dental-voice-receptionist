"""
Pydantic schemas matching RetellAI webhook payloads.
See: https://docs.retellai.com/api-references/webhook
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


# ── Inbound RetellAI Webhook ───────────────────────────────────────────────────

class RetellCallObject(BaseModel):
    """Partial representation of the call object RetellAI embeds in webhooks."""

    call_id: str
    agent_id: Optional[str] = None
    call_status: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    call_analysis: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class RetellToolCallObject(BaseModel):
    """Tool-call details embedded in a 'tool_call' event."""

    tool_call_id: str
    name: str
    arguments: Dict[str, Any]


class RetellWebhookPayload(BaseModel):
    """Top-level payload sent by RetellAI to POST /retell/webhook."""

    event: str                                     # call_started | call_ended | tool_call | call_analyzed
    call: RetellCallObject
    tool_call: Optional[RetellToolCallObject] = None

    model_config = {"extra": "allow"}


# ── Outbound Tool-Call Response ────────────────────────────────────────────────

class ToolCallResponse(BaseModel):
    """Response Claude sends back to RetellAI for a tool_call event."""

    tool_call_id: str
    result: str                # plain-text result the LLM will read aloud / use


# ── Specific Tool Argument Schemas ─────────────────────────────────────────────
# These are validated internally when we handle individual tool calls.

class BookAppointmentArgs(BaseModel):
    full_name: str
    phone: str
    email: str
    service: str
    preferred_date: str
    preferred_time: str
    reason: Optional[str] = None


class CheckAvailabilityArgs(BaseModel):
    date: str
    time: Optional[str] = None


class GetFAQArgs(BaseModel):
    topic: str


class TransferToHumanArgs(BaseModel):
    reason: Optional[str] = None
