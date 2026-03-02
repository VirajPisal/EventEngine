"""
Test Stage 1 - Run seed script with proper imports
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run seed
from db.seed import seed_database

if __name__ == "__main__":
    seed_database(drop_existing="--drop" in sys.argv or "-d" in sys.argv)
