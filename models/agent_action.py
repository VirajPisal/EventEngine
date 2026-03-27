"""
AgentAction model - Stores pending/completed agent actions for organizer approval
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime, timezone

from db.base import Base


class AgentAction(Base):
    """Agent action requiring organizer approval"""
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    action_type = Column(String(100), nullable=False)  # SEND_REMINDER, POST_LINKEDIN, etc.
    description = Column(String(500), nullable=False)
    payload_json = Column(Text, nullable=True)  # JSON string of action data
    status = Column(String(20), nullable=False, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED, EXECUTED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    executed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AgentAction(id={self.id}, type='{self.action_type}', status='{self.status}')>"
