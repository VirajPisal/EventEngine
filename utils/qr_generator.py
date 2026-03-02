"""
QR Code Generator - Secure QR codes for attendance verification
Uses JWT tokens to ensure QR codes are authentic and time-limited
"""
import jwt
import io
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

from config.settings import settings
from utils.logger import logger


class QRCodeGenerator:
    """Generate and validate secure QR codes for event attendance"""
    
    def __init__(self):
        """Initialize QR code generator"""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
    
    def generate_qr_token(
        self,
        participant_id: int,
        event_id: int,
        expiry_hours: int = 24
    ) -> str:
        """
        Generate a secure JWT token for QR code
        
        Args:
            participant_id: Participant ID
            event_id: Event ID
            expiry_hours: Token expiry in hours (default: 24)
        
        Returns:
            JWT token string
        """
        payload = {
            'participant_id': participant_id,
            'event_id': event_id,
            'issued_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat(),
            'type': 'attendance_qr'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"[QR] Generated token for participant {participant_id}, event {event_id}")
        
        return token
    
    def validate_qr_token(
        self,
        token: str
    ) -> Dict:
        """
        Validate a QR code token
        
        Args:
            token: JWT token string
        
        Returns:
            Dict with validation result and payload
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiry
            expires_at = datetime.fromisoformat(payload['expires_at'])
            now = datetime.now(timezone.utc)
            
            if now > expires_at:
                return {
                    'valid': False,
                    'reason': 'Token expired',
                    'expired_at': expires_at.isoformat()
                }
            
            # Check token type
            if payload.get('type') != 'attendance_qr':
                return {
                    'valid': False,
                    'reason': 'Invalid token type'
                }
            
            logger.debug(f"[QR] Token validated for participant {payload['participant_id']}")
            
            return {
                'valid': True,
                'participant_id': payload['participant_id'],
                'event_id': payload['event_id'],
                'issued_at': payload['issued_at'],
                'expires_at': payload['expires_at']
            }
        
        except jwt.ExpiredSignatureError:
            logger.warning(f"[QR] Token expired")
            return {
                'valid': False,
                'reason': 'Token expired'
            }
        
        except jwt.InvalidTokenError as e:
            logger.warning(f"[QR] Invalid token: {str(e)}")
            return {
                'valid': False,
                'reason': f'Invalid token: {str(e)}'
            }
        
        except Exception as e:
            logger.error(f"[QR] Token validation error: {str(e)}")
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}'
            }
    
    def generate_qr_code_image(
        self,
        token: str,
        size: int = 300
    ) -> str:
        """
        Generate QR code image from token
        
        Args:
            token: JWT token string
            size: QR code size in pixels (default: 300)
        
        Returns:
            Base64-encoded PNG image string
        """
        if not QRCODE_AVAILABLE:
            logger.warning("[QR] qrcode library not installed - returning placeholder")
            return None
            
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(token)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Encode to base64
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            logger.debug(f"[QR] Generated QR code image (size: {len(img_base64)} bytes)")
            
            return img_base64
        
        except ImportError:
            logger.warning("[QR] qrcode library not installed - cannot generate image")
            return None
        
        except Exception as e:
            logger.error(f"[QR] Error generating QR code image: {str(e)}")
            return None
    
    def generate_attendance_qr(
        self,
        participant_id: int,
        event_id: int,
        expiry_hours: int = 24
    ) -> Dict:
        """
        Generate complete attendance QR code with token and image
        
        Args:
            participant_id: Participant ID
            event_id: Event ID
            expiry_hours: Token expiry in hours
        
        Returns:
            Dict with token and image data
        """
        # Generate token
        token = self.generate_qr_token(participant_id, event_id, expiry_hours)
        
        # Generate image
        image_base64 = self.generate_qr_code_image(token)
        
        return {
            'token': token,
            'image_base64': image_base64,
            'image_available': image_base64 is not None,
            'participant_id': participant_id,
            'event_id': event_id,
            'expires_in_hours': expiry_hours
        }


# Singleton instance
_qr_generator_instance = None


def get_qr_generator() -> QRCodeGenerator:
    """Get or create the singleton QR code generator instance"""
    global _qr_generator_instance
    
    if _qr_generator_instance is None:
        _qr_generator_instance = QRCodeGenerator()
    
    return _qr_generator_instance
