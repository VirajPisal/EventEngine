"""
Event Service - Event CRUD and state transition orchestration
All business logic for event management lives here
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from models.event import Event
from models.participant import Participant
from config.constants import EventState, EventType
from core.state_machine import StateMachine, InvalidStateTransitionError
from utils.logger import logger


class EventService:
    """Service for event management and lifecycle orchestration"""
    
    @staticmethod
    def create_event(
        db: Session,
        name: str,
        description: str,
        event_type: EventType,
        start_time: datetime,
        end_time: datetime,
        venue: Optional[str] = None,
        meeting_link: Optional[str] = None,
        max_participants: Optional[int] = None,
        registration_deadline: Optional[datetime] = None,
        created_by: Optional[str] = None,
        custom_email_template: Optional[str] = None,
        certificate_template: Optional[str] = None
    ) -> Event:
        """
        Create a new event in CREATED state
        
        Args:
            db: Database session
            name: Event name
            description: Event description
            event_type: ONLINE, OFFLINE, or HYBRID
            start_time: Event start datetime
            end_time: Event end datetime
            venue: Physical venue (for offline/hybrid)
            meeting_link: Online meeting link (for online/hybrid)
            max_participants: Maximum participant capacity
            registration_deadline: Registration cutoff datetime
            created_by: Creator identifier
        
        Returns:
            Created Event instance
        """
        event = Event(
            name=name,
            description=description,
            event_type=event_type,
            state=EventState.CREATED,  # Always starts here
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            meeting_link=meeting_link,
            max_participants=max_participants,
            registration_deadline=registration_deadline,
            created_by=created_by,
            custom_email_template=custom_email_template,
            certificate_template=certificate_template
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        logger.info(f"Event created: {event.name} (ID: {event.id}, Type: {event_type.value})")
        logger.log_agent_decision(
            decision=f"Event '{event.name}' created in CREATED state",
            event_id=event.id,
            reasoning=f"New {event_type.value} event scheduled for {start_time.strftime('%Y-%m-%d %H:%M')}"
        )
        
        return event
    
    @staticmethod
    def get_event(
        db: Session,
        event_id: int,
        include_relationships: bool = False
    ) -> Optional[Event]:
        """
        Get event by ID
        
        Args:
            db: Database session
            event_id: Event ID
            include_relationships: If True, eagerly load participants, attendance, analytics
        
        Returns:
            Event instance or None
        """
        query = db.query(Event).filter(Event.id == event_id)
        
        if include_relationships:
            query = query.options(
                joinedload(Event.participants),
                joinedload(Event.attendance_records),
                joinedload(Event.analytics)
            )
        
        return query.first()
    
    @staticmethod
    def get_event_with_stats(db: Session, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Get event with computed statistics for UI
        Returns rich data structure for EventDetail page
        
        Returns:
            Dictionary with event data + stats, or None
        """
        event = EventService.get_event(db, event_id, include_relationships=True)
        
        if not event:
            return None
        
        # Calculate stats
        total_participants = len(event.participants)
        confirmed = sum(1 for p in event.participants if p.is_confirmed)
        attended = sum(1 for p in event.participants if p.has_attended)
        
        confirmation_rate = (confirmed / total_participants * 100) if total_participants > 0 else 0
        attendance_rate = (attended / confirmed * 100) if confirmed > 0 else 0
        
        # Build state timeline
        state_timeline = EventService._build_state_timeline(event)
        
        return {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "event_type": event.event_type.value,
            "state": event.state.value,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "venue": event.venue,
            "meeting_link": event.meeting_link,
            "max_participants": event.max_participants,
            "custom_email_template": event.custom_email_template,
            "certificate_template": event.certificate_template,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            # Stats for UI
            "stats": {
                "total_registered": total_participants,
                "total_confirmed": confirmed,
                "total_attended": attended,
                "confirmation_rate": round(confirmation_rate, 1),
                "attendance_rate": round(attendance_rate, 1),
                "available_spots": (event.max_participants - total_participants) if event.max_participants else None
            },
            # For state pipeline visualization
            "state_timeline": state_timeline,
            "allowed_transitions": [s.value for s in StateMachine.get_allowed_transitions(event.state)]
        }
    
    @staticmethod
    def _build_state_timeline(event: Event) -> Dict[str, Optional[str]]:
        """
        Build state timeline for UI visualization
        Maps each state to when it was entered (or None if not yet reached)
        """
        # TODO: In the future, store state history in a separate table
        # For now, use available timestamps
        return {
            "CREATED": event.created_at.isoformat(),
            "REGISTRATION_OPEN": None,  # Will track this later
            "SCHEDULED": None,
            "ATTENDANCE_OPEN": None,
            "RUNNING": None,
            "COMPLETED": None,
            "ANALYZING": None,
            "REPORT_GENERATED": None,
            "CANCELLED": None
        }
    
    @staticmethod
    def list_events(
        db: Session,
        state: Optional[EventState] = None,
        event_type: Optional[EventType] = None,
        is_active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """
        List events with optional filtering
        
        Args:
            db: Database session
            state: Filter by specific state
            event_type: Filter by event type
            is_active_only: If True, exclude CANCELLED and REPORT_GENERATED
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of Event instances
        """
        query = db.query(Event)
        
        # Apply filters
        if state:
            query = query.filter(Event.state == state)
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        if is_active_only:
            query = query.filter(
                and_(
                    Event.state != EventState.CANCELLED,
                    Event.state != EventState.REPORT_GENERATED
                )
            )
        
        # Order by start time (upcoming events first)
        query = query.order_by(Event.start_time.asc())
        
        return query.limit(limit).offset(offset).all()
    
    @staticmethod
    def transition_event_state(
        db: Session,
        event_id: int,
        new_state: EventState,
        reason: Optional[str] = None,
        triggered_by: str = "manual"
    ) -> Dict[str, Any]:
        """
        Transition event to new state with validation
        
        Args:
            db: Database session
            event_id: Event ID
            new_state: Target state
            reason: Reason for transition
            triggered_by: Who/what triggered it ("manual", "agent", "scheduler")
        
        Returns:
            Result dictionary with success status and message
        
        Raises:
            InvalidStateTransitionError: If transition is not allowed
        """
        event = EventService.get_event(db, event_id)
        
        if not event:
            return {
                "success": False,
                "message": f"Event {event_id} not found"
            }
        
        old_state = event.state
        
        try:
            # Attempt transition through state machine
            StateMachine.transition(event, new_state, reason=reason or f"{triggered_by} transition")
            
            db.commit()
            db.refresh(event)
            
            logger.info(f"Event {event_id} transitioned: {old_state.value} -> {new_state.value} (by {triggered_by})")
            
            return {
                "success": True,
                "message": f"Event transitioned from {old_state.value} to {new_state.value}",
                "old_state": old_state.value,
                "new_state": new_state.value
            }
        
        except InvalidStateTransitionError as e:
            db.rollback()
            logger.warning(f"Invalid transition attempted for Event {event_id}: {old_state.value} -> {new_state.value}")
            
            return {
                "success": False,
                "message": str(e),
                "old_state": old_state.value,
                "attempted_state": new_state.value,
                "allowed_transitions": [s.value for s in StateMachine.get_allowed_transitions(old_state)]
            }
    
    @staticmethod
    def cancel_event(
        db: Session,
        event_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel an event (transition to CANCELLED state)
        
        Args:
            db: Database session
            event_id: Event ID
            reason: Cancellation reason
        
        Returns:
            Result dictionary
        """
        return EventService.transition_event_state(
            db,
            event_id,
            EventState.CANCELLED,
            reason=reason or "Event cancelled",
            triggered_by="manual"
        )
    
    @staticmethod
    def get_active_events_count(db: Session) -> int:
        """Get count of active events (for dashboard)"""
        return db.query(Event).filter(
            and_(
                Event.state != EventState.CANCELLED,
                Event.state != EventState.REPORT_GENERATED
            )
        ).count()
    
    @staticmethod
    def delete_event(db: Session, event_id: int) -> bool:
        """
        Hard delete an event (use with caution!)
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            True if deleted, False if not found
        """
        event = EventService.get_event(db, event_id)
        
        if not event:
            return False
        
        logger.warning(f"Event {event_id} '{event.name}' permanently deleted")
        db.delete(event)
        db.commit()
        
        return True
