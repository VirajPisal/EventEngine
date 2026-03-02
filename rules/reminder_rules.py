"""
Reminder Rules - Adaptive reminder strategy based on engagement
Determines reminder type and timing based on confirmation rate and event timeline
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum

from models.event import Event
from config.constants import ReminderType, CONFIRMATION_THRESHOLDS, REMINDER_WINDOWS


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (assume UTC if naive)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ReminderStrategy:
    """Determines which reminder strategy to use"""
    
    @staticmethod
    def determine_reminder_type(confirmation_rate: float) -> ReminderType:
        """
        Determine reminder intensity based on confirmation rate
        
        Args:
            confirmation_rate: Current confirmation rate (0-100)
        
        Returns:
            ReminderType (LIGHT, MODERATE, or AGGRESSIVE)
        """
        if confirmation_rate < CONFIRMATION_THRESHOLDS["LOW"]:  # < 30%
            return ReminderType.AGGRESSIVE
        elif confirmation_rate < CONFIRMATION_THRESHOLDS["MODERATE"]:  # 30-70%
            return ReminderType.MODERATE
        else:  # >= 70%
            return ReminderType.LIGHT
    
    @staticmethod
    def should_send_reminder(
        event: Event,
        confirmation_rate: float,
        last_reminder_sent: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Decide if a reminder should be sent now
        
        Args:
            event: Event instance
            confirmation_rate: Current confirmation rate (0-100)
            last_reminder_sent: When last reminder was sent (None if never)
        
        Returns:
            (should_send: bool, reason: str or None)
        """
        now = datetime.now(timezone.utc)
        start_time = ensure_timezone_aware(event.start_time)
        hours_until_event = (start_time - now).total_seconds() / 3600
        
        # Don't send if event already started or ended
        if hours_until_event <= 0:
            return False, "Event has already started"
        
        # Don't send if event is too far away (more than 7 days)
        if hours_until_event > REMINDER_WINDOWS["FIRST_REMINDER"]:
            return False, f"Event is {int(hours_until_event/24)} days away - too early for reminders"
        
        # Check if we've sent a reminder recently (avoid spam)
        if last_reminder_sent:
            hours_since_last = (now - last_reminder_sent).total_seconds() / 3600
            
            # Minimum gap between reminders: 12 hours
            if hours_since_last < 12:
                return False, f"Last reminder sent {int(hours_since_last)} hours ago - too soon"
        
        # Determine if we're in a reminder window
        reminder_window = ReminderStrategy._get_current_reminder_window(hours_until_event)
        
        if not reminder_window:
            return False, "Not in a reminder window"
        
        # Always send if confirmation rate is low
        if confirmation_rate < CONFIRMATION_THRESHOLDS["LOW"]:
            return True, f"Low confirmation rate ({confirmation_rate:.1f}%) - aggressive reminder needed"
        
        # Send if we're approaching event and rate is moderate
        if hours_until_event < REMINDER_WINDOWS["FINAL_REMINDER"] and confirmation_rate < CONFIRMATION_THRESHOLDS["MODERATE"]:
            return True, f"Event in {int(hours_until_event)} hours with moderate confirmation ({confirmation_rate:.1f}%)"
        
        # Send final reminder regardless of confirmation rate
        if hours_until_event < REMINDER_WINDOWS["LAST_CALL"]:
            return True, f"Final reminder - event in {int(hours_until_event)} hours"
        
        # Don't send if confirmation rate is high and we're not close to event
        if confirmation_rate >= CONFIRMATION_THRESHOLDS["HIGH"]:
            return False, f"High confirmation rate ({confirmation_rate:.1f}%) - no urgent reminder needed"
        
        # Default: send if in a reminder window
        return True, f"In {reminder_window} window"
    
    @staticmethod
    def _get_current_reminder_window(hours_until_event: float) -> Optional[str]:
        """
        Determine which reminder window we're currently in
        
        Args:
            hours_until_event: Hours until event starts
        
        Returns:
            Window name or None
        """
        if hours_until_event <= REMINDER_WINDOWS["LAST_CALL"]:
            return "last_call"
        elif hours_until_event <= REMINDER_WINDOWS["FINAL_REMINDER"]:
            return "final_reminder"
        elif hours_until_event <= REMINDER_WINDOWS["SECOND_REMINDER"]:
            return "second_reminder"
        elif hours_until_event <= REMINDER_WINDOWS["FIRST_REMINDER"]:
            return "first_reminder"
        return None
    
    @staticmethod
    def get_reminder_content(
        reminder_type: ReminderType,
        event_name: str,
        start_time: datetime,
        confirmation_rate: float
    ) -> Dict[str, str]:
        """
        Generate reminder message content based on type
        
        Args:
            reminder_type: Type of reminder
            event_name: Event name
            start_time: Event start time
            confirmation_rate: Current confirmation rate
        
        Returns:
            Dict with 'subject', 'message', and 'tone' keys
        """
        now = datetime.now(timezone.utc)
        start_time_aware = ensure_timezone_aware(start_time)
        hours_until = (start_time_aware - now).total_seconds() / 3600
        
        if reminder_type == ReminderType.LIGHT:
            return {
                "subject": f"Reminder: {event_name} is coming up!",
                "message": f"Friendly reminder that '{event_name}' starts in {int(hours_until)} hours. "
                           f"Please confirm your attendance if you haven't already. Looking forward to seeing you there!",
                "tone": "friendly"
            }
        
        elif reminder_type == ReminderType.MODERATE:
            return {
                "subject": f"Action Required: Confirm your attendance for {event_name}",
                "message": f"We noticed you registered for '{event_name}' but haven't confirmed yet. "
                           f"The event starts in {int(hours_until)} hours. "
                           f"Please confirm your attendance to secure your spot. We currently have {confirmation_rate:.0f}% confirmations.",
                "tone": "encouraging"
            }
        
        elif reminder_type == ReminderType.AGGRESSIVE:
            return {
                "subject": f"⚠️ URGENT: Confirm for {event_name} - Starts in {int(hours_until)}h",
                "message": f"IMPORTANT: You registered for '{event_name}' but haven't confirmed your attendance. "
                           f"The event starts in {int(hours_until)} hours and we need your confirmation NOW to finalize arrangements. "
                           f"Current confirmation rate is only {confirmation_rate:.0f}%. "
                           f"⚡ Please confirm immediately or your spot may be released.",
                "tone": "urgent"
            }
        
        return {
            "subject": f"Reminder about {event_name}",
            "message": f"This is a reminder about '{event_name}'.",
            "tone": "neutral"
        }
    
    @staticmethod
    def get_reminder_schedule(event_start_time: datetime) -> List[Dict]:
        """
        Generate recommended reminder schedule based on event start time
        
        Args:
            event_start_time: When the event starts
        
        Returns:
            List of dicts with 'send_at' and 'window_name'
        """
        schedule = []
        
        for window_name, hours_before in REMINDER_WINDOWS.items():
            send_at = event_start_time - timedelta(hours=hours_before)
            
            # Only schedule future reminders
            if send_at > datetime.now(timezone.utc):
                schedule.append({
                    "window_name": window_name,
                    "send_at": send_at,
                    "hours_before_event": hours_before
                })
        
        return sorted(schedule, key=lambda x: x["send_at"])


class ReminderRules:
    """Business rules for reminder behavior"""
    
    @staticmethod
    def should_target_confirmed(confirmation_rate: float, hours_until_event: float) -> bool:
        """
        Determine if reminders should also target already-confirmed participants
        
        Args:
            confirmation_rate: Current confirmation rate
            hours_until_event: Hours until event starts
        
        Returns:
            True if should send to confirmed participants too
        """
        # In last 24 hours, send to everyone as a final reminder
        if hours_until_event < 24:
            return True
        
        # If confirmation rate is very high, send gentle reminder to all
        if confirmation_rate >= 85:
            return True
        
        # Otherwise, only target unconfirmed
        return False
    
    @staticmethod
    def calculate_reminder_priority(
        confirmation_rate: float,
        hours_until_event: float
    ) -> int:
        """
        Calculate priority score for reminder (1-10, higher = more urgent)
        Used by agent to prioritize reminder tasks
        
        Args:
            confirmation_rate: Current confirmation rate
            hours_until_event: Hours until event starts
        
        Returns:
            Priority score (1-10)
        """
        score = 5  # Base priority
        
        # Urgency based on time
        if hours_until_event < 2:
            score += 5  # Maximum urgency
        elif hours_until_event < 24:
            score += 3
        elif hours_until_event < 48:
            score += 2
        
        # Urgency based on confirmation rate
        if confirmation_rate < 20:
            score += 4  # Critical
        elif confirmation_rate < 40:
            score += 2
        elif confirmation_rate < 60:
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    @staticmethod
    def get_recommended_action(
        confirmation_rate: float,
        hours_until_event: float,
        total_registered: int
    ) -> Dict[str, any]:
        """
        Get recommended agent action based on current state
        
        Args:
            confirmation_rate: Current confirmation rate
            hours_until_event: Hours until event starts
            total_registered: Total registered participants
        
        Returns:
            Dict with recommended action and reasoning
        """
        if total_registered == 0:
            return {
                "action": "none",
                "reason": "No participants registered"
            }
        
        # Critical: Low confirmation rate close to event
        if confirmation_rate < 30 and hours_until_event < 48:
            return {
                "action": "send_aggressive_reminder",
                "reason": f"CRITICAL: Only {confirmation_rate:.0f}% confirmed with {int(hours_until_event)}h remaining",
                "priority": 10
            }
        
        # Send moderate reminder if rate is low-moderate
        if confirmation_rate < 60 and hours_until_event < 96:
            return {
                "action": "send_moderate_reminder",
                "reason": f"Moderate confirmation rate ({confirmation_rate:.0f}%) - encouragement needed",
                "priority": 6
            }
        
        # Send light reminder if approaching event
        if hours_until_event < 24:
            return {
                "action": "send_light_reminder",
                "reason": f"Final 24-hour reminder to all participants",
                "priority": 7
            }
        
        # All good
        if confirmation_rate >= 70:
            return {
                "action": "monitor",
                "reason": f"Good confirmation rate ({confirmation_rate:.0f}%) - continue monitoring",
                "priority": 2
            }
        
        return {
            "action": "wait",
            "reason": "No urgent action needed at this time",
            "priority": 1
        }
