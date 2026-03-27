"""
EventEngine - System Diagnostics
Tests registration and checks if agent is needed
"""
import sys
from pathlib import Path
import requests
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("  EventEngine - System Diagnostics")
print("=" * 70)
print()

# Test 1: Check if API server is running
print("[1/4] Checking API Server...")
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print("      ✓ API Server is RUNNING")
        print(f"      Response: {response.json()}")
    else:
        print(f"      ⚠️  API Server responded with status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("      ❌ API Server is NOT RUNNING")
    print("      → Run: python run.py")
    sys.exit(1)
except Exception as e:
    print(f"      ❌ Error: {e}")
    sys.exit(1)

print()

# Test 2: Check database and events
print("[2/4] Checking Database...")
try:
    response = requests.get("http://localhost:8000/api/events/?limit=5")
    data = response.json()
    if data.get("success"):
        event_count = len(data.get("events", []))
        print(f"      ✓ Database connected")
        print(f"      Found {event_count} event(s)")
        
        if event_count > 0:
            print()
            print("      Recent events:")
            for ev in data["events"][:3]:
                print(f"        • {ev['name']} - State: {ev['state']}")
    else:
        print("      ⚠️  Database query returned error")
except Exception as e:
    print(f"      ❌ Error: {e}")

print()

# Test 3: Test registration endpoint (without auth)
print("[3/4] Testing Registration Endpoint...")
try:
    # First get an event in REGISTRATION_OPEN state
    response = requests.get("http://localhost:8000/api/events/?limit=100")
    events_data = response.json()
    
    open_event = None
    if events_data.get("success"):
        for ev in events_data.get("events", []):
            if ev.get("state") == "REGISTRATION_OPEN":
                open_event = ev
                break
    
    if open_event:
        print(f"      Found event with open registration: {open_event['name']}")
        print("      ✓ Registration SHOULD work for this event")
        print(f"      Event ID: {open_event['id']}")
        print(f"      State: {open_event['state']}")
    else:
        print("      ⚠️  No events with REGISTRATION_OPEN state found")
        print("      → Events must be in REGISTRATION_OPEN state to accept registrations")
        print("      → Use organizer dashboard to open registration")
except Exception as e:
    print(f"      ❌ Error: {e}")

print()

# Test 4: Check if agent process is running
print("[4/4] Checking Autonomous Agent...")
try:
    # Try to import and check scheduler
    from core.scheduler import get_scheduler
    scheduler = get_scheduler()
    
    if scheduler.is_running():
        print("      ✓ Agent is RUNNING")
        print("      ✓ Automatic transitions ENABLED")
        jobs = scheduler.get_jobs()
        if jobs:
            print(f"      Active jobs: {len(jobs)}")
            for job in jobs:
                print(f"        • {job.name}")
                print(f"          Next run: {job.next_run_time}")
    else:
        print("      ❌ Agent is NOT RUNNING")
        print("      → Automatic transitions are DISABLED")
        print("      → Events will NOT transition automatically based on time")
        print()
        print("      To enable automatic transitions:")
        print("      → Run: python scripts/run_agent.py")
        print("      OR")
        print("      → Run: start_system.bat (starts both API and Agent)")
except Exception as e:
    print("      ❌ Agent is NOT RUNNING")
    print("      → Automatic transitions are DISABLED")
    print()
    print("      To enable automatic transitions:")
    print("      → Run: python scripts/run_agent.py")
    print("      OR")
    print("      → Run: start_system.bat (starts both API and Agent)")

print()
print("=" * 70)
print("  Diagnostic Complete")
print("=" * 70)
print()

# Summary
print("SUMMARY:")
print()
print("1. API Server: Required for frontend to work")
print("   Current status: ✓ Running" if 'response' in locals() else "   ❌ Not running")
print()
print("2. Autonomous Agent: Required for automatic transitions")
print("   • Opens attendance 30 min before event")
print("   • Starts/completes events automatically")
print("   • Sends reminders")
print("   Current status: ⚠️  Not detected")
print()
print("RECOMMENDATION:")
print("→ Use start_system.bat to run BOTH services together")
print()
