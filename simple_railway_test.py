#!/usr/bin/env python3
"""
Simple Railway test without Unicode characters
"""

import os
import sys

def main():
    print("Railway Test Starting...")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Directory: {os.getcwd()}")
    print(f"Railway Env: {os.getenv('RAILWAY_ENVIRONMENT', 'No')}")
    
    try:
        print("Testing imports...")
        import fastapi
        print("FastAPI: OK")
        
        import uvicorn
        print("Uvicorn: OK")
        
        import psycopg2
        print("Psycopg2: OK")
        
        import jwt
        print("PyJWT: OK")
        
        from ortools.sat.python import cp_model
        print("OR-Tools: OK")
        
        print("Testing app modules...")
        from database import ScheduleDatabase, load_subjects_from_db
        print("Database: OK")
        
        from scheduler import generate_schedule
        print("Scheduler: OK")
        
        from app import app
        print("FastAPI App: OK")
        
        print("All tests passed!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
