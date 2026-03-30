"""
Registration Service - Participant registration and confirmation management
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from models.event import Event
from models.participant import Participant
from config.constants import EventState, ParticipantStatus
from utils.logger import logger
from utils.qr_generator import get_qr_generator
from notifications.email import get_email_service
from services.calendar_service import CalendarService


class RegistrationService:
    """Service for managing participant registrations"""
    
    @staticmethod
    def register_participant(
        db: Session,
        event_id: int,
        name: str,
        email: str,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new participant for an event
        
        Args:
            db: Database session
            event_id: Event ID
            name: Participant name
            email: Participant email
            phone: Participant phone number
        
        Returns:
            Dictionary with success status and participant data or error message
        """
        # Check if event exists and accepts registrations
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            return {
                "success": False,
                "message": f"Event {event_id} not found"
            }
        
        if event.state != EventState.REGISTRATION_OPEN:
            return {
                "success": False,
                "message": f"Registration is not open for this event (current state: {event.state.value})"
            }
        
        # Check capacity
        if event.max_participants:
            current_count = db.query(Participant).filter(
                and_(
                    Participant.event_id == event_id,
                    Participant.status != ParticipantStatus.CANCELLED
                )
            ).count()
            
            if current_count >= event.max_participants:
                return {
                    "success": False,
                    "message": "Event is at full capacity"
                }
        
        # Check if already registered
        existing = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.email == email,
                Participant.status != ParticipantStatus.CANCELLED
            )
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "This email is already registered for this event"
            }
        
        # Create participant
        participant = Participant(
            event_id=event_id,
            name=name,
            email=email,
            phone=phone,
            status=ParticipantStatus.REGISTERED,
            is_confirmed=False
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        # Generate QR code for attendance
        qr_generator = get_qr_generator()
        qr_data = qr_generator.generate_attendance_qr(
            participant_id=participant.id,
            event_id=event_id,
            expiry_hours=24
        )
        
        # Store QR token in database
        participant.qr_token = qr_data['token']
        db.commit()
        
        # Generate Calendar Invite (.ics)
        ics_content = CalendarService.generate_ics_content(
            name=event.name,
            description=event.description or f"Event {event.name}",
            start_time=event.start_time,
            end_time=event.end_time or event.start_time,
            location=event.venue or event.meeting_link or "Online",
            uid=f"event-{event.id}-part-{participant.id}"
        )
        
        # Generate Google Calendar Link
        google_cal_link = CalendarService.generate_google_calendar_link(
            name=event.name,
            description=event.description or f"Event {event.name}",
            start_time=event.start_time,
            end_time=event.end_time or event.start_time,
            location=event.venue or event.meeting_link or "Online"
        )
        
        # Send confirmation email with QR code and Calendar Invite
        email_service = get_email_service()
        try:
            email_result = email_service.send_registration_confirmation(
                to_email=email,
                participant_name=name,  # Fixed: use participant_name
                event_name=event.name,
                event_start_time=event.start_time,
                event_details={
                    'event_type': event.event_type.value,
                    'venue': event.venue,
                    'meeting_link': event.meeting_link,
                    'description': event.description,
                    'end_time': event.end_time,
                    'registration_deadline': event.registration_deadline,
                    'organizer': event.created_by
                },
                qr_code_data=qr_data.get('image_base64'),
                participant_id=participant.id,
                custom_content=event.custom_email_template,
                ics_content=ics_content,
                google_cal_link=google_cal_link
            )
            email_sent = email_result.get('success', False)
        except Exception as e:
            logger.error(f"Failed to send registration confirmation email: {e}")
            email_sent = False
        
        # Log activity
        logger.log_registration(
            event_id=event_id,
            event_name=event.name,
            participant_name=name,
            participant_email=email
        )
        
        return {
            "success": True,
            "message": "Registration successful",
            "email_sent": email_sent,
            "participant": {
                "id": participant.id,
                "name": participant.name,
                "email": participant.email,
                "status": participant.status.value,
                "registered_at": participant.registered_at.isoformat(),
                "qr_code_sent": email_sent and qr_data.get('image_available', False)
            }
        }
    
    @staticmethod
    def confirm_participant(
        db: Session,
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Confirm a participant's registration
        
        Args:
            db: Database session
            participant_id: Participant ID
        
        Returns:
            Dictionary with success status and updated data
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": f"Participant {participant_id} not found"
            }
        
        if participant.is_confirmed:
            return {
                "success": False,
                "message": "Participant is already confirmed"
            }
        
        # Update status
        participant.is_confirmed = True
        participant.confirmed_at = datetime.now(timezone.utc)
        participant.status = ParticipantStatus.CONFIRMED
        
        db.commit()
        db.refresh(participant)
        
        # Get event for logging
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        
        # Calculate new confirmation rate
        confirmation_rate = RegistrationService.get_confirmation_rate(db, participant.event_id)
        
        # Log activity
        logger.log_confirmation(
            event_id=participant.event_id,
            event_name=event.name if event else "Unknown Event",
            participant_name=participant.name,
            new_confirmation_rate=confirmation_rate
        )
        
        return {
            "success": True,
            "message": "Registration confirmed",
            "participant": {
                "id": participant.id,
                "name": participant.name,
                "status": participant.status.value,
                "confirmed_at": participant.confirmed_at.isoformat()
            },
            "event_confirmation_rate": round(confirmation_rate, 1)
        }
    
    @staticmethod
    def cancel_registration(
        db: Session,
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Cancel a participant's registration
        
        Args:
            db: Database session
            participant_id: Participant ID
        
        Returns:
            Dictionary with success status
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": f"Participant {participant_id} not found"
            }
        
        if participant.status == ParticipantStatus.CANCELLED:
            return {
                "success": False,
                "message": "Registration is already cancelled"
            }
        
        participant.status = ParticipantStatus.CANCELLED
        
        db.commit()
        
        logger.info(f"Participant {participant_id} ({participant.name}) cancelled registration for Event {participant.event_id}")
        
        return {
            "success": True,
            "message": "Registration cancelled"
        }
    
    @staticmethod
    def resend_confirmation_email(
        db: Session,
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Resend confirmation email to a participant
        
        Args:
            db: Database session
            participant_id: Participant ID
        
        Returns:
            Dictionary with success status and email_sent flag
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": f"Participant {participant_id} not found"
            }
        
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            return {
                "success": False,
                "message": f"Event not found for participant {participant_id}"
            }
        
        # Try to send confirmation email
        email_sent = False
        try:
            email_service = get_email_service()
            email_service.send_registration_confirmation(
                to_email=participant.email,
                participant_name=participant.name,
                event_name=event.name,
                event_start_time=event.start_time,
                event_details={
                    'event_type': event.event_type.value if event.event_type else 'N/A',
                    'venue': event.venue,
                    'meeting_link': event.meeting_link
                },
                qr_code_data=None
            )
            email_sent = True
        except Exception as e:
            logger.warning(f"Failed to send confirmation email to {participant.email}: {e}")
        
        logger.info(f"Resent confirmation email to participant {participant_id} ({participant.name}), sent={email_sent}")
        
        return {
            "success": True,
            "message": "Confirmation email resent" if email_sent else "Confirmation processed (email service unavailable)",
            "email_sent": email_sent
        }
    
    @staticmethod
    def get_confirmation_rate(db: Session, event_id: int) -> float:
        """
        Calculate confirmation rate for an event
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Confirmation rate as percentage (0-100)
        """
        # Get total registered (excluding cancelled)
        total = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.status != ParticipantStatus.CANCELLED
            )
        ).count()
        
        if total == 0:
            return 0.0
        
        # Get confirmed count
        confirmed = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.is_confirmed == True
            )
        ).count()
        
        return (confirmed / total) * 100
    
    @staticmethod
    def get_event_participants(
        db: Session,
        event_id: int,
        status: Optional[ParticipantStatus] = None,
        is_confirmed: Optional[bool] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Participant]:
        """
        Get participants for an event with optional filtering
        
        Args:
            db: Database session
            event_id: Event ID
            status: Filter by participant status
            is_confirmed: Filter by confirmation status
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of Participant instances
        """
        query = db.query(Participant).filter(Participant.event_id == event_id)
        
        if status:
            query = query.filter(Participant.status == status)
        
        if is_confirmed is not None:
            query = query.filter(Participant.is_confirmed == is_confirmed)
        
        # Order by registration time
        query = query.order_by(Participant.registered_at.desc())
        
        return query.limit(limit).offset(offset).all()
    
    @staticmethod
    def get_unconfirmed_participants(db: Session, event_id: int) -> List[Participant]:
        """
        Get all unconfirmed participants for an event (for sending reminders)
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            List of unconfirmed Participant instances
        """
        return db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.is_confirmed == False,
                Participant.status == ParticipantStatus.REGISTERED
            )
        ).all()
    
    @staticmethod
    def get_participant_stats(db: Session, event_id: int) -> Dict[str, Any]:
        """
        Get participant statistics for an event (for UI)
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Dictionary with various stats
        """
        # Total counts
        total = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.status != ParticipantStatus.CANCELLED
            )
        ).count()
        
        confirmed = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.is_confirmed == True
            )
        ).count()
        
        attended = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.status == ParticipantStatus.ATTENDED
            )
        ).count()
        
        cancelled = db.query(Participant).filter(
            and_(
                Participant.event_id == event_id,
                Participant.status == ParticipantStatus.CANCELLED
            )
        ).count()
        
        # Calculate rates
        confirmation_rate = (confirmed / total * 100) if total > 0 else 0
        attendance_rate = (attended / confirmed * 100) if confirmed > 0 else 0
        
        return {
            "total_registered": total,
            "total_confirmed": confirmed,
            "total_attended": attended,
            "total_cancelled": cancelled,
            "unconfirmed": total - confirmed,
            "confirmation_rate": round(confirmation_rate, 1),
            "attendance_rate": round(attendance_rate, 1)
        }
    
    @staticmethod
    def bulk_reminder_targets(
        db: Session,
        event_id: int,
        target_unconfirmed: bool = True
    ) -> List[Participant]:
        """
        Get list of participants to send reminders to
        
        Args:
            db: Database session
            event_id: Event ID
            target_unconfirmed: If True, return only unconfirmed; if False, return all registered
        
        Returns:
            List of Participant instances
        """
        if target_unconfirmed:
            return RegistrationService.get_unconfirmed_participants(db, event_id)
        else:
            return RegistrationService.get_event_participants(
                db,
                event_id,
                status=ParticipantStatus.REGISTERED
            ) + RegistrationService.get_event_participants(
                db,
                event_id,
                status=ParticipantStatus.CONFIRMED
            )
