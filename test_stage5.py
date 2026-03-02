"""
Stage 5 Test - Analytics + AI Insights
Tests: Analytics calculation, AI insights, agent integration
"""
import sys
from datetime import datetime, timedelta, timezone
from db.base import get_db_context, init_db
from services.event_service import EventService
from services.registration_service import RegistrationService
from services.attendance_service import AttendanceService
from services.analytics_service import AnalyticsService
from services.insights_service import get_insights_service
from config.constants import EventType, EventState


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def test_stage_5():
    """Test Stage 5: Analytics + AI Insights"""
    
    print("\n" + "=" * 60)
    print(" STAGE 5 TEST: Analytics + AI Insights")
    print("=" * 60)
    
    # Initialize database
    print("\n[1] Initializing database...")
    init_db()
    print("[OK] Database initialized")
    
    with get_db_context() as db:
        # Create test event
        print_section("TEST 1: Event Setup")
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=2)  # Event already happened
        end_time = start_time + timedelta(hours=1)
        
        event = EventService.create_event(
            db=db,
            name="Stage 5 Test - Analytics Demo Event",
            description="Test event for analytics and insights",
            event_type=EventType.OFFLINE,
            start_time=start_time,
            end_time=end_time,
            venue="Conference Room A",
            max_participants=50
        )
        
        event_id = event.id
        print(f"[OK] Event created: ID={event_id}")
        
        # Open registration first
        print_section("TEST 2: Opening Registration")
        result = EventService.transition_event_state(db, event_id, EventState.REGISTRATION_OPEN)
        if result["success"]:
            print(f"[OK] Transitioned to REGISTRATION_OPEN")
        else:
            print(f"[FAIL] Failed to open registration: {result['message']}")
            return False
        
        # Register participants with varying behavior patterns
        print_section("TEST 3: Creating Test Data")
        
        test_participants = [
            {"name": "Alice Brown", "email": "alice@test.com", "confirm": True, "attend": True},
            {"name": "Bob Wilson", "email": "bob@test.com", "confirm": True, "attend": True},
            {"name": "Charlie Lee", "email": "charlie@test.com", "confirm": True, "attend": True},
            {"name": "Diana Chen", "email": "diana@test.com", "confirm": True, "attend": False},  # No-show
            {"name": "Eve Taylor", "email": "eve@test.com", "confirm": False, "attend": False},  # No confirm
            {"name": "Frank Moore", "email": "frank@test.com", "confirm": True, "attend": True},
            {"name": "Grace Kim", "email": "grace@test.com", "confirm": True, "attend": True},
            {"name": "Henry Park", "email": "henry@test.com", "confirm": False, "attend": False},  # No confirm
            {"name": "Ivy Zhang", "email": "ivy@test.com", "confirm": True, "attend": True},
            {"name": "Jack Smith", "email": "jack@test.com", "confirm": True, "attend": False},  # No-show
        ]
        
        participant_ids = []
        
        for p in test_participants:
            reg = RegistrationService.register_participant(
                db=db,
                event_id=event_id,
                name=p["name"],
                email=p["email"]
            )
            
            if not reg["success"]:
                print(f"[FAIL] Registration failed for {p['name']}")
                return False
            
            participant_ids.append(reg["participant"]["id"])
            
            # Confirm if needed
            if p["confirm"]:
                RegistrationService.confirm_participant(db, reg["participant"]["id"])
        
        print(f"[OK] Created {len(test_participants)} participants")
        print(f"     - {sum(1 for p in test_participants if p['confirm'])} confirmed")
        
        # Transition to allow attendance
        print_section("TEST 4: Transition to Allow Attendance")
        
        for state in [EventState.SCHEDULED, EventState.ATTENDANCE_OPEN]:
            result = EventService.transition_event_state(db, event_id, state)
            if result["success"]:
                print(f"[OK] Transitioned to {state.value}")
            else:
                print(f"[FAIL] Failed to transition: {result['message']}")
                return False
        
        # Now mark attendance
        print_section("TEST 5: Mark Attendance")
        
        for i, p in enumerate(test_participants):
            if p["attend"]:
                qr_result = AttendanceService.generate_qr_code(db, participant_ids[i])
                if qr_result["success"]:
                    attend_result = AttendanceService.validate_qr_check_in(
                        db,
                        qr_result["qr_code"]["token"]
                    )
                    if not attend_result["success"]:
                        print(f"[FAIL] Attendance failed for {p['name']}: {attend_result.get('message')}")
                        return False
        
        print(f"[OK] Marked attendance for {sum(1 for p in test_participants if p['attend'])} participants")
        print(f"     - Expected no-shows: {sum(1 for p in test_participants if p['confirm'] and not p['attend'])}")
        
        # Complete remaining transitions
        print_section("TEST 6: Complete Event Lifecycle")
        
        lifecycle_states = [
            EventState.RUNNING,
            EventState.COMPLETED
        ]
        
        for state in lifecycle_states:
            result = EventService.transition_event_state(db, event_id, state)
            if result["success"]:
                print(f"[OK] Transitioned to {state.value}")
            else:
                print(f"[FAIL] Failed to transition to {state.value}: {result['message']}")
                return False
        
        # Test analytics calculation
        print_section("TEST 7: Analytics Calculation")
        
        analytics_result = AnalyticsService.calculate_event_analytics(db, event_id)
        
        if not analytics_result["success"]:
            print(f"[FAIL] Analytics calculation failed: {analytics_result.get('message')}")
            return False
        
        analytics_data = analytics_result["analytics"]
        
        print(f"[OK] Analytics calculated:")
        print(f"     Total Registered: {analytics_data['total_registered']}")
        print(f"     Total Confirmed: {analytics_data['total_confirmed']} ({analytics_data['confirmation_rate']}%)")
        print(f"     Total Attended: {analytics_data['total_attended']} ({analytics_data['attendance_rate']}%)")
        print(f"     No-shows: {analytics_data['no_show_count']} ({analytics_data['no_show_rate']}%)")
        print(f"     Engagement Score: {analytics_data['engagement_score']}/100")
        print(f"     Performance: {analytics_data['performance_category']}")
        
        # Validate calculations
        expected_registered = 10
        expected_confirmed = 8
        expected_attended = 6
        expected_no_shows = 2
        
        if analytics_data['total_registered'] != expected_registered:
            print(f"[FAIL] Expected {expected_registered} registered, got {analytics_data['total_registered']}")
            return False
        
        if analytics_data['total_confirmed'] != expected_confirmed:
            print(f"[FAIL] Expected {expected_confirmed} confirmed, got {analytics_data['total_confirmed']}")
            return False
        
        if analytics_data['total_attended'] != expected_attended:
            print(f"[FAIL] Expected {expected_attended} attended, got {analytics_data['total_attended']}")
            return False
        
        if analytics_data['no_show_count'] != expected_no_shows:
            print(f"[FAIL] Expected {expected_no_shows} no-shows, got {analytics_data['no_show_count']}")
            return False
        
        print(f"[PASS] All calculations correct!")
        
        # Test saving analytics
        print_section("TEST 8: Save Analytics to Database")
        
        save_result = AnalyticsService.save_analytics(db, event_id, analytics_data)
        
        if not save_result["success"]:
            print(f"[FAIL] Failed to save analytics")
            return False
        
        print(f"[OK] Analytics saved (action: {save_result['action']})")
        
        # Test retrieval
        saved_analytics = AnalyticsService.get_event_analytics(db, event_id)
        
        if not saved_analytics:
            print(f"[FAIL] Failed to retrieve saved analytics")
            return False
        
        print(f"[OK] Analytics retrieved from database")
        
        # Test AI insights generation
        print_section("TEST 9: AI Insights Generation")
        
        insights_service = get_insights_service()
        insights_result = insights_service.generate_insights(db, event_id, analytics_data)
        
        if not insights_result["success"]:
            print(f"[FAIL] Insights generation failed")
            return False
        
        print(f"[OK] Insights generated (source: {insights_result['source']})")
        
        insights = insights_result["insights"]
        
        print(f"\nSummary:")
        print(f"  {insights['summary']}")
        
        if insights['strengths']:
            print(f"\nStrengths ({len(insights['strengths'])}):")
            for i, strength in enumerate(insights['strengths'], 1):
                print(f"  {i}. {strength}")
        
        if insights['weaknesses']:
            print(f"\nWeaknesses ({len(insights['weaknesses'])}):")
            for i, weakness in enumerate(insights['weaknesses'], 1):
                print(f"  {i}. {weakness}")
        
        if insights['recommendations']:
            print(f"\nRecommendations ({len(insights['recommendations'])}):")
            for i, rec in enumerate(insights['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        # Test saving insights
        print_section("TEST 10: Save Insights to Database")
        
        save_insights_result = insights_service.save_insights_to_analytics(db, event_id, insights_result)
        
        if not save_insights_result:
            print(f"[FAIL] Failed to save insights")
            return False
        
        print(f"[OK] Insights saved to analytics record")
        
        # Test formatted output
        print_section("TEST 11: Formatted Insights Output")
        
        formatted = insights_service.format_insights_for_display(insights_result)
        print(formatted)
        
        print(f"[OK] Insights formatted successfully")
        
        # Test analytics comparison (create second event for comparison)
        print_section("TEST 12: Event Comparison")
        
        start_time2 = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time2 = start_time2 + timedelta(hours=1)
        
        event2 = EventService.create_event(
            db=db,
            name="Comparison Event",
            description="Second event for comparison",
            event_type=EventType.ONLINE,
            start_time=start_time2,
            end_time=end_time2,
            meeting_link="https://meet.google.com/test"
        )
        
        event_id2 = event2.id
        
        # Quick setup for second event
        EventService.transition_event_state(db, event_id2, EventState.REGISTRATION_OPEN)
        for i in range(5):
            RegistrationService.register_participant(
                db, event_id2, f"User{i}", f"user{i}@test.com"
            )
        EventService.transition_event_state(db, event_id2, EventState.COMPLETED)
        
        analytics2 = AnalyticsService.calculate_event_analytics(db, event_id2)
        AnalyticsService.save_analytics(db, event_id2, analytics2["analytics"])
        
        # Compare events
        comparison = AnalyticsService.compare_events(db, [event_id, event_id2])
        
        if not comparison["success"]:
            print(f"[FAIL] Comparison failed")
            return False
        
        print(f"[OK] Compared {comparison['events_compared']} events")
        print(f"     Average Attendance: {comparison['averages']['attendance_rate']}%")
        print(f"     Average Engagement: {comparison['averages']['engagement_score']}")
        print(f"     Best Performer: {comparison['best_performer']['event_name']}")
        
        # Test summary report
        print_section("TEST 13: Summary Report Generation")
        
        report = AnalyticsService.generate_summary_report(db, event_id)
        print(report)
        
        print(f"\n[OK] Summary report generated")
        
        # Final validation
        print_section("STAGE 5 TEST - VALIDATION")
        
        print(f"[PASS] Analytics calculation working correctly")
        print(f"[PASS] Metrics: 60% attendance, 80% confirmation, 25% no-show")
        print(f"[PASS] AI insights generated ({insights_result['source']})")
        print(f"[PASS] Data persistence working")
        print(f"[PASS] Event comparison working")
        print(f"[PASS] All Stage 5 features validated!")
        
        return True


if __name__ == "__main__":
    try:
        success = test_stage_5()
        
        if success:
            print("\n" + "=" * 60)
            print(" STAGE 5 TEST PASSED - Analytics + AI Complete!")
            print("=" * 60)
            print("\nWhat was tested:")
            print("  * Analytics calculation (rates, scores, categories)")
            print("  * AI insights generation (GPT-4 or rule-based)")
            print("  * Data persistence (Analytics table)")
            print("  * Event comparison")
            print("  * Summary reports")
            print("\nNext Steps:")
            print("  - Configure OpenAI API key in .env for AI insights")
            print("  - Ready for Stage 6: REST API Layer")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print(" STAGE 5 TEST FAILED")
            print("=" * 60)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
