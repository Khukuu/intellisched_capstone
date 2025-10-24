#!/usr/bin/env python3
"""
Direct test of the scheduler to identify issues
"""

from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db
from scheduler import generate_schedule

def test_scheduler_direct():
    print("🧪 Testing Scheduler Directly")
    print("=" * 50)
    
    try:
        # Load data
        subjects = load_courses_from_db()
        teachers = load_teachers_from_db()
        rooms = load_rooms_from_db()
        
        print(f"📚 Subjects: {len(subjects)}")
        print(f"👨‍🏫 Teachers: {len(teachers)}")
        print(f"🏫 Rooms: {len(rooms)}")
        
        # Test parameters
        semester_filter = 1
        desired_sections_per_year = {1: 1, 2: 1, 3: 1, 4: 0}
        
        print(f"\n🎯 Testing with semester {semester_filter} and sections {desired_sections_per_year}")
        
        # Test the scheduler directly
        result = generate_schedule(subjects, teachers, rooms, semester_filter, desired_sections_per_year)
        
        print(f"✅ Scheduler completed successfully!")
        print(f"Generated {len(result)} schedule items")
        
        if result:
            print("Sample results:")
            if isinstance(result, list):
                for item in result[:5]:
                    print(f"  - {item}")
            else:
                print(f"  - {result}")
        else:
            print("⚠️ No schedule items generated")
            
    except Exception as e:
        print(f"❌ Error in scheduler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scheduler_direct()
