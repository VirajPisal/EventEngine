"""
Promotion Service - Handles autonomous event promotion to potential participants
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.event import Event
from models.user import ParticipantAccount
from models.participant import Participant
from notifications.email import get_email_service
from utils.logger import logger


class PromotionService:
    """Service for managing automated event promotions"""

    @staticmethod
    def promote_event(db: Session, event_id: int) -> Dict[str, Any]:
        """
        Identify potential participants and send promotional emails
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"success": False, "message": "Event not found"}

        # Use cases for promotion:
        # 1. No participants yet
        # 2. Below 50% capacity
        # 3. New event created

        # Get all registered accounts
        potential_accounts = db.query(ParticipantAccount).all()
        
        # Get already registered participants for this event
        already_registered_emails = [
            p.email for p in db.query(Participant).filter(Participant.event_id == event_id).all()
        ]

        count = 0
        email_service = get_email_service()

        for account in potential_accounts:
            # Skip if already registered
            if account.email in already_registered_emails:
                continue
            
            # Send promotion
            try:
                email_service.send_promotion_email(
                    to_email=account.email,
                    participant_name=account.name,
                    event_name=event.name,
                    event_description=event.description or "No description provided.",
                    event_id=event.id
                )
                count += 1
            except Exception as e:
                logger.error(f"[PROMOTION] Failed to promote to {account.email}: {e}")

        logger.info(f"[PROMOTION] Sent promotional emails to {count} potential participants for Event #{event_id}")
        
        return {
            "success": True,
            "emails_sent": count,
            "message": f"Promoted to {count} users"
        }
