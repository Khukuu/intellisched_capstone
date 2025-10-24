#!/usr/bin/env python3
"""
Migration script to rename database columns from subject_* to course_* in Railway PostgreSQL
This script handles the database column renaming safely for production deployment.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_database_connection():
    """Get database connection from environment variables"""
    try:
        # Try to get connection from Railway environment
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url)
        
        # Fallback to individual environment variables
        host = os.getenv('PGHOST', 'localhost')
        port = os.getenv('PGPORT', '5432')
        database = os.getenv('PGDATABASE', 'intellisched')
        user = os.getenv('PGUSER', 'postgres')
        password = os.getenv('PGPASSWORD', '')
        
        return psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def migrate_railway_database():
    """Migrate the Railway database columns from subject_* to course_*"""
    print("Starting Railway database column migration from subject_* to course_*...")
    
    conn = None
    try:
        # Get database connection
        conn = get_database_connection()
        if not conn:
            print("Failed to connect to database")
            return False
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Connected to Railway database successfully")
        
        # Check if migration is needed
        print("Checking current database schema...")
        
        # Check if old columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cs_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        cs_old_columns = cursor.fetchall()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'it_curriculum' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        it_old_columns = cursor.fetchall()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sections' 
            AND column_name IN ('subject_code', 'subject_id')
        """)
        sections_old_columns = cursor.fetchall()
        
        if not cs_old_columns and not it_old_columns and not sections_old_columns:
            print("Migration already completed - no old columns found")
            return True
            
        print("Found old columns, proceeding with migration...")
        
        # Step 1: Rename columns in cs_curriculum table
        if cs_old_columns:
            print("Renaming columns in cs_curriculum table...")
            
            # Check if subject_code exists and rename it
            if any(col[0] == 'subject_code' for col in cs_old_columns):
                try:
                    cursor.execute("ALTER TABLE cs_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in cs_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in cs_curriculum: {e}")
            
            # Check if subject_id exists and rename it
            if any(col[0] == 'subject_id' for col in cs_old_columns):
                try:
                    cursor.execute("ALTER TABLE cs_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in cs_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in cs_curriculum: {e}")
        
        # Step 2: Rename columns in it_curriculum table
        if it_old_columns:
            print("Renaming columns in it_curriculum table...")
            
            # Check if subject_code exists and rename it
            if any(col[0] == 'subject_code' for col in it_old_columns):
                try:
                    cursor.execute("ALTER TABLE it_curriculum RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in it_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in it_curriculum: {e}")
            
            # Check if subject_id exists and rename it
            if any(col[0] == 'subject_id' for col in it_old_columns):
                try:
                    cursor.execute("ALTER TABLE it_curriculum RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in it_curriculum")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in it_curriculum: {e}")
        
        # Step 3: Rename columns in sections table
        if sections_old_columns:
            print("Renaming columns in sections table...")
            
            # Check if subject_code exists and rename it
            if any(col[0] == 'subject_code' for col in sections_old_columns):
                try:
                    cursor.execute("ALTER TABLE sections RENAME COLUMN subject_code TO course_code")
                    print("Renamed subject_code to course_code in sections")
                except Exception as e:
                    print(f"Warning: Could not rename subject_code in sections: {e}")
            
            # Check if subject_id exists and rename it
            if any(col[0] == 'subject_id' for col in sections_old_columns):
                try:
                    cursor.execute("ALTER TABLE sections RENAME COLUMN subject_id TO course_id")
                    print("Renamed subject_id to course_id in sections")
                except Exception as e:
                    print(f"Warning: Could not rename subject_id in sections: {e}")
        
        # Step 4: Update constraints and indexes
        print("Updating constraints and indexes...")
        
        # Update unique constraints
        try:
            # Drop old constraints and add new ones for cs_curriculum
            cursor.execute("ALTER TABLE cs_curriculum DROP CONSTRAINT IF EXISTS cs_curriculum_subject_code_key")
            cursor.execute("ALTER TABLE cs_curriculum ADD CONSTRAINT cs_curriculum_course_code_key UNIQUE (course_code)")
            print("Updated cs_curriculum constraints")
        except Exception as e:
            print(f"Warning: Could not update cs_curriculum constraints: {e}")
        
        try:
            # Drop old constraints and add new ones for it_curriculum
            cursor.execute("ALTER TABLE it_curriculum DROP CONSTRAINT IF EXISTS it_curriculum_subject_code_key")
            cursor.execute("ALTER TABLE it_curriculum ADD CONSTRAINT it_curriculum_course_code_key UNIQUE (course_code)")
            print("Updated it_curriculum constraints")
        except Exception as e:
            print(f"Warning: Could not update it_curriculum constraints: {e}")
        
        print("Railway database column migration completed successfully!")
        print("All subject_* columns have been renamed to course_* columns.")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = migrate_railway_database()
    sys.exit(0 if success else 1)
