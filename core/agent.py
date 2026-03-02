"""
Agent - Autonomous event lifecycle management
Observe-Decide-Act loop for self-managing events
"""
from datetime import datetime, timezone
from typing import List, Dict
from sqlalchemy.orm import Session

from db.base import get_db_context
from models.event import Event
from config.constants import EventState
from services.event_service import EventService
from services.reminder_service import ReminderService
from services.analytics_service import AnalyticsService
from services.insights_service import get_insights_service
from rules.transition_rules import check_auto_transition_conditions
from utils.logger import logger


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
        Evaluate if reminders should be sent for an event
        
        Args:
            db: Database session
            event: Event to evaluate
        
        Returns:
            Reminder evaluation result
        """
        # Only evaluate reminders for events in registration/scheduled states
        if event.state not in [EventState.REGISTRATION_OPEN, EventState.SCHEDULED]:
            return {"evaluated": False, "reason": "Event not in reminder-eligible state"}
        
        try:
            # Get recommendations
            recommendations = ReminderService.get_reminder_recommendations(db, event.id)
            
            # Check if we should send now
            if recommendations.get('should_send_now'):
                # Send reminders
                result = ReminderService.evaluate_and_send_reminders(
                    db,
                    event.id,
                    force=False  # Respect timing rules
                )
                
                if result.get('sent'):
                    logger.info(
                        f"[AGENT] Sent {result['reminder_type']} reminders for Event #{event.id} "
                        f"'{event.name}' - {result['recipient_count']} recipients"
                    )
                
                return result
            else:
                return {
                    "evaluated": True,
                    "sent": False,
                    "reason": recommendations.get('send_reason', 'Not time to send yet')
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
            EventService.transition_event_state(db, event.id, "REPORT_GENERATED")
            
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
                            EventService.transition_event_state(db, event.id, "ANALYZING")
                
                # Check for events in ANALYZING state and generate their analytics
                analyzing_events = db.query(Event).filter(
                    Event.state == EventState.ANALYZING
                ).all()
                
                for event in analyzing_events:
                    self.generate_analytics_and_insights(db, event)
                
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
