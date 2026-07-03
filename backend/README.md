# QuensultingAI Dental Clinic – AI Voice Receptionist

> A production-ready Voice AI receptionist built with **RetellAI** + **FastAPI** that handles inbound calls, books appointments, answers FAQs, and sends confirmation emails.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Folder Structure](#folder-structure)
4. [Installation](#installation)
5. [Google Sheets Setup](#google-sheets-setup)
6. [Gmail SMTP Setup](#gmail-smtp-setup)
7. [RetellAI Setup](#retellai-setup)
8. [Environment Variables](#environment-variables)
9. [Running the Server](#running-the-server)
10. [API Reference](#api-reference)
11. [Swagger Docs](#swagger-docs)
12. [Running Tests](#running-tests)
13. [Deployment (Render / Railway)](#deployment)
14. [Troubleshooting](#troubleshooting)
15. [Future Improvements](#future-improvements)

---

## Project Overview

This project implements an AI receptionist for **QuensultingAI Dental Clinic** that:

- Handles inbound voice calls via **RetellAI**
- Books dental appointments with full validation (working hours, holidays, conflict detection)
- Stores all bookings in **Google Sheets**
- Sends professional HTML **confirmation emails** via Gmail SMTP
- Answers clinic FAQs naturally during the conversation
- Transfers to a human agent when needed
- Handles interruptions, corrections, and confused callers gracefully

**Clinic details:**
- Working days: Monday – Saturday
- Working hours: 9:00 AM – 6:00 PM (IST)
- Services: Dental Cleaning, Root Canal Treatment, Teeth Whitening, Braces Consultation, Tooth Extraction, General Dental Consultation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Inbound Phone Call                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                           RetellAI                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Conversational Flow (retell_flow.json)                  │   │
│  │  States: Greeting → Collect Info → Confirm → Goodbye     │   │
│  │  Tools:  book_appointment, check_availability,           │   │
│  │          get_faq_answer, transfer_to_human               │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │  HTTPS Webhook (POST /retell/webhook)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │  /health   │  │  /book       │  │  /retell/webhook      │    │
│  │  /avail.   │  │  /send-conf  │  │  (tool dispatcher)    │    │
│  └────────────┘  └──────────────┘  └──────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Business Logic Services                               │     │
│  │  validation_service  │  availability_service           │     │
│  │  booking_service     │  sheets_service                 │     │
│  │  email_service                                         │     │
│  └────────────────────────────────────────────────────────┘     │
└──────────┬───────────────────────────┬──────────────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────┐        ┌───────────────────────┐
│  Google Sheets   │        │  Gmail SMTP            │
│  (Appointments   │        │  (Confirmation Email)  │
│   spreadsheet)   │        │                        │
└──────────────────┘        └───────────────────────┘
```

---

## Folder Structure

```
backend/
│
├── app/
│   ├── config/
│   │   └── settings.py          # Pydantic settings from .env
│   │
│   ├── constants/
│   │   └── clinic.py            # Services, working hours, FAQs, enums
│   │
│   ├── middleware/
│   │   └── logging_middleware.py # Request/response timing logger
│   │
│   ├── models/
│   │   └── booking.py           # BookingRecord dataclass
│   │
│   ├── routers/
│   │   ├── booking.py           # POST /book, GET /availability, POST /send-confirmation
│   │   ├── health.py            # GET /health
│   │   └── webhook.py           # POST /retell/webhook
│   │
│   ├── schemas/
│   │   ├── booking.py           # Request/response Pydantic schemas
│   │   └── webhook.py           # RetellAI webhook payload schemas
│   │
│   ├── services/
│   │   ├── availability_service.py  # Slot availability logic
│   │   ├── booking_service.py       # Orchestrates full booking flow
│   │   ├── email_service.py         # Gmail SMTP confirmation emails
│   │   ├── sheets_service.py        # Google Sheets read/write
│   │   └── validation_service.py    # All input validation rules
│   │
│   ├── utils/
│   │   ├── date_utils.py        # Timezone-aware date/time helpers
│   │   ├── id_generator.py      # Booking ID generator (QDC-YYYYMMDD-NNN)
│   │   └── logger.py            # Centralised logging configuration
│   │
│   └── main.py                  # FastAPI app factory + entry point
│
├── tests/
│   ├── conftest.py              # Fixtures, mocks, TestClient setup
│   ├── test_health.py
│   ├── test_booking.py
│   ├── test_validation.py
│   ├── test_availability.py
│   └── test_webhook.py
│
├── logs/                        # Auto-created at runtime (gitignored)
│
├── retell_flow.json             # Complete RetellAI conversational flow
├── holidays.json                # Public holiday configuration
├── requirements.txt
├── .env.example                 # Template for environment variables
├── .gitignore
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11 or higher
- A Google Cloud project with Google Sheets API enabled
- A Gmail account with 2FA and an App Password
- A RetellAI account

### 1. Clone the repository

```bash
git clone https://github.com/your-username/quensultingai-dental-receptionist.git
cd quensultingai-dental-receptionist/backend
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate on macOS / Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in all required values
```

---

## Google Sheets Setup

### Step 1 – Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g. `quensultingai-dental`)
3. Enable the **Google Sheets API** and **Google Drive API**

### Step 2 – Create a Service Account

1. Go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
3. Name it `dental-receptionist` and click **Create and Continue**
4. Grant the role **Editor** → click **Done**

### Step 3 – Download credentials.json

1. Click on the service account you just created
2. Go to the **Keys** tab → **Add Key → Create new key → JSON**
3. Download the file and rename it to `credentials.json`
4. Place `credentials.json` in the `backend/` directory
5. **Never commit this file to git** (it is gitignored)

### Step 4 – Create the Google Sheet

1. Create a new Google Spreadsheet at [sheets.google.com](https://sheets.google.com)
2. Name the first sheet tab `Appointments`
3. Share the spreadsheet with the service account email (found in `credentials.json` under `client_email`) with **Editor** access
4. Copy the Spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
5. Set `GOOGLE_SHEETS_SPREADSHEET_ID=SPREADSHEET_ID` in your `.env`

The backend will automatically create the header row on first run.

---

## Gmail SMTP Setup

1. Enable **2-Step Verification** on your Gmail account
2. Go to [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an App Password for **Mail** → **Other (custom name)** → `DentalReceptionist`
4. Copy the 16-character password into `GMAIL_APP_PASSWORD` in `.env`
5. Set `GMAIL_SENDER_EMAIL` to your Gmail address

---

## RetellAI Setup

### Step 1 – Create a RetellAI account

Sign up at [app.retellai.com](https://app.retellai.com)

### Step 2 – Import the conversational flow

1. In the RetellAI dashboard, go to **LLMs → Create New LLM**
2. Select **Retell LLM** type
3. Click **Import** and upload `retell_flow.json`
4. Replace `{{WEBHOOK_URL}}` in the JSON with your public backend URL
   (e.g. `https://your-app.onrender.com`)

### Step 3 – Create an Agent

1. Go to **Agents → Create Agent**
2. Select the LLM you just created
3. Choose a voice (recommended: `en-US-Neural2-F` or any natural-sounding voice)
4. Set the agent's language to **English (India)** for best results with Indian phone numbers
5. Copy the **Agent ID** into `RETELL_AGENT_ID` in `.env`

### Step 4 – Configure the webhook

In the agent settings, set the webhook URL to:
```
https://your-backend.com/retell/webhook
```

### Step 5 – Get your API key

Go to **Dashboard → API Keys** and copy your key into `RETELL_API_KEY` in `.env`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Yes | Path to `credentials.json` |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Yes | Google Sheets document ID |
| `GOOGLE_SHEETS_WORKSHEET_NAME` | No | Sheet tab name (default: `Appointments`) |
| `GMAIL_SENDER_EMAIL` | Yes | Gmail address for sending confirmations |
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password (16 chars) |
| `GMAIL_SENDER_NAME` | No | Display name in emails |
| `RETELL_API_KEY` | Yes | RetellAI API key |
| `RETELL_WEBHOOK_SECRET` | No | Webhook signature secret |
| `RETELL_AGENT_ID` | No | RetellAI agent ID |
| `TIMEZONE` | No | IANA timezone (default: `Asia/Kolkata`) |
| `SLOT_DURATION_MINUTES` | No | Appointment slot length (default: `30`) |
| `SHEETS_MAX_RETRIES` | No | Retry attempts for Sheets API (default: `3`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |
| `DEBUG` | No | Enable debug mode (default: `false`) |
| `PORT` | No | Server port (default: `8000`) |

---

## Running the Server

```bash
# Development (with auto-reload)
DEBUG=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Or simply:

```bash
python app/main.py
```

---

## API Reference

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "service": "QuensultingAI Dental Clinic AI Receptionist"
}
```

---

### `POST /book`

Create a new appointment.

**Request body:**
```json
{
  "full_name": "Priya Sharma",
  "phone": "9876543210",
  "email": "priya@example.com",
  "service": "Dental Cleaning",
  "preferred_date": "2026-08-15",
  "preferred_time": "10:00",
  "reason": "Routine check-up"
}
```

**Success response (201):**
```json
{
  "success": true,
  "booking_id": "QDC-20260815-001",
  "message": "Appointment confirmed! ...",
  "customer_name": "Priya Sharma",
  "service": "Dental Cleaning",
  "appointment_date": "2026-08-15",
  "appointment_time": "10:00",
  "email_sent": true
}
```

**Error codes:** `400` (validation), `409` (conflict), `503` (Sheets unavailable)

---

### `GET /availability?date=YYYY-MM-DD`

Check available slots for a date.

**Response:**
```json
{
  "date": "2026-08-15",
  "day_of_week": "Saturday",
  "is_working_day": true,
  "is_holiday": false,
  "holiday_name": null,
  "available_slots": [
    {"time": "09:00", "available": true},
    {"time": "09:30", "available": false},
    ...
  ]
}
```

---

### `POST /send-confirmation`

Re-send a confirmation email for an existing booking.

**Request body:**
```json
{
  "booking_id": "QDC-20260815-001",
  "email": "priya@example.com"
}
```

---

### `POST /retell/webhook`

Receives RetellAI webhook events. Not called directly by clients.

**Supported events:** `call_started`, `call_ended`, `call_analyzed`, `tool_call`

**Supported tools:** `book_appointment`, `check_availability`, `get_faq_answer`, `transfer_to_human`

---

## Swagger Docs

With the server running, open:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_booking.py -v

# Run with coverage report
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

All tests mock external dependencies (Google Sheets and Gmail) and run fully offline.

---

## Deployment

### Deploy to Render

1. Push your code to GitHub (ensure `.env` and `credentials.json` are gitignored)

2. Go to [render.com](https://render.com) → **New Web Service**

3. Connect your GitHub repository

4. Configure the service:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

5. Add all environment variables from `.env` in the Render dashboard under **Environment**

6. For `credentials.json`, go to **Environment → Secret Files** and upload the file with path `credentials.json`

7. Deploy and copy the public URL (e.g. `https://your-app.onrender.com`)

8. Update `{{WEBHOOK_URL}}` in `retell_flow.json` to your Render URL and re-import to RetellAI

### Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub**

2. Connect your repository

3. Railway auto-detects Python. Set the start command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

4. Add all environment variables in the Railway dashboard under **Variables**

5. For `credentials.json`, add its entire JSON content as the env variable `GOOGLE_CREDENTIALS_JSON` and update `settings.py` to write it to a file on startup (or use the Railway volume feature)

6. Deploy and use the generated Railway URL in RetellAI webhook settings

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Ensure venv is activated and `pip install -r requirements.txt` was run |
| `google.auth.exceptions.DefaultCredentialsError` | Check `credentials.json` path matches `GOOGLE_SHEETS_CREDENTIALS_FILE` in `.env` |
| `gspread.exceptions.SpreadsheetNotFound` | Verify `GOOGLE_SHEETS_SPREADSHEET_ID` and that the service account email has Editor access to the sheet |
| `smtplib.SMTPAuthenticationError` | Ensure you're using a Gmail App Password (not your main password) and 2FA is enabled |
| `422 Unprocessable Entity` on `/book` | Check request body matches the schema — especially date format (`YYYY-MM-DD`) and time format (`HH:MM`) |
| RetellAI webhook not reaching the backend | Ensure the server is publicly accessible. Use [ngrok](https://ngrok.com) for local testing: `ngrok http 8000` |
| Logs not appearing | Check `LOG_DIR` path is writable. The `logs/` directory is created automatically |

---

## Future Improvements

- **Cancellation & rescheduling via voice** — add `cancel_booking` and `reschedule_booking` tool calls to the RetellAI flow
- **SMS reminders** — send appointment reminders 24 hours before via Twilio or MSG91
- **WhatsApp integration** — allow booking confirmations and reminders via WhatsApp Business API
- **Multi-clinic support** — parameterise clinic configuration to support multiple branches
- **Analytics dashboard** — build a simple dashboard showing bookings by service, time, and day
- **Payment link in email** — include a Razorpay / Stripe payment link for advance consultation fees
- **Callback queue** — if all slots are full, offer to add the caller to a waiting list
- **Voice authentication** — verify returning patients by phone number before showing their booking history
- **PostgreSQL backend** — migrate from Google Sheets to a proper relational database for scale
