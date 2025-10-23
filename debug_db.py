#!/usr/bin/env python3
"""
Debug script to see what's actually in the database tables
"""

import psycopg2
from psycopg2.extras import RealDictCursor

def debug_database():
    print("Debugging Database Contents")
    print("=" * 50)
    
    connection_string = "postgresql://postgres:asdf1234@localhost:5432/intellisched"
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # List all tables
        print("1. Available tables:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Check subjects table
        print("\n2. Subjects table:")
        cursor.execute("SELECT COUNT(*) as count FROM subjects")
        subject_count = cursor.fetchone()['count']
        print(f"   Total rows: {subject_count}")
        
        if subject_count > 0:
            cursor.execute("SELECT * FROM subjects LIMIT 3")
            subjects = cursor.fetchall()
            for subject in subjects:
                print(f"   Sample: {dict(subject)}")
        
        # Check teachers table
        print("\n3. Teachers table:")
        cursor.execute("SELECT COUNT(*) as count FROM teachers")
        teacher_count = cursor.fetchone()['count']
        print(f"   Total rows: {teacher_count}")
        
        if teacher_count > 0:
            cursor.execute("SELECT * FROM teachers LIMIT 3")
            teachers = cursor.fetchall()
            for teacher in teachers:
                print(f"   Sample: {dict(teacher)}")
        
        # Check rooms table
        print("\n4. Rooms table:")
        cursor.execute("SELECT COUNT(*) as count FROM rooms")
        room_count = cursor.fetchone()['count']
        print(f"   Total rows: {room_count}")
        
        if room_count > 0:
            cursor.execute("SELECT * FROM rooms LIMIT 3")
            rooms = cursor.fetchall()
            for room in rooms:
                print(f"   Sample: {dict(room)}")
        
        # Check table structure
        print("\n5. Table structure:")
        for table_name in ['subjects', 'teachers', 'rooms']:
            print(f"\n   {table_name.upper()} table columns:")
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            for col in columns:
                print(f"      - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_database()

