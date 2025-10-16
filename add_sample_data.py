#!/usr/bin/env python3
"""
Add Sample Data to Railway Database
This script adds basic sample data to get the app working
"""

import os
from database import db

def add_sample_data():
    """Add sample data to the database"""
    
    print("📦 Adding Sample Data to Railway Database")
    print("=" * 40)
    
    try:
        # Add sample subjects
        print("1. Adding sample subjects...")
        sample_subjects = [
            ("CS101", "Introduction to Programming", 3, 0, 1, "CS"),
            ("CS102", "Data Structures", 3, 0, 2, "CS"),
            ("CS201", "Algorithms", 3, 0, 3, "CS"),
            ("CS301", "Database Systems", 3, 0, 4, "CS"),
            ("CS401", "Software Engineering", 3, 0, 5, "CS")
        ]
        
        for code, name, units, lab_hours, year, program in sample_subjects:
            try:
                db.db.execute_single("""
                    INSERT INTO subjects (subject_code, subject_name, units, lab_hours_per_week, year_level, program_specialization)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (subject_code) DO NOTHING
                """, (code, name, units, lab_hours, year, program))
            except Exception as e:
                print(f"   ⚠️ Could not add {code}: {e}")
        
        print("✅ Sample subjects added!")
        
        # Add sample teachers
        print("2. Adding sample teachers...")
        sample_teachers = [
            ("T001", "Dr. John Smith", "CS101,CS102"),
            ("T002", "Dr. Jane Doe", "CS201,CS301"),
            ("T003", "Dr. Bob Johnson", "CS401"),
            ("T004", "Dr. Alice Brown", "CS101,CS201"),
            ("T005", "Dr. Charlie Wilson", "CS102,CS301")
        ]
        
        for teacher_id, name, can_teach in sample_teachers:
            try:
                db.db.execute_single("""
                    INSERT INTO teachers (teacher_id, teacher_name, can_teach)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (teacher_id) DO NOTHING
                """, (teacher_id, name, can_teach))
            except Exception as e:
                print(f"   ⚠️ Could not add {teacher_id}: {e}")
        
        print("✅ Sample teachers added!")
        
        # Add sample rooms
        print("3. Adding sample rooms...")
        sample_rooms = [
            ("R001", "Room 101", False),
            ("R002", "Room 102", False),
            ("R003", "Lab 201", True),
            ("R004", "Lab 202", True),
            ("R005", "Room 301", False)
        ]
        
        for room_id, name, is_lab in sample_rooms:
            try:
                db.db.execute_single("""
                    INSERT INTO rooms (room_id, room_name, is_laboratory)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (room_id) DO NOTHING
                """, (room_id, name, is_lab))
            except Exception as e:
                print(f"   ⚠️ Could not add {room_id}: {e}")
        
        print("✅ Sample rooms added!")
        
        print("\n🎉 Sample data added successfully!")
        print("Your app should now work with basic data.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        return False

if __name__ == "__main__":
    print("Railway Sample Data Setup")
    print("This will add basic sample data to your database.")
    
    confirm = input("\nDo you want to add sample data? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        add_sample_data()
    else:
        print("❌ Operation cancelled.")
