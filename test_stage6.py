"""
Stage 6 Test - REST API Layer
Tests: All FastAPI endpoints for events, registrations, attendance, analytics
"""
import sys
import requests
import time
from datetime import datetime, timedelta, timezone

# Base URL for API
BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def test_stage_6():
    """Test Stage 6: REST API Layer"""
    
    print("\n" + "=" * 60)
    print(" STAGE 6 TEST: REST API Layer")
    print("=" * 60)
    
    # Check if server is running
    print_section("TEST 1: Server Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Server is running: {response.json()}")
        else:
            print(f"[FAIL] Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Server is not running!")
        print("Please start the server with: python api/main.py")
        print("Or in another terminal: uvicorn api.main:app --reload")
        return False
    
    # Test root endpoint
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        print(f"[OK] Root endpoint: {response.json()}")
    else:
        print(f"[FAIL] Root endpoint failed")
        return False
    
    # Test event creation
    print_section("TEST 2: Create Event")
    
    start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()
    
    event_data = {
        "name": "Stage 6 API Test Event",
        "description": "Testing all API endpoints for event management and analytics",
        "event_type": "OFFLINE",
        "start_time": start_time,
        "end_time": end_time,
        "venue": "API Test Hall",
        "max_participants": 50
    }
    
    response = requests.post(f"{BASE_URL}/api/events/", json=event_data)
    if response.status_code == 201:
        event = response.json()["event"]
        event_id = event["id"]
        print(f"[OK] Event created: ID={event_id}, Name={event['name']}")
        print(f"     State: {event['state']}, Type: {event['event_type']}")
    else:
        print(f"[FAIL] Failed to create event: {response.text}")
        return False
    
    # Test list events
    print_section("TEST 3: List Events")
    
    response = requests.get(f"{BASE_URL}/api/events/")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Listed {data['count']} events")
        if data['count'] > 0:
            print(f"     First event: {data['events'][0]['name']}")
    else:
        print(f"[FAIL] Failed to list events: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test get single event
    print_section("TEST 4: Get Event Details")
    
    response = requests.get(f"{BASE_URL}/api/events/{event_id}")
    if response.status_code == 200:
        event = response.json()["event"]
        print(f"[OK] Retrieved event: {event['name']}")
        print(f"     Registered: {event['stats']['total_registered']}, Confirmed: {event['stats']['total_confirmed']}")
        print(f"     State: {event['state']}, Allowed transitions: {len(event['allowed_transitions'])}")
    else:
        print(f"[FAIL] Failed to get event details")
        return False
    
    # Test event state transition
    print_section("TEST 5: Transition Event State")
    
    transition_data = {
        "new_state": "REGISTRATION_OPEN",
        "reason": "Opening registration via API test",
        "triggered_by": "test_suite"
    }
    
    response = requests.post(f"{BASE_URL}/api/events/{event_id}/transition", json=transition_data)
    if response.status_code == 200:
        transition = response.json()["transition"]
        print(f"[OK] Transitioned: {transition['old_state']} -> {transition['new_state']}")
    else:
        print(f"[FAIL] Failed to transition event: {response.text}")
        return False
    
    # Test participant registration
    print_section("TEST 6: Register Participants")
    
    participants_data = [
        {"name": "Alice Johnson", "email": "alice@api-test.com"},
        {"name": "Bob Smith", "email": "bob@api-test.com"},
        {"name": "Charlie Brown", "email": "charlie@api-test.com"}
    ]
    
    participant_ids = []
    
    for p_data in participants_data:
        registration_data = {
            "event_id": event_id,
            **p_data
        }
        
        response = requests.post(f"{BASE_URL}/api/registrations/register", json=registration_data)
        if response.status_code == 201:
            participant = response.json()["participant"]
            participant_ids.append(participant["id"])
            print(f"[OK] Registered: {participant['name']} (ID={participant['id']})")
        else:
            print(f"[FAIL] Failed to register {p_data['name']}: {response.text}")
            return False
    
    print(f"[OK] Registered {len(participant_ids)} participants")
    
    # Test get participant
    print_section("TEST 7: Get Participant Details")
    
    response = requests.get(f"{BASE_URL}/api/registrations/{participant_ids[0]}")
    if response.status_code == 200:
        participant = response.json()["participant"]
        print(f"[OK] Retrieved participant: {participant['name']}")
        print(f"     Status: {participant['status']}, Confirmed: {participant['is_confirmed']}")
    else:
        print(f"[FAIL] Failed to get participant: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test participant confirmation
    print_section("TEST 8: Confirm Participants")
    
    for p_id in participant_ids:
        confirm_data = {"participant_id": p_id}
        response = requests.post(f"{BASE_URL}/api/registrations/confirm", json=confirm_data)
        if response.status_code == 200:
            print(f"[OK] Confirmed participant {p_id}")
        else:
            print(f"[FAIL] Failed to confirm participant {p_id}")
            return False
    
    # Transition to attendance open
    print_section("TEST 9: Open Attendance")
    
    for state in ["SCHEDULED", "ATTENDANCE_OPEN"]:
        transition_data = {
            "new_state": state,
            "triggered_by": "test_suite"
        }
        response = requests.post(f"{BASE_URL}/api/events/{event_id}/transition", json=transition_data)
        if response.status_code == 200:
            print(f"[OK] Transitioned to {state}")
        else:
            print(f"[FAIL] Failed to transition to {state}")
            return False
    
    # Test QR code generation
    print_section("TEST 10: Generate QR Codes")
    
    qr_tokens = []
    
    for p_id in participant_ids[:2]:  # Generate QR for first 2 participants
        qr_data = {"participant_id": p_id}
        response = requests.post(f"{BASE_URL}/api/attendance/qr/generate", json=qr_data)
        if response.status_code == 200:
            qr_code = response.json()["qr_code"]
            qr_tokens.append(qr_code["token"])
            print(f"[OK] Generated QR for participant {p_id}")
            print(f"     Token length: {len(qr_code['token'])} chars")
        else:
            print(f"[FAIL] Failed to generate QR for participant {p_id}: {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    
    # Test QR check-in
    print_section("TEST 11: QR Code Check-In")
    
    for i, token in enumerate(qr_tokens):
        checkin_data = {
            "qr_token": token,
            "check_in_ip": "127.0.0.1",
            "check_in_device": "API Test Client"
        }
        response = requests.post(f"{BASE_URL}/api/attendance/qr/validate", json=checkin_data)
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] QR check-in successful for {result['participant']['name']}")
            print(f"     Status: {result['participant']['status']}")
        else:
            print(f"[FAIL] QR check-in failed: {response.text}")
            return False
    
    # Test OTP generation and check-in
    print_section("TEST 12: OTP Check-In")
    
    otp_participant_id = participant_ids[2]  # Third participant uses OTP
    
    # Generate OTP
    otp_data = {"participant_id": otp_participant_id}
    response = requests.post(f"{BASE_URL}/api/attendance/otp/generate", json=otp_data)
    if response.status_code == 200:
        otp_result = response.json()
        otp_code = otp_result["otp"]
        print(f"[OK] Generated OTP: {otp_code}")
        print(f"     SMS sent: {otp_result['sms_sent']}")
    else:
        print(f"[FAIL] Failed to generate OTP")
        return False
    
    # Validate OTP
    validate_otp_data = {
        "participant_id": otp_participant_id,
        "otp": otp_code
    }
    response = requests.post(f"{BASE_URL}/api/attendance/otp/validate", json=validate_otp_data)
    if response.status_code == 200:
        result = response.json()
        print(f"[OK] OTP check-in successful for {result['participant']['name']}")
    else:
        print(f"[FAIL] OTP check-in failed: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test attendance retrieval
    print_section("TEST 13: Get Attendance Records")
    
    response = requests.get(f"{BASE_URL}/api/attendance/event/{event_id}")
    if response.status_code == 200:
        attendance_data = response.json()
        print(f"[OK] Retrieved {attendance_data['count']} attendance records")
        for record in attendance_data['attendance']:
            print(f"     - {record['participant_name']}: {record['check_in_method']}")
    else:
        print(f"[FAIL] Failed to get attendance records: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test attendance stats
    print_section("TEST 14: Get Attendance Stats")
    
    response = requests.get(f"{BASE_URL}/api/attendance/event/{event_id}/stats")
    if response.status_code == 200:
        stats = response.json()["stats"]
        print(f"[OK] Attendance stats:")
        print(f"     Total registered: {stats['total_registered']}")
        print(f"     Total confirmed: {stats['total_confirmed']}")
        print(f"     Total attended: {stats['total_attended']}")
        print(f"     Attendance rate: {stats['attendance_rate']}%")
        print(f"     No-show rate: {stats['no_show_rate']}%")
    else:
        print(f"[FAIL] Failed to get attendance stats")
        return False
    
    # Complete event
    print_section("TEST 15: Complete Event")
    
    for state in ["RUNNING", "COMPLETED"]:
        transition_data = {
            "new_state": state,
            "triggered_by": "test_suite"
        }
        response = requests.post(f"{BASE_URL}/api/events/{event_id}/transition", json=transition_data)
        if response.status_code == 200:
            print(f"[OK] Transitioned to {state}")
        else:
            print(f"[FAIL] Failed to transition to {state}")
            return False
    
    # Test analytics calculation
    print_section("TEST 16: Calculate Analytics")
    
    analytics_data = {"event_id": event_id}
    response = requests.post(f"{BASE_URL}/api/analytics/calculate", json=analytics_data)
    if response.status_code == 200:
        analytics = response.json()["analytics"]
        print(f"[OK] Analytics calculated:")
        print(f"     Total registered: {analytics['total_registered']}")
        print(f"     Total attended: {analytics['total_attended']}")
        print(f"     Attendance rate: {analytics['attendance_rate']}%")
        print(f"     Engagement score: {analytics['engagement_score']}/100")
        print(f"     Performance: {analytics['performance_category']}")
    else:
        print(f"[FAIL] Failed to calculate analytics")
        return False
    
    # Test get analytics
    print_section("TEST 17: Get Saved Analytics")
    
    response = requests.get(f"{BASE_URL}/api/analytics/event/{event_id}")
    if response.status_code == 200:
        analytics = response.json()["analytics"]
        print(f"[OK] Retrieved saved analytics")
        print(f"     Engagement score: {analytics['engagement_score']}")
    else:
        print(f"[FAIL] Failed to get analytics")
        return False
    
    # Test insights generation
    print_section("TEST 18: Generate AI Insights")
    
    insights_data = {"event_id": event_id}
    response = requests.post(f"{BASE_URL}/api/analytics/insights/generate", json=insights_data)
    if response.status_code == 200:
        result = response.json()
        insights = result["insights"]
        print(f"[OK] Insights generated (source: {result['source']})")
        print(f"\n     Summary: {insights['summary']}")
        print(f"\n     Strengths: {len(insights['strengths'])}")
        for strength in insights['strengths'][:2]:
            print(f"       - {strength}")
        print(f"\n     Recommendations: {len(insights['recommendations'])}")
        for rec in insights['recommendations'][:2]:
            print(f"       - {rec}")
    else:
        print(f"[FAIL] Failed to generate insights: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test get insights
    print_section("TEST 19: Get Saved Insights")
    
    response = requests.get(f"{BASE_URL}/api/analytics/insights/{event_id}")
    if response.status_code == 200:
        insights = response.json()["insights"]
        print(f"[OK] Retrieved saved insights")
        if isinstance(insights, dict):
            print(f"     Recommendations count: {len(insights.get('recommendations', []))}")
        else:
            print(f"     Insights data type: {type(insights)}")
    else:
        print(f"[FAIL] Failed to get insights: {response.status_code}")
        print(f"       Response: {response.text}")
        return False
    
    # Test summary report
    print_section("TEST 20: Generate Summary Report")
    
    response = requests.get(f"{BASE_URL}/api/analytics/report/{event_id}")
    if response.status_code == 200:
        report = response.json()["report"]
        print(f"[OK] Generated summary report:")
        print("\n" + report[:500] + "...")
    else:
        print(f"[FAIL] Failed to generate report")
        return False
    
    # Test event participants list
    print_section("TEST 21: Get Event Participants")
    
    response = requests.get(f"{BASE_URL}/api/events/{event_id}/participants")
    if response.status_code == 200:
        participants = response.json()
        print(f"[OK] Retrieved {participants['count']} participants")
    else:
        print(f"[FAIL] Failed to get participants")
        return False
    
    # Test dashboard stats
    print_section("TEST 22: Dashboard Statistics")
    
    response = requests.get(f"{BASE_URL}/api/analytics/dashboard?limit=5")
    if response.status_code == 200:
        dashboard = response.json()["dashboard"]
        print(f"[OK] Dashboard stats:")
        print(f"     Total events: {dashboard['total_events']}")
        print(f"     Total participants: {dashboard['total_participants']}")
        print(f"     Overall attendance: {dashboard['overall_attendance_rate']}%")
        print(f"     Average engagement: {dashboard['average_engagement']}")
    else:
        print(f"[FAIL] Failed to get dashboard stats")
        return False
    
    # Final validation
    print_section("STAGE 6 TEST - VALIDATION")
    
    print(f"[PASS] Event management API working")
    print(f"[PASS] Registration API working")
    print(f"[PASS] Attendance API (QR + OTP) working")
    print(f"[PASS] Analytics API working")
    print(f"[PASS] AI Insights API working")
    print(f"[PASS] All 22 API endpoint tests passed!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_stage_6()
        
        if success:
            print("\n" + "=" * 60)
            print(" STAGE 6 TEST PASSED - REST API Complete!")
            print("=" * 60)
            print("\nWhat was tested:")
            print("  * Event CRUD operations (create, list, get)")
            print("  * Event state transitions via API")
            print("  * Participant registration and confirmation")
            print("  * QR code generation and validation")
            print("  * OTP generation and validation")
            print("  * Attendance tracking and stats")
            print("  * Analytics calculation and retrieval")
            print("  * AI insights generation")
            print("  * Summary reports")
            print("  * Dashboard statistics")
            print("\nNext Steps:")
            print("  - API is ready for frontend integration")
            print("  - Access API docs at: http://localhost:8000/docs")
            print("  - Ready for Stage 7: UI Dashboard")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print(" STAGE 6 TEST FAILED")
            print("=" * 60)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
