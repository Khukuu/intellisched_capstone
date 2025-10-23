#!/usr/bin/env python3
"""
Debug database issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_database():
    """Debug database issues"""
    print("Debugging database...")
    
    try:
        from database import db
        print("✅ Database module imported")
        
        # Check if users table exists
        print("\nChecking users table...")
        result = db.db.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'users'
        """)
        print(f"Users table exists: {len(result) > 0}")
        
        if len(result) > 0:
            # Check users table structure
            print("\nChecking users table structure...")
            columns = db.db.execute_query("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
            print("Users table columns:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")
            
            # Check if there are any users
            print("\nChecking existing users...")
            users = db.db.execute_query("SELECT username, role FROM users")
            print(f"Found {len(users)} users:")
            for user in users:
                print(f"  - {user['username']} ({user['role']})")
        
        # Check if new tables exist
        print("\nChecking new tables...")
        tables_to_check = ['schedule_approvals', 'notifications']
        for table in tables_to_check:
            result = db.db.execute_query(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = '{table}'
            """)
            print(f"{table} table exists: {len(result) > 0}")
        
        # Test creating a user manually
        print("\nTesting manual user creation...")
        try:
            import hashlib
            import secrets
            
            password = "test123"
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            db.db.execute_single("""
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ('debug_test_user', password_hash, salt, 'Debug Test', 'debug@test.com', 'user'))
            
            print("✅ Manual user creation successful")
            
            # Clean up
            db.db.execute_single("DELETE FROM users WHERE username = %s", ('debug_test_user',))
            print("✅ Test user cleaned up")
            
        except Exception as e:
            print(f"❌ Manual user creation failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database()
