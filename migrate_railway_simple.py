#!/usr/bin/env python3
"""
Simple Railway database migration script
This script can be run in the Railway environment to rename columns
"""

import os
import sys
from database import ScheduleDatabase

def migrate_railway_columns():
    """Migrate Railway database columns using existing database connection"""
    print("Starting Railway database column migration...")
    
    try:
        # Use existing database connection
        db = ScheduleDatabase()
        
        print("Connected to Railway database successfully")
        
        # Check if migration is needed
        print("Checking current database schema...")
        
        # Check if old columns exist
        cs_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        
        it_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'it_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        
        sections_old_columns = db.db.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sections' 
            AND column_name IN ('subject_code', 'subject_id')
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
                try:
                    db.db.execute_single("ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in cs_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in cs_curriculum: {e}")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in cs_old_columns):
                try:
                    db.db.execute_single("ALTER TABLE cs_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in cs_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in cs_curriculum: {e}")
        
        # Step 2: Rename columns in it_curriculum table
        if it_old_columns:
            print("Renaming columns in it_curriculum table...")
            
            # Check if subject_code exists and rename it
            if any(col['column_name'] == 'subject_code' for col in it_old_columns):
                try:
                    db.db.execute_single("ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in it_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in it_curriculum: {e}")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in it_old_columns):
                try:
                    db.db.execute_single("ALTER TABLE it_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in it_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in it_curriculum: {e}")
        
        # Step 3: Rename columns in sections table
        if sections_old_columns:
            print("Renaming columns in sections table...")
            
            # Check if subject_code exists and rename it
            if any(col['column_name'] == 'subject_code' for col in sections_old_columns):
                try:
                    db.db.execute_single("ALTER TABLE sections RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in sections")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in sections: {e}")
            
            # Check if subject_id exists and rename it
            if any(col['column_name'] == 'subject_id' for col in sections_old_columns):
                try:
                    db.db.execute_single("ALTER TABLE sections RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in sections")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in sections: {e}")
        
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
        
        print("Railway database column migration completed successfully!")
        print("All subject_* columns have been renamed to course_* columns.")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_railway_columns()
    sys.exit(0 if success else 1)
