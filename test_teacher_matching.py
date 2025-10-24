#!/usr/bin/env python3
"""
Test teacher-subject matching logic
"""

from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db

def test_teacher_matching():
    print("🧪 Testing Teacher-Subject Matching")
    print("=" * 40)
    
    # Load data
    subjects = load_courses_from_db()
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()
    
    print(f"📚 Subjects: {len(subjects)}")
    print(f"👨‍🏫 Teachers: {len(teachers)}")
    
    # Test the teacher cleaning logic from scheduler
    print("\n🔧 Testing Teacher Data Cleaning:")
    cleaned_teachers_data = []
    for t in teachers:
        teacher_id = t.get('teacher_id')
        teacher_name = t.get('teacher_name')
        if teacher_id and teacher_name:
            cleaned_teachers_data.append({
                'teacher_id': teacher_id,
                'teacher_name': teacher_name.strip(),
                'can_teach': str(t.get('can_teach', '')).replace(' ', '')
            })
        else:
            print(f"Warning: Skipping teacher row due to missing ID or name: {t}")
    
    print(f"Cleaned teachers: {len(cleaned_teachers_data)}")
    
    # Test subject-teacher matching for a few subjects
    print("\n🎯 Testing Subject-Teacher Matching:")
    
    for subject in subjects[:5]:  # Test first 5 subjects
        subject_code = subject['subject_code'].strip()
        print(f"\nSubject: {subject_code}")
        
        valid_teachers_for_subj = [
            t['teacher_id'] for t in cleaned_teachers_data 
            if subject_code in t['can_teach'].split(',')
        ]
        
        print(f"  Valid teachers: {valid_teachers_for_subj}")
        
        if not valid_teachers_for_subj:
            print(f"  ⚠️ No teachers found for {subject_code}")
            # Show what teachers can teach
            for teacher in cleaned_teachers_data[:3]:
                print(f"    Teacher {teacher['teacher_id']} can teach: {teacher['can_teach']}")
    
    # Test room filtering
    print("\n🏫 Testing Room Filtering:")
    lecture_rooms = [
        r['room_id'] for r in rooms
        if not r.get('is_laboratory', False)
    ]
    lab_rooms = [
        r['room_id'] for r in rooms
        if r.get('is_laboratory', False)
    ]
    
    print(f"Lecture rooms: {lecture_rooms}")
    print(f"Lab rooms: {lab_rooms}")

if __name__ == "__main__":
    test_teacher_matching()
