#!/usr/bin/env python3
"""
Simple test to check basic functionality
"""

def test_basic_imports():
    print("🧪 Testing Basic Imports")
    print("=" * 30)
    
    try:
        print("1. Testing database imports...")
        from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db
        print("   ✅ Database imports successful")
        
        print("2. Testing OR-Tools import...")
        from ortools.sat.python import cp_model
        print("   ✅ OR-Tools import successful")
        
        print("3. Testing data loading...")
        subjects = load_courses_from_db()
        teachers = load_teachers_from_db()
        rooms = load_rooms_from_db()
        print(f"   ✅ Data loaded: {len(subjects)} subjects, {len(teachers)} teachers, {len(rooms)} rooms")
        
        print("4. Testing scheduler import...")
        from scheduler import generate_schedule
        print("   ✅ Scheduler import successful")
        
        print("\n✅ All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_imports()
