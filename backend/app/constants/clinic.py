"""
Clinic-specific constants: working hours, services, FAQs.
Centralising these here means a single place to update when clinic details change.
"""

from enum import Enum
from typing import Dict, List, Set

# ── Clinic Identity ────────────────────────────────────────────────────────────
CLINIC_NAME = "QuensultingAI Dental Clinic"
CLINIC_PHONE = "+91-98765-43210"
CLINIC_EMAIL = "appointments@quensultingai-dental.com"
CLINIC_ADDRESS = "123 Dental Street, Health District, Bengaluru – 560001, Karnataka, India"
CLINIC_MAPS_URL = "https://maps.google.com/?q=QuensultingAI+Dental+Clinic"

# ── Working Schedule ───────────────────────────────────────────────────────────
WORKING_DAYS: List[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
]

# Python weekday integers (Monday=0 … Saturday=5); Sunday=6 is excluded
WORKING_WEEKDAY_INTS: Set[int] = {0, 1, 2, 3, 4, 5}

WORKING_HOURS_START: int = 9   # 09:00
WORKING_HOURS_END: int = 18    # 18:00 (last slot starts at 17:30)

BOOKING_ID_PREFIX: str = "QDC"


# ── Dental Services ────────────────────────────────────────────────────────────
class DentalService(str, Enum):
    DENTAL_CLEANING = "Dental Cleaning"
    ROOT_CANAL = "Root Canal Treatment"
    TEETH_WHITENING = "Teeth Whitening"
    BRACES_CONSULTATION = "Braces Consultation"
    TOOTH_EXTRACTION = "Tooth Extraction"
    GENERAL_CONSULTATION = "General Dental Consultation"


DENTAL_SERVICES: List[str] = [s.value for s in DentalService]

# Human-friendly aliases the voice AI might hear
SERVICE_ALIASES: Dict[str, str] = {
    "cleaning": DentalService.DENTAL_CLEANING,
    "dental cleaning": DentalService.DENTAL_CLEANING,
    "root canal": DentalService.ROOT_CANAL,
    "root canal treatment": DentalService.ROOT_CANAL,
    "whitening": DentalService.TEETH_WHITENING,
    "teeth whitening": DentalService.TEETH_WHITENING,
    "braces": DentalService.BRACES_CONSULTATION,
    "braces consultation": DentalService.BRACES_CONSULTATION,
    "extraction": DentalService.TOOTH_EXTRACTION,
    "tooth extraction": DentalService.TOOTH_EXTRACTION,
    "remove tooth": DentalService.TOOTH_EXTRACTION,
    "consultation": DentalService.GENERAL_CONSULTATION,
    "general consultation": DentalService.GENERAL_CONSULTATION,
    "checkup": DentalService.GENERAL_CONSULTATION,
    "check up": DentalService.GENERAL_CONSULTATION,
}


# ── Google Sheets Column Layout ────────────────────────────────────────────────
SHEET_HEADERS: List[str] = [
    "Timestamp",
    "Booking ID",
    "Customer Name",
    "Phone",
    "Email",
    "Service",
    "Date",
    "Time",
    "Reason",
    "Status",
]


# ── Booking Statuses ───────────────────────────────────────────────────────────
class BookingStatus(str, Enum):
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    RESCHEDULED = "Rescheduled"
    NO_SHOW = "No Show"


# ── FAQs ───────────────────────────────────────────────────────────────────────
FAQS: Dict[str, str] = {
    "timings": (
        "We are open Monday to Saturday, 9:00 AM to 6:00 PM. "
        "We are closed on Sundays and public holidays."
    ),
    "fee": (
        "Our General Dental Consultation starts at ₹500. "
        "Dental Cleaning is ₹800–₹1,500. Root Canal Treatment ranges from ₹5,000–₹12,000 "
        "depending on the tooth. Teeth Whitening is ₹3,000–₹6,000. "
        "Braces Consultation is complimentary — treatment costs are discussed at the appointment. "
        "Tooth Extraction starts at ₹1,000."
    ),
    "walk_ins": (
        "Yes, we do accept walk-in patients, but we strongly recommend booking an appointment "
        "in advance to minimise your waiting time, as our schedule can fill up quickly."
    ),
    "emergency": (
        "If you are experiencing a dental emergency — such as severe toothache, a knocked-out "
        "tooth, or facial swelling — please call us immediately at +91-98765-43210. "
        "We do our best to accommodate emergency cases on the same day."
    ),
    "location": (
        "We are located at 123 Dental Street, Health District, Bengaluru – 560001. "
        "You can find us easily on Google Maps by searching QuensultingAI Dental Clinic."
    ),
    "payment": (
        "We accept cash, all major credit and debit cards, UPI payments such as GPay and PhonePe, "
        "net banking, and most major health insurance plans. "
        "Please inform us of your insurance provider when booking."
    ),
    "parking": (
        "Yes, we have free dedicated parking available for all patients "
        "in the basement of our building. Valet parking is also available on request."
    ),
    "cancellation": (
        "You can cancel your appointment at no charge up to 24 hours before the scheduled time. "
        "Late cancellations or no-shows may incur a nominal fee of ₹200."
    ),
    "rescheduling": (
        "Appointments can be rescheduled up to 2 hours before the scheduled time. "
        "Please call us or ask me to reschedule and I will be happy to help you find a new slot."
    ),
    "insurance": (
        "We work with most major health insurance providers including Star Health, HDFC ERGO, "
        "ICICI Lombard, and government schemes like CGHS and ECHS. "
        "Please bring your insurance card on your visit."
    ),
}

# ── Human Transfer ─────────────────────────────────────────────────────────────
HUMAN_TRANSFER_NUMBER: str = "+91-98765-43210"
HUMAN_TRANSFER_SIP: str = "sip:reception@quensultingai-dental.com"
