"""
Registration Routes
Endpoints for participant registration and confirmation
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from sqlalchemy.orm import Session

from db.base import get_db, get_db_context
from services.registration_service import RegistrationService
from services.calendar_service import CalendarService
from models.participant import Participant
from models.event import Event
from utils.logger import logger

router = APIRouter()


# Request/Response Models
class RegisterParticipantRequest(BaseModel):
    event_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)


class ConfirmParticipantRequest(BaseModel):
    participant_id: int = Field(..., ge=1)


# Endpoints
@router.post("/register", status_code=201)
async def register_participant(request: RegisterParticipantRequest):
    """
    Register a participant for an event
    
    - **event_id**: Event ID to register for
    - **name**: Participant name (2-100 chars)
    - **email**: Valid email address
    - **phone**: Optional phone number
    
    Returns participant details with QR code for attendance
    """
    try:
        with get_db_context() as db:
            result = RegistrationService.register_participant(
                db=db,
                event_id=request.event_id,
                name=request.name,
                email=request.email,
                phone=request.phone
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Registered participant: {request.name} for event {request.event_id}")
            
            return {
                "success": True,
                "message": result["message"],
                "participant": {
                    "id": result["participant"]["id"],
                    "name": result["participant"]["name"],
                    "email": result["participant"]["email"],
                    "phone": result["participant"].get("phone"),
                    "status": result["participant"]["status"],
                    "qr_token": result["participant"].get("qr_token"),
                    "registered_at": result["participant"]["registered_at"]
                },
                "email_sent": result.get("email_sent", False)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to register participant: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register participant: {str(e)}")


@router.post("/confirm")
async def confirm_participant(request: ConfirmParticipantRequest):
    """
    Confirm a participant's registration
    
    - **participant_id**: Participant ID to confirm
    
    Usually triggered when participant clicks confirmation link in email
    """
    try:
        with get_db_context() as db:
            result = RegistrationService.confirm_participant(
                db=db,
                participant_id=request.participant_id
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Confirmed participant: {request.participant_id}")
            
            return {
                "success": True,
                "message": result["message"],
                "participant": {
                    "id": result["participant"]["id"],
                    "name": result["participant"]["name"],
                    "status": result["participant"]["status"],
                    "confirmed_at": result["participant"]["confirmed_at"]
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to confirm participant: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm participant: {str(e)}")


@router.get("/confirm/{participant_id}", response_class=HTMLResponse)
async def confirm_participant_via_link(participant_id: int):
    """
    Self-confirmation link sent in registration email.
    Student clicks this link to confirm their attendance.
    Returns a simple HTML success/error page.
    """
    try:
        with get_db_context() as db:
            result = RegistrationService.confirm_participant(db=db, participant_id=participant_id)

        if result["success"]:
            name = result["participant"]["name"]
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Attendance Confirmed!</title>
  <style>
    body {{ font-family: Arial, sans-serif; display: flex; justify-content: center;
           align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }}
    .box {{ background: white; padding: 2.5rem 3rem; border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,.1); text-align: center; max-width: 420px; }}
    .icon {{ font-size: 3rem; }}
    h1 {{ color: #22c55e; margin: 0.5rem 0; }}
    p {{ color: #555; }}
    a {{ display: inline-block; margin-top: 1.5rem; padding: 0.6rem 1.5rem;
         background: #4f46e5; color: white; border-radius: 6px; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">✅</div>
    <h1>You're Confirmed!</h1>
    <p>Hi <strong>{name}</strong>, your attendance has been confirmed successfully.</p>
    <p>We look forward to seeing you at the event!</p>
    <a href="/frontend/index.html">Go to EventEngine</a>
  </div>
</body>
</html>""", status_code=200)
        else:
            # Already confirmed or not found
            msg = result["message"]
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Confirmation Status</title>
  <style>
    body {{ font-family: Arial, sans-serif; display: flex; justify-content: center;
           align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }}
    .box {{ background: white; padding: 2.5rem 3rem; border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,.1); text-align: center; max-width: 420px; }}
    .icon {{ font-size: 3rem; }}
    h1 {{ color: #f59e0b; margin: 0.5rem 0; }}
    p {{ color: #555; }}
    a {{ display: inline-block; margin-top: 1.5rem; padding: 0.6rem 1.5rem;
         background: #4f46e5; color: white; border-radius: 6px; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">ℹ️</div>
    <h1>Already Confirmed</h1>
    <p>{msg}</p>
    <a href="/frontend/index.html">Go to EventEngine</a>
  </div>
</body>
</html>""", status_code=200)

    except Exception as e:
        logger.error(f"[API] Confirm link error for participant {participant_id}: {e}")
        raise HTTPException(status_code=500, detail="Confirmation failed")


@router.get("/{participant_id}")
async def get_participant(participant_id: int):
    """
    Get participant details
    
    - **participant_id**: Participant ID
    """
    try:
        with get_db_context() as db:
            participant = db.query(Participant).filter(Participant.id == participant_id).first()
            
            if not participant:
                raise HTTPException(status_code=404, detail="Participant not found")
            
            return {
                "success": True,
                "participant": {
                    "id": participant.id,
                    "event_id": participant.event_id,
                    "name": participant.name,
                    "email": participant.email,
                    "phone": participant.phone,
                    "status": participant.status.value,
                    "is_confirmed": participant.is_confirmed,
                    "confirmed_at": participant.confirmed_at.isoformat() if participant.confirmed_at else None,
                    "registered_at": participant.registered_at.isoformat(),
                    "qr_token": participant.qr_token
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get participant {participant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get participant: {str(e)}")


@router.delete("/{participant_id}")
async def cancel_registration(participant_id: int):
    """
    Cancel a participant's registration
    
    - **participant_id**: Participant ID
    """
    try:
        with get_db_context() as db:
            result = RegistrationService.cancel_registration(
                db=db,
                participant_id=participant_id
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Cancelled registration: {participant_id}")
            
            return {
                "success": True,
                "message": result["message"],
                "participant_id": participant_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to cancel registration {participant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel registration: {str(e)}")


@router.post("/{participant_id}/resend-confirmation")
async def resend_confirmation(participant_id: int):
    """
    Resend confirmation email to participant

    - **participant_id**: Participant ID
    """
    try:
        with get_db_context() as db:
            result = RegistrationService.resend_confirmation_email(
                db=db,
                participant_id=participant_id
            )

            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])

            return {
                "success": True,
                "message": "Confirmation email resent successfully",
                "email_sent": result.get("email_sent", False)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to resend confirmation for participant {participant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resend confirmation: {str(e)}")


@router.get("/participant/{email}")
async def get_participant_registrations(email: str):
    """
    Get all registrations for a participant by email

    - **email**: Participant email address

    Returns all events the participant has registered for
    """
    try:
        from models.event import Event

        with get_db_context() as db:
            # Get all participants with this email
            participants = db.query(Participant).filter(Participant.email == email).all()

            if not participants:
                return {
                    "success": True,
                    "count": 0,
                    "registrations": []
                }

            # Build response with event details
            registrations = []
            for p in participants:
                event = db.query(Event).filter(Event.id == p.event_id).first()
                registrations.append({
                    "id": p.id,
                    "event_id": p.event_id,
                    "event_name": event.name if event else None,
                    "name": p.name,
                    "email": p.email,
                    "phone": p.phone,
                    "status": p.status.value,
                    "is_confirmed": p.is_confirmed,
                    "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
                    "registered_at": p.registered_at.isoformat(),
                    "qr_token": p.qr_token,
                    "event_start_time": event.start_time.isoformat() if event else None,
                    "event_end_time": event.end_time.isoformat() if event and event.end_time else (event.start_time.isoformat() if event else None),
                    "event_location": (event.venue or event.meeting_link or "Online") if event else "N/A",
                    "meeting_link": event.meeting_link if event else None,
                    "event_state": event.state.value if event else None,
                    "event_description": event.description if event else ""
                })

            return {
                "success": True,
                "count": len(registrations),
                "registrations": registrations
            }

    except Exception as e:
        logger.error(f"[API] Failed to get registrations for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get registrations: {str(e)}")


@router.get("/{registration_id}/ics")
async def get_registration_ics(
    registration_id: int
):
    """Generate and return an .ics calendar file for a registration"""
    with get_db_context() as db:
        participant = db.query(Participant).filter(Participant.id == registration_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Registration not found")
            
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
            
        ics_content = CalendarService.generate_ics_content(
            name=event.name,
            description=event.description or f"Event {event.name}",
            start_time=event.start_time,
            end_time=event.end_time or event.start_time,
            location=event.venue or event.meeting_link or "Online",
            uid=f"event-{event.id}-part-{participant.id}"
        )
        
        return Response(
            content=ics_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=event_{event.id}.ics"
            }
        )
