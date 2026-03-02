"""
Attendance model - QR/OTP validation records
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.base import Base


class Attendance(Base):
    """Attendance check-in records"""
    __tablename__ = "attendance"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Event and Participant Reference
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False, index=True, unique=True)
    
    # Check-in Details
    checked_in_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    check_in_method = Column(String(20), nullable=False)  # "QR" or "OTP"
    
    # Validation
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_notes = Column(String(500), nullable=True)  # e.g., "Late check-in", "Early check-in"
    
    # Location Data (optional)
    check_in_ip = Column(String(50), nullable=True)
    check_in_device = Column(String(255), nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="attendance_records")
    participant = relationship("Participant", back_populates="attendance")
    
    def __repr__(self):
        return f"<Attendance(id={self.id}, participant_id={self.participant_id}, method='{self.check_in_method}')>"
