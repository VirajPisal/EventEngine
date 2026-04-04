"""
Transition Rules - Guard functions for state transitions
Defines business logic conditions that must be met before state transitions
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from models.event import Event
from config.constants import EventState, CONFIRMATION_THRESHOLDS
from services.registration_service import RegistrationService


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (assume UTC if naive)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TransitionRules:
    """Guard functions for state transitions"""
    
    @staticmethod
    def can_open_registration(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if registration can be opened
        
        Rules:
        - Event must be in CREATED state
        - Event must have valid start/end times
        - Start time must be in the future
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.CREATED:
            return False, f"Registration can only be opened from CREATED state (current: {event.state.value})"
        
        if not event.start_time or not event.end_time:
            return False, "Event must have valid start and end times"
        
        start_time = ensure_timezone_aware(event.start_time)
        end_time = ensure_timezone_aware(event.end_time)
        now = datetime.now(timezone.utc)
        
        if start_time <= now:
            return False, "Event start time must be in the future"
        
        if start_time >= end_time:
            return False, "Event start time must be before end time"
        
        return True, "Registration can be opened"
    
    @staticmethod
    def can_schedule(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if event can be scheduled (close registration)
        
        Rules:
        - Event must be in REGISTRATION_OPEN state
        - Should have minimum participants (configurable)
        - Optional: minimum confirmation rate threshold
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.REGISTRATION_OPEN:
            return False, f"Can only schedule from REGISTRATION_OPEN state (current: {event.state.value})"
        
        # Get participant count
        confirmation_rate = RegistrationService.get_confirmation_rate(db, event.id)
        stats = RegistrationService.get_participant_stats(db, event.id)
        
        # Check if we have any participants
        if stats["total_registered"] == 0:
            return False, "Cannot schedule event with zero participants"
        
        # Optional: Check minimum confirmation rate
        # This is a soft rule - can be overridden manually
        min_rate = CONFIRMATION_THRESHOLDS["LOW"]  # 30%
        if confirmation_rate < min_rate:
            # Allow but warn
            return True, f"Warning: Low confirmation rate ({confirmation_rate:.1f}%), but scheduling allowed"
        
        return True, f"Event ready to schedule ({stats['total_registered']} registered, {confirmation_rate:.1f}% confirmed)"
    
    @staticmethod
    def can_open_attendance(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if attendance can be opened
        
        Rules:
        - Event must be in SCHEDULED state
        - Must be within attendance window (before event start)
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.SCHEDULED:
            return False, f"Attendance can only be opened from SCHEDULED state (current: {event.state.value})"
        
        now = datetime.now(timezone.utc)
        start_time = ensure_timezone_aware(event.start_time)
        end_time = ensure_timezone_aware(event.end_time)
        
        # Check if we're within the attendance window
        # Allow opening 30 minutes before event start
        attendance_open_time = start_time - timedelta(minutes=30)
        
        if now < attendance_open_time:
            minutes_until = (attendance_open_time - now).total_seconds() / 60
            return False, f"Too early to open attendance (opens {int(minutes_until)} minutes before start)"
        
        # Don't allow if event already passed
        if now > end_time:
            return False, "Event has already ended"
        
        return True, "Attendance can be opened"
    
    @staticmethod
    def can_start_running(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if event can start running
        
        Rules:
        - Event must be in ATTENDANCE_OPEN or SCHEDULED state
        - Current time must be at or after start time
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state not in [EventState.ATTENDANCE_OPEN, EventState.SCHEDULED]:
            return False, f"Event can only start from ATTENDANCE_OPEN or SCHEDULED state (current: {event.state.value})"
        
        now = datetime.now(timezone.utc)
        start_time = ensure_timezone_aware(event.start_time)
        
        if now < start_time:
            minutes_until = (start_time - now).total_seconds() / 60
            return False, f"Event hasn't started yet ({int(minutes_until)} minutes remaining)"
        
        return True, "Event can start running"
    
    @staticmethod
    def can_complete(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if event can be marked as completed
        
        Rules:
        - Event must be in RUNNING state
        - Current time should be at or after end time
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.RUNNING:
            return False, f"Event can only complete from RUNNING state (current: {event.state.value})"
        
        now = datetime.now(timezone.utc)
        end_time = ensure_timezone_aware(event.end_time)
        
        # Allow completion even if end time hasn't passed (manual completion)
        # But warn if it's too early
        if now < end_time:
            return True, "Event can be completed (ending early)"
        
        return True, "Event can be completed"
    
    @staticmethod
    def can_analyze(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if analytics can be generated
        
        Rules:
        - Event must be in COMPLETED state
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.COMPLETED:
            return False, f"Analytics can only be generated from COMPLETED state (current: {event.state.value})"
        
        return True, "Analytics can be generated"
    
    @staticmethod
    def can_generate_report(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if final report can be generated
        
        Rules:
        - Event must be in ANALYZING state
        - Analytics must exist
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state != EventState.ANALYZING:
            return False, f"Report can only be generated from ANALYZING state (current: {event.state.value})"
        
        if not event.analytics:
            return False, "Analytics must be generated before report"
        
        return True, "Report can be generated"
    
    @staticmethod
    def can_cancel(db: Session, event: Event) -> Tuple[bool, str]:
        """
        Check if event can be cancelled
        
        Rules:
        - Event cannot already be cancelled or completed
        
        Returns:
            (allowed: bool, reason: str)
        """
        if event.state == EventState.CANCELLED:
            return False, "Event is already cancelled"
        
        if event.state == EventState.REPORT_GENERATED:
            return False, "Cannot cancel event that has completed and generated report"
        
        return True, "Event can be cancelled"
    
    @staticmethod
    def evaluate_transition(
        db: Session,
        event: Event,
        target_state: EventState
    ) -> Tuple[bool, str]:
        """
        Evaluate if a transition to target state is allowed based on business rules
        
        Args:
            db: Database session
            event: Event instance
            target_state: Desired state
        
        Returns:
            (allowed: bool, reason: str)
        """
        # Map states to their guard functions
        guards = {
            EventState.REGISTRATION_OPEN: TransitionRules.can_open_registration,
            EventState.SCHEDULED: TransitionRules.can_schedule,
            EventState.ATTENDANCE_OPEN: TransitionRules.can_open_attendance,
            EventState.RUNNING: TransitionRules.can_start_running,
            EventState.COMPLETED: TransitionRules.can_complete,
            EventState.ANALYZING: TransitionRules.can_analyze,
            EventState.REPORT_GENERATED: TransitionRules.can_generate_report,
            EventState.CANCELLED: TransitionRules.can_cancel,
        }
        
        guard_func = guards.get(target_state)
        
        if not guard_func:
            return True, "No specific rules for this transition"
        
        return guard_func(db, event)


def check_auto_transition_conditions(db: Session, event: Event) -> Dict[str, any]:
    """
    Check if event should auto-transition based on time/conditions
    Used by the agent to determine next actions
    
    Args:
        db: Database session
        event: Event instance
    
    Returns:
        Dictionary with:
        - should_transition: bool
        - target_state: EventState or None
        - reason: str
    """
    now = datetime.now(timezone.utc)
    start_time = ensure_timezone_aware(event.start_time)
    end_time = ensure_timezone_aware(event.end_time)
    
    # CREATED → REGISTRATION_OPEN (Immediate or 1 minute after creation)
    if event.state == EventState.CREATED:
        # Only auto-open if event was created more than 2 minutes ago (gives organizer time to review)
        created_at = ensure_timezone_aware(event.created_at)
        if (now - created_at).total_seconds() > 120:
            if event.start_time and event.end_time:
                return {
                    "should_transition": True,
                    "target_state": EventState.REGISTRATION_OPEN,
                    "reason": "Event review period complete, opening registration"
                }

    # REGISTRATION_OPEN → SCHEDULED (24 hours before start time)
    elif event.state == EventState.REGISTRATION_OPEN:
        scheduling_deadline = start_time - timedelta(hours=24)
        if now >= scheduling_deadline:
            return {
                "should_transition": True,
                "target_state": EventState.SCHEDULED,
                "reason": "Registration closed (24-hour scheduling deadline reached)"
            }

    # SCHEDULED → ATTENDANCE_OPEN (30 min before start)
    elif event.state == EventState.SCHEDULED:
        attendance_open_time = start_time - timedelta(minutes=30)
        if now >= attendance_open_time:
            return {
                "should_transition": True,
                "target_state": EventState.ATTENDANCE_OPEN,
                "reason": "Attendance window opened (30 minutes before start)"
            }
    
    # ATTENDANCE_OPEN → RUNNING (at start time)
    elif event.state == EventState.ATTENDANCE_OPEN:
        if now >= start_time:
            return {
                "should_transition": True,
                "target_state": EventState.RUNNING,
                "reason": "Event start time reached"
            }
    
    # RUNNING → COMPLETED (after end time)
    elif event.state == EventState.RUNNING:
        # Give 15 minutes grace period after scheduled end
        completion_time = end_time + timedelta(minutes=15)
        if now >= completion_time:
            return {
                "should_transition": True,
                "target_state": EventState.COMPLETED,
                "reason": "Event end time reached"
            }
    
    # COMPLETED → ANALYZING (immediately)
    elif event.state == EventState.COMPLETED:
        return {
            "should_transition": True,
            "target_state": EventState.ANALYZING,
            "reason": "Event completed, ready for analytics"
        }

    # ANALYZING → REPORT_GENERATED (after analytics are processed)
    elif event.state == EventState.ANALYZING:
        if event.analytics:
            return {
                "should_transition": True,
                "target_state": EventState.REPORT_GENERATED,
                "reason": "Analytics processing complete"
            }
    
    return {
        "should_transition": False,
        "target_state": None,
        "reason": "No auto-transition conditions met"
    }
