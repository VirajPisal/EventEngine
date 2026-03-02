# Event Lifecycle Agent

A **Stateful Agentic Event Lifecycle Management System** with automatic state transitions, adaptive reminders, and LLM-powered insights.

## Architecture

Built with:
- **FastAPI** - REST API framework
- **SQLAlchemy** - ORM and database management
- **PostgreSQL** - Persistent state storage
- **APScheduler** - Time-based triggers and agent loop
- **LangChain + OpenAI** - AI-powered event insights

## Event Lifecycle States

```
CREATED → REGISTRATION_OPEN → SCHEDULED → ATTENDANCE_OPEN → 
RUNNING → COMPLETED → ANALYZING → REPORT_GENERATED
                                    ↓
                              CANCELLED (anytime)
```

## Project Structure

```
event-lifecycle-agent/
├── config/          # Settings, constants, prompts
├── core/            # State machine, agent loop, scheduler
├── models/          # SQLAlchemy models (Event, Participant, etc.)
├── services/        # Business logic for each lifecycle phase
├── rules/           # Declarative rules for reminders and transitions
├── notifications/   # Email, SMS, push notification channels
├── api/             # FastAPI routes
├── db/              # Database setup and migrations
├── utils/           # QR codes, OTP, logging utilities
├── tests/           # Unit and integration tests
└── scripts/         # Entry points (run_agent.py, etc.)
```

## Setup

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+
- OpenAI API key (for insights generation)

### 2. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Start PostgreSQL (ensure it's running)
# Create database
psql -U postgres -c "CREATE DATABASE event_lifecycle;"

# Run seed script to create tables and sample data
python db/seed.py --drop
```

### 4. Run the Agent

```bash
python scripts/run_agent.py
```

## Development Stages

This project is built in 6 incremental stages:

- **Stage 1** ✅ Foundation (DB + Models + State Machine)
- **Stage 2** ⏳ Core Services (Event, Registration, Reminders)
- **Stage 3** ⏳ Agent Loop + Scheduler
- **Stage 4** ⏳ Attendance + Notifications
- **Stage 5** ⏳ Analytics + Insights + Report
- **Stage 6** ⏳ API Layer

## Key Features

- **Finite State Machine**: All state changes validated and logged
- **Autonomous Agent**: Observe → Decide → Act loop
- **Adaptive Reminders**: Rule-based reminder strategy based on confirmation rate
- **Dual Attendance**: QR codes (offline) + OTP (online)
- **AI Insights**: LLM-generated recommendations from event analytics
- **Multi-channel Notifications**: Email, SMS, webhooks

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
