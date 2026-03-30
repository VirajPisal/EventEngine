"""
Event Management Routes
Endpoints for creating, listing, and managing events
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import re
import json

from db.base import get_db_context
from services.event_service import EventService
from services.registration_service import RegistrationService
from models.participant import Participant
from config.constants import EventType, EventState, ParticipantStatus
from api.deps import get_current_organizer
from utils.logger import logger


router = APIRouter()


# Request/Response Models
class EventCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=1000)
    event_type: str = Field(..., pattern="^(ONLINE|OFFLINE|HYBRID)$")
    start_time: datetime
    end_time: datetime
    venue: Optional[str] = None
    meeting_link: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=1)
    registration_deadline: Optional[datetime] = None
    custom_email_template: Optional[str] = None
    certificate_template: Optional[str] = None


class EventUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    venue: Optional[str] = None
    meeting_link: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=1)


class NLPParseRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000)


class EventTransitionRequest(BaseModel):
    new_state: str = Field(..., pattern="^(CREATED|REGISTRATION_OPEN|SCHEDULED|ATTENDANCE_OPEN|RUNNING|COMPLETED|ANALYZING|REPORT_GENERATED|CANCELLED)$")
    reason: Optional[str] = None
    triggered_by: str = "api"


# Endpoints
@router.post("/parse-natural-language")
async def parse_natural_language(
    request: NLPParseRequest,
    user: dict = Depends(get_current_organizer),
):
    """
    Parse natural language text to extract event fields.
    Tries OpenAI if API key is set, else uses regex+dateutil fallback.
    """
    text = request.text
    try:
        openai_key = __import__("os").getenv("OPENAI_API_KEY", "")
        if openai_key:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract event details from user text. Return ONLY valid JSON with keys: "
                            "name, description, event_type (ONLINE/OFFLINE/HYBRID), start_time (ISO8601), "
                            "end_time (ISO8601), venue, meeting_link, max_participants. "
                            "Use null for missing fields."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            return {"success": True, "source": "openai", "parsed": parsed}

        # Fallback: dateutil + regex
        from dateutil import parser as dateutil_parser
        parsed = {"name": None, "description": None, "event_type": "OFFLINE",
                  "start_time": None, "end_time": None, "venue": None,
                  "meeting_link": None, "max_participants": None}

        # Detect event type
        lower = text.lower()
        if "online" in lower:
            parsed["event_type"] = "ONLINE"
        elif "hybrid" in lower:
            parsed["event_type"] = "HYBRID"

        # Extract meeting link
        link_match = re.search(r"https?://\S+", text)
        if link_match:
            parsed["meeting_link"] = link_match.group(0)

        # Extract max participants
        cap_match = re.search(r"(\d+)\s*(?:participants|seats|capacity|people|max)", lower)
        if cap_match:
            parsed["max_participants"] = int(cap_match.group(1))

        # Try to find dates
        # First pass: full date+time patterns (ISO or written)
        date_candidates = re.findall(
            r"\d{4}-\d{2}-\d{2}[T ]?\d{2}:\d{2}(?::\d{2})?"
            r"|\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}(?:\s+(?:\d{1,2}:\d{2}|\d{1,2})\s*(?:AM|PM|am|pm))?"
            r"|\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}(?:\s+(?:\d{1,2}:\d{2}|\d{1,2})\s*(?:AM|PM|am|pm))?",
            text
        )
        times = []
        for dc in date_candidates:
            try:
                times.append(dateutil_parser.parse(dc, fuzzy=True))
            except (ValueError, OverflowError):
                pass

        # Second pass: if only one full date found, look for standalone time tokens
        # e.g. "3 PM" or "5:30 PM" associated with that date
        if len(times) == 1:
            base_date = times[0]
            time_tokens = re.findall(r"\b(\d{1,2}(?::\d{2})?)\s*(AM|PM|am|pm)\b", text)
            extra_times = []
            for tt in time_tokens:
                try:
                    t = dateutil_parser.parse(f"{tt[0]} {tt[1]}")
                    combined = base_date.replace(hour=t.hour, minute=t.minute, second=0)
                    extra_times.append(combined)
                except (ValueError, OverflowError):
                    pass
            extra_times = sorted(set(extra_times))
            if len(extra_times) >= 2:
                times = extra_times
            elif len(extra_times) == 1 and extra_times[0] != base_date:
                times = sorted([base_date, extra_times[0]])

        if len(times) >= 2:
            times.sort()
            parsed["start_time"] = times[0].isoformat()
            parsed["end_time"] = times[1].isoformat()
        elif len(times) == 1:
            from datetime import timedelta
            parsed["start_time"] = times[0].isoformat()
            parsed["end_time"] = (times[0] + timedelta(hours=2)).isoformat()

        # Use first sentence as name
        sentences = re.split(r"[.!\n]", text)
        if sentences:
            parsed["name"] = sentences[0].strip()[:200]
        parsed["description"] = text[:500]

        return {"success": True, "source": "fallback", "parsed": parsed}

    except Exception as e:
        logger.error(f"[API] NLP parse failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


@router.post("/", status_code=201)
async def create_event(event: EventCreateRequest):
    """
    Create a new event
    
    - **name**: Event name (3-200 chars)
    - **description**: Event description (10-1000 chars)
    - **event_type**: ONLINE, OFFLINE, or HYBRID
    - **start_time**: Event start datetime (ISO format)
    - **end_time**: Event end datetime (ISO format)
    - **venue**: Physical location (required for OFFLINE/HYBRID)
    - **meeting_link**: Online meeting URL (required for ONLINE/HYBRID)
    - **max_participants**: Maximum attendees (optional)
    """
    try:
        with get_db_context() as db:
            # Convert string to EventType enum
            event_type_enum = EventType[event.event_type]
            
            # Create event
            created_event = EventService.create_event(
                db=db,
                name=event.name,
                description=event.description,
                event_type=event_type_enum,
                start_time=event.start_time,
                end_time=event.end_time,
                venue=event.venue,
                meeting_link=event.meeting_link,
                max_participants=event.max_participants,
                registration_deadline=event.registration_deadline,
                custom_email_template=event.custom_email_template,
                certificate_template=event.certificate_template
            )
            
            logger.info(f"[API] Created event: {created_event.name} (ID: {created_event.id})")
            
            return {
                "success": True,
                "message": "Event created successfully",
                "event": {
                    "id": created_event.id,
                    "name": created_event.name,
                    "description": created_event.description,
                    "event_type": created_event.event_type.value,
                    "state": created_event.state.value,
                    "start_time": created_event.start_time.isoformat(),
                    "end_time": created_event.end_time.isoformat(),
                    "venue": created_event.venue,
                    "meeting_link": created_event.meeting_link,
                    "max_participants": created_event.max_participants,
                    "custom_email_template": created_event.custom_email_template,
                    "certificate_template": created_event.certificate_template,
                    "created_at": created_event.created_at.isoformat()
                }
            }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


@router.get("/")
async def list_events(
    state: Optional[str] = Query(None, description="Filter by state"),
    event_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List all events with optional filtering
    
    - **state**: Filter by event state (optional)
    - **event_type**: Filter by event type (optional)
    - **limit**: Max results to return (1-100, default 50)
    - **offset**: Number of results to skip (for pagination)
    """
    try:
        with get_db_context() as db:
            events = EventService.list_events(
                db=db,
                state=EventState[state] if state else None,
                event_type=EventType[event_type] if event_type else None,
                limit=limit,
                offset=offset
            )
            
            return {
                "success": True,
                "count": len(events),
                "events": [
                    {
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
                        "stats": {
                            "total_registered": db.query(Participant).filter(
                                Participant.event_id == event.id,
                                Participant.status != ParticipantStatus.CANCELLED
                            ).count(),
                            "total_confirmed": db.query(Participant).filter(
                                Participant.event_id == event.id,
                                Participant.is_confirmed == True
                            ).count(),
                            "total_attended": db.query(Participant).filter(
                                Participant.event_id == event.id,
                                Participant.status == ParticipantStatus.ATTENDED
                            ).count(),
                        }
                    }
                    for event in events
                ]
            }
    
    except Exception as e:
        logger.error(f"[API] Failed to list events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")


@router.get("/{event_id}")
async def get_event(event_id: int):
    """
    Get detailed information about a specific event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            event_data = EventService.get_event_with_stats(db, event_id)
            
            if not event_data:
                raise HTTPException(status_code=404, detail="Event not found")
            
            return {
                "success": True,
                "event": event_data
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get event: {str(e)}")


@router.post("/{event_id}/transition")
async def transition_event(event_id: int, request: EventTransitionRequest):
    """
    Manually transition an event to a new state
    
    - **event_id**: Event ID
    - **new_state**: Target state (e.g., REGISTRATION_OPEN, SCHEDULED)
    - **reason**: Optional reason for transition
    - **triggered_by**: Who triggered the transition (default: api)
    """
    try:
        with get_db_context() as db:
            # Convert string to EventState enum
            new_state_enum = EventState[request.new_state]
            
            result = EventService.transition_event_state(
                db=db,
                event_id=event_id,
                new_state=new_state_enum,
                reason=request.reason,
                triggered_by=request.triggered_by
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return {
                "success": True,
                "message": result["message"],
                "transition": {
                    "old_state": result["old_state"],
                    "new_state": result["new_state"],
                    "triggered_by": request.triggered_by
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to transition event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to transition event: {str(e)}")


@router.delete("/{event_id}")
async def cancel_event(event_id: int, reason: Optional[str] = None):
    """
    Cancel an event
    
    - **event_id**: Event ID
    - **reason**: Optional cancellation reason
    """
    try:
        with get_db_context() as db:
            result = EventService.transition_event_state(
                db=db,
                event_id=event_id,
                new_state=EventState.CANCELLED,
                reason=reason or "Event cancelled via API",
                triggered_by="api"
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return {
                "success": True,
                "message": "Event cancelled successfully",
                "event_id": event_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to cancel event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel event: {str(e)}")


@router.get("/{event_id}/participants")
async def get_event_participants(event_id: int):
    """
    Get all participants for an event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            participants = RegistrationService.get_event_participants(db, event_id)
            
            return {
                "success": True,
                "event_id": event_id,
                "count": len(participants),
                "participants": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "email": p.email,
                        "status": p.status.value,
                        "is_confirmed": p.is_confirmed,
                        "has_attended": p.has_attended,
                        "registered_at": p.registered_at.isoformat(),
                        "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None
                    }
                    for p in participants
                ]
            }
    
    except Exception as e:
        logger.error(f"[API] Failed to get participants for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get participants: {str(e)}")
