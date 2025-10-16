#!/usr/bin/env python3
"""
Update User Passwords Script for IntelliSched
This script updates existing user passwords to use environment variables
"""

import os
import sys
import hashlib
import secrets
from database import db

def update_user_password(username, new_password):
    """Update a user's password"""
    try:
        # Generate new salt and hash
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((new_password + salt).encode()).hexdigest()
        
        # Update in database
        db.db.execute_single("""
            UPDATE users 
            SET password_hash = %s, salt = %s 
            WHERE username = %s
        """, (password_hash, salt, username))
        
        return True
    except Exception as e:
        print(f"[ERROR] Error updating {username}: {e}")
        return False

def update_all_passwords():
    """Update all default user passwords"""
    
    print("Updating IntelliSched User Passwords")
    print("=" * 40)
    
    # Get passwords from environment variables
    passwords = {
        'admin': os.getenv('ADMIN_PASSWORD', 'AdminSecure123!'),
        'chair': os.getenv('CHAIR_PASSWORD', 'ChairSecure123!'),
        'dean': os.getenv('DEAN_PASSWORD', 'DeanSecure123!'),
        'sec': os.getenv('SECRETARY_PASSWORD', 'SecretarySecure123!')
    }
    
    success_count = 0
    
    for username, password in passwords.items():
        if update_user_password(username, password):
            print(f"[OK] Updated password for: {username}")
            success_count += 1
        else:
            print(f"[ERROR] Failed to update: {username}")
    
    print(f"\n[SUCCESS] Updated {success_count}/4 user passwords!")
    
    if success_count == 4:
        print("\nYou can now login with the new passwords:")
        print("   Admin: admin / [new password]")
        print("   Chair: chair / [new password]")
        print("   Dean: dean / [new password]")
        print("   Secretary: sec / [new password]")
    
    return success_count == 4

if __name__ == "__main__":
    print("[WARN] This will update existing user passwords!")
    print("Make sure you have set your environment variables first.")
    
    confirm = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        update_all_passwords()
    else:
        print("[CANCELLED] Operation cancelled.")
        sys.exit(1)
