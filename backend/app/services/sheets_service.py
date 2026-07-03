"""
Google Sheets integration service.
Handles all read/write operations against the appointments spreadsheet.
Implements retry logic with exponential back-off for transient API failures.
"""

import json
import os
import time as time_module
from typing import List, Optional

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from google.oauth2.service_account import Credentials

from app.config.settings import get_settings
from app.constants.clinic import SHEET_HEADERS, BookingStatus
from app.models.booking import BookingRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Google API scopes required
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _build_client() -> gspread.Client:
    """Authenticate and return a gspread client.
    Tries GOOGLE_CREDENTIALS_JSON env var first (for Vercel/serverless),
    falls back to credentials file path.
    """
    raw_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if raw_json:
        info = json.loads(raw_json)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=_SCOPES,
        )
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    """Return the target worksheet, creating the header row if it is new."""
    client = _build_client()
    spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEETS_WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=settings.GOOGLE_SHEETS_WORKSHEET_NAME,
            rows=1000,
            cols=len(SHEET_HEADERS),
        )
        logger.info("Created new worksheet '%s'.", settings.GOOGLE_SHEETS_WORKSHEET_NAME)

    # Ensure header row exists
    existing = worksheet.row_values(1)
    if not existing or existing != SHEET_HEADERS:
        worksheet.insert_row(SHEET_HEADERS, 1)
        logger.info("Inserted header row into worksheet.")

    return worksheet


def _with_retry(fn, *args, **kwargs):
    """
    Execute *fn* with exponential back-off retry on APIError.
    Raises on final failure after settings.SHEETS_MAX_RETRIES attempts.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(1, settings.SHEETS_MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except APIError as exc:
            last_exc = exc
            wait = settings.SHEETS_RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Google Sheets API error (attempt %d/%d): %s — retrying in %.1fs",
                attempt,
                settings.SHEETS_MAX_RETRIES,
                exc,
                wait,
            )
            time_module.sleep(wait)
        except Exception as exc:
            logger.error("Unexpected Sheets error: %s", exc)
            raise
    raise RuntimeError(
        f"Google Sheets operation failed after {settings.SHEETS_MAX_RETRIES} attempts."
    ) from last_exc


def append_booking(record: BookingRecord) -> bool:
    """
    Append a booking record as a new row in the worksheet.

    Returns:
        True on success, raises on failure (after retries).
    """
    def _do_append():
        ws = _get_worksheet()
        ws.append_row(record.to_sheet_row(), value_input_option="USER_ENTERED")
        logger.info("Appended booking %s to Google Sheets.", record.booking_id)
        return True

    return _with_retry(_do_append)


def get_all_bookings() -> List[BookingRecord]:
    """Fetch all booking rows from the worksheet (excluding the header)."""
    def _do_fetch():
        ws = _get_worksheet()
        rows = ws.get_all_values()
        # rows[0] is the header; skip it
        return [BookingRecord.from_sheet_row(row) for row in rows[1:] if any(row)]

    return _with_retry(_do_fetch)


def get_bookings_for_date(date_str: str) -> List[BookingRecord]:
    """Return all bookings whose appointment_date matches *date_str* (YYYY-MM-DD)."""
    all_bookings = get_all_bookings()
    return [b for b in all_bookings if b.appointment_date == date_str]


def get_booking_by_id(booking_id: str) -> Optional[BookingRecord]:
    """Look up a single booking by its booking ID."""
    all_bookings = get_all_bookings()
    for record in all_bookings:
        if record.booking_id == booking_id:
            return record
    return None


def count_bookings_for_date(date_str: str) -> int:
    """Return the number of bookings already stored for a given date."""
    return len(get_bookings_for_date(date_str))


def is_slot_taken(date_str: str, time_str: str) -> bool:
    """
    Return True if the given date+time slot already has a confirmed booking.
    Cancelled bookings free the slot.
    """
    bookings = get_bookings_for_date(date_str)
    for b in bookings:
        if (
            b.appointment_time == time_str
            and b.status != BookingStatus.CANCELLED.value
        ):
            logger.info(
                "Slot %s %s is already taken (booking %s).",
                date_str,
                time_str,
                b.booking_id,
            )
            return True
    return False


def update_booking_status(booking_id: str, new_status: str) -> bool:
    """
    Update the status column of an existing booking row.

    Returns:
        True if the row was found and updated, False if booking_id was not found.
    """
    def _do_update():
        ws = _get_worksheet()
        rows = ws.get_all_values()
        # Find the row index (1-based, including header at row 1)
        for idx, row in enumerate(rows[1:], start=2):
            if row[1] == booking_id:  # column index 1 = Booking ID
                status_col = SHEET_HEADERS.index("Status") + 1
                ws.update_cell(idx, status_col, new_status)
                logger.info("Updated booking %s status to '%s'.", booking_id, new_status)
                return True
        logger.warning("Booking ID %s not found in sheet.", booking_id)
        return False

    return _with_retry(_do_update)
