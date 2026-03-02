"""
Participant model - Registration and confirmation tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.base import Base
from config.constants import ParticipantStatus


class Participant(Base):
    """Participant registration model"""
    __tablename__ = "participants"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Event Reference
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Participant Info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    
    # Status
    status = Column(SQLEnum(ParticipantStatus), nullable=False, default=ParticipantStatus.REGISTERED, index=True)
    
    # Confirmation
    is_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Attendance Credentials
    qr_token = Column(String(500), nullable=True, unique=True)  # For offline events
    otp = Column(String(10), nullable=True)  # For online events
    otp_expires_at = Column(DateTime, nullable=True)
    
    # Metadata
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    attendance = relationship("Attendance", back_populates="participant", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Participant(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def has_attended(self) -> bool:
        """Check if participant has attended the event"""
        return self.status == ParticipantStatus.ATTENDED
