#!/usr/bin/env python3
"""
Test script to verify frontend availability days integration
"""

from database import load_teachers_from_db, update_teacher

def test_frontend_availability():
    print("🧪 Testing Frontend Availability Days Integration")
    print("=" * 60)
    
    try:
        # Load teachers to check current data
        teachers = load_teachers_from_db()
        print(f"📚 Loaded {len(teachers)} teachers from database")
        
        if teachers:
            sample_teacher = teachers[0]
            print(f"\n📋 Sample teacher data structure:")
            print(f"  - teacher_id: {sample_teacher.get('teacher_id')}")
            print(f"  - teacher_name: {sample_teacher.get('teacher_name')}")
            print(f"  - can_teach: {sample_teacher.get('can_teach')}")
            print(f"  - availability_days: {sample_teacher.get('availability_days')}")
            
            # Test updating a teacher with specific availability
            test_teacher_id = sample_teacher['teacher_id']
            print(f"\nTesting teacher availability update...")
            
            # Set teacher to only be available on Tue, Thu, Sat
            limited_availability = ['Tue', 'Thu', 'Sat']
            update_teacher(test_teacher_id, {
                'teacher_name': sample_teacher['teacher_name'],
                'can_teach': sample_teacher['can_teach'],
                'availability_days': limited_availability
            })
            print(f"✅ Updated teacher availability to: {limited_availability}")
            
            # Reload teachers to verify the update
            updated_teachers = load_teachers_from_db()
            updated_teacher = next((t for t in updated_teachers if t['teacher_id'] == test_teacher_id), None)
            
            if updated_teacher:
                print(f"\n✅ Verification - Updated teacher data:")
                print(f"  - teacher_id: {updated_teacher.get('teacher_id')}")
                print(f"  - teacher_name: {updated_teacher.get('teacher_name')}")
                print(f"  - availability_days: {updated_teacher.get('availability_days')}")
                
                if updated_teacher.get('availability_days') == limited_availability:
                    print("✅ Frontend integration test PASSED - availability_days field is working!")
                else:
                    print("❌ Frontend integration test FAILED - availability_days not updated correctly")
            else:
                print("❌ Could not find updated teacher")
        else:
            print("❌ No teachers found in database")
            
    except Exception as e:
        print(f"❌ Error in frontend integration test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_frontend_availability()
