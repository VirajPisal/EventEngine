"""
Scheduler - APScheduler configuration for periodic agent tasks
Handles background job scheduling for autonomous event management
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from typing import Optional
import logging

from config.settings import settings

# Configure APScheduler logging
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class EventScheduler:
    """Manages background scheduled tasks for event automation"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.scheduler = BackgroundScheduler(
            timezone='UTC',
            job_defaults={
                'coalesce': True,  # Combine missed runs into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 30  # Grace period for missed jobs (seconds)
            }
        )
        self._running = False
    
    def add_agent_loop_job(self, agent_function, interval_seconds: int = None):
        """
        Add the main agent loop as a recurring job
        
        Args:
            agent_function: The agent's main loop function to execute
            interval_seconds: How often to run (default from settings)
        """
        interval = interval_seconds or settings.AGENT_LOOP_INTERVAL_SECONDS
        
        self.scheduler.add_job(
            func=agent_function,
            trigger=IntervalTrigger(seconds=interval),
            id='agent_loop',
            name='Main Agent Loop - Check Events',
            replace_existing=True
        )
        
        print(f"[Scheduler] Agent loop scheduled every {interval} seconds")
    
    def add_reminder_evaluation_job(self, reminder_function, interval_minutes: int = 5):
        """
        Add reminder evaluation as a recurring job
        
        Args:
            reminder_function: The reminder evaluation function to execute
            interval_minutes: How often to evaluate reminders
        """
        self.scheduler.add_job(
            func=reminder_function,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='reminder_evaluation',
            name='Reminder Evaluation - Check Engagement',
            replace_existing=True
        )
        
        print(f"[Scheduler] Reminder evaluation scheduled every {interval_minutes} minutes")
    
    def start(self):
        """Start the scheduler"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            print(f"[Scheduler] Started at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    def stop(self):
        """Stop the scheduler gracefully"""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            print(f"[Scheduler] Stopped at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running and self.scheduler.running
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def print_jobs(self):
        """Print scheduled jobs information"""
        jobs = self.get_jobs()
        
        if not jobs:
            print("[Scheduler] No jobs scheduled")
            return
        
        print(f"\n[Scheduler] Active Jobs ({len(jobs)}):")
        print("=" * 70)
        
        for job in jobs:
            print(f"  ID: {job.id}")
            print(f"  Name: {job.name}")
            print(f"  Next Run: {job.next_run_time}")
            print(f"  Trigger: {job.trigger}")
            print("-" * 70)


# Singleton instance
_scheduler_instance: Optional[EventScheduler] = None


def get_scheduler() -> EventScheduler:
    """Get or create the singleton scheduler instance"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = EventScheduler()
    
    return _scheduler_instance
