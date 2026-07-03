# Loom Walkthrough Script
## QuensultingAI Dental Clinic – AI Voice Receptionist
### 5-Minute Demo Script

---

> **Recording tips:**
> - Speak at a relaxed pace. 5 minutes ≈ 700–750 words.
> - Screen-share your code editor and terminal side by side.
> - Use the Loom cursor highlight to draw attention to key lines.

---

## [0:00 – 0:30] Introduction

**Say:**

"Hi everyone — I'm [your name], and in this walkthrough I'm going to show you the AI Voice Receptionist I built for QuensultingAI Dental Clinic as part of my internship assignment.

The core idea is simple: replace a manual human receptionist with a voice AI that can handle inbound phone calls — booking appointments, answering FAQs, and sending confirmation emails — all automatically, 24 hours a day.

Let's dive in."

---

## [0:30 – 1:00] Problem Statement

**Say:**

"Dental clinics get dozens of calls every day — most of them asking the same three things: 'Can I book an appointment?', 'What are your hours?', and 'Where are you located?'

A human receptionist handling these calls is expensive, error-prone, and unavailable after 6 PM. An AI receptionist can handle all of this instantly, at zero marginal cost per call, and free up the human staff for complex cases.

This project builds exactly that — a production-grade system, not a demo prototype."

---

## [1:00 – 1:45] Architecture

**Show:** The ASCII architecture diagram in README.md.

**Say:**

"Here's the architecture. It has four layers:

First, **RetellAI** — this handles the voice call. It converts speech to text, runs it through the conversational flow, and converts the AI's response back to natural speech.

Second, the **FastAPI backend** — this is the brain. RetellAI sends tool-call webhooks here whenever it needs to check availability or book an appointment.

Third, **Google Sheets** — this is the persistence layer. Every booking is stored as a row in a shared spreadsheet that the clinic staff can monitor in real time.

Fourth, **Gmail SMTP** — after a successful booking, the patient receives a beautiful HTML confirmation email with all the details."

---

## [1:45 – 2:30] RetellAI Conversational Flow

**Show:** `retell_flow.json` in the editor. Scroll through the states.

**Say:**

"This is the conversational flow JSON that powers the AI's brain. It defines a finite state machine with 14 states.

The AI starts at the **greeting** state. Based on what the caller says, it routes to one of four paths: booking, FAQ, emergency, or human transfer.

The booking path walks through 7 data-collection states — name, phone, email, service, date, time, and an optional reason. At each step, the AI confirms what it heard before moving on.

The key design principle here is that the AI never submits the booking until it reads back every detail and the caller explicitly confirms. If the caller says 'wait, that's the wrong date' — the AI goes back, collects the new date, and re-reads the full summary.

There are also 4 custom tools the AI can call during the conversation."

---

## [2:30 – 3:15] FastAPI Backend

**Show:** `app/routers/webhook.py` — the tool dispatcher.

**Say:**

"The webhook router is the entry point for all RetellAI events. It receives a POST request with the event type and dispatches it to the right handler.

For a `book_appointment` tool call, for example — it extracts the arguments, validates every field, checks for slot conflicts, generates a unique booking ID in the format QDC-YYYYMMDD-NNN, saves to Google Sheets, sends the email, and returns a plain-text result that RetellAI reads aloud to the caller.

Let me show you the validation service."

**Show:** `app/services/validation_service.py` — the `validate_booking_request` function.

**Say:**

"Every field is validated: phone numbers must be valid 10-digit Indian mobiles, dates must be future weekdays, times must fall within 9 AM to 5:30 PM, and services must match our canonical list. If any field fails, we collect all errors and surface them together — no round-trips for individual failures."

---

## [3:15 – 3:45] Google Sheets & Email

**Show:** `app/services/sheets_service.py` — the `append_booking` and `is_slot_taken` functions.

**Say:**

"The Sheets service handles everything: appending new bookings, checking for conflicts, counting existing bookings for the day to generate sequential IDs, and updating statuses. It has built-in retry logic with exponential back-off — if the Google API returns a transient error, it retries up to 3 times before giving up.

Conflict detection is here — `is_slot_taken` checks if any confirmed booking already exists for the same date and time."

**Show:** `app/services/email_service.py` — briefly show the HTML template.

**Say:**

"The email service generates a full HTML email — professionally styled with the clinic's branding, all booking details, a directions link, and the cancellation policy. If email sending fails, the booking is NOT rolled back — it's logged and the API returns a partial-success flag so the caller still gets a booking ID."

---

## [3:45 – 4:15] Advanced Features Demo

**Show:** Terminal — run the server. Then switch to Swagger UI at `/docs`.

**Say:**

"Let me quickly demo the API. The server is running. Here's the Swagger UI at `/docs` — every endpoint is fully documented with example requests.

Let me hit `GET /availability` for next Monday."

**Action:** Call GET /availability with a valid future date.

**Say:**

"You can see all 18 slots from 9 AM to 5:30 PM. Now let me book one."

**Action:** Call POST /book with valid payload.

**Say:**

"201 Created — booking ID QDC-20260708-001. And if I try to book the same slot again..."

**Action:** Call POST /book with same date and time.

**Say:**

"409 Conflict. The slot is protected. No double-bookings."

---

## [4:15 – 4:45] Testing

**Show:** Terminal — run `pytest tests/ -v`.

**Say:**

"The project has a comprehensive test suite with 40-plus test cases covering all endpoints, all validation rules, conflict detection, and all RetellAI webhook scenarios.

All external dependencies — Google Sheets and Gmail — are mocked, so the tests run completely offline in milliseconds. This is important for CI/CD pipelines.

Every test passes."

---

## [4:45 – 5:00] Conclusion

**Say:**

"To summarise — this project delivers a complete, production-ready AI voice receptionist:
- A 14-state RetellAI conversational flow that handles bookings, FAQs, emergencies, and escalations
- A FastAPI backend with 5 endpoints, full validation, and retry logic
- Google Sheets as a real-time booking database
- Professional HTML confirmation emails
- Conflict detection, holiday blocking, and timezone awareness
- 40-plus test cases, structured logging, and a clean modular architecture

Everything is documented in the README and ready to deploy to Render or Railway in under 10 minutes.

Thank you for watching — I'm happy to answer any questions!"

---

**[End recording]**

---

> **Post-recording checklist:**
> - [ ] Trim any pauses longer than 2 seconds
> - [ ] Add captions / subtitles
> - [ ] Set thumbnail to the architecture diagram
> - [ ] Title: "QuensultingAI Dental Clinic – AI Voice Receptionist | RetellAI + FastAPI"
