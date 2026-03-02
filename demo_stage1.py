"""
Interactive Demo - Stage 1 Features
Run this to see what we've built!
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from config.constants import EventState, EventType, ParticipantStatus
# Import all models to ensure SQLAlchemy relationships work
from models.event import Event
from models.participant import Participant
from models.attendance import Attendance
from models.analytics import Analytics
from core.state_machine import StateMachine, InvalidStateTransitionError, ALLOWED_TRANSITIONS

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_section(text):
    print(f"\n>>> {text}")
    print("-" * 70)

# Main Demo
print_header("🚀 EVENT LIFECYCLE AGENT - STAGE 1 DEMO")

# 1. Show Configuration
print_section("1. Configuration System")
print(f"App Name: {settings.APP_NAME}")
print(f"Database: {settings.DB_NAME} @ {settings.DB_HOST}:{settings.DB_PORT}")
print(f"Debug Mode: {settings.DEBUG}")
print(f"Agent Loop Interval: {settings.AGENT_LOOP_INTERVAL_SECONDS}s")

# 2. Show Event States
print_section("2. Event Lifecycle States (FSM)")
for i, state in enumerate(EventState, 1):
    terminal = " [TERMINAL]" if StateMachine.is_terminal_state(state) else ""
    print(f"  {i}. {state.value}{terminal}")

# 3. Show State Transitions
print_section("3. State Transition Rules")
for state, allowed in ALLOWED_TRANSITIONS.items():
    if allowed:
        transitions = " → ".join([s.value for s in allowed])
        print(f"  {state.value:20} → {transitions}")
    else:
        print(f"  {state.value:20} → [TERMINAL STATE - No transitions]")

# 4. Create Mock Event
print_section("4. Creating a Mock Event")
event = Event(
    name="AI & Machine Learning Summit 2026",
    description="Annual summit featuring latest AI breakthroughs",
    event_type=EventType.HYBRID,
    state=EventState.CREATED,
    start_time=datetime.now(timezone.utc) + timedelta(days=45),
    end_time=datetime.now(timezone.utc) + timedelta(days=45, hours=6),
    venue="Tech Convention Center, Hall A",
    meeting_link="https://meet.example.com/ai-summit",
    max_participants=300,
    created_by="admin"
)

print(f"✓ Event Created:")
print(f"  Name: {event.name}")
print(f"  Type: {event.event_type.value}")
print(f"  Current State: {event.state.value}")
print(f"  Start: {event.start_time.strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Capacity: {event.max_participants} participants")
print(f"  Venue: {event.venue}")
print(f"  Online: {event.meeting_link}")

# 5. Test State Transitions
print_section("5. Testing State Machine Transitions")

transitions_to_test = [
    (EventState.REGISTRATION_OPEN, "Opening registration to public"),
    (EventState.SCHEDULED, "Registration closed, event scheduled"),
    (EventState.ATTENDANCE_OPEN, "Opening attendance check-in window"),
    (EventState.RUNNING, "Event is now live"),
]

for new_state, reason in transitions_to_test:
    old_state = event.state
    try:
        StateMachine.transition(event, new_state, reason=reason)
        print(f"✓ {old_state.value:20} → {new_state.value:20} | {reason}")
    except InvalidStateTransitionError as e:
        print(f"✗ {old_state.value:20} ⛔ {new_state.value:20} | REJECTED")

# 6. Test Invalid Transition
print_section("6. Testing Invalid Transition (Should Fail)")
current = event.state
try:
    StateMachine.transition(event, EventState.REPORT_GENERATED)
    print(f"✗ ERROR: Invalid transition was allowed!")
except InvalidStateTransitionError as e:
    print(f"✓ Invalid transition correctly rejected:")
    print(f"  Attempted: {current.value} → REPORT_GENERATED")
    print(f"  Reason: Cannot skip states in lifecycle")

# 7. Create Mock Participants
print_section("7. Creating Mock Participants")
participants_data = [
    {"name": "Alice Johnson", "email": "alice@techcorp.com", "phone": "+1-555-0101"},
    {"name": "Bob Martinez", "email": "bob@innovate.io", "phone": "+1-555-0102"},
    {"name": "Carol Zhang", "email": "carol@ailab.edu", "phone": "+1-555-0103"},
    {"name": "David Kumar", "email": "david@startup.dev", "phone": "+1-555-0104"},
]

participants = []
for p_data in participants_data:
    participant = Participant(
        event_id=1,  # Mock ID
        name=p_data["name"],
        email=p_data["email"],
        phone=p_data["phone"],
        status=ParticipantStatus.REGISTERED
    )
    participants.append(participant)
    print(f"  ✓ {participant.name:20} | {participant.email:25} | {participant.status.value}")

# 8. Show Model Relationships
print_section("8. Model Structure")
print("Event Model:")
print(f"  - ID, Name, Description, Type")
print(f"  - State (FSM-controlled) ⚠️  NEVER modified directly")
print(f"  - Timing: start_time, end_time, registration_deadline")
print(f"  - Capacity: max_participants")
print(f"  - Relationships: participants, attendance_records, analytics")

print("\nParticipant Model:")
print(f"  - ID, Event ID, Name, Email, Phone")
print(f"  - Status: {', '.join([s.value for s in ParticipantStatus])}")
print(f"  - Confirmation tracking")
print(f"  - Attendance credentials: qr_token, otp")

print("\nAttendance Model:")
print(f"  - Event ID, Participant ID")
print(f"  - Check-in method: QR or OTP")
print(f"  - Validation status and notes")

print("\nAnalytics Model:")
print(f"  - Registration metrics: total, confirmed, confirmation_rate")
print(f"  - Attendance metrics: total_attended, no_show_rate")
print(f"  - Engagement score (0-100)")

# 9. Show Complete Lifecycle Path
print_section("9. Complete Event Lifecycle Path")
lifecycle_event = Event(
    name="Test Lifecycle Event",
    event_type=EventType.ONLINE,
    state=EventState.CREATED,
    start_time=datetime.now(timezone.utc) + timedelta(days=30),
    end_time=datetime.now(timezone.utc) + timedelta(days=30, hours=2)
)

lifecycle_path = [
    EventState.REGISTRATION_OPEN,
    EventState.SCHEDULED,
    EventState.ATTENDANCE_OPEN,
    EventState.RUNNING,
    EventState.COMPLETED,
    EventState.ANALYZING,
    EventState.REPORT_GENERATED
]

print("Transitioning through complete lifecycle:")
print(f"  START: {lifecycle_event.state.value}")

for state in lifecycle_path:
    old_state = lifecycle_event.state
    StateMachine.transition(lifecycle_event, state)
    print(f"    ↓")
    print(f"  {state.value}")

print(f"\n✓ Event reached terminal state: {lifecycle_event.state.value}")
print(f"✓ No further transitions possible: {StateMachine.is_terminal_state(lifecycle_event.state)}")

# 10. Summary
print_header("📊 STAGE 1 SUMMARY")
print("\n✅ What We Built:")
print("  1. Configuration System (settings.py, constants.py)")
print("  2. Database Layer (SQLAlchemy engine, session management)")
print("  3. Four Core Models (Event, Participant, Attendance, Analytics)")
print("  4. State Machine (9 states, transition validation)")
print("  5. Validation & Testing Suite")
print("\n✅ Exit Check:")
print("  ✓ Can create Event with state CREATED")
print("  ✓ Can transition through state machine")
print("  ✓ Invalid transitions are rejected")
print("  ✓ Full lifecycle path validated")
print("\n🎯 Next Stage:")
print("  Stage 2: Core Services (event_service, registration_service, reminder_service)")
print("\n" + "=" * 70)
