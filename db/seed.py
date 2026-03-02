"""
Database seed script for development and testing
"""
from datetime import datetime, timedelta, timezone
from db.base import init_db, drop_db, get_db_context
from models.event import Event
from models.participant import Participant
from config.constants import EventState, EventType, ParticipantStatus
from core.state_machine import StateMachine


def seed_database(drop_existing: bool = False):
    """
    Seed database with sample data for development
    
    Args:
        drop_existing: If True, drop all tables before seeding
    """
    print("=" * 60)
    print("DATABASE SEEDING STARTED")
    print("=" * 60)
    
    # Drop existing tables if requested
    if drop_existing:
        print("\n[1/4] Dropping existing tables...")
        drop_db()
        print("✓ Tables dropped")
    
    # Initialize database (create tables)
    print("\n[2/4] Creating tables...")
    init_db()
    print("✓ Tables created")
    
    # Create sample events
    print("\n[3/4] Creating sample events...")
    with get_db_context() as db:
        # Event 1: Tech Conference (upcoming)
        event1 = Event(
            name="Tech Conference 2026",
            description="Annual technology conference featuring latest trends in AI and Cloud Computing",
            event_type=EventType.OFFLINE,
            state=EventState.CREATED,
            start_time=datetime.now(timezone.utc) + timedelta(days=30),
            end_time=datetime.now(timezone.utc) + timedelta(days=30, hours=8),
            registration_deadline=datetime.now(timezone.utc) + timedelta(days=25),
            venue="Convention Center, Hall A",
            max_participants=500,
            created_by="admin"
        )
        db.add(event1)
        print(f"  ✓ Created: {event1.name} (State: {event1.state.value})")
        
        # Event 2: Online Webinar (soon)
        event2 = Event(
            name="Python Best Practices Webinar",
            description="Learn advanced Python patterns and best practices",
            event_type=EventType.ONLINE,
            state=EventState.CREATED,
            start_time=datetime.now(timezone.utc) + timedelta(hours=48),
            end_time=datetime.now(timezone.utc) + timedelta(hours=50),
            meeting_link="https://meet.example.com/python-webinar",
            max_participants=100,
            created_by="admin"
        )
        db.add(event2)
        print(f"  ✓ Created: {event2.name} (State: {event2.state.value})")
        
        # Event 3: Workshop (hybrid)
        event3 = Event(
            name="DevOps Workshop",
            description="Hands-on workshop on CI/CD and containerization",
            event_type=EventType.HYBRID,
            state=EventState.CREATED,
            start_time=datetime.now(timezone.utc) + timedelta(days=15),
            end_time=datetime.now(timezone.utc) + timedelta(days=15, hours=4),
            venue="Training Room 3",
            meeting_link="https://meet.example.com/devops-workshop",
            max_participants=50,
            created_by="admin"
        )
        db.add(event3)
        print(f"  ✓ Created: {event3.name} (State: {event3.state.value})")
        
        db.flush()  # Ensure IDs are assigned
        
        # Test state transitions
        print("\n[4/4] Testing state machine transitions...")
        
        try:
            # Valid transition: CREATED → REGISTRATION_OPEN
            print(f"\n  Testing: {event1.name}")
            print(f"    Current state: {event1.state.value}")
            StateMachine.transition(event1, EventState.REGISTRATION_OPEN, reason="Opening registration for seeding test")
            print(f"    ✓ Transitioned to: {event1.state.value}")
            
            # Add some participants to event 1
            participants_data = [
                {"name": "Alice Johnson", "email": "alice@example.com", "phone": "+1234567890"},
                {"name": "Bob Smith", "email": "bob@example.com", "phone": "+1234567891"},
                {"name": "Carol White", "email": "carol@example.com", "phone": "+1234567892"},
            ]
            
            for p_data in participants_data:
                participant = Participant(
                    event_id=event1.id,
                    name=p_data["name"],
                    email=p_data["email"],
                    phone=p_data["phone"],
                    status=ParticipantStatus.REGISTERED
                )
                db.add(participant)
            
            print(f"    ✓ Added {len(participants_data)} participants")
            
            # Another valid transition: REGISTRATION_OPEN → SCHEDULED
            StateMachine.transition(event1, EventState.SCHEDULED, reason="Registration period ended")
            print(f"    ✓ Transitioned to: {event1.state.value}")
            
            # Test invalid transition
            print(f"\n  Testing invalid transition (should fail)...")
            try:
                StateMachine.transition(event1, EventState.REPORT_GENERATED)
                print("    ✗ ERROR: Invalid transition was allowed!")
            except Exception as e:
                print(f"    ✓ Correctly rejected: {str(e)[:80]}...")
            
        except Exception as e:
            print(f"    ✗ Error during transitions: {e}")
            raise
    
    print("\n" + "=" * 60)
    print("DATABASE SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nSummary:")
    print("  - 3 events created")
    print("  - 3 participants registered for Event 1")
    print("  - State machine tested and validated")
    print("\nYou can now start the application!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Check if --drop flag is provided
    drop_existing = "--drop" in sys.argv or "-d" in sys.argv
    
    if drop_existing:
        print("\n⚠️  WARNING: This will drop all existing tables!")
        confirm = input("Are you sure you want to continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("Seeding cancelled.")
            sys.exit(0)
    
    try:
        seed_database(drop_existing=drop_existing)
    except Exception as e:
        print(f"\n✗ SEEDING FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
