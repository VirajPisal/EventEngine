"""
Simple run script for EventEngine API server
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("  Starting EventEngine API Server")
    print("=" * 70)
    print()
    print("  Open → http://localhost:8000/frontend/login.html")
    print()
    print("  API Docs → http://localhost:8000/docs")
    print()
    print("=" * 70)
    print()
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
