from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from services.google_calendar_service import GoogleCalendarService
from api.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class MeetLinkRequest(BaseModel):
    event_name: str
    start_time: str
    duration_minutes: Optional[int] = 60

@router.post("/generate-meet-link")
async def generate_meet_link(request: MeetLinkRequest, current_user=Depends(get_current_user)):
    """
    Generates a real Google Meet link via Google Calendar API.
    Requires credentials.json and initial user authentication.
    """
    try:
        # Parse ISO string to datetime
        dt = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
        
        link = GoogleCalendarService.create_meet_link(
            event_name=request.event_name,
            start_time=dt,
            duration_minutes=request.duration_minutes
        )
        
        if not link:
            # Check if a debug log was created
            error_msg = "Failed to generate link. Ensure Google Calendar API is enabled and credentials are correct."
            try:
                if os.path.exists("google_api_debug.log"):
                    with open("google_api_debug.log", "r") as f:
                        lines = f.readlines()
                        if lines:
                            error_msg = f"Google API Error: {lines[-1].strip()}"
            except: pass

            return {
                "success": False, 
                "message": error_msg,
                "is_setup_required": True
            }
            
        return {"success": True, "meet_link": link}
        
    except Exception as e:
        logger.error(f"Meet link generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
