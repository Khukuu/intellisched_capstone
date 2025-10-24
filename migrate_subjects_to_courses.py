#!/usr/bin/env python3
"""
Migration script to rename 'subjects' to 'courses' in the database schema.
This script handles the database schema changes safely.
"""

import os
import sys
from database import ScheduleDatabase

def migrate_database():
    """Migrate the database schema from subjects to courses"""
    print("Starting migration from 'subjects' to 'courses'...")
    
    try:
        # Initialize database connection
        db = ScheduleDatabase()
        
        # Check if migration is needed
        print("Checking current database schema...")
        
        # Check if old columns exist
        cs_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' 
            AND column_name IN ('subject_code', 'subject_name')
        """)
        
        it_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'it_curriculum' 
            AND column_name IN ('subject_code', 'subject_name')
        """)
        
        sections_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sections' 
            AND column_name = 'subject_code'
        """)
        
        if not cs_columns and not it_columns and not sections_columns:
            print("Migration already completed - no old columns found")
            return True
            
        print("Found old columns, proceeding with migration...")
        
        # Step 1: Add new columns
        print("Adding new course_code and course_name columns...")
        
        # CS curriculum
        if cs_columns:
            db.db.execute_single("ALTER TABLE cs_curriculum ADD COLUMN IF NOT EXISTS course_code VARCHAR(50)")
            db.db.execute_single("ALTER TABLE cs_curriculum ADD COLUMN IF NOT EXISTS course_name VARCHAR(255)")
            
            # Copy data from old columns to new columns
            db.db.execute_single("UPDATE cs_curriculum SET course_code = subject_code WHERE course_code IS NULL")
            db.db.execute_single("UPDATE cs_curriculum SET course_name = subject_name WHERE course_name IS NULL")
            
            print("CS curriculum data migrated")
        
        # IT curriculum
        if it_columns:
            db.db.execute_single("ALTER TABLE it_curriculum ADD COLUMN IF NOT EXISTS course_code VARCHAR(50)")
            db.db.execute_single("ALTER TABLE it_curriculum ADD COLUMN IF NOT EXISTS course_name VARCHAR(255)")
            
            # Copy data from old columns to new columns
            db.db.execute_single("UPDATE it_curriculum SET course_code = subject_code WHERE course_code IS NULL")
            db.db.execute_single("UPDATE it_curriculum SET course_name = subject_name WHERE course_name IS NULL")
            
            print("IT curriculum data migrated")
        
        # Sections table
        if sections_columns:
            db.db.execute_single("ALTER TABLE sections ADD COLUMN IF NOT EXISTS course_code VARCHAR(50)")
            db.db.execute_single("UPDATE sections SET course_code = subject_code WHERE course_code IS NULL")
            print("Sections data migrated")
        
        # Step 2: Update constraints and indexes
        print("Updating constraints and indexes...")
        
        # Drop old unique constraints and add new ones
        try:
            db.db.execute_single("ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code)")
        except Exception as e:
            print(f"Warning: Could not update CS curriculum constraint: {e}")
        
        try:
            db.db.execute_single("ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code)")
        except Exception as e:
            print(f"Warning: Could not update IT curriculum constraint: {e}")
        
        # Step 3: Make new columns NOT NULL
        print("Making new columns NOT NULL...")
        
        try:
            db.db.execute_single("ALTER TABLE cs_curriculum ALTER COLUMN course_code SET NOT NULL")
            db.db.execute_single("ALTER TABLE cs_curriculum ALTER COLUMN course_name SET NOT NULL")
        except Exception as e:
            print(f"Warning: Could not set CS curriculum columns NOT NULL: {e}")
        
        try:
            db.db.execute_single("ALTER TABLE it_curriculum ALTER COLUMN course_code SET NOT NULL")
            db.db.execute_single("ALTER TABLE it_curriculum ALTER COLUMN course_name SET NOT NULL")
        except Exception as e:
            print(f"Warning: Could not set IT curriculum columns NOT NULL: {e}")
        
        print("Migration completed successfully!")
        print("Note: Old columns (subject_code, subject_name) are preserved for safety.")
        print("You can drop them manually after verifying the migration worked correctly.")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
