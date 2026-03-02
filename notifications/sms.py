"""
SMS Notifications - Twilio Integration
Sends SMS reminders, OTP codes, and urgent notifications
"""
from typing import Dict
from datetime import datetime

from config.settings import settings
from utils.logger import logger


class SMSService:
    """SMS service using Twilio API"""
    
    def __init__(self):
        """Initialize SMS service with Twilio credentials"""
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self._check_configuration()
    
    def _check_configuration(self):
        """Check if SMS service is configured"""
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning("[SMS] Twilio credentials not configured - SMS will be simulated")
            self.configured = False
        else:
            self.configured = True
            logger.info("[SMS] Twilio configured successfully")
    
    def send_sms(
        self,
        to_phone: str,
        message: str
    ) -> Dict:
        """
        Send an SMS via Twilio
        
        Args:
            to_phone: Recipient phone number (E.164 format: +1234567890)
            message: SMS message content
        
        Returns:
            Dict with success status and message
        """
        if not self.configured:
            # Simulate SMS sending when not configured
            logger.info(f"[SMS] [SIMULATED] To: {to_phone} | Message: {message[:50]}...")
            return {
                "success": True,
                "simulated": True,
                "message": "SMS simulated (Twilio not configured)"
            }
        
        try:
            # Import Twilio library
            from twilio.rest import Client
            
            # Create Twilio client
            client = Client(self.account_sid, self.auth_token)
            
            # Send SMS
            twilio_message = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone
            )
            
            logger.info(f"[SMS] Sent to {to_phone} | SID: {twilio_message.sid} | Status: {twilio_message.status}")
            
            return {
                "success": True,
                "simulated": False,
                "message_sid": twilio_message.sid,
                "status": twilio_message.status,
                "message": "SMS sent successfully"
            }
        
        except ImportError:
            # Twilio library not installed - simulate
            logger.warning("[SMS] Twilio library not installed - simulating SMS")
            logger.info(f"[SMS] [SIMULATED] To: {to_phone} | Message: {message[:50]}...")
            return {
                "success": True,
                "simulated": True,
                "message": "SMS simulated (Twilio library not installed)"
            }
        
        except Exception as e:
            logger.error(f"[SMS] Failed to send to {to_phone}: {str(e)}")
            return {
                "success": False,
                "simulated": False,
                "message": f"SMS failed: {str(e)}"
            }
    
    def send_otp(
        self,
        to_phone: str,
        participant_name: str,
        otp_code: str,
        event_name: str
    ) -> Dict:
        """
        Send OTP code via SMS
        
        Args:
            to_phone: Participant phone number
            participant_name: Participant name
            otp_code: 6-digit OTP code
            event_name: Event name
        
        Returns:
            Dict with success status
        """
        message = f"""
{participant_name}, your attendance OTP for {event_name}: {otp_code}

Valid for 15 minutes. Do not share this code.

- EventEngine
        """.strip()
        
        result = self.send_sms(to_phone, message)
        
        if result['success']:
            logger.info(f"[SMS] OTP sent to {to_phone} for event: {event_name}")
        
        return result
    
    def send_reminder(
        self,
        to_phone: str,
        participant_name: str,
        event_name: str,
        event_start_time: datetime,
        hours_until: int
    ) -> Dict:
        """
        Send event reminder via SMS
        
        Args:
            to_phone: Participant phone number
            participant_name: Participant name
            event_name: Event name
            event_start_time: Event start time
            hours_until: Hours until event starts
        
        Returns:
            Dict with success status
        """
        if hours_until < 1:
            time_text = "starting soon"
        elif hours_until == 1:
            time_text = "in 1 hour"
        elif hours_until < 24:
            time_text = f"in {hours_until} hours"
        else:
            days = hours_until // 24
            time_text = f"in {days} day{'s' if days > 1 else ''}"
        
        message = f"""
{participant_name}, reminder: {event_name} is {time_text}.

Date: {event_start_time.strftime('%b %d at %I:%M %p')}

Please confirm your attendance.

- EventEngine
        """.strip()
        
        result = self.send_sms(to_phone, message)
        
        if result['success']:
            logger.info(f"[SMS] Reminder sent to {to_phone} for event: {event_name}")
        
        return result
    
    def send_urgent_notification(
        self,
        to_phone: str,
        participant_name: str,
        event_name: str,
        notification_message: str
    ) -> Dict:
        """
        Send urgent notification via SMS
        
        Args:
            to_phone: Participant phone number
            participant_name: Participant name
            event_name: Event name
            notification_message: Notification message
        
        Returns:
            Dict with success status
        """
        message = f"""
URGENT: {participant_name}

{notification_message}

Event: {event_name}

- EventEngine
        """.strip()
        
        result = self.send_sms(to_phone, message)
        
        if result['success']:
            logger.info(f"[SMS] Urgent notification sent to {to_phone}")
        
        return result


# Singleton instance
_sms_service_instance = None


def get_sms_service() -> SMSService:
    """Get or create the singleton SMS service instance"""
    global _sms_service_instance
    
    if _sms_service_instance is None:
        _sms_service_instance = SMSService()
    
    return _sms_service_instance
