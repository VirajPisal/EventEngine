"""
Analytics model - Event metrics snapshot
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from db.base import Base


class Analytics(Base):
    """Event analytics and metrics snapshot"""
    __tablename__ = "analytics"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Event Reference (One-to-One)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True, index=True)
    
    # Registration Metrics
    total_registered = Column(Integer, default=0, nullable=False)
    total_confirmed = Column(Integer, default=0, nullable=False)
    confirmation_rate = Column(Float, default=0.0, nullable=False)  # Percentage
    
    # Attendance Metrics
    total_attended = Column(Integer, default=0, nullable=False)
    attendance_rate = Column(Float, default=0.0, nullable=False)  # Percentage of confirmed
    no_show_count = Column(Integer, default=0, nullable=False)
    no_show_rate = Column(Float, default=0.0, nullable=False)  # Percentage
    
    # Conversion Metrics
    registration_to_attendance_rate = Column(Float, default=0.0, nullable=False)  # Percentage
    
    # Engagement Score (0-100)
    engagement_score = Column(Float, default=0.0, nullable=False)
    
    # Timing Metrics
    avg_confirmation_time_hours = Column(Float, nullable=True)  # Average time to confirm after registration
    
    # Additional Insights (JSON)
    additional_metrics = Column(JSON, nullable=True)  # Flexible field for custom metrics
    ai_insights = Column(JSON, nullable=True)  # AI-generated insights and recommendations
    
    # Generation Timestamp
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    event = relationship("Event", back_populates="analytics")
    
    def __repr__(self):
        return f"<Analytics(event_id={self.event_id}, attendance_rate={self.attendance_rate:.1f}%, engagement={self.engagement_score:.1f})>"
    
    @property
    def is_good_attendance(self) -> bool:
        """Check if attendance rate is considered good (>75%)"""
        from config.constants import ANALYTICS_THRESHOLDS
        return self.attendance_rate >= ANALYTICS_THRESHOLDS["GOOD_ATTENDANCE_RATE"]
