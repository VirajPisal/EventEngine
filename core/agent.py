"""
Agent - Autonomous event lifecycle management
Observe-Decide-Act loop for self-managing events
"""
from datetime import datetime, timezone
from typing import List, Dict
from sqlalchemy.orm import Session

from db.base import get_db_context
from models.event import Event
from models.participant import Participant
from models.agent_action import AgentAction
from models.feedback import Feedback
from config.constants import EventState, EventType, ParticipantStatus
from services.event_service import EventService
from services.reminder_service import ReminderService
from services.analytics_service import AnalyticsService
from services.promotion_service import PromotionService
from services.certificate_service import CertificateService
from services.insights_service import get_insights_service
from rules.transition_rules import check_auto_transition_conditions
from utils.logger import logger
import json


class EventAgent:
    """Autonomous agent for managing event lifecycle"""
    
    def __init__(self):
        """Initialize the agent"""
        self.name = "EventEngine Agent"
        self.version = "1.0.0"
        self._running = False
        self._cycle_count = 0
    
    def observe(self, db: Session) -> List[Event]:
        """
        OBSERVE: Query all active events that need monitoring
        
        Returns:
            List of events in active states
        """
        # Get events that are not in terminal states
        active_states = [
            EventState.CREATED,
            EventState.REGISTRATION_OPEN,
            EventState.SCHEDULED,
            EventState.ATTENDANCE_OPEN,
            EventState.RUNNING,
            EventState.COMPLETED,
            EventState.ANALYZING
        ]
        
        events = db.query(Event).filter(
            Event.state.in_(active_states)
        ).all()
        
        return events
    
    def decide(self, db: Session, event: Event) -> Dict:
        """
        DECIDE: Determine if event needs state transition
        
        Args:
            db: Database session
            event: Event to evaluate
        
        Returns:
            Decision dict with should_transition, target_state, reason
        """
        # Check if event needs auto-transition based on time/conditions
        decision = check_auto_transition_conditions(db, event)
        
        return decision
    
    def act(self, db: Session, event: Event, decision: Dict) -> bool:
        """
        ACT: Execute the decided action
        
        Args:
            db: Database session
            event: Event to act upon
            decision: Decision from decide() phase
        
        Returns:
            True if action was successful
        """
        if not decision.get('should_transition'):
            return False
        
        target_state = decision.get('target_state')
        reason = decision.get('reason', 'Auto-transition by agent')
        
        try:
            # Execute state transition
            result = EventService.transition_event_state(
                db,
                event.id,
                target_state,
                reason=reason,
                triggered_by="agent"
            )
            
            if result['success']:
                logger.info(
                    f"[AGENT] Auto-transitioned Event #{event.id} '{event.name}': "
                    f"{event.state.value} -> {target_state.value} | {reason}"
                )
                return True
            else:
                logger.warning(
                    f"[AGENT] Failed to transition Event #{event.id}: {result['message']}"
                )
                return False
        
        except Exception as e:
            logger.error(f"[AGENT] Error during transition: {str(e)}")
            return False
    
    def evaluate_reminders(self, db: Session, event: Event) -> Dict:
        """
        Evaluate if reminders should be sent for an event.
        Instead of sending immediately, creates a PENDING AgentAction
        for organizer approval.
        """
        if event.state not in [EventState.REGISTRATION_OPEN, EventState.SCHEDULED]:
            return {"evaluated": False, "reason": "Event not in reminder-eligible state"}

        try:
            recommendations = ReminderService.get_reminder_recommendations(db, event.id)

            if recommendations.get('should_send_now'):
                # Check if there's already a pending reminder action for this event
                existing = db.query(AgentAction).filter(
                    AgentAction.event_id == event.id,
                    AgentAction.action_type == "SEND_REMINDER",
                    AgentAction.status == "PENDING",
                ).first()
                if existing:
                    return {"evaluated": True, "sent": False, "reason": "Pending action already exists"}

                # Create pending action instead of sending directly
                action = AgentAction(
                    event_id=event.id,
                    action_type="SEND_REMINDER",
                    description=(
                        f"Send {recommendations.get('reminder_type', 'reminder')} reminders "
                        f"for '{event.name}' — {recommendations.get('send_reason', '')}"
                    ),
                    payload_json=json.dumps({"event_id": event.id}),
                    status="PENDING",
                )
                db.add(action)

                logger.info(
                    f"[AGENT] Created pending reminder action for Event #{event.id} '{event.name}'"
                )
                return {"evaluated": True, "sent": False, "reason": "Pending approval"}
            else:
                return {
                    "evaluated": True,
                    "sent": False,
                    "reason": recommendations.get('send_reason', 'Not time to send yet'),
                }
        except Exception as e:
            logger.error(f"[AGENT] Error evaluating reminders: {str(e)}")
            return {"evaluated": False, "error": str(e)}
    
    def generate_analytics_and_insights(self, db: Session, event: Event) -> Dict:
        """
        Generate analytics and AI insights for a completed event
        
        Args:
            db: Database session
            event: Event that just completed
        
        Returns:
            Dict with generation results
        """
        try:
            logger.info(f"[AGENT] Generating analytics for Event #{event.id} '{event.name}'")
            
            # Step 1: Calculate analytics
            analytics_result = AnalyticsService.calculate_event_analytics(db, event.id)
            
            if not analytics_result['success']:
                logger.error(f"[AGENT] Analytics calculation failed: {analytics_result.get('message')}")
                return {"success": False, "error": analytics_result.get('message')}
            
            analytics_data = analytics_result['analytics']
            
            # Step 2: Save analytics to database
            save_result = AnalyticsService.save_analytics(db, event.id, analytics_data)
            
            if not save_result['success']:
                logger.error(f"[AGENT] Failed to save analytics")
                return {"success": False, "error": "Failed to save analytics"}
            
            # Step 3: Generate AI insights
            insights_service = get_insights_service()
            insights = insights_service.generate_insights(db, event.id, analytics_data)
            
            if not insights['success']:
                logger.error(f"[AGENT] Insights generation failed")
                return {"success": False, "error": "Insights generation failed"}
            
            # Step 4: Save insights to analytics record
            insights_service.save_insights_to_analytics(db, event.id, insights)
            
            # Step 5: Transition event to REPORT_GENERATED
            EventService.transition_event_state(db, event.id, EventState.REPORT_GENERATED)
            
            logger.info(
                f"[AGENT] Analytics complete for Event #{event.id}: "
                f"Engagement={analytics_data['engagement_score']}, "
                f"Category={analytics_data['performance_category']}"
            )
            
            return {
                "success": True,
                "analytics": analytics_data,
                "insights": insights,
                "insights_source": insights['source']
            }
        
        except Exception as e:
            logger.error(f"[AGENT] Error generating analytics: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def run_cycle(self):
        """
        Execute one complete observe-decide-act cycle
        Main function called by scheduler
        """
        self._cycle_count += 1
        
        try:
            with get_db_context() as db:
                # OBSERVE: Get all active events
                events = self.observe(db)
                
                if not events:
                    # No events to manage
                    return
                
                logger.debug(f"[AGENT] Cycle #{self._cycle_count} - Monitoring {len(events)} events")
                
                # Process each event
                for event in events:
                    # DECIDE: Check if transition needed
                    decision = self.decide(db, event)
                    
                    # ACT: Execute transition if needed
                    if decision['should_transition']:
                        self.act(db, event, decision)
                        
                        # If we just moved event to COMPLETED, trigger analytics
                        if decision['target_state'] == EventState.COMPLETED:
                            logger.info(f"[AGENT] Event #{event.id} completed - triggering analytics")
                            # Transition to ANALYZING state first
                            EventService.transition_event_state(db, event.id, EventState.ANALYZING)
                
                # Check for events in ANALYZING state and generate their analytics
                analyzing_events = db.query(Event).filter(
                    Event.state == EventState.ANALYZING
                ).all()
                
                for event in analyzing_events:
                    self.generate_analytics_and_insights(db, event)
                
                # NEW: PROMOTION CYCLE
                self.run_promotion_cycle(db)
                
                # NEW: CERTIFICATE CYCLE
                self.run_certificate_cycle(db)

                # NEW: FEEDBACK CYCLE
                self.run_feedback_cycle(db)

                # NEW: FEEDBACK SUMMARY CYCLE
                self.run_feedback_summary_cycle(db)
                
        except Exception as e:
            logger.error(f"[AGENT] Error in cycle #{self._cycle_count}: {str(e)}")
    
    def run_reminder_cycle(self):
        """
        Execute reminder evaluation cycle
        Separate from main cycle to run on different schedule
        """
        try:
            with get_db_context() as db:
                # Get events eligible for reminders
                events = db.query(Event).filter(
                    Event.state.in_([EventState.REGISTRATION_OPEN, EventState.SCHEDULED])
                ).all()
                
                if not events:
                    return
                
                logger.debug(f"[AGENT] Reminder cycle - Evaluating {len(events)} events")
                
                for event in events:
                    self.evaluate_reminders(db, event)
        
        except Exception as e:
            logger.error(f"[AGENT] Error in reminder cycle: {str(e)}")
    
    def run_promotion_cycle(self, db: Session):
        """
        Identify new events and send promotions to potential participants autonomously
        """
        try:
            # Events in REGISTRATION_OPEN state are eligible for promotion
            eligible_events = db.query(Event).filter(
                Event.state == EventState.REGISTRATION_OPEN
            ).all()

            if not eligible_events:
                return

            for event in eligible_events:
                # Basic rule: promote if less than 50% capacity
                if event.max_participants:
                    participant_count = db.query(Participant).filter(
                        Participant.event_id == event.id
                    ).count()
                    
                    if participant_count < (event.max_participants * 0.5):
                        logger.info(f"[AGENT] Autonomous Promotion: Event #{event.id} '{event.name}' is below 50% capacity. Promoting...")
                        PromotionService.promote_event(db, event.id)
                else:
                    # If no max capacity, promote anyway periodically?
                    # For now, let's just promote once. I'll add a 'promoted' field later or check history.
                    # Since we don't have a 'promoted' field, let's promote if it only has few participants.
                    participant_count = db.query(Participant).filter(
                        Participant.event_id == event.id
                    ).count()
                    if participant_count < 5:
                        PromotionService.promote_event(db, event.id)

        except Exception as e:
            logger.error(f"[AGENT] Error in promotion cycle: {str(e)}")
    
    def run_certificate_cycle(self, db: Session):
        """
        Check completed online events and send certificates to participants
        """
        try:
            # Events in COMPLETED or ANALYZING state are eligible for certificate issuance
            eligible_events = db.query(Event).filter(
                Event.state.in_([EventState.COMPLETED, EventState.ANALYZING, EventState.REPORT_GENERATED]),
                Event.event_type == EventType.ONLINE,
                Event.certificate_template != None
            ).all()

            if not eligible_events:
                return

            email_service = get_email_service()

            for event in eligible_events:
                # Get all participants who attended
                attendees = db.query(Participant).filter(
                    Participant.event_id == event.id,
                    Participant.status == ParticipantStatus.ATTENDED
                ).all()

                for att in attendees:
                    # Check if already sent? (Wait, I'll assume we send once for now)
                    # We can mark it in the metadata or just assume it's part of the 'completion' flow
                    
                    # Generate certificate
                    cert_data = CertificateService.generate_certificate(
                        participant_name=att.name,
                        event_name=event.name,
                        template_base64=event.certificate_template,
                        completion_date=event.end_time.strftime('%Y-%m-%d')
                    )

                    if cert_data:
                        # Send email (Need a new email method for certificates)
                        subject = f"Your Certificate for '{event.name}' is Ready!"
                        body_text = f"Congratulations {att.name}! Find your participation certificate attached."
                        body_html = f"<h2>Congratulations!</h2><p>Hi {att.name}, we are happy to share your participation certificate for <strong>{event.name}</strong>. Well done!</p>"
                        
                        email_service.send_email(
                            to_email=att.email,
                            subject=subject,
                            body_text=body_text,
                            body_html=body_html,
                            attachments=[{
                                'content': cert_data,
                                'filename': 'Certificate.png',
                                'type': 'image/png'
                            }]
                        )
                        logger.info(f"[AGENT] Sent certificate to {att.email} for Event #{event.id}")

        except Exception as e:
            logger.error(f"[AGENT] Error in certificate cycle: {str(e)}")

    def run_feedback_cycle(self, db: Session):
        """
        Check completed events and send feedback survey links to attendees
        """
        try:
            # Events in COMPLETED or ANALYZING state can receive survey links
            # We target participants of COMPLETED events specifically
            completed_events = db.query(Event).filter(
                Event.state == EventState.COMPLETED
            ).all()

            if not completed_events:
                return

            email_service = get_email_service()

            for event in completed_events:
                # Get all participants who attended
                attendees = db.query(Participant).filter(
                    Participant.event_id == event.id,
                    Participant.status == ParticipantStatus.ATTENDED
                ).all()

                for att in attendees:
                    # Send feedback invitation
                    subject = f"How was '{event.name}'? Share your feedback!"
                    feedback_url = f"http://localhost:8000/frontend/portal.html?feedback={event.id}"
                    
                    body_html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                        <h2 style="color: #6366f1;">Thanks for attending!</h2>
                        <p>Hi <strong>{att.name}</strong>, we hope you enjoyed <strong>{event.name}</strong>.</p>
                        <p>Could you take 30 seconds to rate the event? Your feedback helps us improve future events!</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{feedback_url}" style="background:#6366f1; color:white; padding:12px 30px; border-radius:8px; text-decoration:none; font-weight: bold; display:inline-block;">
                                ⭐ Give Feedback
                            </a>
                        </div>
                        <p style="color: #666; font-size: 0.9em;">If the button doesn't work, copy this link: {feedback_url}</p>
                    </div>
                    """
                    
                    email_service.send_email(
                        to_email=att.email,
                        subject=subject,
                        body_text=f"Please rate {event.name} at {feedback_url}",
                        body_html=body_html
                    )

                # Move to ANALYZING once surveys are sent
                event.state = EventState.ANALYZING
                db.commit()
                logger.info(f"[AGENT] Surveys sent for Event #{event.id}, transitioning to ANALYZING")

        except Exception as e:
            logger.error(f"[AGENT] Error in feedback cycle: {str(e)}")

    def run_feedback_summary_cycle(self, db: Session):
        """
        Summarize feedback for events in ANALYZING state
        """
        try:
            # Events in ANALYZING state that might have feedback now
            analyzing_events = db.query(Event).filter(
                Event.state == EventState.ANALYZING
            ).all()

            for event in analyzing_events:
                # Check for feedback
                feedbacks = db.query(Feedback).filter(Feedback.event_id == event.id).all()
                
                # Logic: Summarize if we have at least some feedback, 
                # or if it's been in ANALYZING for > some time.
                # For this demo, if count > 0, we summarize.
                if not feedbacks:
                    continue
                
                # Aggregate summary
                avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
                comments = [f.comment for f in feedbacks if f.comment]
                
                # Propose a 'REPORT_GENERATION' action or just mark as COMPLETED
                # We'll push it to REPORT_GENERATED after summarizing
                action = AgentAction(
                    event_id=event.id,
                    action_type="REPORT_GENERATION",
                    description=f"Generated AI performance summary from {len(feedbacks)} reviews. Avg Rating: {avg_rating:.1f}/5.",
                    status="PENDING",
                    parameters={
                        "avg_rating": avg_rating,
                        "response_count": len(feedbacks),
                        "top_comments": comments[:5]
                    }
                )
                db.add(action)
                
                # Update event state to REPORT_GENERATED
                event.state = EventState.REPORT_GENERATED
                db.commit()
                logger.info(f"[AGENT] Compiled feedback for Event #{event.id}. Avg: {avg_rating:.1f}")

        except Exception as e:
            logger.error(f"[AGENT] Error in feedback summary cycle: {str(e)}")

    
    def start(self):
        """Mark agent as running"""
        self._running = True
        logger.info(f"[AGENT] {self.name} v{self.version} started")
    
    def stop(self):
        """Mark agent as stopped"""
        self._running = False
        logger.info(f"[AGENT] {self.name} stopped (Executed {self._cycle_count} cycles)")
    
    def is_running(self) -> bool:
        """Check if agent is running"""
        return self._running
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            "agent_name": self.name,
            "version": self.version,
            "running": self._running,
            "total_cycles": self._cycle_count,
            "started_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_agent_instance = None


def get_agent() -> EventAgent:
    """Get or create the singleton agent instance"""
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = EventAgent()
    
    return _agent_instance
