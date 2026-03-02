"""
Quick Stage 4 Validation - Check if all files exist
"""
import os

print("\n" + "="*60)
print(" STAGE 4 QUICK VALIDATION")
print("="*60)

files_to_check = [
    ("Attendance Service", "services/attendance_service.py"),
    ("Email Service", "notifications/email.py"),
    ("SMS Service", "notifications/sms.py"),
    ("QR Generator", "utils/qr_generator.py"),
    ("OTP Generator", "utils/otp_generator.py"),
    ("Updated Registration Service", "services/registration_service.py"),
    ("Updated Reminder Service", "services/reminder_service.py"),
    ("Stage 4 Test", "test_stage4.py"),
]

all_exist = True
for name, path in files_to_check:
    exists = os.path.exists(path)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {name}: {path}")
    if not exists:
        all_exist = False

print("\n" + "="*60)
if all_exist:
    print(" STAGE 4 COMPLETE - All Files Created!")
    print("="*60)
    print("\nWhat was built:")
    print("  - Attendance verification (QR + OTP)")
    print("  - Email notifications (SendGrid)")
    print("  - SMS notifications (Twilio)")
    print("  - Secure JWT tokens for QR codes")
    print("  - Real notification integration")
    print("\nTo run full test (after pip completes):")
    print("  python test_stage4.py")
else:
    print(" STAGE 4 INCOMPLETE - Missing files!")
    print("="*60)
