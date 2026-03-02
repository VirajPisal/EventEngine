"""
Attendance Service - Manage event check-ins via QR code or OTP
Validates attendance and tracks who showed up
"""
from typing import Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.event import Event
from models.participant import Participant
from models.attendance import Attendance
from config.constants import EventState, ParticipantStatus, AttendanceMethod
from utils.qr_generator import get_qr_generator
from utils.otp_generator import get_otp_generator
from utils.logger import logger


class AttendanceService:
    """Service for managing event attendance check-ins"""
    
    @staticmethod
    def generate_qr_code(
        db: Session,
        participant_id: int
    ) -> Dict:
        """
        Generate QR code for a participant
        
        Args:
            db: Database session
            participant_id: Participant ID
        
        Returns:
            Dict with QR code data
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": "Participant not found"
            }
        
        qr_generator = get_qr_generator()
        
        # Generate QR code
        qr_data = qr_generator.generate_attendance_qr(
            participant_id=participant.id,
            event_id=participant.event_id,
            expiry_hours=24
        )
        
        # Store QR token in database
        participant.qr_token = qr_data['token']
        db.commit()
        
        logger.info(f"[ATTENDANCE] Generated QR code for participant {participant_id}")
        
        return {
            "success": True,
            "qr_code": qr_data,
            "participant_id": participant_id,
            "event_id": participant.event_id
        }
    
    @staticmethod
    def generate_otp(
        db: Session,
        participant_id: int
    ) -> Dict:
        """
        Generate OTP for a participant
        
        Args:
            db: Database session
            participant_id: Participant ID
        
        Returns:
            Dict with OTP data
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": "Participant not found"
            }
        
        otp_generator = get_otp_generator()
        
        # Generate OTP
        otp_data = otp_generator.generate_otp_with_expiry()
        
        # Store OTP in database
        participant.otp = otp_data['otp']
        participant.otp_expires_at = otp_data['expires_at']
        db.commit()
        
        logger.info(f"[ATTENDANCE] Generated OTP for participant {participant_id}")
        
        return {
            "success": True,
            "otp": otp_data['otp'],
            "expires_at": otp_data['expires_at'],
            "expiry_minutes": otp_data['expiry_minutes'],
            "participant_id": participant_id,
            "event_id": participant.event_id
        }
    
    @staticmethod
    def validate_qr_check_in(
        db: Session,
        qr_token: str,
        check_in_ip: Optional[str] = None,
        check_in_device: Optional[str] = None
    ) -> Dict:
        """
        Validate QR code and mark attendance
        
        Args:
            db: Database session
            qr_token: QR code JWT token
            check_in_ip: IP address of check-in (optional)
            check_in_device: Device info (optional)
        
        Returns:
            Dict with validation result
        """
        qr_generator = get_qr_generator()
        
        # Validate QR token
        validation = qr_generator.validate_qr_token(qr_token)
        
        if not validation['valid']:
            logger.warning(f"[ATTENDANCE] Invalid QR token: {validation['reason']}")
            return {
                "success": False,
                "message": f"Invalid QR code: {validation['reason']}"
            }
        
        participant_id = validation['participant_id']
        event_id = validation['event_id']
        
        # Get participant and event
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not participant or not event:
            return {
                "success": False,
                "message": "Participant or event not found"
            }
        
        # Check if event allows attendance
        if event.state not in [EventState.ATTENDANCE_OPEN, EventState.RUNNING]:
            return {
                "success": False,
                "message": f"Event is not open for attendance (current state: {event.state.value})"
            }
        
        # Check if already attended
        existing = db.query(Attendance).filter(
            Attendance.participant_id == participant_id,
            Attendance.event_id == event_id
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "Attendance already recorded",
                "checked_in_at": existing.checked_in_at.isoformat()
            }
        
        # Record attendance
        attendance = Attendance(
            event_id=event_id,
            participant_id=participant_id,
            checked_in_at=datetime.now(timezone.utc),
            check_in_method=AttendanceMethod.QR_CODE,
            is_valid=True,
            validation_notes="QR code validated successfully",
            check_in_ip=check_in_ip,
            check_in_device=check_in_device
        )
        
        db.add(attendance)
        
        # Update participant status
        participant.status = ParticipantStatus.ATTENDED
        
        db.commit()
        
        logger.info(f"[ATTENDANCE] QR check-in successful for participant {participant_id}, event {event_id}")
        
        # Log activity
        logger.log_attendance(
            event_id=event_id,
            event_name=event.name,
            participant_name=participant.name,
            check_in_method="QR_CODE"
        )
        
        return {
            "success": True,
            "message": "Attendance recorded successfully",
            "participant": {
                "id": participant.id,
                "name": participant.name,
                "email": participant.email,
                "status": participant.status.value
            },
            "event": {
                "id": event.id,
                "name": event.name
            },
            "attendance": {
                "checked_in_at": attendance.checked_in_at.isoformat(),
                "check_in_method": "QR_CODE"
            }
        }
    
    @staticmethod
    def validate_otp_check_in(
        db: Session,
        participant_id: int,
        otp_code: str,
        check_in_ip: Optional[str] = None,
        check_in_device: Optional[str] = None
    ) -> Dict:
        """
        Validate OTP and mark attendance
        
        Args:
            db: Database session
            participant_id: Participant ID
            otp_code: OTP code provided by participant
            check_in_ip: IP address of check-in (optional)
            check_in_device: Device info (optional)
        
        Returns:
            Dict with validation result
        """
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            return {
                "success": False,
                "message": "Participant not found"
            }
        
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        
        if not event:
            return {
                "success": False,
                "message": "Event not found"
            }
        
        # Check if event allows attendance
        if event.state not in [EventState.ATTENDANCE_OPEN, EventState.RUNNING]:
            return {
                "success": False,
                "message": f"Event is not open for attendance (current state: {event.state.value})"
            }
        
        # Validate OTP
        otp_generator = get_otp_generator()
        validation = otp_generator.validate_otp(
            otp_code,
            participant.otp,
            participant.otp_expires_at
        )
        
        if not validation['valid']:
            logger.warning(f"[ATTENDANCE] Invalid OTP for participant {participant_id}: {validation['reason']}")
            return {
                "success": False,
                "message": f"Invalid OTP: {validation['reason']}"
            }
        
        # Check if already attended
        existing = db.query(Attendance).filter(
            Attendance.participant_id == participant_id,
            Attendance.event_id == event.id
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "Attendance already recorded",
                "checked_in_at": existing.checked_in_at.isoformat()
            }
        
        # Record attendance
        attendance = Attendance(
            event_id=event.id,
            participant_id=participant_id,
            checked_in_at=datetime.now(timezone.utc),
            check_in_method=AttendanceMethod.OTP,
            is_valid=True,
            validation_notes="OTP validated successfully",
            check_in_ip=check_in_ip,
            check_in_device=check_in_device
        )
        
        db.add(attendance)
        
        # Update participant status
        participant.status = ParticipantStatus.ATTENDED
        
        # Clear OTP after successful use
        participant.otp = None
        participant.otp_expires_at = None
        
        db.commit()
        
        logger.info(f"[ATTENDANCE] OTP check-in successful for participant {participant_id}, event {event.id}")
        
        # Log activity
        logger.log_attendance(
            event_id=event.id,
            event_name=event.name,
            participant_name=participant.name,
            check_in_method="OTP"
        )
        
        return {
            "success": True,
            "message": "Attendance recorded successfully",
            "participant": {
                "id": participant.id,
                "name": participant.name,
                "email": participant.email,
                "status": participant.status.value
            },
            "event": {
                "id": event.id,
                "name": event.name
            },
            "attendance": {
                "checked_in_at": attendance.checked_in_at.isoformat(),
                "check_in_method": "OTP"
            }
        }
    
    @staticmethod
    def get_attendance_stats(
        db: Session,
        event_id: int
    ) -> Dict:
        """
        Get attendance statistics for an event
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Dict with attendance stats
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            return {
                "success": False,
                "message": "Event not found"
            }
        
        # Count participants
        total_registered = db.query(Participant).filter(
            Participant.event_id == event_id,
            Participant.status != ParticipantStatus.CANCELLED
        ).count()
        
        total_confirmed = db.query(Participant).filter(
            Participant.event_id == event_id,
            Participant.is_confirmed == True
        ).count()
        
        total_attended = db.query(Attendance).filter(
            Attendance.event_id == event_id,
            Attendance.is_valid == True
        ).count()
        
        # Calculate rates
        attendance_rate = (total_attended / total_registered * 100) if total_registered > 0 else 0
        no_show_count = total_confirmed - total_attended
        no_show_rate = (no_show_count / total_confirmed * 100) if total_confirmed > 0 else 0
        
        return {
            "success": True,
            "event_id": event_id,
            "event_name": event.name,
            "event_state": event.state.value,
            "total_registered": total_registered,
            "total_confirmed": total_confirmed,
            "total_attended": total_attended,
            "attendance_rate": round(attendance_rate, 1),
            "no_show_count": no_show_count,
            "no_show_rate": round(no_show_rate, 1)
        }
