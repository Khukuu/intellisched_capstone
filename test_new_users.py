#!/usr/bin/env python3
"""
Test script to verify that the new dean and secretary users are created properly.
Run this script to test the user creation and authentication.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db, verify_user_credentials

def test_user_creation():
    """Test that all users are created properly"""
    print("🧪 Testing user creation and authentication...")
    
    # Test users to verify
    test_users = [
        {'username': 'admin', 'password': 'admin123', 'role': 'admin'},
        {'username': 'chair', 'password': 'chair123', 'role': 'chair'},
        {'username': 'dean', 'password': 'dean123', 'role': 'dean'},
        {'username': 'sec', 'password': 'sec123', 'role': 'secretary'},
    ]
    
    print("\n📋 Testing user authentication:")
    print("-" * 50)
    
    for user in test_users:
        print(f"\n🔐 Testing {user['username']} ({user['role']})...")
        
        # Test authentication
        auth_result = verify_user_credentials(user['username'], user['password'])
        
        if auth_result:
            print(f"  ✅ Authentication successful")
            print(f"  📝 Role: {auth_result.get('role', 'Unknown')}")
            print(f"  👤 Full Name: {auth_result.get('full_name', 'N/A')}")
            print(f"  📧 Email: {auth_result.get('email', 'N/A')}")
            
            # Verify role matches expected
            if auth_result.get('role') == user['role']:
                print(f"  ✅ Role verification passed")
            else:
                print(f"  ❌ Role verification failed (expected: {user['role']}, got: {auth_result.get('role')})")
        else:
            print(f"  ❌ Authentication failed")
    
    print("\n" + "=" * 50)
    print("🎉 User creation and authentication test completed!")
    print("\n📝 Available user roles:")
    print("  • admin - System administrator")
    print("  • chair - Department chair (can generate and save schedules)")
    print("  • dean - Dean (can view and approve schedules)")
    print("  • secretary - Secretary (can view, edit, and delete approved schedules)")

if __name__ == "__main__":
    try:
        test_user_creation()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
