#!/usr/bin/env python3
"""
Debug script to understand schedule generation issues
"""

from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db

def debug_schedule_issue():
    print("🔍 Debugging Schedule Generation Issue")
    print("=" * 50)
    
    # Load data
    subjects = load_courses_from_db()
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()
    
    print(f"📚 Subjects loaded: {len(subjects)}")
    print(f"👨‍🏫 Teachers loaded: {len(teachers)}")
    print(f"🏫 Rooms loaded: {len(rooms)}")
    
    # Check semester data
    print("\n📊 Semester Analysis:")
    semesters = {}
    year_levels = {}
    
    for subject in subjects:
        semester = subject.get('semester')
        year_level = subject.get('year_level')
        
        if semester not in semesters:
            semesters[semester] = 0
        semesters[semester] += 1
        
        if year_level not in year_levels:
            year_levels[year_level] = 0
        year_levels[year_level] += 1
    
    print(f"Available semesters: {semesters}")
    print(f"Available year levels: {year_levels}")
    
    # Test semester filtering logic
    print("\n🧪 Testing Semester Filtering Logic:")
    
    # Test with semester 1
    semester_filter = 1
    print(f"\nTesting with semester_filter = {semester_filter}")
    
    try:
        available_years = set(
            int(s.get('year_level', 0)) for s in subjects
            if s.get('semester') == semester_filter and s.get('year_level')
        )
        print(f"Available years for semester {semester_filter}: {available_years}")
        
        # Check what subjects match
        matching_subjects = [
            s for s in subjects 
            if s.get('semester') == semester_filter
        ]
        print(f"Subjects matching semester {semester_filter}: {len(matching_subjects)}")
        
        if matching_subjects:
            print("Sample matching subjects:")
            for s in matching_subjects[:5]:
                print(f"  - {s['subject_code']}: Year {s.get('year_level')}, Semester {s.get('semester')}")
        
    except Exception as e:
        print(f"Error in filtering: {e}")
    
    # Test with semester as string
    print(f"\nTesting with semester_filter = '{semester_filter}' (string)")
    try:
        available_years = set(
            int(s.get('year_level', 0)) for s in subjects
            if str(s.get('semester')) == str(semester_filter) and s.get('year_level')
        )
        print(f"Available years for semester '{semester_filter}': {available_years}")
        
        # Check what subjects match
        matching_subjects = [
            s for s in subjects 
            if str(s.get('semester')) == str(semester_filter)
        ]
        print(f"Subjects matching semester '{semester_filter}': {len(matching_subjects)}")
        
    except Exception as e:
        print(f"Error in filtering: {e}")
    
    # Check teacher data
    print("\n👨‍🏫 Teacher Analysis:")
    for teacher in teachers[:3]:
        print(f"Teacher: {teacher}")
    
    # Check room data
    print("\n🏫 Room Analysis:")
    for room in rooms[:3]:
        print(f"Room: {room}")

if __name__ == "__main__":
    debug_schedule_issue()
