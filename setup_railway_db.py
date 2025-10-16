#!/usr/bin/env python3
"""
Railway Database Setup Script
This script sets up the database schema and populates it with initial data
"""

import os
import sys
from database import db

def setup_database():
    """Set up the database schema and initial data"""
    
    print("🚀 Setting up Railway Database")
    print("=" * 40)
    
    try:
        # Test database connection
        print("1. Testing database connection...")
        test_query = "SELECT 1 as test"
        result = db.db.execute_query(test_query)
        print("✅ Database connection successful!")
        
        # Create tables (this should already be done by the app)
        print("2. Checking table structure...")
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """
        tables = db.db.execute_query(tables_query)
        print(f"✅ Found {len(tables)} tables: {[t['table_name'] for t in tables]}")
        
        # Check if we have data
        print("3. Checking for existing data...")
        
        # Check subjects
        subjects_count = len(db.db.execute_query("SELECT COUNT(*) as count FROM subjects"))
        print(f"   Subjects: {subjects_count}")
        
        # Check teachers
        teachers_count = len(db.db.execute_query("SELECT COUNT(*) as count FROM teachers"))
        print(f"   Teachers: {teachers_count}")
        
        # Check rooms
        rooms_count = len(db.db.execute_query("SELECT COUNT(*) as count FROM rooms"))
        print(f"   Rooms: {rooms_count}")
        
        if subjects_count == 0 or teachers_count == 0 or rooms_count == 0:
            print("\n⚠️ Database is empty. You need to populate it with data.")
            print("   Options:")
            print("   1. Upload CSV files through the web interface")
            print("   2. Use the migration script with your local data")
            print("   3. Add sample data manually")
        else:
            print("\n✅ Database has data and should be working!")
            
        return True
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

if __name__ == "__main__":
    print("Railway Database Setup")
    print("This will check your database connection and structure.")
    
    if setup_database():
        print("\n🎉 Database setup completed!")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
