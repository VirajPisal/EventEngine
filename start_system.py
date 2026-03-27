"""
EventEngine System Launcher
Starts both API server AND autonomous agent together
Usage: python start_system.py
"""
import sys
import subprocess
import signal
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Process holders
api_process = None
agent_process = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully - shutdown both processes"""
    print("\n\n" + "=" * 70)
    print("  🛑 Shutting down EventEngine System...")
    print("=" * 70)
    
    if agent_process:
        print("  └─ Stopping Agent...")
        agent_process.terminate()
        agent_process.wait()
        print("     ✓ Agent stopped")
    
    if api_process:
        print("  └─ Stopping API Server...")
        api_process.terminate()
        api_process.wait()
        print("     ✓ API Server stopped")
    
    print("=" * 70)
    print("  ✓ Shutdown complete")
    print("=" * 70)
    sys.exit(0)


def start_system():
    """Start both API server and agent"""
    global api_process, agent_process
    
    print("=" * 70)
    print("  🚀 EventEngine - Complete System Startup")
    print("=" * 70)
    print()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start API Server
        print("  [1/2] Starting API Server...")
        api_process = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        print("      ✓ API Server started (PID: {})".format(api_process.pid))
        
        # Wait a bit for API server to initialize
        time.sleep(3)
        
        # Start Autonomous Agent
        print("  [2/2] Starting Autonomous Agent...")
        agent_process = subprocess.Popen(
            [sys.executable, "scripts/run_agent.py"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        print("      ✓ Agent started (PID: {})".format(agent_process.pid))
        
        print()
        print("=" * 70)
        print("  ✅ EventEngine System Running")
        print("=" * 70)
        print()
        print("  📱 Frontend URL:")
        print("     → http://localhost:8000/frontend/login.html")
        print()
        print("  📚 API Documentation:")
        print("     → http://localhost:8000/docs")
        print()
        print("  🤖 Autonomous Features:")
        print("     ✓ Auto state transitions (based on time)")
        print("     ✓ Open attendance 30 min before event")
        print("     ✓ Start/complete events automatically")
        print("     ✓ Send reminder notifications")
        print()
        print("=" * 70)
        print("  Press Ctrl+C to stop both services")
        print("=" * 70)
        print()
        
        # Monitor both processes
        while True:
            # Check if API process died
            if api_process.poll() is not None:
                print("  ⚠️  API Server stopped unexpectedly!")
                if agent_process:
                    agent_process.terminate()
                sys.exit(1)
            
            # Check if agent process died
            if agent_process.poll() is not None:
                print("  ⚠️  Agent stopped unexpectedly!")
                if api_process:
                    api_process.terminate()
                sys.exit(1)
            
            time.sleep(1)
    
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        if agent_process:
            agent_process.terminate()
        if api_process:
            api_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    start_system()
