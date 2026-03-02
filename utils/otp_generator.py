"""
OTP Generator - One-Time Password generation and validation
Backup attendance verification method when QR codes aren't available
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from utils.logger import logger


class OTPGenerator:
    """Generate and validate OTP codes for attendance"""
    
    def __init__(self):
        """Initialize OTP generator"""
        self.otp_length = 6
        self.otp_expiry_minutes = 15
    
    def generate_otp(self) -> str:
        """
        Generate a random 6-digit OTP code
        
        Returns:
            6-digit OTP string
        """
        # Generate 6-digit numeric OTP
        otp = ''.join(random.choices(string.digits, k=self.otp_length))
        
        logger.debug(f"[OTP] Generated OTP code")
        
        return otp
    
    def get_otp_expiry_time(self) -> datetime:
        """
        Get OTP expiry timestamp
        
        Returns:
            Expiry datetime (15 minutes from now)
        """
        return datetime.now(timezone.utc) + timedelta(minutes=self.otp_expiry_minutes)
    
    def validate_otp(
        self,
        provided_otp: str,
        stored_otp: str,
        otp_expires_at: datetime
    ) -> Dict:
        """
        Validate an OTP code
        
        Args:
            provided_otp: OTP code provided by user
            stored_otp: OTP code stored in database
            otp_expires_at: OTP expiry timestamp
        
        Returns:
            Dict with validation result
        """
        # Check if OTP exists
        if not stored_otp or not otp_expires_at:
            logger.warning(f"[OTP] No OTP found for validation")
            return {
                'valid': False,
                'reason': 'No OTP generated for this participant'
            }
        
        # Check if expired
        now = datetime.now(timezone.utc)
        
        # Ensure otp_expires_at is timezone-aware
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        
        if now > otp_expires_at:
            logger.warning(f"[OTP] OTP expired")
            return {
                'valid': False,
                'reason': 'OTP expired',
                'expired_at': otp_expires_at.isoformat()
            }
        
        # Check if OTP matches
        if provided_otp.strip() != stored_otp.strip():
            logger.warning(f"[OTP] OTP mismatch")
            return {
                'valid': False,
                'reason': 'Invalid OTP code'
            }
        
        logger.info(f"[OTP] OTP validated successfully")
        
        return {
            'valid': True,
            'message': 'OTP validated successfully'
        }
    
    def generate_otp_with_expiry(self) -> Dict:
        """
        Generate OTP with expiry information
        
        Returns:
            Dict with OTP code and expiry time
        """
        otp = self.generate_otp()
        expires_at = self.get_otp_expiry_time()
        
        return {
            'otp': otp,
            'expires_at': expires_at,
            'expiry_minutes': self.otp_expiry_minutes
        }
    
    def is_otp_expired(self, otp_expires_at: Optional[datetime]) -> bool:
        """
        Check if OTP is expired
        
        Args:
            otp_expires_at: OTP expiry timestamp
        
        Returns:
            True if expired, False otherwise
        """
        if not otp_expires_at:
            return True
        
        now = datetime.now(timezone.utc)
        
        # Ensure timezone-aware
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        
        return now > otp_expires_at
    
    def get_remaining_time(self, otp_expires_at: datetime) -> Optional[int]:
        """
        Get remaining time for OTP in seconds
        
        Args:
            otp_expires_at: OTP expiry timestamp
        
        Returns:
            Remaining seconds, or None if expired
        """
        if not otp_expires_at:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Ensure timezone-aware
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        
        if now > otp_expires_at:
            return None
        
        remaining_seconds = int((otp_expires_at - now).total_seconds())
        
        return remaining_seconds


# Singleton instance
_otp_generator_instance = None


def get_otp_generator() -> OTPGenerator:
    """Get or create the singleton OTP generator instance"""
    global _otp_generator_instance
    
    if _otp_generator_instance is None:
        _otp_generator_instance = OTPGenerator()
    
    return _otp_generator_instance
