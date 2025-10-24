#!/usr/bin/env python3
"""
One-liner migration script for Railway
"""

import os
import sys
from database import ScheduleDatabase

def main():
    print("Railway Database Migration")
    db = ScheduleDatabase()
    
    # Check current state
    try:
        # Check if old columns exist
        cs_old = db.db.execute_query("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' AND column_name = 'subject_code'
        """)
        
        if cs_old:
            print("Found subject_code columns, renaming...")
            
            # Rename columns
            db.db.execute_single("ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code")
            db.db.execute_single("ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code") 
            db.db.execute_single("ALTER TABLE sections RENAME COLUMN subject_code TO course_code")
            
            # Update constraints
            db.db.execute_single("ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code)")
            db.db.execute_single("ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code)")
            
            print("Migration completed!")
        else:
            print("Columns already migrated")
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
