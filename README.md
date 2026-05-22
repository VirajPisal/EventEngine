# EventEngine: Autonomous Event Lifecycle Management System

EventEngine is a comprehensive, autonomous platform designed to manage the entire lifecycle of an event with minimal human intervention. Powered by a robust Finite State Machine (FSM), an autonomous background agent loop, and LangGraph-powered AI insights, EventEngine automates everything from registration and intelligent reminders to post-event analytics, certificate generation, and promotional campaigns.

## 🌟 Key Features

### 1. Autonomous Lifecycle Management (Agent Loop)
A background scheduling agent constantly monitors all events and acts based on their current state in the Finite State Machine (FSM). The agent observes the database, decides on actions, and executes them, allowing events to effectively manage themselves.

*   **Auto-Transitions:** Moves events seamlessly between states (`CREATED` ➔ `REGISTRATION_OPEN` ➔ `SCHEDULED` ➔ `ATTENDANCE_OPEN` ➔ `RUNNING` ➔ `COMPLETED` ➔ `ANALYZING` ➔ `REPORT_GENERATED`).
*   **Smart Reminders:** Evaluates whether it's the right time to send 24-hour, 1-hour, or "starting now" reminders based on the event's start time. Actions are queued for organizer approval or executed directly based on configurations.
*   **Autonomous Promotion:** Identifies potential participants for events with low registration (e.g., under 50% capacity) and autonomously sends promotional emails with event details.
*   **Automated Certificate Generation:** For completed online events, the system automatically overlays the participant's name on a certificate template and emails it to them.
*   **Feedback Collection:** Triggers feedback surveys immediately upon event completion to attendees.

### 2. Intelligent FSM (Finite State Machine)
Strict rules dictate how an event progresses, preventing illegal state changes and ensuring data integrity.
*   **Strict State Enforcement:** Prevents manual overrides that break the logical flow (e.g., cannot move from `COMPLETED` back to `REGISTRATION_OPEN`).
*   **Terminal States:** `CANCELLED` and `REPORT_GENERATED` signify the end of the event's active lifecycle.

### 3. Comprehensive Dual-Portal Frontend
*   **Organizer Dashboard:** Provides deep insights into active events, pending agent actions (Approve/Reject UI), real-time attendance statistics, and AI-generated post-event reports.
*   **Participant Portal:** A dedicated view for users to browse events, manage their registrations, and directly join meetings via a conditionally rendered "Join Meeting" button (hidden when an event is completed or cancelled). Includes a dynamic attendance page using QR code technology.

### 4. AI-Powered Strategic Insights (LangGraph)
Post-event, EventEngine aggregates attendance data, feedback ratings, and registration numbers.
*   Uses **LangChain & LangGraph** to evaluate performance.
*   Provides actionable, strategic insights for future events (e.g., "Increase marketing budget," "Change time slot").
*   Supports Multi-Key Failover (Groq, Gemini, OpenAI) to ensure high availability for AI inferences.

### 5. Multi-Channel Notifications & Integrations
*   **Email Engine:** Robust SMTP configuration for sending HTML/Text emails for OTPs, confirmations, promotional blasts, and certificates.
*   **Google Calendar & Meet:** Direct integration via OAuth to generate real Google Meet links for online events dynamically.
*   **SMS (Twilio):** Configured for critical SMS delivery to mobile numbers (Requires Twilio credentials).

## 🏗️ System Architecture

EventEngine is built on a modern, decoupled architecture:

*   **Backend:** FastAPI (Python) - Provides high-performance async REST API endpoints.
*   **Database:** SQLAlchemy ORM with SQLite (default) / PostgreSQL support.
*   **Agent Scheduler:** APScheduler runs the Observe-Decide-Act loop at 30-second and 5-minute intervals.
*   **Frontend:** Vanilla HTML, CSS (Dark Theme, Glassmorphism), and Javascript. Communicates entirely via REST.
*   **AI Engine:** LangGraph, LangChain, Groq/OpenAI/Gemini.
*   **Authentication:** JWT-based Role-Based Access Control (RBAC) separating `organizer` and `participant`.

### 📂 Directory Structure
```text
EventEngine/
├── api/                  # FastAPI routers (events, auth, agent, analytics)
├── config/               # Settings, constants, and environment configs
├── core/                 # Core engine logic (Agent, StateMachine, Scheduler)
├── db/                   # Database session management
├── frontend/             # HTML/CSS/JS Portals (Dashboard, Portal, Analytics)
├── models/               # SQLAlchemy ORM Models (Event, User, Participant)
├── notifications/        # Email (SMTP) and SMS (Twilio) services
├── rules/                # Transition rules for the FSM
├── services/             # Business logic layer (Analytics, Promotion, Certs)
│   └── ai/               # LangGraph AI Insights engine
├── utils/                # Logging, QR generation, helpers
├── run.py                # Main entry point to launch the uvicorn server
└── requirements.txt      # Python dependencies
```

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   A Gmail account (with App Passwords enabled) or another SMTP provider.

### 2. Installation
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/yourusername/EventEngine.git
cd EventEngine
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the sample environment file and configure your credentials:
```bash
cp .env.example .env
```
Edit `.env` and fill in your details. CRITICAL fields include:
*   `SECRET_KEY`: Set a secure string for JWT generation.
*   `SMTP_USER` & `SMTP_PASSWORD`: Required for email functionality (e.g., Gmail App Password).
*   `GROQ_API_KEYS` or `OPENAI_API_KEY`: Required for the AI Analytics engine.

*(Optional)* For Google Calendar/Meet integration, place your `credentials.json` from the Google Cloud Console into the project root.

### 4. Running the Application
Start the FastAPI server:
```bash
python run.py
```
This will initialize the database schema automatically, start the backend on `http://localhost:8000`, and begin the background Autonomous Agent.

### 5. Accessing the Platform
*   **Participant Login / Registration:** [http://localhost:8000/frontend/login.html](http://localhost:8000/frontend/login.html)
*   **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

*(Note: Create an Organizer account via the registration form to access the main Dashboard, or a Participant account to access the Portal.)*

## 🔄 The Lifecycle in Action

1.  **Creation:** An organizer creates an event. It enters the `CREATED` state.
2.  **Registration:** The agent or organizer transitions the event to `REGISTRATION_OPEN`. The system autonomously promotes the event to potential participants.
3.  **Scheduling:** As the event nears, it transitions to `SCHEDULED`. The agent queues reminders (24h, 1h) to be sent via email.
4.  **Running:** During the event (`RUNNING` / `ATTENDANCE_OPEN`), participants join via the portal link or scan QR codes for attendance.
5.  **Completion:** The agent moves the event to `COMPLETED` when the end time is reached. It emails feedback surveys and participation certificates.
6.  **Analysis:** The event moves to `ANALYZING`. LangGraph reviews attendance rates and feedback, generating a comprehensive report.
7.  **Finalization:** The event enters `REPORT_GENERATED`, and insights are available on the Organizer Dashboard.

## 🔮 Future Enhancements
*   **Full SMS Activation:** Completing the Twilio integration for global SMS updates.
*   **ICS Calendar Attachments:** Sending standard calendar invite files alongside confirmation emails.
*   **LinkedIn Integration:** One-click automated promotion of upcoming events to LinkedIn via API.
*   **Advanced Analytics Dashboards:** Implementing charting libraries (e.g., Chart.js) in the frontend for visual AI insights.

---
*Built with ❤️ for fully autonomous event management.*
