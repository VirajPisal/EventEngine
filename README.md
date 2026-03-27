# EventEngine — Autonomous Event Lifecycle Management System

EventEngine is an **AI-powered autonomous event management system** that handles the full lifecycle of an event — from creation to post-event analytics — with minimal human intervention. The system uses an autonomous agent loop, a finite state machine, adaptive reminder intelligence, and real email/QR/OTP-based attendance verification.

---

## Table of Contents
- [What This Project Does](#what-this-project-does)
- [Architecture Overview](#architecture-overview)
- [Event Lifecycle (State Machine)](#event-lifecycle-state-machine)
- [Manual vs Autonomous Actions](#manual-vs-autonomous-actions)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [What Is Implemented](#what-is-implemented)
- [What Is Remaining / Planned](#what-is-remaining--planned)
- [How to Run](#how-to-run)
- [API Documentation](#api-documentation)
- [Environment Variables](#environment-variables)

---

## What This Project Does

EventEngine automates the management of events so that the organizer only needs to:
1. Create the event
2. Open registration
3. Close registration when ready

Everything else — opening attendance, starting the event, ending it, sending smart reminders, generating analytics and AI insights — is handled **automatically by the agent** based on real-time clock checks and participant behavior.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (HTML/JS)                │
│   Dashboard | Events | Registrations | Attendance   │
│                   | Analytics                        │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI (api/)                      │
│  /events  /registrations  /attendance  /analytics   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               SERVICES LAYER (services/)             │
│  EventService | RegistrationService | Attendance    │
│  ReminderService | AnalyticsService | InsightsService│
└────────┬─────────────┬──────────────┬───────────────┘
         │             │              │
┌────────▼──────┐ ┌────▼─────┐ ┌─────▼──────────────┐
│  CORE AGENT   │ │ DATABASE │ │   NOTIFICATIONS     │
│  (core/)      │ │ SQLite/  │ │   Email (SMTP)      │
│  agent.py     │ │ Postgres │ │   SMS (Twilio)      │
│  scheduler.py │ │ SQLAlch. │ │   (notifications/)  │
│  state_machine│ └──────────┘ └────────────────────┘
└───────────────┘
```

**Core design pattern — The Agent runs an Observe → Decide → Act loop every 60 seconds:**
- **Observe**: Query all active events from the database
- **Decide**: Check transition rules and reminder rules for each event
- **Act**: Auto-transition states or send reminders if conditions are met

---

## Event Lifecycle (State Machine)

All state changes are enforced through a strict **Finite State Machine (FSM)**. Invalid transitions are rejected.

```
                    ┌─────────┐
                    │ CREATED │  ← Organizer creates event
                    └────┬────┘
                         │ Organizer opens registration
               ┌─────────▼──────────┐
               │  REGISTRATION_OPEN │  ← Participants register here
               └─────────┬──────────┘     Agent sends smart reminders
                         │ Organizer closes registration
                ┌────────▼────────┐
                │   SCHEDULED     │  ← Event is confirmed
                └────────┬────────┘
                         │ AUTO: 30 min before start time
             ┌───────────▼───────────┐
             │   ATTENDANCE_OPEN     │  ← QR / OTP check-in enabled
             └───────────┬───────────┘
                         │ AUTO: at exact start time
                  ┌──────▼──────┐
                  │   RUNNING   │  ← Event is live
                  └──────┬──────┘
                         │ AUTO: 15 min after end time
                 ┌────────▼────────┐
                 │   COMPLETED     │
                 └────────┬────────┘
                          │ AUTO: immediately
                  ┌────────▼────────┐
                  │   ANALYZING     │  ← Agent calculates metrics
                  └────────┬────────┘
                           │ AUTO: after analytics saved
              ┌─────────────▼─────────────┐
              │     REPORT_GENERATED      │  ← Final state ✓
              └───────────────────────────┘

              CANCELLED ← possible from any state (manual only)
```

---

## How This Project is Agentic

### What does "Agentic" mean here?
A traditional event management system is **reactive** — it only does something when a human clicks a button. EventEngine is **agentic** — it has an autonomous agent that continuously observes the world, reasons about what needs to happen, and acts on its own without waiting for human instruction.

The agent follows the classic **Observe → Decide → Act** loop, running every 60 seconds in the background:

```
┌──────────────────────────────────────────────────────────┐
│                   AGENT LOOP (every 60s)                 │
│                                                          │
│  OBSERVE ──► Query all active events from database       │
│     │                                                    │
│  DECIDE ──► For each event:                              │
│     │        - Check time-based transition rules         │
│     │        - Check confirmation rates                  │
│     │        - Check reminder windows                    │
│     │                                                    │
│  ACT    ──► If condition met:                            │
│              - Auto-transition event state               │
│              - Send reminder emails                      │
│              - Generate analytics                        │
└──────────────────────────────────────────────────────────┘
```

**Key agentic properties of EventEngine:**

| Property | How EventEngine achieves it |
|----------|-----------------------------|
| **Autonomy** | Agent runs without human input — transitions states, sends emails, generates reports on its own |
| **Perception** | Reads real-time data — current timestamp, event states, confirmation rates, last-reminder timestamps |
| **Reasoning** | Applies business rules (transition_rules.py, reminder_rules.py) to decide what action is appropriate |
| **Action** | Executes state transitions, triggers emails, calculates analytics |
| **Adaptivity** | Changes reminder strategy dynamically based on live confirmation rate data |
| **Goal-directed** | Every event has a goal: reach REPORT_GENERATED — the agent steers it there automatically |

---

## Agentic Decision Rules (Exact Thresholds)

These are the precise rules the agent uses to make decisions. These are **not hardcoded if-else** — they are declarative rules in `rules/transition_rules.py` and `rules/reminder_rules.py`.

### 1. Auto State Transition Rules

| Current State | Condition | Agent Action |
|--------------|-----------|--------------|
| `SCHEDULED` | Current time ≥ (event start − **30 minutes**) | Auto-transition → `ATTENDANCE_OPEN` |
| `ATTENDANCE_OPEN` | Current time ≥ event start time | Auto-transition → `RUNNING` |
| `RUNNING` | Current time ≥ (event end + **15 min grace**) | Auto-transition → `COMPLETED` |
| `COMPLETED` | Immediately after completion | Auto-transition → `ANALYZING` |
| `ANALYZING` | After analytics are calculated and saved | Auto-transition → `REPORT_GENERATED` |

### 2. Smart Reminder Rules

The agent evaluates reminders **every 5 minutes** for all events in `REGISTRATION_OPEN` or `SCHEDULED` state.

**When does the agent start sending reminders?**
- Only when the event is **≤ 7 days (168 hours)** away — no spam if event is far in future

**Reminder Windows (triggers):**

| Window | Hours Before Event | Agent Behaviour |
|--------|--------------------|-----------------|
| First Reminder | **168 hours (7 days)** | Sends a heads-up reminder |
| Second Reminder | **48 hours (2 days)** | Stronger reminder |
| Final Reminder | **24 hours (1 day)** | Urgent reminder regardless of confirmation rate |
| Last Call | **2 hours** | Final call, sent to ALL registrants no matter what |

**Anti-spam guard:** Agent enforces a **minimum 12-hour gap** between any two reminders — will not send again even if rules match.

### 3. Adaptive Reminder Intensity (Based on Confirmation Rate)

The agent checks what % of registered participants have clicked the confirmation link and adapts:

| Confirmation Rate | Reminder Type | Tone | Subject Line |
|------------------|---------------|------|--------------|
| **≥ 70%** | `LIGHT` | Friendly | *"Reminder: EventName is coming up!"* |
| **30% – 69%** | `MODERATE` | Encouraging | *"Don't forget: EventName starts in Xh – confirm now!"* |
| **< 30%** | `AGGRESSIVE` | Urgent 🚨 | *"⚠️ URGENT: Confirm for EventName – Starts in Xh"* |

**Special case — AGGRESSIVE mode behaviour:**
- Triggered when confirmation rate falls **below 30%**
- The email tells participants their **spot may be released** if they don't confirm
- Includes the exact current confirmation percentage in the message
- Bypasses the normal "is it a reminder window?" check — sends immediately if rate is critical

**Special case — Final reminder (< 2 hours):**
- Sent to ALL registrants regardless of confirmation rate
- Even confirmed participants get this as a final reminder to actually show up

### 4. Attendance Check-In Window

| Rule | Value |
|------|-------|
| QR / OTP check-in opens | **30 minutes before** event start |
| QR / OTP check-in closes | At event end time |
| OTP validity duration | **15 minutes** from generation |

### 5. Analytics Evaluation Rules (Post-Event)

After the event completes, the agent auto-calculates and grades event performance:

| Metric | Threshold | Label |
|--------|-----------|-------|
| Attendance rate | **> 75%** | Good ✅ |
| Attendance rate | **50% – 75%** | Average ⚠️ |
| Attendance rate | **< 50%** | Poor ❌ |
| Engagement score | **> 80** | High engagement |

If OpenAI API key is configured, the agent feeds these metrics to **GPT-4o-mini** and generates natural language insights and recommendations for the next event.

---

## Manual vs Autonomous Actions

### What the organizer does manually (5 steps only):
| Step | Action |
|------|--------|
| 1 | Create an event (name, date, venue, capacity) |
| 2 | Open registration |
| 3 | Close registration / schedule the event |
| 4 | Cancel if needed |
| 5 | Participants register themselves via the registration form |

### What the agent does automatically:
| Trigger | Action |
|---------|--------|
| Participant registers | Generates QR code + sends confirmation email |
| 7 days before event | Starts sending reminder emails |
| Confirmation rate < 30% | Escalates to AGGRESSIVE reminders (urgent tone) |
| Confirmation rate 30–70% | MODERATE reminders (encouraging tone) |
| Confirmation rate > 70% | LIGHT reminders (friendly tone) |
| 30 min before start | Opens attendance (ATTENDANCE_OPEN) |
| At start time | Marks event as RUNNING |
| 15 min after end time | Marks event as COMPLETED |
| After COMPLETED | Calculates analytics (attendance rate, no-show rate, etc.) |
| After analytics | Generates AI insights and recommendations |

---

## Project Structure

```
EventEngine/
│
├── run.py                    # ← START HERE: launches the server
│
├── api/                      # REST API layer (FastAPI routes)
│   ├── main.py               # App config, middleware, route registration
│   └── routes/
│       ├── events.py         # CRUD for events + state transitions
│       ├── registrations.py  # Register participants, confirm attendance
│       ├── attendance.py     # QR check-in, OTP check-in
│       └── analytics.py      # Event analytics and insights
│
├── core/                     # The brain of the system
│   ├── agent.py              # Observe → Decide → Act loop
│   ├── scheduler.py          # APScheduler — runs agent every 60 seconds
│   └── state_machine.py      # FSM — enforces valid state transitions
│
├── services/                 # Business logic layer
│   ├── event_service.py      # Create/update/transition events
│   ├── registration_service.py # Register participants, send emails
│   ├── reminder_service.py   # Evaluate and send reminders
│   ├── attendance_service.py # QR/OTP check-in logic
│   ├── analytics_service.py  # Calculate post-event metrics
│   └── insights_service.py   # GPT-4 powered insights (optional)
│
├── models/                   # Database models (SQLAlchemy ORM)
│   ├── event.py              # Event table
│   ├── participant.py        # Participant table (stores QR token + OTP)
│   ├── attendance.py         # Attendance check-in records
│   └── analytics.py          # Post-event analytics data
│
├── rules/                    # Declarative business rules
│   ├── transition_rules.py   # Guard conditions for each state transition
│   └── reminder_rules.py     # When/how to send reminders based on data
│
├── notifications/            # Notification channels
│   ├── email.py              # Gmail SMTP email service
│   └── sms.py                # Twilio SMS (configured but inactive)
│
├── utils/                    # Utilities
│   ├── qr_generator.py       # JWT-secured QR code generation
│   ├── otp_generator.py      # 6-digit OTP generation and validation
│   └── logger.py             # Structured application logging
│
├── config/
│   ├── settings.py           # Loads all config from .env
│   └── constants.py          # Enums: EventState, ParticipantStatus, etc.
│
├── db/
│   ├── base.py               # DB engine, session, init
│   └── seed.py               # Sample data for development
│
├── frontend/                 # Static HTML/CSS/JS frontend
│   ├── index.html            # Dashboard
│   ├── events.html           # Events management
│   ├── registrations.html    # Registrations list
│   ├── attendance.html       # Attendance check-in
│   └── analytics.html        # Analytics dashboard
│
├── .env                      # Environment variables (NOT committed)
└── requirements.txt          # Python dependencies
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Agent Scheduler | APScheduler |
| Email | Gmail SMTP (smtplib) |
| SMS | Twilio (configured, inactive) |
| QR Codes | `qrcode` library + JWT tokens |
| AI Insights | OpenAI GPT-4o-mini (optional) |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Auth/Security | JWT (PyJWT) |

---

## What Is Implemented

### ✅ Core System
- [x] Finite State Machine with 9 states and enforced valid transitions
- [x] Autonomous Agent loop (Observe → Decide → Act, every 60 seconds)
- [x] APScheduler background scheduler
- [x] SQLite database with SQLAlchemy ORM
- [x] Full REST API (FastAPI) with Swagger docs at `/docs`
- [x] Static HTML frontend (Dashboard, Events, Registrations, Attendance, Analytics)

### ✅ Event Management
- [x] Create, list, update events (ONLINE / OFFLINE / HYBRID)
- [x] Manual state transitions via API
- [x] Auto state transitions by agent (ATTENDANCE_OPEN → RUNNING → COMPLETED → ANALYZING → REPORT_GENERATED)

### ✅ Registration & Notifications
- [x] Participant registration with capacity checks and duplicate detection
- [x] Auto confirmation email with QR code attached (Gmail SMTP)
- [x] Confirmation link in email — participant confirms attendance via one click
- [x] JWT-secured QR code generation (time-limited, tamper-proof)
- [x] 6-digit OTP generation and validation (backup check-in method)

### ✅ Smart Reminders
- [x] Agent evaluates reminder need every 5 minutes
- [x] Adaptive strategy: LIGHT / MODERATE / AGGRESSIVE based on confirmation rate
- [x] Reminder windows: 7 days, 2 days, 1 day, 2 hours before event
- [x] 12-hour spam guard (no repeated reminders too soon)

### ✅ Attendance
- [x] QR code check-in (scan JWT token)
- [x] OTP check-in (6-digit backup, 15-min expiry)
- [x] Attendance records with timestamp, method, IP address
- [x] Post-check-in confirmation email to participant

### ✅ Analytics
- [x] Auto-calculates: total_registered, confirmed, attended, no_show_rate, attendance_rate
- [x] Rule-based insights when OpenAI is not configured
- [x] GPT-4o-mini AI insights when OpenAI API key is provided
- [x] Analytics dashboard in frontend

---

## What Is Remaining / Planned

### ❌ From Original Plan
| Feature | Status | Notes |
|---------|--------|-------|
| Auto Google Meet link creation | ❌ Not done | API creates event but `meeting_link` is manually pasted; Google Calendar API integration needed |
| Calendar invite (.ics) in email | ❌ Not done | No `.ics` file attached to confirmation emails |
| OTP delivery via email/SMS | ❌ Partial | OTP is generated and stored but not automatically sent to participant; Twilio SMS slot exists but inactive |

### 🔲 Planned Enhancements
| Feature | Description |
|---------|-------------|
| Google Meet auto-creation | Use Google Calendar API to auto-generate Meet link on event creation |
| .ics calendar invite | Attach calendar file to confirmation email (works with Google/Outlook/Apple) |
| OTP via email | Auto-email the OTP to participant when generated |
| Waitlist management | Auto-register next person when someone cancels from a full event |
| Feedback form post-event | Agent emails participants a feedback form after COMPLETED |
| PDF certificate generation | Auto-generate attendance certificate and email to participants |
| SMS reminders via Twilio | Twilio is already in requirements and `.env`, just needs credentials |
| Role-based access | Admin / Organizer / Viewer roles with JWT auth |

### 🚀 New Features (In Progress)

#### 1. LinkedIn One-Click Event Post
After an event is created, the organizer sees a **"Post to LinkedIn"** button. The agent auto-drafts the post using the event name, date, description, and registration link. The organizer previews it and hits **Allow** — the post goes live instantly via the LinkedIn Share API.

**Flow:**
```
Organizer creates event
        ↓
EventEngine shows: [Preview Post] [Post to LinkedIn] [Skip]
        ↓  (one click)
Agent posts to LinkedIn:
─────────────────────────────────────────
🎯 Exciting Event Alert!

We're hosting [EventName] on [Date] at [Venue/Online]

[Description]

🔗 Register here: http://yourapp/register/[event_id]
#EventName #EventEngine
─────────────────────────────────────────
```

**What's needed:**
- LinkedIn Developer App (`client_id` + `client_secret`) — free
- Manager completes OAuth once → token stored
- All future posts: one click, no tab switching

#### 2. Low Registration Alert to Organizer (Agent Intelligence)
The agent now monitors registration pace and alerts the organizer proactively — not just participants.

| Trigger | Agent Action |
|---------|-------------|
| 3 days before event and < 20% capacity filled | Emails organizer: *"Only 5/50 spots filled. Consider promoting."* |
| 1 day before event and < 40% capacity filled | Emails organizer with urgent alert and a ready-to-use LinkedIn/WhatsApp share link |
| 5+ cancellations within 1 hour | Emails organizer: *"Cancellation spike detected — 5 participants cancelled in the last hour"* |
| Event hits 100% capacity 5+ days early | Notifies organizer to consider increasing capacity or opening a waitlist |

This turns the agent from a **mailer** into a genuine **event intelligence system** that watches the event health and flags issues before they become problems.

#### 3. Attendance Certificate Emailer
After the event reaches `REPORT_GENERATED`, the agent automatically emails a **personalized PDF certificate of participation** to every participant who checked in.

**Certificate includes:**
- Participant's full name
- Event name, date, and venue
- Organizer name / organization
- Unique certificate ID (verifiable)
- Auto-signed with event details

**No action required from the organizer** — the agent handles generation and delivery entirely. Uses the `reportlab` Python library for PDF generation.

---

## How to Run

### Requirements
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd EventEngine

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# source .venv/bin/activate       # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Edit .env file — set your Gmail credentials for email to work:
#   SMTP_USER=youremail@gmail.com
#   SMTP_PASSWORD=your-16-char-app-password

# 5. Start the server
python run.py
```

### Access the App

| Page | URL |
|------|-----|
| Dashboard | http://localhost:8000/frontend/index.html |
| Events | http://localhost:8000/frontend/events.html |
| Registrations | http://localhost:8000/frontend/registrations.html |
| Attendance | http://localhost:8000/frontend/attendance.html |
| Analytics | http://localhost:8000/frontend/analytics.html |
| Swagger API Docs | http://localhost:8000/docs |

> No external database setup needed — SQLite is used by default and the `.db` file is created automatically on first run.

---

## API Documentation

Interactive API documentation is available at **http://localhost:8000/docs** when the server is running.

Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/events/` | List all events |
| `POST` | `/api/events/` | Create a new event |
| `POST` | `/api/events/{id}/transition` | Change event state |
| `POST` | `/api/registrations/register` | Register a participant |
| `GET` | `/api/registrations/confirm/{id}` | Participant confirms attendance |
| `POST` | `/api/attendance/qr/validate` | Check in via QR code |
| `POST` | `/api/attendance/otp/generate` | Generate OTP for participant |
| `POST` | `/api/attendance/otp/validate` | Check in via OTP |
| `GET` | `/api/analytics/{event_id}` | Get event analytics |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Email (required for real emails)
SMTP_USER=youremail@gmail.com
SMTP_PASSWORD=your-app-password      # Gmail App Password (16 chars)

# AI Insights (optional)
OPENAI_API_KEY=sk-...                # GPT-4o-mini insights

# SMS (optional)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...

# Agent timing
AGENT_LOOP_INTERVAL_SECONDS=60       # How often agent checks events
```

> **Gmail App Password**: Go to Google Account → Security → 2-Step Verification → App Passwords → Create one for "EventEngine"

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_state_machine.py

# Run with coverage
pytest --cov=.
```

## License

MIT
