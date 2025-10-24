#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection and data loading
"""

from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db

def test_database():
    print("🧪 Testing PostgreSQL Database Connection")
    print("=" * 50)
    
    try:
        # Test subjects
        print("📚 Loading subjects...")
        subjects = load_courses_from_db()
        print(f"   Found {len(subjects)} subjects")
        if subjects:
            print(f"   Sample: {subjects[0]['subject_code']} - {subjects[0]['subject_name']}")
        
        # Test teachers
        print("\n👨‍🏫 Loading teachers...")
        teachers = load_teachers_from_db()
        print(f"   Found {len(teachers)} teachers")
        if teachers:
            print(f"   Sample: {teachers[0]['teacher_id']} - {teachers[0]['teacher_name']}")
        
        # Test rooms
        print("\n🏫 Loading rooms...")
        rooms = load_rooms_from_db()
        print(f"   Found {len(rooms)} rooms")
        if rooms:
            print(f"   Sample: {rooms[0]['room_id']} - {rooms[0]['room_name']}")
        
        print("\n✅ Database test completed!")
        
        if len(subjects) == 0:
            print("\n⚠️ Warning: No subjects found in database!")
            print("   Make sure you have inserted subject data into the 'subjects' table")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("\n🔧 Check your PostgreSQL connection and database setup")

if __name__ == "__main__":
    test_database()
