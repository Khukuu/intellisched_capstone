#!/usr/bin/env python3
"""
Reset Users Script for IntelliSched
This script deletes existing users and recreates them with new passwords
"""

import os
import sys
from database import db

def reset_users():
    """Delete existing users and recreate them with new passwords"""
    
    print("🔄 Resetting IntelliSched Users")
    print("=" * 40)
    
    # Users to reset
    users_to_reset = ['admin', 'chair', 'dean', 'sec']
    
    try:
        # Delete existing users
        for username in users_to_reset:
            try:
                db.db.execute_single("DELETE FROM users WHERE username = %s", (username,))
                print(f"✅ Deleted existing user: {username}")
            except Exception as e:
                print(f"⚠️ Could not delete {username}: {e}")
        
        # Recreate users with new passwords
        print("\n🔄 Creating users with new passwords...")
        db.create_default_admin()
        
        print("\n🎉 Users reset successfully!")
        print("\n📝 New login credentials:")
        print("   Admin: admin / [password from environment variable]")
        print("   Chair: chair / [password from environment variable]")
        print("   Dean: dean / [password from environment variable]")
        print("   Secretary: sec / [password from environment variable]")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting users: {e}")
        return False

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete all existing admin users!")
    print("Make sure you have set your environment variables first.")
    
    confirm = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        reset_users()
    else:
        print("❌ Operation cancelled.")
        sys.exit(1)
