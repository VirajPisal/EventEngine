"""
User models - Organizer and Participant accounts for authentication
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone

from db.base import Base


class Organizer(Base):
    """Organizer account model"""
    __tablename__ = "organizers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Organizer(id={self.id}, name='{self.name}', email='{self.email}')>"


class ParticipantAccount(Base):
    """Participant account model (separate from per-event Participant registration)"""
    __tablename__ = "participant_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ParticipantAccount(id={self.id}, name='{self.name}', email='{self.email}')>"
