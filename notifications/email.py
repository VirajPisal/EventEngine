"""
Email Notifications - SendGrid Integration
Sends confirmation emails, reminders, and event notifications
"""
from typing import Dict, Optional, List
from datetime import datetime
import os

from config.settings import settings
from utils.logger import logger


class EmailService:
    """Email service using SendGrid API"""
    
    def __init__(self):
        """Initialize email service with SendGrid credentials"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self._check_configuration()
    
    def _check_configuration(self):
        """Check if email service is configured"""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("[EMAIL] SendGrid credentials not configured - emails will be simulated")
            self.configured = False
        else:
            self.configured = True
            logger.info("[EMAIL] SendGrid configured successfully")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send an email via SendGrid
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of attachments (optional)
        
        Returns:
            Dict with success status and message
        """
        if not self.configured:
            # Simulate email sending when not configured
            logger.info(f"[EMAIL] [SIMULATED] To: {to_email} | Subject: {subject}")
            logger.debug(f"[EMAIL] [SIMULATED] Body: {body_text[:100]}...")
            return {
                "success": True,
                "simulated": True,
                "message": "Email simulated (SendGrid not configured)"
            }
        
        try:
            # Import SendGrid library
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
            
            # Create message
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body_text,
                html_content=body_html or body_text
            )
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    attached_file = Attachment(
                        FileContent(attachment['content']),
                        FileName(attachment['filename']),
                        FileType(attachment.get('type', 'application/octet-stream')),
                        Disposition('attachment')
                    )
                    message.attachment = attached_file
            
            # Send email
            sg = SendGridAPIClient(self.smtp_user)
            response = sg.send(message)
            
            logger.info(f"[EMAIL] Sent to {to_email} | Subject: {subject} | Status: {response.status_code}")
            
            return {
                "success": True,
                "simulated": False,
                "message": f"Email sent successfully (Status: {response.status_code})"
            }
        
        except ImportError:
            # SendGrid library not installed - simulate
            logger.warning("[EMAIL] SendGrid library not installed - simulating email")
            logger.info(f"[EMAIL] [SIMULATED] To: {to_email} | Subject: {subject}")
            return {
                "success": True,
                "simulated": True,
                "message": "Email simulated (SendGrid library not installed)"
            }
        
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send to {to_email}: {str(e)}")
            return {
                "success": False,
                "simulated": False,
                "message": f"Email failed: {str(e)}"
            }
    
    def send_registration_confirmation(
        self,
        to_email: str,
        participant_name: str,
        event_name: str,
        event_start_time: datetime,
        event_details: Dict,
        qr_code_data: Optional[str] = None
    ) -> Dict:
        """
        Send registration confirmation email with QR code
        
        Args:
            to_email: Participant email
            participant_name: Participant name
            event_name: Event name
            event_start_time: Event start time
            event_details: Event details dict
            qr_code_data: QR code image data (base64)
        
        Returns:
            Dict with success status
        """
        subject = f"Registration Confirmed: {event_name}"
        
        body_text = f"""
Dear {participant_name},

Thank you for registering for {event_name}!

Event Details:
- Date & Time: {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}
- Type: {event_details.get('event_type', 'N/A')}
- Meeting Link: {event_details.get('meeting_link', 'Will be provided closer to event')}

Your registration is confirmed. Please check your email for attendance instructions closer to the event date.

Best regards,
EventEngine Team
        """
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #4CAF50;">Registration Confirmed!</h2>
            <p>Dear <strong>{participant_name}</strong>,</p>
            <p>Thank you for registering for <strong>{event_name}</strong>!</p>
            
            <h3>Event Details:</h3>
            <ul>
                <li><strong>Date & Time:</strong> {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}</li>
                <li><strong>Type:</strong> {event_details.get('event_type', 'N/A')}</li>
                <li><strong>Meeting Link:</strong> <a href="{event_details.get('meeting_link', '#')}">{event_details.get('meeting_link', 'Will be provided')}</a></li>
            </ul>
            
            <p>Your registration is confirmed. Please check your email for attendance instructions closer to the event date.</p>
            
            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">EventEngine - Autonomous Event Management</p>
        </body>
        </html>
        """
        
        attachments = []
        if qr_code_data:
            attachments.append({
                'content': qr_code_data,
                'filename': 'qr_code.png',
                'type': 'image/png'
            })
        
        return self.send_email(to_email, subject, body_text, body_html, attachments)
    
    def send_reminder(
        self,
        to_email: str,
        participant_name: str,
        event_name: str,
        event_start_time: datetime,
        reminder_type: str,
        message_content: Dict
    ) -> Dict:
        """
        Send event reminder email
        
        Args:
            to_email: Participant email
            participant_name: Participant name
            event_name: Event name
            event_start_time: Event start time
            reminder_type: Type of reminder (LIGHT, MODERATE, AGGRESSIVE)
            message_content: Message content dict with subject, message, tone
        
        Returns:
            Dict with success status
        """
        subject = message_content.get('subject', f"Reminder: {event_name}")
        
        body_text = f"""
Dear {participant_name},

{message_content.get('message', 'This is a reminder about your upcoming event.')}

Event: {event_name}
Date & Time: {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}

Please confirm your attendance if you haven't already.

Best regards,
EventEngine Team
        """
        
        # Determine tone styling
        tone_color = {
            'friendly': '#4CAF50',
            'encouraging': '#FF9800',
            'urgent': '#f44336'
        }.get(message_content.get('tone', 'friendly'), '#4CAF50')
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="border-left: 4px solid {tone_color}; padding-left: 15px;">
                <h2 style="color: {tone_color};">Event Reminder</h2>
                <p>Dear <strong>{participant_name}</strong>,</p>
                <p>{message_content.get('message', 'This is a reminder about your upcoming event.')}</p>
            </div>
            
            <h3>Event Details:</h3>
            <ul>
                <li><strong>Event:</strong> {event_name}</li>
                <li><strong>Date & Time:</strong> {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}</li>
            </ul>
            
            <p><strong>Please confirm your attendance if you haven't already.</strong></p>
            
            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">EventEngine - Autonomous Event Management</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body_text, body_html)
    
    def send_attendance_confirmation(
        self,
        to_email: str,
        participant_name: str,
        event_name: str,
        checked_in_at: datetime
    ) -> Dict:
        """
        Send attendance confirmation email
        
        Args:
            to_email: Participant email
            participant_name: Participant name
            event_name: Event name
            checked_in_at: Check-in timestamp
        
        Returns:
            Dict with success status
        """
        subject = f"Attendance Confirmed: {event_name}"
        
        body_text = f"""
Dear {participant_name},

Your attendance for {event_name} has been successfully recorded!

Check-in Time: {checked_in_at.strftime('%B %d, %Y at %I:%M %p UTC')}

Thank you for attending!

Best regards,
EventEngine Team
        """
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #4CAF50;">Attendance Confirmed!</h2>
            <p>Dear <strong>{participant_name}</strong>,</p>
            <p>Your attendance for <strong>{event_name}</strong> has been successfully recorded!</p>
            
            <p><strong>Check-in Time:</strong> {checked_in_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
            
            <p>Thank you for attending!</p>
            
            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">EventEngine - Autonomous Event Management</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body_text, body_html)


# Singleton instance
_email_service_instance = None


def get_email_service() -> EmailService:
    """Get or create the singleton email service instance"""
    global _email_service_instance
    
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    
    return _email_service_instance
