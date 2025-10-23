#!/usr/bin/env python3
"""
Fix Railway Database Schema
This script adds the missing availability_days column to the teachers table
"""

import os
from database import db

def fix_teachers_table():
    """Add missing availability_days column to teachers table"""
    
    print("Fixing Railway Database Schema")
    print("=" * 40)
    
    try:
        # Check if column exists
        print("1. Checking teachers table structure...")
        columns_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'teachers' AND table_schema = 'public'
        """
        columns = db.db.execute_query(columns_query)
        column_names = [col['column_name'] for col in columns]
        print(f"   Current columns: {column_names}")
        
        # Add availability_days column if it doesn't exist
        if 'availability_days' not in column_names:
            print("2. Adding availability_days column...")
            db.db.execute_single("""
                ALTER TABLE teachers 
                ADD COLUMN availability_days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri'
            """)
            print("✅ availability_days column added!")
        else:
            print("✅ availability_days column already exists!")
        
        # Update existing teachers with default availability
        print("3. Setting default availability for existing teachers...")
        db.db.execute_single("""
            UPDATE teachers 
            SET availability_days = 'Mon,Tue,Wed,Thu,Fri' 
            WHERE availability_days IS NULL OR availability_days = ''
        """)
        print("✅ Default availability set!")
        
        print("\nDatabase schema fixed!")
        print("Your app should now start without errors.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False

if __name__ == "__main__":
    print("Railway Database Schema Fix")
    print("This will add the missing availability_days column.")
    
    fix_teachers_table()
