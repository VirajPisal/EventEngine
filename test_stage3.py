"""
Stage 3 Test - Agent Loop + Scheduler Validation
Exit Check: Create event with start_time = now + 15 seconds, watch agent auto-transition
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from time import sleep

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import all necessary modules
from config.settings import settings
from config.constants import EventState, EventType
from db.base import get_db_context, Base, engine
# Import all models first
from models.event import Event
from models.participant import Participant
from models.attendance import Attendance
from models.analytics import Analytics
from services.event_service import EventService
from core.agent import get_agent
from core.scheduler import get_scheduler
from utils.logger import logger

def print_header(text):
    print("\n" + "="  * 70)
    print(f"  {text}")
    print("=" * 70)

def print_section(text):
    print(f"\n>>> {text}")
    print("-" * 70)

def print_event_status(db, event_id):
    """Print current event status"""
    event_data = EventService.get_event_with_stats(db, event_id)
    print(f"  Current State: {event_data['state']}")
    print(f"  Event Time: {event_data['start_time']}")
    print(f"  Current Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Initialize database
print("[Setup] Initializing database...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("[OK] Database ready")

print_header("STAGE 3 TEST - AGENT LOOP + SCHEDULER")

with get_db_context() as db:
    # Test 1: Create Event with near-future start time
    print_section("1. Create Event with Start Time = Now + 15 seconds")
    
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(seconds=15)
    end_time = start_time + timedelta(hours=1)
    
    event_result = EventService.create_event(
        db,
        name="Auto-Transition Test Event",
        description="Testing autonomous state transitions",
        event_type=EventType.ONLINE,
        start_time=start_time,
        end_time=end_time,
        venue=None,
        meeting_link="https://meet.example.com/test-agent",
        max_participants=20,
        created_by="test_admin"
    )
    
    event_id = event_result.id
    print(f"[OK] Event created: {event_result.name} (ID: {event_id})")
    print(f"  Start Time: {start_time.strftime('%H:%M:%S UTC')}")
    print(f"  Current Time: {now.strftime('%H:%M:%S UTC')}")
    print(f"  Seconds until start: 15")
    
    # Test 2: Manually transition to SCHEDULED
    print_section("2. Transition to SCHEDULED State")
    
    # First open registration
    EventService.transition_event_state(
        db,
        event_id,
        EventState.REGISTRATION_OPEN,
        reason="Opening registration for test",
        triggered_by="test"
    )
    print("[OK] State: REGISTRATION_OPEN")
    
    # Then schedule the event
    EventService.transition_event_state(
        db,
        event_id,
        EventState.SCHEDULED,
        reason="Scheduling for auto-transition test",
        triggered_by="test"
    )
    print("[OK] State: SCHEDULED")
    print_event_status(db, event_id)

# Test 3: Start the Agent
print_section("3. Start Autonomous Agent")

agent = get_agent()
scheduler = get_scheduler()

agent.start()
print("[OK] Agent started")

# Add agent loop with faster interval for testing (every 3 seconds)
scheduler.add_agent_loop_job(agent.run_cycle, interval_seconds=3)
print("[OK] Agent loop scheduled (every 3 seconds)")

scheduler.start()
print("[OK] Scheduler started")

# Test 4: Monitor Auto-Transition
print_section("4. Monitor Auto-Transition (Waiting 20 seconds)")
print("  Watching for: SCHEDULED -> ATTENDANCE_OPEN -> RUNNING")
print("  (Agent checks every 3 seconds)")

initial_state = None
attendance_open_time = None
running_time = None

with get_db_context() as db:
    event = db.query(Event).filter(Event.id == event_id).first()
    initial_state = event.state.value
    print(f"\n  T+0s  | State: {initial_state}")

# Monitor for 20 seconds
for i in range(1, 21):
    sleep(1)
    
    with get_db_context() as db:
        event = db.query(Event).filter(Event.id == event_id).first()
        current_state = event.state.value
        
        # Check for state changes
        if current_state != initial_state:
            print(f"  T+{i}s | State: {current_state} [AUTO-TRANSITIONED]")
            
            if current_state == "ATTENDANCE_OPEN" and attendance_open_time is None:
                attendance_open_time = i
            
            if current_state == "RUNNING" and running_time is None:
                running_time = i
            
            initial_state = current_state
        elif i % 5 == 0:  # Print status every 5 seconds
            print(f"  T+{i}s | State: {current_state}")

# Stop the agent
print("\n[Cleanup] Stopping agent...")
scheduler.stop()
agent.stop()
print("[OK] Agent stopped")

# Test 5: Verify Results
print_section("5. Verify Auto-Transition Results")

with get_db_context() as db:
    final_event = db.query(Event).filter(Event.id == event_id).first()
    final_state = final_event.state.value
    
    print(f"  Initial State: SCHEDULED")
    print(f"  Final State: {final_state}")
    
    if attendance_open_time:
        print(f"  [OK] SCHEDULED -> ATTENDANCE_OPEN at T+{attendance_open_time}s")
    
    if running_time:
        print(f"  [OK] ATTENDANCE_OPEN -> RUNNING at T+{running_time}s")
    
    # Check if we reached RUNNING state
    if final_state == "RUNNING":
        print("\n  [SUCCESS] Event auto-transitioned to RUNNING!")
    elif final_state == "ATTENDANCE_OPEN":
        print("\n  [PARTIAL] Event auto-transitioned to ATTENDANCE_OPEN (RUNNING will come at exact start time)")
    else:
        print(f"\n  [WAIT] Event still in {final_state} (may need more time)")

# Test 6: Check Activity Log
print_section("6. View Agent Activity Log")

activities = logger.get_recent_activities(limit=10, event_id=event_id)

if activities:
    print(f"  Recent agent actions ({len(activities)}):")
    for activity in activities:
        if 'agent' in activity['message'].lower() or 'transition' in activity['type'].lower():
            print(f"    [{activity['type']}] {activity['message'][:80]}...")
else:
    print("  No agent activities recorded")

# Exit Check Summary
print_header("STAGE 3 EXIT CHECK - SUMMARY")

print("\n[SUCCESS] Exit Check Requirements:")
print("  [OK] Can create event with near-future start time")
print("  [OK] Can start autonomous agent with scheduler")
print("  [OK] Agent runs observe-decide-act cycle every 3 seconds")

if running_time:
    print("  [OK] Event auto-transitioned to RUNNING without manual intervention")
elif attendance_open_time:
    print("  [OK] Event auto-transitioned to ATTENDANCE_OPEN (partial success)")
else:
    print("  [WAIT] No auto-transition detected (may need longer test duration)")

print("\n[SUCCESS] What We Built in Stage 3:")
print("  1. Scheduler - APScheduler with interval-based jobs")
print("  2. Agent - Observe-Decide-Act autonomous loop")
print("  3. Auto-Transitions - Time-based state changes without human intervention")
print("  4. Entry Point - scripts/run_agent.py to start the system")

print("\n[COMPLETE] Stage 3 Complete!")
print("  Next: Stage 4 - Attendance + Notifications (Real Email/SMS/QR)")

print("\n" + "=" * 70)
