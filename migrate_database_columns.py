#!/usr/bin/env python3
"""
Migration script to rename database columns from subject_* to course_*
This script handles the database column renaming safely.
"""

import os
import sys
from database import ScheduleDatabase

def migrate_database_columns():
    """Migrate the database columns from subject_* to course_*"""
    print("Starting database column migration from subject_* to course_*...")
    
    try:
        # Initialize database connection
        db = ScheduleDatabase()
        
        # Check if migration is needed
        print("Checking current database schema...")
        
        # Check if old columns exist and new columns don't exist
        cs_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        
        cs_new_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' 
            AND column_name IN ('course_code', 'course_id')
        """)
        
        it_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'it_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        
        it_new_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'it_curriculum' 
            AND column_name IN ('course_code', 'course_id')
        """)
        
        sections_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sections' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        
        sections_new_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sections' 
            AND column_name IN ('course_code', 'course_id')
        """)
        
        if not cs_old_columns and not it_old_columns and not sections_old_columns:
            print("Migration already completed - no old columns found")
            return True
            
        print("Found old columns, proceeding with migration...")
        
        # Step 1: Rename columns in cs_curriculum table
        if cs_old_columns:
            print("Renaming columns in cs_curriculum table...")
            
            # Check if subject_code exists and rename it
            if any(col['column_name'] == 'subject_code' for col in cs_old_columns):
                if not any(col['column_name'] == 'course_code' for col in cs_new_columns):
                    db.db.execute_single("ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in cs_curriculum")
                else:
                    print("course_code already exists in cs_curriculum")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in cs_old_columns):
                if not any(col['column_name'] == 'course_id' for col in cs_new_columns):
                    db.db.execute_single("ALTER TABLE cs_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in cs_curriculum")
                else:
                    print("course_id already exists in cs_curriculum")
        
        # Step 2: Rename columns in it_curriculum table
        if it_old_columns:
            print("Renaming columns in it_curriculum table...")
            
            # Check if subject_code exists and rename it
            if any(col['column_name'] == 'subject_code' for col in it_old_columns):
                if not any(col['column_name'] == 'course_code' for col in it_new_columns):
                    db.db.execute_single("ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in it_curriculum")
                else:
                    print("course_code already exists in it_curriculum")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in it_old_columns):
                if not any(col['column_name'] == 'course_id' for col in it_new_columns):
                    db.db.execute_single("ALTER TABLE it_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in it_curriculum")
                else:
                    print("course_id already exists in it_curriculum")
        
        # Step 3: Rename columns in sections table
        if sections_old_columns:
            print("Renaming columns in sections table...")
            
            # Check if subject_code exists and rename it
            if any(col['column_name'] == 'subject_code' for col in sections_old_columns):
                if not any(col['column_name'] == 'course_code' for col in sections_new_columns):
                    db.db.execute_single("ALTER TABLE sections RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in sections")
                else:
                    print("course_code already exists in sections")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in sections_old_columns):
                if not any(col['column_name'] == 'course_id' for col in sections_new_columns):
                    db.db.execute_single("ALTER TABLE sections RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in sections")
                else:
                    print("course_id already exists in sections")
        
        # Step 4: Update constraints and indexes
        print("Updating constraints and indexes...")
        
        # Update unique constraints
        try:
            # Drop old constraints and add new ones for cs_curriculum
            db.db.execute_single("ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code)")
            print("Updated cs_curriculum constraints")
        except Exception as e:
            print(f"Warning: Could not update cs_curriculum constraints: {e}")
        
        try:
            # Drop old constraints and add new ones for it_curriculum
            db.db.execute_single("ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key")
            db.db.execute_single("ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code)")
            print("Updated it_curriculum constraints")
        except Exception as e:
            print(f"Warning: Could not update it_curriculum constraints: {e}")
        
        print("Column migration completed successfully!")
        print("All subject_* columns have been renamed to course_* columns.")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database_columns()
    sys.exit(0 if success else 1)
