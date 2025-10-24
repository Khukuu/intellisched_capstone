#!/usr/bin/env python3
"""
Railway deployment debug script
"""

import os
import sys
import traceback

def debug_railway():
    print("=== Railway Debug Information ===")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'Not Railway')}")
    print(f"Port: {os.getenv('PORT', 'Not set')}")
    print(f"Database URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set'}")
    
    print("\n=== Testing Imports ===")
    
    # Test basic imports
    try:
        import fastapi
        print("FastAPI imported")
    except Exception as e:
        print(f"FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        print("Uvicorn imported")
    except Exception as e:
        print(f"✗ Uvicorn import failed: {e}")
        return False
    
    try:
        import psycopg2
        print("✓ Psycopg2 imported")
    except Exception as e:
        print(f"✗ Psycopg2 import failed: {e}")
        return False
    
    try:
        import jwt
        print("✓ PyJWT imported")
    except Exception as e:
        print(f"✗ PyJWT import failed: {e}")
        return False
    
    try:
        from ortools.sat.python import cp_model
        print("✓ OR-Tools imported")
    except Exception as e:
        print(f"✗ OR-Tools import failed: {e}")
        return False
    
    print("\n=== Testing Application Modules ===")
    
    # Test database module
    try:
        from database import ScheduleDatabase, load_subjects_from_db
        print("✓ Database module imported")
        
        # Test database connection
        db = ScheduleDatabase()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database module failed: {e}")
        traceback.print_exc()
        return False
    
    # Test scheduler module
    try:
        from scheduler import generate_schedule
        print("✓ Scheduler module imported")
    except Exception as e:
        print(f"✗ Scheduler module failed: {e}")
        traceback.print_exc()
        return False
    
    # Test app module
    try:
        from app import app
        print("✓ FastAPI app imported")
    except Exception as e:
        print(f"✗ FastAPI app failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n=== All Tests Passed ===")
    return True

if __name__ == "__main__":
    success = debug_railway()
    sys.exit(0 if success else 1)
