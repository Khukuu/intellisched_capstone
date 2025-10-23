#!/usr/bin/env python3
"""
Simple test to check database connection and user creation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and user creation"""
    print("Testing database connection...")
    
    try:
        from database import db
        print("✅ Database module imported successfully")
        
        # Test basic connection
        test_query = db.db.execute_query("SELECT 1 as test")
        if test_query and len(test_query) > 0:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
            
        # Test user creation
        print("\nTesting user creation...")
        from database import create_user
        
        # Test creating a temporary user
        test_user_data = {
            'username': 'test_user_123',
            'password': 'test123',
            'full_name': 'Test User',
            'email': 'test@example.com',
            'role': 'user'
        }
        
        success = create_user(test_user_data)
        if success:
            print("✅ User creation successful")
            
            # Clean up test user
            db.db.execute_single("DELETE FROM users WHERE username = %s", ('test_user_123',))
            print("✅ Test user cleaned up")
        else:
            print("❌ User creation failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_database_connection():
        print("\nDatabase connection test passed!")
    else:
        print("\nDatabase connection test failed!")