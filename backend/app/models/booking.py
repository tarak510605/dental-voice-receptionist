"""
Internal data model for a booking record.
This is a plain dataclass (no ORM) — Google Sheets is the persistence layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BookingRecord:
    """Represents a fully resolved booking stored in Google Sheets."""

    booking_id: str
    customer_name: str
    phone: str
    email: str
    service: str
    appointment_date: str        # ISO format: YYYY-MM-DD
    appointment_time: str        # 24-h format: HH:MM
    reason: Optional[str]
    status: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_sheet_row(self) -> List[str]:
        """Serialise to a list matching SHEET_HEADERS column order."""
        return [
            self.timestamp,
            self.booking_id,
            self.customer_name,
            self.phone,
            self.email,
            self.service,
            self.appointment_date,
            self.appointment_time,
            self.reason or "",
            self.status,
        ]

    @classmethod
    def from_sheet_row(cls, row: List[str]) -> "BookingRecord":
        """Deserialise from a Google Sheets row (must match SHEET_HEADERS order)."""
        return cls(
            timestamp=row[0] if len(row) > 0 else "",
            booking_id=row[1] if len(row) > 1 else "",
            customer_name=row[2] if len(row) > 2 else "",
            phone=row[3] if len(row) > 3 else "",
            email=row[4] if len(row) > 4 else "",
            service=row[5] if len(row) > 5 else "",
            appointment_date=row[6] if len(row) > 6 else "",
            appointment_time=row[7] if len(row) > 7 else "",
            reason=row[8] if len(row) > 8 else None,
            status=row[9] if len(row) > 9 else "",
        )
