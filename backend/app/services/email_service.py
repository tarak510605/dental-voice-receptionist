"""
Gmail SMTP email service.
Sends professional HTML confirmation emails after a successful booking.
Email failures are logged and surfaced as partial-success — they do NOT
roll back a booking that has already been saved to Google Sheets.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Tuple

from app.config.settings import get_settings
from app.constants.clinic import (
    CLINIC_NAME,
    CLINIC_ADDRESS,
    CLINIC_PHONE,
    CLINIC_EMAIL,
    CLINIC_MAPS_URL,
)
from app.models.booking import BookingRecord
from app.utils.date_utils import format_date_human, format_time_human
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def _build_confirmation_html(record: BookingRecord) -> str:
    """Render the HTML body of the confirmation email."""
    human_date = format_date_human(record.appointment_date)
    human_time = format_time_human(record.appointment_time)
    sent_at = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Appointment Confirmation – {CLINIC_NAME}</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; background: #f4f6f8; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
    .header {{ background: #1a73e8; padding: 32px 40px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; letter-spacing: 0.5px; }}
    .header p {{ color: #d0e4ff; margin: 6px 0 0; font-size: 14px; }}
    .body {{ padding: 36px 40px; }}
    .greeting {{ font-size: 18px; color: #202124; margin-bottom: 6px; }}
    .sub {{ font-size: 14px; color: #5f6368; margin-bottom: 28px; }}
    .card {{ background: #f8faff; border: 1px solid #d2e3fc; border-radius: 8px;
             padding: 24px 28px; margin-bottom: 28px; }}
    .card h2 {{ margin: 0 0 16px; font-size: 15px; color: #1a73e8; text-transform: uppercase;
                letter-spacing: 0.8px; }}
    .row {{ display: flex; justify-content: space-between; padding: 8px 0;
            border-bottom: 1px solid #e8eaed; font-size: 14px; }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: #5f6368; font-weight: 600; }}
    .value {{ color: #202124; text-align: right; }}
    .booking-id {{ font-size: 22px; font-weight: 700; color: #1a73e8; text-align: center;
                   background: #e8f0fe; border-radius: 6px; padding: 14px; margin-bottom: 28px;
                   letter-spacing: 1px; }}
    .cta {{ background: #1a73e8; color: #ffffff; text-align: center; padding: 14px 28px;
            border-radius: 6px; font-size: 15px; font-weight: 600; text-decoration: none;
            display: inline-block; margin: 8px 0; }}
    .note {{ background: #fef9e7; border-left: 4px solid #f9ab00; padding: 14px 18px;
             border-radius: 4px; font-size: 13px; color: #5f4b08; margin-bottom: 24px; }}
    .footer {{ background: #f8faff; padding: 20px 40px; text-align: center; font-size: 12px;
               color: #80868b; border-top: 1px solid #e8eaed; }}
    .footer a {{ color: #1a73e8; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>&#x1F4C5; Appointment Confirmed</h1>
      <p>{CLINIC_NAME}</p>
    </div>
    <div class="body">
      <p class="greeting">Dear {record.customer_name},</p>
      <p class="sub">
        Your dental appointment has been successfully booked. Please find the details below.
      </p>

      <div class="booking-id">Booking ID: {record.booking_id}</div>

      <div class="card">
        <h2>&#x1F4CB; Appointment Details</h2>
        <div class="row">
          <span class="label">Service</span>
          <span class="value">{record.service}</span>
        </div>
        <div class="row">
          <span class="label">Date</span>
          <span class="value">{human_date}</span>
        </div>
        <div class="row">
          <span class="label">Time</span>
          <span class="value">{human_time}</span>
        </div>
        <div class="row">
          <span class="label">Patient Name</span>
          <span class="value">{record.customer_name}</span>
        </div>
        <div class="row">
          <span class="label">Phone</span>
          <span class="value">+91-{record.phone}</span>
        </div>
        {"<div class='row'><span class='label'>Reason</span><span class='value'>" + record.reason + "</span></div>" if record.reason else ""}
      </div>

      <div class="card">
        <h2>&#x1F3E5; Clinic Details</h2>
        <div class="row">
          <span class="label">Clinic</span>
          <span class="value">{CLINIC_NAME}</span>
        </div>
        <div class="row">
          <span class="label">Address</span>
          <span class="value">{CLINIC_ADDRESS}</span>
        </div>
        <div class="row">
          <span class="label">Phone</span>
          <span class="value">{CLINIC_PHONE}</span>
        </div>
        <div class="row">
          <span class="label">Email</span>
          <span class="value">{CLINIC_EMAIL}</span>
        </div>
      </div>

      <div class="note">
        &#x26A0;&#xFE0F; <strong>Cancellation Policy:</strong>
        Please cancel at least 24 hours in advance to avoid a ₹200 late-cancellation fee.
        To cancel or reschedule, call us at {CLINIC_PHONE}.
      </div>

      <div style="text-align:center; margin-bottom: 20px;">
        <a class="cta" href="{CLINIC_MAPS_URL}" target="_blank">&#x1F4CD; Get Directions</a>
      </div>

      <p style="font-size:14px; color:#5f6368;">
        Thank you for choosing <strong>{CLINIC_NAME}</strong>.
        We look forward to seeing you and ensuring your smile is at its best!
      </p>
    </div>
    <div class="footer">
      <p>This is an automated confirmation. Please do not reply to this email.</p>
      <p>
        {CLINIC_NAME} &bull; {CLINIC_ADDRESS}<br/>
        <a href="tel:{CLINIC_PHONE}">{CLINIC_PHONE}</a> &bull;
        <a href="mailto:{CLINIC_EMAIL}">{CLINIC_EMAIL}</a>
      </p>
      <p style="color:#bdc1c6;">Sent on {sent_at}</p>
    </div>
  </div>
</body>
</html>"""


def _build_plain_text(record: BookingRecord) -> str:
    """Plain-text fallback for email clients that don't render HTML."""
    human_date = format_date_human(record.appointment_date)
    human_time = format_time_human(record.appointment_time)
    return f"""Dear {record.customer_name},

Your appointment at {CLINIC_NAME} has been confirmed.

BOOKING ID : {record.booking_id}
Service    : {record.service}
Date       : {human_date}
Time       : {human_time}
Phone      : +91-{record.phone}

CLINIC DETAILS
--------------
{CLINIC_NAME}
{CLINIC_ADDRESS}
Phone : {CLINIC_PHONE}
Email : {CLINIC_EMAIL}

CANCELLATION POLICY
Please cancel at least 24 hours in advance to avoid a ₹200 fee.
Call us at {CLINIC_PHONE} to cancel or reschedule.

Thank you for choosing {CLINIC_NAME}. We look forward to seeing you!
"""


def send_confirmation_email(record: BookingRecord) -> Tuple[bool, str]:
    """
    Send a confirmation email to the patient.

    Returns:
        (success: bool, message: str)
        On failure the booking record is NOT rolled back — callers handle partial success.
    """
    if not settings.GMAIL_SENDER_EMAIL or not settings.GMAIL_APP_PASSWORD:
        msg = "Gmail credentials are not configured — skipping email."
        logger.warning(msg)
        return False, msg

    recipient = record.email
    subject = f"Appointment Confirmed – {CLINIC_NAME} | {record.booking_id}"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.GMAIL_SENDER_NAME} <{settings.GMAIL_SENDER_EMAIL}>"
    message["To"] = recipient

    plain_part = MIMEText(_build_plain_text(record), "plain", "utf-8")
    html_part = MIMEText(_build_confirmation_html(record), "html", "utf-8")
    message.attach(plain_part)
    message.attach(html_part)

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.GMAIL_SENDER_EMAIL, settings.GMAIL_APP_PASSWORD)
            server.sendmail(
                settings.GMAIL_SENDER_EMAIL,
                recipient,
                message.as_string(),
            )
        logger.info(
            "Confirmation email sent to %s for booking %s.", recipient, record.booking_id
        )
        return True, f"Confirmation email sent to {recipient}."

    except smtplib.SMTPAuthenticationError:
        msg = "Gmail authentication failed. Check GMAIL_APP_PASSWORD in .env."
        logger.error(msg)
        return False, msg

    except smtplib.SMTPRecipientsRefused:
        msg = f"Email address {recipient} was rejected by the SMTP server."
        logger.error(msg)
        return False, msg

    except Exception as exc:
        msg = f"Failed to send confirmation email: {exc}"
        logger.error(msg)
        return False, msg
