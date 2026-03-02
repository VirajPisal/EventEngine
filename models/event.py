"""
Event model - Core entity with state management
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.base import Base
from config.constants import EventState, EventType


class Event(Base):
    """Event model with state field for FSM"""
    __tablename__ = "events"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(SQLEnum(EventType), nullable=False, default=EventType.OFFLINE)
    
    # State Management (CRITICAL - only modified via state_machine)
    state = Column(SQLEnum(EventState), nullable=False, default=EventState.CREATED, index=True)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    registration_deadline = Column(DateTime, nullable=True)
    
    # Location / Link
    venue = Column(String(500), nullable=True)  # For offline events
    meeting_link = Column(String(500), nullable=True)  # For online events
    
    # Capacity
    max_participants = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)  # User ID or name
    
    # Relationships
    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="event", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="event", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', state='{self.state}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if event is in an active state"""
        return self.state not in [EventState.CANCELLED, EventState.REPORT_GENERATED]
    
    @property
    def can_register(self) -> bool:
        """Check if registration is currently open"""
        return self.state == EventState.REGISTRATION_OPEN
