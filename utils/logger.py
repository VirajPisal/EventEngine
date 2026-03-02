"""
Structured logging system with activity tracking for UI
Logs both to file and to database for agent activity feed
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

from config.settings import settings


class ActivityType(str, Enum):
    """Types of activities for UI activity feed"""
    STATE_TRANSITION = "state_transition"
    REMINDER_SENT = "reminder_sent"
    REGISTRATION = "registration"
    CONFIRMATION = "confirmation"
    ATTENDANCE = "attendance"
    ANALYTICS_GENERATED = "analytics_generated"
    AGENT_DECISION = "agent_decision"
    ERROR = "error"


class EventLogger:
    """
    Structured logger for the event system
    Provides both file logging and activity tracking for UI
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.logger = self._setup_file_logger()
        self.activity_buffer = []  # In-memory buffer for recent activities
        self.max_buffer_size = 100
    
    def _setup_file_logger(self) -> logging.Logger:
        """Setup file-based logger"""
        # Create logs directory if it doesn't exist
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        logger = logging.getLogger("event_agent")
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # File handler
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _add_to_activity_buffer(
        self,
        activity_type: ActivityType,
        message: str,
        event_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add activity to in-memory buffer for UI feed"""
        activity = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": activity_type.value,
            "message": message,
            "event_id": event_id,
            "metadata": metadata or {}
        }
        
        self.activity_buffer.append(activity)
        
        # Keep buffer size manageable
        if len(self.activity_buffer) > self.max_buffer_size:
            self.activity_buffer.pop(0)
    
    # Core logging methods
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        self.logger.info(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self.logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """Log error level message"""
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    # Structured activity logging for UI
    
    def log_state_transition(
        self,
        event_id: int,
        event_name: str,
        old_state: str,
        new_state: str,
        reason: Optional[str] = None,
        triggered_by: str = "agent"
    ):
        """Log state transition for UI activity feed"""
        message = f"Event #{event_id} '{event_name}' transitioned: {old_state} -> {new_state}"
        if reason:
            message += f" | Reason: {reason}"
        
        self.info(f"[STATE_TRANSITION] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.STATE_TRANSITION,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
                "triggered_by": triggered_by
            }
        )
    
    def log_reminder_sent(
        self,
        event_id: int,
        event_name: str,
        recipient_count: int,
        reminder_type: str,
        confirmation_rate: float
    ):
        """Log reminder batch sent"""
        message = f"Sent {reminder_type} reminder to {recipient_count} participants for Event #{event_id} '{event_name}' (Confirmation rate: {confirmation_rate:.1f}%)"
        
        self.info(f"[REMINDER] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.REMINDER_SENT,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "recipient_count": recipient_count,
                "reminder_type": reminder_type,
                "confirmation_rate": confirmation_rate
            }
        )
    
    def log_registration(
        self,
        event_id: int,
        event_name: str,
        participant_name: str,
        participant_email: str
    ):
        """Log new registration"""
        message = f"New registration for Event #{event_id} '{event_name}': {participant_name} ({participant_email})"
        
        self.info(f"[REGISTRATION] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.REGISTRATION,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "participant_name": participant_name,
                "participant_email": participant_email
            }
        )
    
    def log_confirmation(
        self,
        event_id: int,
        event_name: str,
        participant_name: str,
        new_confirmation_rate: float
    ):
        """Log participant confirmation"""
        message = f"{participant_name} confirmed for Event #{event_id} '{event_name}' (Rate now: {new_confirmation_rate:.1f}%)"
        
        self.info(f"[CONFIRMATION] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.CONFIRMATION,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "participant_name": participant_name,
                "confirmation_rate": new_confirmation_rate
            }
        )
    
    def log_attendance(
        self,
        event_id: int,
        event_name: str,
        participant_name: str,
        check_in_method: str
    ):
        """Log attendance check-in"""
        message = f"{participant_name} checked in to Event #{event_id} '{event_name}' via {check_in_method}"
        
        self.info(f"[ATTENDANCE] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.ATTENDANCE,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "participant_name": participant_name,
                "method": check_in_method
            }
        )
    
    def log_analytics_generated(
        self,
        event_id: int,
        event_name: str,
        attendance_rate: float,
        engagement_score: float
    ):
        """Log analytics generation"""
        message = f"Analytics generated for Event #{event_id} '{event_name}': {attendance_rate:.1f}% attendance, {engagement_score:.1f} engagement score"
        
        self.info(f"[ANALYTICS] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.ANALYTICS_GENERATED,
            message,
            event_id=event_id,
            metadata={
                "event_name": event_name,
                "attendance_rate": attendance_rate,
                "engagement_score": engagement_score
            }
        )
    
    def log_agent_decision(
        self,
        decision: str,
        event_id: Optional[int] = None,
        reasoning: Optional[str] = None
    ):
        """Log autonomous agent decision"""
        message = f"Agent decision: {decision}"
        if reasoning:
            message += f" | Reasoning: {reasoning}"
        
        self.info(f"[AGENT] {message}")
        
        self._add_to_activity_buffer(
            ActivityType.AGENT_DECISION,
            message,
            event_id=event_id,
            metadata={
                "decision": decision,
                "reasoning": reasoning
            }
        )
    
    def get_recent_activities(self, limit: int = 50, event_id: Optional[int] = None) -> list:
        """
        Get recent activities for UI activity feed
        
        Args:
            limit: Maximum number of activities to return
            event_id: Filter by event ID (None = all events)
        
        Returns:
            List of activity dictionaries
        """
        activities = self.activity_buffer.copy()
        
        # Filter by event_id if specified
        if event_id is not None:
            activities = [a for a in activities if a.get("event_id") == event_id]
        
        # Return most recent first
        return list(reversed(activities[-limit:]))


# Global logger instance
logger = EventLogger()
