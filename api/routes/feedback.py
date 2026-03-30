"""
Feedback Routes - Submit and view event feedback
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from db.base import get_db
from models.feedback import Feedback
from models.event import Event
from models.participant import Participant
from config.constants import EventState

router = APIRouter()

class FeedbackCreateRequest(BaseModel):
    event_id: int
    participant_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

@router.post("/")
async def submit_feedback(
    req: FeedbackCreateRequest,
    db: Session = Depends(get_db)
):
    """Submit feedback for an event"""
    # Check if participant attended (simplified check for now)
    participant = db.query(Participant).filter(Participant.id == req.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    # Check if feedback already submitted
    existing = db.query(Feedback).filter(
        Feedback.event_id == req.event_id,
        Feedback.participant_id == req.participant_id
    ).first()
    
    if existing:
        return {"success": False, "message": "Feedback already submitted for this event"}

    new_fb = Feedback(
        event_id=req.event_id,
        participant_id=req.participant_id,
        rating=req.rating,
        comment=req.comment
    )
    
    db.add(new_fb)
    db.commit()
    db.refresh(new_fb)
    
    return {"success": True, "message": "Feedback submitted successfully", "feedback_id": new_fb.id}

@router.get("/event/{event_id}")
async def get_event_feedback(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get feedback for a specific event"""
    feedbacks = db.query(Feedback).filter(Feedback.event_id == event_id).all()
    
    if not feedbacks:
        return {"success": True, "count": 0, "feedbacks": [], "average_rating": 0}
        
    avg = sum(f.rating for f in feedbacks) / len(feedbacks)
    
    return {
        "success": True, 
        "count": len(feedbacks), 
        "average_rating": round(avg, 1),
        "feedbacks": [{
            "id": f.id,
            "rating": f.rating,
            "comment": f.comment,
            "submitted_at": f.submitted_at.isoformat()
        } for f in feedbacks]
    }
