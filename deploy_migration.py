#!/usr/bin/env python3
"""
Deployment script to run Railway database migration
This script can be run in Railway environment
"""

import os
import sys

def main():
    print("🚀 Starting Railway Database Migration Deployment")
    print("=" * 50)
    
    # Check if we're in Railway environment
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("✅ Running in Railway environment")
    else:
        print("⚠️  Not in Railway environment - this should be run on Railway")
    
    # Check database connection
    try:
        from database import ScheduleDatabase
        db = ScheduleDatabase()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Run the migration
    try:
        from migrate_railway_simple import migrate_railway_columns
        success = migrate_railway_columns()
        
        if success:
            print("✅ Migration completed successfully!")
            print("🎉 Railway database is now updated to use course_* columns")
            return True
        else:
            print("❌ Migration failed!")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
