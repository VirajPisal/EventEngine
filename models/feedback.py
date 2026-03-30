"""
Feedback Model - Participant ratings and reviews
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from datetime import datetime

from db.base import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    
    rating = Column(Integer, nullable=False) # 1 to 5
    comment = Column(Text, nullable=True)
    
    submitted_at = Column(DateTime, default=func.now())
