"""
Email Notifications - SMTP Integration (works with Gmail, Outlook, etc.)
Sends confirmation emails, reminders, and event notifications
"""
from typing import Dict, Optional, List
from datetime import datetime
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

from config.settings import settings
from utils.logger import logger


class EmailService:
    """Email service using SMTP (Gmail / Outlook / any provider)"""

    def __init__(self):
        pass  # credentials are read fresh on every send

    def _check_configuration(self):
        """Read credentials fresh from settings (which re-reads .env each call)"""
        user = settings.SMTP_USER
        pwd = settings.SMTP_PASSWORD
        if not user or not pwd:
            logger.warning("[EMAIL] SMTP credentials not configured — emails will be simulated")
            return False
        return True

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of dicts with keys: content (base64 str), filename, type

        Returns:
            Dict with success status and message
        """
        # Read credentials fresh every time (no stale singleton)
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        from_email = settings.EMAIL_FROM or smtp_user

        if not smtp_user or not smtp_password:
            logger.info(f"[EMAIL] [SIMULATED] To: {to_email} | Subject: {subject}")
            return {
                "success": True,
                "simulated": True,
                "sent": False,
                "message": "Email simulated — configure SMTP_USER and SMTP_PASSWORD in .env to send real emails"
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email

            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Add attachments
            if attachments:
                for att in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(base64.b64decode(att["content"]))
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
                    msg.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())

            logger.info(f"[EMAIL] Sent to {to_email} | Subject: {subject}")
            return {"success": True, "simulated": False, "sent": True, "message": "Email sent successfully"}

        except Exception as e:
            logger.error(f"[EMAIL] Failed to send to {to_email}: {str(e)}")
            return {"success": False, "simulated": False, "sent": False, "message": f"Email failed: {str(e)}"}
    
    def send_registration_confirmation(
        self,
        to_email: str,
        participant_name: str,
        event_name: str,
        event_start_time: datetime,
        event_details: Dict,
        qr_code_data: Optional[str] = None,
        participant_id: Optional[int] = None
    ) -> Dict:
        """
        Send registration confirmation email with QR code and confirmation link.
        """
        subject = f"You're Registered: {event_name} — Please Confirm Attendance"

        confirm_url = f"http://localhost:8000/api/registrations/confirm/{participant_id}" if participant_id else None
        confirm_text = f"\nPlease confirm you will attend by clicking this link:\n{confirm_url}\n" if confirm_url else ""

        body_text = f"""
Dear {participant_name},

You have successfully registered for {event_name}!
{confirm_text}
Event Details:
- Date & Time: {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}
- Type: {event_details.get('event_type', 'N/A')}
- Venue: {event_details.get('venue') or 'N/A'}
- Meeting Link: {event_details.get('meeting_link') or 'Will be provided closer to event'}

Your QR code for attendance check-in is attached to this email.

Best regards,
EventEngine Team
        """

        confirm_btn = f"""
            <div style="text-align:center; margin: 24px 0;">
              <a href="{confirm_url}"
                 style="background:#22c55e; color:white; padding:14px 32px;
                        border-radius:8px; text-decoration:none; font-size:16px;
                        font-weight:bold; display:inline-block;">
                ✅ Confirm My Attendance
              </a>
            </div>
            <p style="color:#888; font-size:12px; text-align:center;">
              Or paste this link in your browser:<br>
              <a href="{confirm_url}">{confirm_url}</a>
            </p>
        """ if confirm_url else ""

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width:600px; margin:auto;">
            <h2 style="color: #4f46e5;">You're Registered! 🎉</h2>
            <p>Dear <strong>{participant_name}</strong>,</p>
            <p>You have successfully registered for <strong>{event_name}</strong>.</p>

            <h3>Action Required</h3>
            <p>Please confirm that you will attend by clicking the button below:</p>
            {confirm_btn}

            <h3>Event Details:</h3>
            <ul>
                <li><strong>Date & Time:</strong> {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')}</li>
                <li><strong>Type:</strong> {event_details.get('event_type', 'N/A')}</li>
                <li><strong>Venue:</strong> {event_details.get('venue') or 'N/A'}</li>
                <li><strong>Meeting Link:</strong> <a href="{event_details.get('meeting_link', '#')}">{event_details.get('meeting_link') or 'Will be provided'}</a></li>
            </ul>

            <p>Your <strong>QR code</strong> for attendance check-in is attached. Keep it handy on event day.</p>

            <hr style="border: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">EventEngine — Autonomous Event Management</p>
        </body>
        </html>
        """

        attachments = []
        if qr_code_data:
            attachments.append({
                'content': qr_code_data,
                'filename': 'attendance_qr.png',
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
