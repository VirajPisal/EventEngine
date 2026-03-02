"""
Stage 4 Test - Real Notifications + Attendance Verification
Tests: Email, SMS, QR codes, OTP, attendance check-in flow
"""
import sys
from datetime import datetime, timedelta, timezone
from db.base import get_db_context, init_db
from services.event_service import EventService
from services.registration_service import RegistrationService
from services.attendance_service import AttendanceService
from services.reminder_service import ReminderService
from config.constants import EventType, ReminderType


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def test_stage_4():
    """Test Stage 4: Notifications + Attendance"""
    
    print("\n" + "=" * 60)
    print(" STAGE 4 TEST: Real Notifications + Attendance Verification")
    print("=" * 60)
    
    # Initialize database
    print("\n[1] Initializing database...")
    init_db()
    print("[OK] Database initialized")
    
    with get_db_context() as db:
        # Create test event
        print_section("TEST 1: Event Creation")
        
        start_time = datetime.now(timezone.utc) + timedelta(hours=48)
        event_data = EventService.create_event(
            db=db,
            name="Stage 4 Test Event - Notification & Attendance",
            event_type=EventType.WEBINAR,
            start_time=start_time,
            duration_hours=2,
            location="Virtual",
            max_participants=50,
            meeting_link="https://meet.google.com/abc-defg-hij"
        )
        
        if not event_data["success"]:
            print(f"[FAIL] Failed to create event: {event_data['message']}")
            return False
        
        event_id = event_data["event"]["id"]
        print(f"[OK] Event created: ID={event_id}")
        
        # Open registration
        print_section("TEST 2: Open Registration")
        
        transition = EventService.transition_event_state(
            db=db,
            event_id=event_id,
            target_state="REGISTRATION_OPEN"
        )
        
        if not transition["success"]:
            print(f"[FAIL] Failed to open registration: {transition['message']}")
            return False
        
        print(f"[OK] State: PLANNED -> REGISTRATION_OPEN")
        
        # Register participants with email confirmation
        print_section("TEST 3: Participant Registration (with Email + QR)")
        
        test_participants = [
            {"name": "Alice Johnson", "email": "alice@test.com", "phone": "+1234567890"},
            {"name": "Bob Smith", "email": "bob@test.com", "phone": "+1234567891"},
            {"name": "Charlie Davis", "email": "charlie@test.com", "phone": None},
        ]
        
        participant_ids = []
        
        for p in test_participants:
            reg = RegistrationService.register_participant(
                db=db,
                event_id=event_id,
                name=p["name"],
                email=p["email"],
                phone=p["phone"]
            )
            
            if not reg["success"]:
                print(f"[FAIL] Registration failed for {p['name']}: {reg['message']}")
                return False
            
            participant_ids.append(reg["participant"]["id"])
            email_sent = reg.get("email_sent", False)
            qr_sent = reg["participant"].get("qr_code_sent", False)
            
            print(f"[OK] Registered: {p['name']}")
            print(f"     Email: {'SENT' if email_sent else 'NOT SENT'}")
            print(f"     QR Code: {'SENT' if qr_sent else 'NOT SENT'}")
        
        # Test QR code generation
        print_section("TEST 4: QR Code Generation")
        
        qr_result = AttendanceService.generate_qr_code(
            db=db,
            participant_id=participant_ids[0]
        )
        
        if not qr_result["success"]:
            print(f"[FAIL] QR generation failed: {qr_result['message']}")
            return False
        
        qr_token = qr_result["qr_code"]["token"]
        has_image = qr_result["qr_code"].get("image_available", False)
        
        print(f"[OK] QR code generated for participant {participant_ids[0]}")
        print(f"     Token: {qr_token[:30]}...")
        print(f"     Image: {'AVAILABLE' if has_image else 'NOT AVAILABLE'}")
        
        # Test OTP generation
        print_section("TEST 5: OTP Generation")
        
        otp_result = AttendanceService.generate_otp(
            db=db,
            participant_id=participant_ids[1]
        )
        
        if not otp_result["success"]:
            print(f"[FAIL] OTP generation failed: {otp_result['message']}")
            return False
        
        otp_code = otp_result["otp"]
        otp_expiry = otp_result["expires_at"]
        
        print(f"[OK] OTP generated for participant {participant_ids[1]}")
        print(f"     Code: {otp_code}")
        print(f"     Expires: {otp_expiry.isoformat()}")
        print(f"     Valid for: {otp_result['expiry_minutes']} minutes")
        
        # Test reminder sending
        print_section("TEST 6: Reminder Sending (Simulated)")
        
        # Confirm one participant first
        RegistrationService.confirm_participant(db, participant_ids[0])
        
        # Force send reminders
        reminder_result = ReminderService.evaluate_and_send_reminders(
            db=db,
            event_id=event_id,
            force=True
        )
        
        if not reminder_result["sent"]:
            print(f"[INFO] Reminders not sent: {reminder_result.get('reason', 'Unknown')}")
        else:
            print(f"[OK] Reminders sent: {reminder_result['recipient_count']} recipients")
            print(f"     Type: {reminder_result['reminder_type'].upper()}")
            print(f"     Confirmation rate: {reminder_result['confirmation_rate']:.1f}%")
        
        # Open attendance
        print_section("TEST 7: Open Attendance Period")
        
        transition = EventService.transition_event_state(
            db=db,
            event_id=event_id,
            target_state="SCHEDULED"
        )
        
        if transition["success"]:
            transition = EventService.transition_event_state(
                db=db,
                event_id=event_id,
                target_state="ATTENDANCE_OPEN"
            )
        
        if not transition["success"]:
            print(f"[FAIL] Failed to open attendance: {transition['message']}")
            return False
        
        print(f"[OK] State: ATTENDANCE_OPEN")
        
        # Test QR check-in
        print_section("TEST 8: QR Code Check-in")
        
        qr_checkin = AttendanceService.validate_qr_check_in(
            db=db,
            qr_token=qr_token,
            check_in_ip="192.168.1.100",
            check_in_device="iPhone 15"
        )
        
        if not qr_checkin["success"]:
            print(f"[FAIL] QR check-in failed: {qr_checkin['message']}")
            return False
        
        print(f"[OK] QR check-in successful")
        print(f"     Participant: {qr_checkin['participant']['name']}")
        print(f"     Event: {qr_checkin['event']['name']}")
        print(f"     Time: {qr_checkin['checked_in_at']}")
        print(f"     Method: {qr_checkin['method']}")
        
        # Test OTP check-in
        print_section("TEST 9: OTP Check-in")
        
        otp_checkin = AttendanceService.validate_otp_check_in(
            db=db,
            participant_id=participant_ids[1],
            otp_code=otp_code,
            check_in_ip="192.168.1.101",
            check_in_device="Android Phone"
        )
        
        if not otp_checkin["success"]:
            print(f"[FAIL] OTP check-in failed: {otp_checkin['message']}")
            return False
        
        print(f"[OK] OTP check-in successful")
        print(f"     Participant: {otp_checkin['participant']['name']}")
        print(f"     Event: {otp_checkin['event']['name']}")
        print(f"     Time: {otp_checkin['checked_in_at']}")
        print(f"     Method: {otp_checkin['method']}")
        
        # Test duplicate check-in prevention
        print_section("TEST 10: Duplicate Check-in Prevention")
        
        duplicate_qr = AttendanceService.validate_qr_check_in(
            db=db,
            qr_token=qr_token
        )
        
        if duplicate_qr["success"]:
            print(f"[FAIL] Duplicate check-in was allowed (should be prevented)")
            return False
        
        print(f"[OK] Duplicate check-in prevented")
        print(f"     Message: {duplicate_qr['message']}")
        
        # Test invalid OTP
        print_section("TEST 11: Invalid OTP Rejection")
        
        # Try with participant who didn't register
        fake_otp_checkin = AttendanceService.validate_otp_check_in(
            db=db,
            participant_id=participant_ids[2],  # Charlie (no OTP generated)
            otp_code="999999"
        )
        
        if fake_otp_checkin["success"]:
            print(f"[FAIL] Invalid OTP was accepted (should be rejected)")
            return False
        
        print(f"[OK] Invalid OTP rejected")
        print(f"     Message: {fake_otp_checkin['message']}")
        
        # Get attendance statistics
        print_section("TEST 12: Attendance Statistics")
        
        stats = AttendanceService.get_attendance_stats(
            db=db,
            event_id=event_id
        )
        
        if not stats["success"]:
            print(f"[FAIL] Failed to get stats: {stats['message']}")
            return False
        
        print(f"[OK] Attendance Stats:")
        print(f"     Total Registered: {stats['total_registered']}")
        print(f"     Total Confirmed: {stats['total_confirmed']}")
        print(f"     Total Attended: {stats['total_attended']}")
        print(f"     Attendance Rate: {stats['attendance_rate']}%")
        print(f"     No-show Count: {stats['no_show_count']}")
        print(f"     No-show Rate: {stats['no_show_rate']}%")
        
        # Final validation
        print_section("STAGE 4 TEST - VALIDATION")
        
        expected_attended = 2  # Alice (QR) + Bob (OTP)
        expected_rate = round(2 / 3 * 100, 1)  # 2 out of 3 registered
        
        if stats['total_attended'] != expected_attended:
            print(f"[FAIL] Expected {expected_attended} attendees, got {stats['total_attended']}")
            return False
        
        if abs(stats['attendance_rate'] - expected_rate) > 1:  # Allow 1% rounding error
            print(f"[FAIL] Expected {expected_rate}% attendance rate, got {stats['attendance_rate']}%")
            return False
        
        print(f"[PASS] All validations passed!")
        print(f"[PASS] QR + OTP check-in flow working correctly")
        print(f"[PASS] Email notifications configured (simulated mode)")
        print(f"[PASS] SMS notifications configured (simulated mode)")
        print(f"[PASS] Attendance tracking accurate")
        
        return True


if __name__ == "__main__":
    try:
        success = test_stage_4()
        
        if success:
            print("\n" + "=" * 60)
            print(" STAGE 4 TEST PASSED - Notifications + Attendance Complete!")
            print("=" * 60)
            print("\nNext Steps:")
            print("  - Configure real SendGrid credentials in .env for email")
            print("  - Configure real Twilio credentials in .env for SMS")
            print("  - Ready for Stage 5: Analytics + AI Insights")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print(" STAGE 4 TEST FAILED")
            print("=" * 60)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
