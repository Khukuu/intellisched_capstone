#!/usr/bin/env python3
"""
Test script to verify Railway deployment environment
"""

import os
import sys

def test_environment():
    print("=== Railway Environment Test ===")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'Not Railway')}")
    
    # Test database connection
    try:
        from database import ScheduleDatabase
        db = ScheduleDatabase()
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
    # Test imports
    try:
        from database import load_subjects_from_db, load_teachers_from_db, load_rooms_from_db
        print("Database imports successful")
    except Exception as e:
        print(f"Database imports failed: {e}")
        return False
    
    try:
        from scheduler import generate_schedule
        print("Scheduler import successful")
    except Exception as e:
        print(f"Scheduler import failed: {e}")
        return False
    
    try:
        from app import app
        print("FastAPI app import successful")
    except Exception as e:
        print(f"FastAPI app import failed: {e}")
        return False
    
    print("All tests passed!")
    return True

if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)
