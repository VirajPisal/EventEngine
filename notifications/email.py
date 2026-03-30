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
        participant_id: Optional[int] = None,
        custom_content: Optional[str] = None
    ) -> Dict:
        """
        Send registration confirmation email with QR code and confirmation link.
        """
        subject = f"Registration Confirmed: {event_name} - Action Required"

        confirm_url = f"http://localhost:8000/api/registrations/confirm/{participant_id}" if participant_id else None
        
        # Handle custom content if provided
        if custom_content:
            body_text = f"""
Hello {participant_name},

{custom_content}

---
EVENT QUICK INFO:
Event: {event_name}
Date: {event_start_time.strftime('%B %d, %Y')}
Confirm Attendance: {confirm_url}
---

Best regards,
EventEngine Team
            """
        else:
            # Default enhanced plain text version
            body_text = f"""
Hello {participant_name},

Congratulations! You have successfully registered for "{event_name}".

EVENT DETAILS:
-----------------------------------------
Event: {event_name}
Date & Time: {event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')} to {event_details.get('end_time').strftime('%B %d, %Y at %I:%M %p UTC') if event_details.get('end_time') else 'N/A'}
Organizer: {event_details.get('organizer') or 'EventEngine Team'}
Format: {event_details.get('event_type', 'N/A').title()}
Venue/Location: {event_details.get('venue') or 'To be announced'}
{"Meeting Link: " + event_details.get('meeting_link') if event_details.get('meeting_link') else ""}
Description: {event_details.get('description', 'No description available.')}
-----------------------------------------

IMPORTANT: ACTION REQUIRED
Please click the link below to confirm your attendance. This helps us manage event capacity:
{confirm_url}

CHECK-IN INFORMATION:
We have attached a unique QR code to this email. Please keep this handy on your phone as it will be scanned at the entrance for your attendance.

Looking forward to seeing you there!

Best regards,
EventEngine Team
        """

        # Enhanced HTML version
        body_html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #4f46e5; margin-bottom: 5px;">Registration Confirmed!</h1>
                <p style="font-size: 1.1em; color: #666;">You're going to <strong>{event_name}</strong></p>
            </div>
            
            <p>Hi <strong>{participant_name}</strong>,</p>
            
            {f'<div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 20px;">{custom_content}</div>' if custom_content else f'<p>Your registration for the upcoming event has been successfully processed. Here are the full details:</p>'}
            
            <div style="background-color: #f9fafb; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #4f46e5;">
                <h3 style="margin-top: 0; color: #1f2937;">Event Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px 0; color: #6b7280; width: 120px;"><strong>Date & Time:</strong></td>
                        <td style="padding: 5px 0; color: #111827;">{event_start_time.strftime('%B %d, %Y at %I:%M %p UTC')} to {event_details.get('end_time').strftime('%B %d, %Y at %I:%M %p UTC') if event_details.get('end_time') else 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0; color: #6b7280;"><strong>Organizer:</strong></td>
                        <td style="padding: 5px 0; color: #111827;">{event_details.get('organizer') or 'EventEngine Team'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0; color: #6b7280;"><strong>Type:</strong></td>
                        <td style="padding: 5px 0; color: #111827;">{event_details.get('event_type', 'N/A').title()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0; color: #6b7280;"><strong>Venue/Link:</strong></td>
                        <td style="padding: 5px 0; color: #111827;">{event_details.get('venue') or 'To be announced'}</td>
                    </tr>
                    {"<tr><td style='padding: 5px 0; color: #6b7280;'><strong>Meeting Link:</strong></td><td style='padding: 5px 0;'><a href='" + event_details.get('meeting_link') + "' style='color: #4f46e5; text-decoration: none;'>" + event_details.get('meeting_link') + "</a></td></tr>" if event_details.get('meeting_link') else ""}
                </table>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; font-size: 0.95em;"><strong>Description:</strong><br>{event_details.get('description', 'Join us for this exciting event!')}</p>
                </div>
            </div>

            <div style="text-align: center; margin: 35px 0; padding: 25px; border: 2px dashed #22c55e; border-radius: 12px; background-color: #f0fdf4;">
                <h3 style="margin-top: 0; color: #15803d;">RSVP Confirmation</h3>
                <p style="margin-bottom: 20px;">Please let us know if you'll definitely be attending!</p>
                <a href="{confirm_url}"
                   style="background-color: #22c55e; color: white; padding: 14px 35px;
                          border-radius: 8px; text-decoration: none; font-size: 16px;
                          font-weight: bold; display: inline-block; transition: background-color 0.3s;">
                  ✅ YES, I WILL ATTEND
                </a>
                <p style="margin-top: 15px; font-size: 0.85em; color: #666;">
                    Confirming helps us ensure we have enough resources for everyone.
                </p>
            </div>

            <div style="margin-top: 30px; text-align: center;">
                <h3 style="color: #1f2937;">Your Entry Pass</h3>
                <p>We've attached your personal <strong>QR code</strong> to this email. Please show it at the check-in desk when you arrive.</p>
            </div>

            <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0;">
            <div style="text-align: center; color: #9ca3af; font-size: 0.8em;">
                <p>Sent via <strong>EventEngine</strong> — Autonomous Event Management</p>
                <p>You received this because you registered for {event_name}.</p>
            </div>
        </body>
        </html>
        """

        attachments = []
        if qr_code_data:
            attachments.append({
                'content': qr_code_data,
                'filename': 'entry_pass_qr.png',
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

    def send_promotion_email(
        self,
        to_email: str,
        participant_name: str,
        event_name: str,
        event_description: str,
        event_id: int
    ) -> Dict:
        """
        Send a promotional email to a potential participant
        """
        subject = f"Invitation: Don't miss out on '{event_name}'!"
        reg_url = f"http://localhost:8000/frontend/portal.html?event_id={event_id}"
        
        body_text = f"""
Hello {participant_name},

We thought you might be interested in our upcoming event: "{event_name}".

{event_description[:200]}...

Interested? You can view more details and register here:
{reg_url}

We hope to see you there!

Best regards,
EventEngine AI Promoter
"""
        
        body_html = f"""
<html>
<body style="font-family: 'Segoe UI', sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: auto; padding: 20px;">
    <div style="text-align: center; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 40px; border-radius: 12px; margin-bottom: 30px;">
        <h1 style="margin: 0;">Special Invitation</h1>
        <p style="font-size: 1.2em; opacity: 0.9;">Join us for {event_name}</p>
    </div>
    
    <p>Hi <strong>{participant_name}</strong>,</p>
    <p>Our autonomous agent identified that you might be interested in this upcoming event. It's a great opportunity to learn and network!</p>
    
    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin: 25px 0;">
        <h3 style="margin-top: 0; color: #4f46e5;">{event_name}</h3>
        <p>{event_description[:300]}...</p>
    </div>
    
    <div style="text-align: center; margin: 35px 0;">
        <a href="{reg_url}" style="background-color: #4f46e5; color: white; padding: 14px 35px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; display: inline-block;">
            View Event & Register
        </a>
    </div>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
    <p style="text-align: center; color: #94a3b8; font-size: 0.85em;">Sent by EventEngine AI Promoter</p>
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
