"""
Calendar Service - Generates iCalendar (.ics) files for events
"""
from datetime import datetime
import uuid
import urllib.parse
from typing import Optional

class CalendarService:
    """Service for generating standard iCalendar files"""

    @staticmethod
    def generate_ics_content(
        name: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        uid: Optional[str] = None
    ) -> str:
        """
        Generate iCalendar (.ics) content as a string
        Follows RFC 5545 standard
        """
        dt_format = "%Y%m%dT%H%M%SZ" # UTC format
        
        # Ensure UTC-like strings (this is a simplified version)
        # In a production app, we'd handle timezones properly, 
        # but for now we'll use the datetime's naive format assuming it's correctly offset
        dt_start = start_time.strftime(dt_format)
        dt_end = end_time.strftime(dt_format)
        dt_stamp = datetime.utcnow().strftime(dt_format)
        
        if not uid:
            uid = str(uuid.uuid4())
            
        # Standard iCalendar blocks
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//EventEngine//EventManagement//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"DTSTAMP:{dt_stamp}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{name}",
            f"DESCRIPTION:{description.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\\n', '\\n')}",
            f"UID:{uid}",
            f"LOCATION:{location or 'Online'}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        
        return "\n".join(lines)

    @staticmethod
    def generate_google_calendar_link(
        name: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None
    ) -> str:
        """
        Generate a URL that opens Google Calendar with pre-filled event details
        """
        dt_format = "%Y%m%dT%H%M%SZ"
        # Convert to local/target format string
        dt_start = start_time.strftime(dt_format)
        dt_end = end_time.strftime(dt_format)
        
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        
        params = {
            "text": name,
            "dates": f"{dt_start}/{dt_end}",
            "details": description,
            "location": location or "Online",
            "trp": "true" # Busy
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{base_url}&{query_string}"
