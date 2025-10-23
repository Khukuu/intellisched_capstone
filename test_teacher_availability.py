#!/usr/bin/env python3
"""
Test script for teacher availability days feature
"""

from database import load_subjects_from_db, load_teachers_from_db, load_rooms_from_db, update_teacher
from scheduler import generate_schedule

def test_teacher_availability():
    print("🧪 Testing Teacher Availability Days Feature")
    print("=" * 60)
    
    try:
        # Load data
        subjects = load_subjects_from_db()
        teachers = load_teachers_from_db()
        rooms = load_rooms_from_db()
        
        print(f"📚 Subjects: {len(subjects)}")
        print(f"👨‍🏫 Teachers: {len(teachers)}")
        print(f"🏫 Rooms: {len(rooms)}")
        
        # Test 1: Check if availability_days field exists in teacher data
        print(f"\nChecking teacher data structure...")
        if teachers:
            sample_teacher = teachers[0]
            print(f"Sample teacher fields: {list(sample_teacher.keys())}")
            if 'availability_days' in sample_teacher:
                print(f"✅ availability_days field found: {sample_teacher['availability_days']}")
            else:
                print("❌ availability_days field not found - need to run migration")
                return
        
        # Test 2: Update a teacher to have limited availability
        print(f"\nTesting teacher availability update...")
        test_teacher_id = teachers[0]['teacher_id']
        print(f"Updating teacher {test_teacher_id} ({teachers[0]['teacher_name']})")
        
        # Set teacher to only be available on Mon, Wed, Fri
        limited_availability = ['Mon', 'Wed', 'Fri']
        update_teacher(test_teacher_id, {
            'teacher_name': teachers[0]['teacher_name'],
            'can_teach': teachers[0]['can_teach'],
            'availability_days': limited_availability
        })
        print(f"✅ Updated teacher availability to: {limited_availability}")
        
        # Test 3: Test scheduler with availability constraints
        print(f"\nTesting scheduler with availability constraints...")
        semester_filter = 1  # Use integer to match database
        # Fix the program_sections structure - it should be nested by program
        program_sections = {
            'CS': {1: 1, 2: 1, 3: 1, 4: 0}
        }
        
        result = generate_schedule(subjects, teachers, rooms, semester_filter, program_sections, programs=['CS'])
        
        if result and 'schedule' in result:
            schedule = result['schedule']
            print(f"✅ Scheduler completed successfully!")
            print(f"Generated {len(schedule)} schedule items")
            
            # Check if the limited availability teacher is only scheduled on their available days
            limited_teacher_name = teachers[0]['teacher_name']
            teacher_schedules = [item for item in schedule if item['teacher_name'] == limited_teacher_name]
            
            if teacher_schedules:
                print(f"\n📅 Checking {limited_teacher_name}'s schedule:")
                for item in teacher_schedules:
                    print(f"  - {item['subject_code']} on {item['day']} at {item['start_time_slot']}")
                
                # Verify all scheduled days are in availability
                scheduled_days = set(item['day'] for item in teacher_schedules)
                invalid_days = scheduled_days - set(limited_availability)
                if invalid_days:
                    print(f"❌ Teacher scheduled on unavailable days: {invalid_days}")
                else:
                    print(f"✅ All scheduled days are within availability: {scheduled_days}")
            else:
                print(f"ℹ️ Teacher {limited_teacher_name} not scheduled (may be due to other constraints)")
        else:
            print("⚠️ No schedule generated")
            
    except Exception as e:
        print(f"❌ Error in teacher availability test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_teacher_availability()
