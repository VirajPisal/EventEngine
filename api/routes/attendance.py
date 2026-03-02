"""
Attendance Routes
Endpoints for QR code generation, OTP generation, and check-in
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from db.base import get_db_context
from services.attendance_service import AttendanceService
from models.attendance import Attendance
from models.participant import Participant
from utils.logger import logger


router = APIRouter()


# Request/Response Models
class GenerateQRRequest(BaseModel):
    participant_id: int = Field(..., ge=1)


class ValidateQRRequest(BaseModel):
    qr_token: str = Field(..., min_length=10)
    check_in_ip: Optional[str] = None
    check_in_device: Optional[str] = None


class GenerateOTPRequest(BaseModel):
    participant_id: int = Field(..., ge=1)


class ValidateOTPRequest(BaseModel):
    participant_id: int = Field(..., ge=1)
    otp: str = Field(..., min_length=6, max_length=6)


# Endpoints
@router.post("/qr/generate")
async def generate_qr_code(request: GenerateQRRequest):
    """
    Generate QR code for participant check-in
    
    - **participant_id**: Participant ID
    
    Returns QR code token and optional base64 image
    """
    try:
        with get_db_context() as db:
            result = AttendanceService.generate_qr_code(
                db=db,
                participant_id=request.participant_id
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Generated QR code for participant {request.participant_id}")
            
            return {
                "success": True,
                "message": "QR code generated successfully",
                "qr_code": {
                    "token": result["qr_code"]["token"],
                    "image_base64": result["qr_code"].get("image_base64"),
                    "expires_in_hours": result["qr_code"]["expires_in_hours"]
                },
                "participant_id": request.participant_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to generate QR code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")


@router.post("/qr/validate")
async def validate_qr_check_in(request: ValidateQRRequest):
    """
    Validate QR code and mark attendance
    
    - **qr_token**: QR code token (JWT)
    - **check_in_ip**: IP address (optional)
    - **check_in_device**: Device info (optional)
    
    Marks participant as ATTENDED if QR code is valid
    """
    try:
        with get_db_context() as db:
            result = AttendanceService.validate_qr_check_in(
                db=db,
                qr_token=request.qr_token,
                check_in_ip=request.check_in_ip,
                check_in_device=request.check_in_device
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] QR check-in successful for participant {result['participant']['id']}")
            
            return {
                "success": True,
                "message": result["message"],
                "participant": {
                    "id": result["participant"]["id"],
                    "name": result["participant"]["name"],
                    "status": result["participant"]["status"]
                },
                "attendance": {
                    "checked_in_at": result["attendance"]["checked_in_at"],
                    "check_in_method": result["attendance"]["check_in_method"]
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed QR check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed QR check-in: {str(e)}")


@router.post("/otp/generate")
async def generate_otp(request: GenerateOTPRequest):
    """
    Generate OTP for participant check-in
    
    - **participant_id**: Participant ID
    
    Returns 6-digit OTP code (sent via SMS if configured)
    """
    try:
        with get_db_context() as db:
            result = AttendanceService.generate_otp(
                db=db,
                participant_id=request.participant_id
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Generated OTP for participant {request.participant_id}")
            
            return {
                "success": True,
                "message": result.get("message", "OTP generated successfully"),
                "otp": result["otp"],
                "expires_at": result["expires_at"].isoformat() if hasattr(result["expires_at"], 'isoformat') else str(result["expires_at"]),
                "sms_sent": result.get("sms_sent", False),
                "participant_id": request.participant_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to generate OTP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate OTP: {str(e)}")


@router.post("/otp/validate")
async def validate_otp_check_in(request: ValidateOTPRequest):
    """
    Validate OTP and mark attendance
    
    - **participant_id**: Participant ID
    - **otp**: 6-digit OTP code
    
    Marks participant as ATTENDED if OTP is valid
    """
    try:
        with get_db_context() as db:
            result = AttendanceService.validate_otp_check_in(
                db=db,
                participant_id=request.participant_id,
                otp_code=request.otp
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] OTP check-in successful for participant {request.participant_id}")
            
            return {
                "success": True,
                "message": result["message"],
                "participant": {
                    "id": result["participant"]["id"],
                    "name": result["participant"]["name"],
                    "status": result["participant"]["status"]
                },
                "attendance": {
                    "checked_in_at": result["attendance"]["checked_in_at"],
                    "check_in_method": result["attendance"]["check_in_method"]
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed OTP check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed OTP check-in: {str(e)}")


@router.get("/event/{event_id}")
async def get_event_attendance(event_id: int):
    """
    Get attendance records for an event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            # Query attendance records with participant details
            attendance_records = db.query(Attendance).filter(
                Attendance.event_id == event_id
            ).join(Participant).all()
            
            return {
                "success": True,
                "event_id": event_id,
                "count": len(attendance_records),
                "attendance": [
                    {
                        "id": record.id,
                        "participant_id": record.participant_id,
                        "participant_name": record.participant.name,
                        "participant_email": record.participant.email,
                        "checked_in_at": record.checked_in_at.isoformat(),
                        "check_in_method": record.check_in_method if isinstance(record.check_in_method, str) else record.check_in_method.value,
                        "check_in_ip": record.check_in_ip,
                        "check_in_device": record.check_in_device
                    }
                    for record in attendance_records
                ]
            }
    
    except Exception as e:
        logger.error(f"[API] Failed to get attendance for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get attendance: {str(e)}")


@router.get("/event/{event_id}/stats")
async def get_attendance_stats(event_id: int):
    """
    Get quick attendance statistics for an event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            stats = AttendanceService.get_attendance_stats(
                db=db,
                event_id=event_id
            )
            
            if not stats:
                raise HTTPException(status_code=404, detail="Event not found or no attendance data")
            
            return {
                "success": True,
                "event_id": event_id,
                "stats": stats
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get attendance stats for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get attendance stats: {str(e)}")
