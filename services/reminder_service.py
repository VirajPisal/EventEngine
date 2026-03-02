"""
Reminder Service - Adaptive reminder logic and execution
Uses rule engine to determine strategy and sends notifications
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.event import Event
from models.participant import Participant
from services.registration_service import RegistrationService
from rules.reminder_rules import ReminderStrategy, ReminderRules
from config.constants import ReminderType
from utils.logger import logger
from notifications.email import get_email_service
from notifications.sms import get_sms_service


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (assume UTC if naive)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ReminderService:
    """Service for sending adaptive reminders to participants"""
    
    @staticmethod
    def evaluate_and_send_reminders(
        db: Session,
        event_id: int,
        force: bool = False
    ) -> Dict[str, any]:
        """
        Evaluate if reminders should be sent and send them
        Main entry point for agent loop
        
        Args:
            db: Database session
            event_id: Event ID    
            force: If True, bypass timing checks and send anyway
        
        Returns:
            Dictionary with results:
            - should_send: bool
            - sent: bool
            - reminder_type: str
            - recipient_count: int
            - reason: str
        """
        # Get event
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            return {
                "should_send": False,
                "sent": False,
                "reason": f"Event {event_id} not found"
            }
        
        # Get stats
        confirmation_rate = RegistrationService.get_confirmation_rate(db, event_id)
        stats = RegistrationService.get_participant_stats(db, event_id)
        
        if stats["total_registered"] == 0:
            return {
                "should_send": False,
                "sent": False,
                "reason": "No participants registered"
            }
        
        # Check if we should send (unless forced)
        if not force:
            should_send, reason = ReminderStrategy.should_send_reminder(
                event,
                confirmation_rate,
                last_reminder_sent=None  # TODO: Track this in Event model
            )
            
            if not should_send:
                return {
                    "should_send": False,
                    "sent": False,
                    "reason": reason,
                    "confirmation_rate": confirmation_rate,
                    "stats": stats
                }
        
        # Determine reminder type based on confirmation rate
        reminder_type = ReminderStrategy.determine_reminder_type(confirmation_rate)
        
        # Get target participants
        start_time = ensure_timezone_aware(event.start_time)
        hours_until_event = (start_time - datetime.now(timezone.utc)).total_seconds() / 3600
        target_confirmed_too = ReminderRules.should_target_confirmed(confirmation_rate, hours_until_event)
        
        if target_confirmed_too:
            # Send to everyone
            recipients = RegistrationService.bulk_reminder_targets(
                db,
                event_id,
                target_unconfirmed=False
            )
        else:
            # Send only to unconfirmed
            recipients = RegistrationService.get_unconfirmed_participants(db, event_id)
        
        if len(recipients) == 0:
            return {
                "should_send": True,
                "sent": False,
                "reason": "No target recipients (all confirmed or cancelled)",
                "confirmation_rate": confirmation_rate
            }
        
        # Send reminders
        result = ReminderService.send_reminder_batch(
            db,
            event,
            recipients,
            reminder_type,
            confirmation_rate
        )
        
        return result
    
    @staticmethod
    def send_reminder_batch(
        db: Session,
        event: Event,
        recipients: List[Participant],
        reminder_type: ReminderType,
        confirmation_rate: float
    ) -> Dict[str, any]:
        """
        Send a batch of reminders to participants
        
        Args:
            db: Database session
            event: Event instance
            recipients: List of participants to send to
            reminder_type: Type of reminder (LIGHT, MODERATE, AGGRESSIVE)
            confirmation_rate: Current confirmation rate
        
        Returns:
            Dictionary with send results
        """
        # Get reminder content
        content = ReminderStrategy.get_reminder_content(
            reminder_type,
            event.name,
            event.start_time,
            confirmation_rate
        )
        
        # Add event details to content for email/SMS services
        content['event_name'] = event.name
        content['event_start_time'] = event.start_time
        
        # Send to each recipient
        sent_count = 0
        failed_count = 0
        
        for participant in recipients:
            try:
                success = ReminderService._send_reminder_to_participant(
                    participant,
                    content,
                    reminder_type
                )
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            
            except Exception as e:
                logger.error(f"Failed to send reminder to {participant.email}: {e}")
                failed_count += 1
        
        # Log activity for UI feed
        logger.log_reminder_sent(
            event_id=event.id,
            event_name=event.name,
            recipient_count=sent_count,
            reminder_type=reminder_type.value.upper(),
            confirmation_rate=confirmation_rate
        )
        
        logger.info(
            f"Sent {reminder_type.value} reminders: {sent_count} sent, {failed_count} failed "
            f"(Event: {event.name}, Confirmation rate: {confirmation_rate:.1f}%)"
        )
        
        return {
            "should_send": True,
            "sent": True,
            "reminder_type": reminder_type.value,
            "recipient_count": sent_count,
            "failed_count": failed_count,
            "confirmation_rate": confirmation_rate,
            "content": content
        }
    
    @staticmethod
    def _send_reminder_to_participant(
        participant: Participant,
        content: Dict[str, str],
        reminder_type: ReminderType
    ) -> bool:
        """
        Send reminder to individual participant via email and optionally SMS
        
        Args:
            participant: Participant instance
            content: Dict with subject, message, tone
            reminder_type: Type of reminder
        
        Returns:
            True if sent successfully
        """
        email_service = get_email_service()
        sms_service = get_sms_service()
        
        email_sent = False
        sms_sent = False
        
        # Always send email
        try:
            email_result = email_service.send_reminder(
                to_email=participant.email,
                to_name=participant.name,
                event_name=content.get('event_name', 'Your Event'),
                event_start_time=content.get('event_start_time'),
                message_content=content['message'],
                tone=content['tone']
            )
            email_sent = email_result.get('sent', False)
        except Exception as e:
            logger.error(f"Failed to send reminder email to {participant.email}: {e}")
        
        # Send SMS for AGGRESSIVE reminders (urgent situations)
        if reminder_type == ReminderType.AGGRESSIVE and participant.phone:
            try:
                sms_result = sms_service.send_reminder(
                    to_phone=participant.phone,
                    event_name=content.get('event_name', 'Your Event'),
                    event_start_time=content.get('event_start_time')
                )
                sms_sent = sms_result.get('sent', False)
            except Exception as e:
                logger.error(f"Failed to send reminder SMS to {participant.phone}: {e}")
        
        # Consider successful if email was sent
        # (SMS is optional enhancement for urgent reminders)
        return email_sent
    
    @staticmethod
    def get_reminder_recommendations(
        db: Session,
        event_id: int
    ) -> Dict[str, any]:
        """
        Get agent recommendations for reminder strategy
        Used by agent to decide actions without sending
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Dictionary with recommendations
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            return {
                "event_id": event_id,
                "error": "Event not found"
            }
        
        # Get stats
        confirmation_rate = RegistrationService.get_confirmation_rate(db, event_id)
        stats = RegistrationService.get_participant_stats(db, event_id)
        
        # Calculate time until event
        now = datetime.now(timezone.utc)
        start_time = ensure_timezone_aware(event.start_time)
        hours_until_event = (start_time - now).total_seconds() / 3600
        
        # Get recommended action
        recommendation = ReminderRules.get_recommended_action(
            confirmation_rate,
            hours_until_event,
            stats["total_registered"]
        )
        
        # Determine reminder type
        reminder_type = ReminderStrategy.determine_reminder_type(confirmation_rate)
        
        # Calculate priority
        priority = ReminderRules.calculate_reminder_priority(
            confirmation_rate,
            hours_until_event
        )
        
        # Check if should send now
        should_send, reason = ReminderStrategy.should_send_reminder(
            event,
            confirmation_rate,
            last_reminder_sent=None
        )
        
        return {
            "event_id": event_id,
            "event_name": event.name,
            "confirmation_rate": round(confirmation_rate, 1),
            "hours_until_event": round(hours_until_event, 1),
            "stats": stats,
            "recommended_action": recommendation["action"],
            "reasoning": recommendation["reason"],
            "priority": priority,
            "should_send_now": should_send,
            "send_reason": reason,
            "recommended_reminder_type": reminder_type.value,
            "target_unconfirmed_only": not ReminderRules.should_target_confirmed(
                confirmation_rate,
                hours_until_event
            )
        }
    
    @staticmethod
    def get_reminder_schedule(event_start_time: datetime) -> List[Dict]:
        """
        Get recommended reminder schedule for an event
        
        Args:
            event_start_time: Event start time
        
        Returns:
            List of scheduled reminder times
        """
        return ReminderStrategy.get_reminder_schedule(event_start_time)
