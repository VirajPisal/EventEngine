"""
Run Agent - Entry point to start the autonomous event management agent
Usage: python scripts/run_agent.py
"""
import sys
import signal
from pathlib import Path
from time import sleep

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agent import get_agent
from core.scheduler import get_scheduler
from config.settings import settings
from utils.logger import logger


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n[System] Shutting down gracefully...")
    stop_agent()
    sys.exit(0)


def start_agent():
    """Start the autonomous agent with scheduler"""
    print("=" * 70)
    print("  EventEngine - Autonomous Event Lifecycle Agent")
    print("=" * 70)
    print(f"  Version: 1.0.0")
    print(f"  Database: {settings.DATABASE_URL}")
    print(f"  Agent Loop Interval: {settings.AGENT_LOOP_INTERVAL_SECONDS} seconds")
    print("=" * 70)
    
    # Get agent and scheduler instances
    agent = get_agent()
    scheduler = get_scheduler()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start agent
        agent.start()
        
        # Add jobs to scheduler
        scheduler.add_agent_loop_job(
            agent.run_cycle,
            interval_seconds=settings.AGENT_LOOP_INTERVAL_SECONDS
        )
        
        scheduler.add_reminder_evaluation_job(
            agent.run_reminder_cycle,
            interval_minutes=5
        )
        
        # Start scheduler
        scheduler.start()
        
        # Print scheduled jobs
        scheduler.print_jobs()
        
        print("\n[System] Agent is running. Press Ctrl+C to stop.")
        print("=" * 70)
        
        # Keep the main thread alive
        while True:
            sleep(1)
    
    except Exception as e:
        logger.error(f"[System] Fatal error: {str(e)}")
        stop_agent()
        sys.exit(1)


def stop_agent():
    """Stop the agent and scheduler"""
    agent = get_agent()
    scheduler = get_scheduler()
    
    print("\n[System] Stopping agent...")
    agent.stop()
    
    print("[System] Stopping scheduler...")
    scheduler.stop()
    
    print("[System] Shutdown complete.")


if __name__ == "__main__":
    start_agent()
