"""
Validate Stage 1 - Check all modules import correctly and state machine works
This script doesn't require a database connection
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("STAGE 1 VALIDATION")
print("=" * 60)

# Test 1: Config imports
print("\n[1/6] Testing config imports...")
try:
    from config.settings import settings
    from config.constants import EventState, EventType, CONFIRMATION_THRESHOLDS
    print(f"  ✓ Settings loaded: {settings.APP_NAME}")
    print(f"  ✓ Constants loaded: {len(EventState)} states defined")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 2: Database module imports
print("\n[2/6] Testing database module...")
try:
    from db.base import Base, engine
    print(f"  ✓ Database engine created: {settings.DB_NAME}")
    print(f"  ✓ Base declarative class available")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 3: Model imports
print("\n[3/6] Testing model imports...")
try:
    from models.event import Event
    from models.participant import Participant
    from models.attendance import Attendance
    from models.analytics import Analytics
    print(f"  ✓ Event model: {Event.__tablename__}")
    print(f"  ✓ Participant model: {Participant.__tablename__}")
    print(f"  ✓ Attendance model: {Attendance.__tablename__}")
    print(f"  ✓ Analytics model: {Analytics.__tablename__}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 4: State machine imports and validation
print("\n[4/6] Testing state machine...")
try:
    from core.state_machine import StateMachine, ALLOWED_TRANSITIONS
    assert StateMachine.validate_fsm() is True
    print(f"  ✓ State machine validated")
    print(f"  ✓ {len(ALLOWED_TRANSITIONS)} states with transitions defined")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 5: State transition logic
print("\n[5/6] Testing state transitions...")
try:
    from datetime import datetime, timedelta, timezone
    
    # Create a mock event (not persisted to DB)
    event = Event(
        name="Test Event",
        event_type=EventType.OFFLINE,
        state=EventState.CREATED,
        start_time=datetime.now(timezone.utc) + timedelta(days=7),
        end_time=datetime.now(timezone.utc) + timedelta(days=7, hours=2)
    )
    
    # Test valid transition
    result = StateMachine.transition(event, EventState.REGISTRATION_OPEN, reason="Validation test")
    assert event.state == EventState.REGISTRATION_OPEN
    print(f"  ✓ Valid transition: CREATED → REGISTRATION_OPEN")
    
    # Test invalid transition
    try:
        StateMachine.transition(event, EventState.COMPLETED)
        print(f"  ✗ Invalid transition was allowed!")
        sys.exit(1)
    except Exception:
        print(f"  ✓ Invalid transition correctly rejected")
    
    # Test full lifecycle path
    StateMachine.transition(event, EventState.SCHEDULED)
    StateMachine.transition(event, EventState.ATTENDANCE_OPEN)
    StateMachine.transition(event, EventState.RUNNING)
    StateMachine.transition(event, EventState.COMPLETED)
    StateMachine.transition(event, EventState.ANALYZING)
    StateMachine.transition(event, EventState.REPORT_GENERATED)
    print(f"  ✓ Full lifecycle path works: CREATED → REPORT_GENERATED")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Terminal state detection
print("\n[6/6] Testing terminal states...")
try:
    assert StateMachine.is_terminal_state(EventState.REPORT_GENERATED) is True
    assert StateMachine.is_terminal_state(EventState.CANCELLED) is True
    assert StateMachine.is_terminal_state(EventState.CREATED) is False
    print(f"  ✓ Terminal states correctly identified")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("STAGE 1 VALIDATION PASSED ✓")
print("=" * 60)
print("\nAll components validated:")
print("  ✓ Configuration system")
print("  ✓ Database setup")
print("  ✓ All 4 models (Event, Participant, Attendance, Analytics)")
print("  ✓ State machine with 9 states")
print("  ✓ State transition validation")
print("\nStage 1 Exit Check:")
print("  ✓ Can create Event model with state CREATED")
print("  ✓ Can transition through state machine")
print("  ✓ Invalid transitions are rejected")
print("\nNote: To test with actual PostgreSQL database:")
print("  1. Ensure PostgreSQL is running")
print("  2. Create database: CREATE DATABASE event_lifecycle;")
print("  3. Run: python test_stage1.py")
print("=" * 60)
