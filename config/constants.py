"""
Application constants including state definitions and thresholds
"""
from enum import Enum


class EventState(str, Enum):
    """Event lifecycle states - FSM definition"""
    CREATED = "CREATED"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    SCHEDULED = "SCHEDULED"
    ATTENDANCE_OPEN = "ATTENDANCE_OPEN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ANALYZING = "ANALYZING"
    REPORT_GENERATED = "REPORT_GENERATED"
    CANCELLED = "CANCELLED"


class ParticipantStatus(str, Enum):
    """Participant registration status"""
    REGISTERED = "REGISTERED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    ATTENDED = "ATTENDED"
    NO_SHOW = "NO_SHOW"


class EventType(str, Enum):
    """Event type - determines attendance mechanism"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HYBRID = "HYBRID"


class ReminderType(str, Enum):
    """Types of reminders based on engagement"""
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class AttendanceMethod(str, Enum):
    """Attendance verification methods"""
    QR_CODE = "QR_CODE"
    OTP = "OTP"
    MANUAL = "MANUAL"


# Timing Constants (in hours before event)
REMINDER_WINDOWS = {
    "FIRST_REMINDER": 168,      # 7 days before
    "SECOND_REMINDER": 48,      # 2 days before
    "FINAL_REMINDER": 24,       # 1 day before
    "LAST_CALL": 2,             # 2 hours before
}

# Confirmation Rate Thresholds (percentage)
CONFIRMATION_THRESHOLDS = {
    "LOW": 30,          # Below 30% = aggressive reminders
    "MODERATE": 70,     # 30-70% = moderate reminders
    "HIGH": 70,         # Above 70% = light reminders
}

# Attendance Window (minutes before/after event start)
ATTENDANCE_WINDOW = {
    "BEFORE_START": 30,     # Can check-in 30 min before
    "AFTER_START": 15,      # Can check-in 15 min after start
}

# Analytics Thresholds
ANALYTICS_THRESHOLDS = {
    "GOOD_ATTENDANCE_RATE": 75,      # >75% is good
    "POOR_ATTENDANCE_RATE": 50,       # <50% is poor
    "HIGH_ENGAGEMENT_SCORE": 80,      # >80 is high engagement
}

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 15

# State Transition Timeout (hours)
STATE_TIMEOUTS = {
    "REGISTRATION_OPEN_TO_SCHEDULED": 24,  # Auto-close registration 24h before event
    "SCHEDULED_TO_ATTENDANCE_OPEN": 0.5,   # Open attendance 30min before start
    "RUNNING_TO_COMPLETED": 2,             # Mark complete 2h after scheduled end
}
