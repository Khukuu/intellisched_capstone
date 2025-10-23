#!/usr/bin/env python3
"""
Migration script to populate PostgreSQL database with CSV data
"""

from database import db

def main():
    print("Starting migration from CSV to PostgreSQL...")
    print(f"Connection string: {db.db.connection_string}")
    
    try:
        # Test database connection
        print("Testing database connection...")
        test_connection = db.db.get_connection()
        test_connection.close()
        print("✅ Database connection successful!")
        
        # Migrate data from CSV files
        print("\nMigrating data from CSV files...")
        db.migrate_from_csv()
        
        # Verify migration
        print("\nVerifying migration...")
        subjects_count = len(db.load_subjects())
        teachers_count = len(db.load_teachers())
        rooms_count = len(db.load_rooms())
        
        print(f"✅ Migration completed successfully!")
        print(f"   📚 Subjects: {subjects_count}")
        print(f"   👨‍🏫 Teachers: {teachers_count}")
        print(f"   🏫 Rooms: {rooms_count}")
        
        # Show sample data
        print("\n📋 Sample data verification:")
        subjects = db.load_subjects()
        if subjects:
            print(f"   Sample subject: {subjects[0]['subject_code']} - {subjects[0]['subject_name']}")
        
        teachers = db.load_teachers()
        if teachers:
            print(f"   Sample teacher: {teachers[0]['teacher_id']} - {teachers[0]['teacher_name']}")
        
        rooms = db.load_rooms()
        if rooms:
            print(f"   Sample room: {rooms[0]['room_id']} - {rooms[0]['room_name']}")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\nTroubleshooting tips:")
        print("   1. Make sure PostgreSQL is running")
        print("   2. Verify the connection string is correct")
        print("   3. Ensure the database 'intellisched' exists")
        print("   4. Check that the user has proper permissions")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\nMigration completed! Your application is now using PostgreSQL.")
        print("You can now run your application with: python app.py")
    else:
        print("\nMigration failed. Please check the error messages above.")
        exit(1)
