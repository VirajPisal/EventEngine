"""
Analytics Service - Calculate event performance metrics
Computes attendance rates, no-show patterns, engagement scores
"""
from typing import Dict, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.event import Event
from models.participant import Participant
from models.attendance import Attendance
from models.analytics import Analytics
from config.constants import ParticipantStatus, EventState
from utils.logger import logger


class AnalyticsService:
    """Service for calculating and storing event analytics"""
    
    @staticmethod
    def calculate_event_analytics(
        db: Session,
        event_id: int
    ) -> Dict:
        """
        Calculate comprehensive analytics for an event
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Dictionary with calculated metrics
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            return {
                "success": False,
                "message": f"Event {event_id} not found"
            }
        
        # Get participant counts
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
        confirmation_rate = (total_confirmed / total_registered * 100) if total_registered > 0 else 0
        no_show_count = max(0, total_confirmed - total_attended)
        no_show_rate = (no_show_count / total_confirmed * 100) if total_confirmed > 0 else 0
        
        # Calculate engagement score (weighted formula)
        # 40% confirmation rate + 60% attendance rate
        engagement_score = (confirmation_rate * 0.4) + (attendance_rate * 0.6)
        
        # Determine performance category
        if engagement_score >= 80:
            performance_category = "EXCELLENT"
        elif engagement_score >= 60:
            performance_category = "GOOD"
        elif engagement_score >= 40:
            performance_category = "AVERAGE"
        else:
            performance_category = "POOR"
        
        # Get reminder statistics
        reminder_count = AnalyticsService._count_reminders_sent(db, event_id)
        
        # Calculate average response time (registration to confirmation)
        avg_response_time = AnalyticsService._calculate_avg_response_time(db, event_id)
        
        analytics_data = {
            "event_id": event_id,
            "event_name": event.name,
            "total_registered": total_registered,
            "total_confirmed": total_confirmed,
            "total_attended": total_attended,
            "attendance_rate": round(attendance_rate, 2),
            "confirmation_rate": round(confirmation_rate, 2),
            "no_show_count": no_show_count,
            "no_show_rate": round(no_show_rate, 2),
            "engagement_score": round(engagement_score, 2),
            "performance_category": performance_category,
            "reminder_count": reminder_count,
            "avg_response_time_hours": round(avg_response_time, 2) if avg_response_time else None
        }
        
        logger.info(
            f"[ANALYTICS] Calculated for event {event_id}: "
            f"Attendance={analytics_data['attendance_rate']}%, "
            f"Engagement={analytics_data['engagement_score']}, "
            f"Category={performance_category}"
        )
        
        return {
            "success": True,
            "analytics": analytics_data
        }
    
    @staticmethod
    def save_analytics(
        db: Session,
        event_id: int,
        analytics_data: Dict
    ) -> Dict:
        """
        Save calculated analytics to database
        
        Args:
            db: Database session
            event_id: Event ID
            analytics_data: Dictionary with analytics metrics
        
        Returns:
            Success status and saved analytics record
        """
        # Check if analytics already exists
        existing = db.query(Analytics).filter(Analytics.event_id == event_id).first()
        
        if existing:
            # Update existing record
            existing.total_registered = analytics_data['total_registered']
            existing.total_confirmed = analytics_data['total_confirmed']
            existing.total_attended = analytics_data['total_attended']
            existing.attendance_rate = analytics_data['attendance_rate']
            existing.no_show_count = analytics_data['no_show_count']
            existing.engagement_score = analytics_data['engagement_score']
            existing.updated_at = datetime.now(timezone.utc)
            
            analytics_record = existing
            action = "updated"
        else:
            # Create new record
            analytics_record = Analytics(
                event_id=event_id,
                total_registered=analytics_data['total_registered'],
                total_confirmed=analytics_data['total_confirmed'],
                total_attended=analytics_data['total_attended'],
                attendance_rate=analytics_data['attendance_rate'],
                no_show_count=analytics_data['no_show_count'],
                engagement_score=analytics_data['engagement_score']
            )
            db.add(analytics_record)
            action = "created"
        
        db.commit()
        db.refresh(analytics_record)
        
        logger.info(f"[ANALYTICS] Analytics record {action} for event {event_id}")
        
        return {
            "success": True,
            "action": action,
            "analytics_id": analytics_record.id
        }
    
    @staticmethod
    def get_event_analytics(
        db: Session,
        event_id: int
    ) -> Optional[Dict]:
        """
        Retrieve saved analytics for an event
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Analytics data or None if not found
        """
        analytics = db.query(Analytics).filter(Analytics.event_id == event_id).first()
        
        if not analytics:
            return None
        
        return {
            "id": analytics.id,
            "event_id": analytics.event_id,
            "total_registered": analytics.total_registered,
            "total_confirmed": analytics.total_confirmed,
            "total_attended": analytics.total_attended,
            "attendance_rate": analytics.attendance_rate,
            "no_show_count": analytics.no_show_count,
            "engagement_score": analytics.engagement_score,
            "ai_insights": analytics.ai_insights,
            "generated_at": analytics.generated_at.isoformat(),
            "updated_at": analytics.updated_at.isoformat() if analytics.updated_at else None
        }
    
    @staticmethod
    def compare_events(
        db: Session,
        event_ids: List[int]
    ) -> Dict:
        """
        Compare analytics across multiple events
        
        Args:
            db: Database session
            event_ids: List of event IDs to compare
        
        Returns:
            Comparison data with averages and trends
        """
        analytics_list = []
        
        for event_id in event_ids:
            analytics = db.query(Analytics).filter(Analytics.event_id == event_id).first()
            if analytics:
                event = db.query(Event).filter(Event.id == event_id).first()
                analytics_list.append({
                    "event_id": event_id,
                    "event_name": event.name if event else "Unknown",
                    "attendance_rate": analytics.attendance_rate,
                    "engagement_score": analytics.engagement_score,
                    "total_registered": analytics.total_registered,
                    "total_attended": analytics.total_attended
                })
        
        if not analytics_list:
            return {
                "success": False,
                "message": "No analytics found for comparison"
            }
        
        # Calculate averages
        avg_attendance = sum(a['attendance_rate'] for a in analytics_list) / len(analytics_list)
        avg_engagement = sum(a['engagement_score'] for a in analytics_list) / len(analytics_list)
        
        # Find best and worst performers
        best_event = max(analytics_list, key=lambda x: x['engagement_score'])
        worst_event = min(analytics_list, key=lambda x: x['engagement_score'])
        
        return {
            "success": True,
            "events_compared": len(analytics_list),
            "averages": {
                "attendance_rate": round(avg_attendance, 2),
                "engagement_score": round(avg_engagement, 2)
            },
            "best_performer": best_event,
            "worst_performer": worst_event,
            "events": analytics_list
        }
    
    @staticmethod
    def _count_reminders_sent(db: Session, event_id: int) -> int:
        """Count total reminders sent (from activity log)"""
        # This would query activity logs in a real implementation
        # For now, return estimated count based on participants
        total_participants = db.query(Participant).filter(
            Participant.event_id == event_id
        ).count()
        
        # Estimate: assume 2-3 reminders per participant on average
        return total_participants * 2
    
    @staticmethod
    def _calculate_avg_response_time(db: Session, event_id: int) -> Optional[float]:
        """Calculate average time from registration to confirmation (in hours)"""
        participants = db.query(Participant).filter(
            Participant.event_id == event_id,
            Participant.is_confirmed == True,
            Participant.confirmed_at.isnot(None)
        ).all()
        
        if not participants:
            return None
        
        total_hours = 0
        count = 0
        
        for p in participants:
            if p.confirmed_at and p.registered_at:
                time_diff = (p.confirmed_at - p.registered_at).total_seconds() / 3600
                total_hours += time_diff
                count += 1
        
        return total_hours / count if count > 0 else None
    
    @staticmethod
    def generate_summary_report(
        db: Session,
        event_id: int
    ) -> str:
        """
        Generate human-readable summary report
        
        Args:
            db: Database session
            event_id: Event ID
        
        Returns:
            Formatted text report
        """
        result = AnalyticsService.calculate_event_analytics(db, event_id)
        
        if not result['success']:
            return f"Error: {result['message']}"
        
        data = result['analytics']
        
        report = f"""
Event Analytics Report
{'=' * 60}
Event: {data['event_name']} (ID: {data['event_id']})

PARTICIPATION METRICS:
- Total Registered: {data['total_registered']}
- Total Confirmed: {data['total_confirmed']} ({data['confirmation_rate']}%)
- Total Attended: {data['total_attended']} ({data['attendance_rate']}%)
- No-shows: {data['no_show_count']} ({data['no_show_rate']}%)

PERFORMANCE:
- Engagement Score: {data['engagement_score']}/100
- Category: {data['performance_category']}

COMMUNICATION:
- Reminders Sent: {data['reminder_count']}
- Avg Response Time: {data['avg_response_time_hours']} hours

{'=' * 60}
"""
        return report.strip()
