#!/usr/bin/env python3
"""
Environment Variables Setup Script for IntelliSched
This script helps you set up environment variables for deployment
"""

import os
import sys

def set_environment_variables():
    """Set environment variables for IntelliSched deployment"""
    
    print("Setting up IntelliSched Environment Variables")
    print("=" * 50)
    
    # Environment variables to set
    env_vars = {
        'DATABASE_URL': 'postgresql://postgres:asdf1234@localhost:5432/intellisched',
        'SECRET_KEY': 'IntelliSched-Super-Secret-JWT-Key-2024-Production-Ready',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
        'HOST': '0.0.0.0',
        'PORT': '8000',
        'RELOAD': 'false',
        'ADMIN_PASSWORD': 'AdminSecure123!',
        'CHAIR_PASSWORD': 'ChairSecure123!',
        'DEAN_PASSWORD': 'DeanSecure123!',
        'SECRETARY_PASSWORD': 'SecretarySecure123!'
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ Set {key} = {value}")
    
    print("\nEnvironment variables set successfully!")
    print("\nTo make these permanent, add them to your shell profile:")
    print("   - Windows: Add to system environment variables")
    print("   - Linux/Mac: Add to ~/.bashrc or ~/.zshrc")
    
    return True

def show_export_commands():
    """Show export commands for manual setup"""
    
    print("\nManual Setup Commands:")
    print("=" * 30)
    
    commands = [
        'export DATABASE_URL="postgresql://postgres:asdf1234@localhost:5432/intellisched"',
        'export SECRET_KEY="IntelliSched-Super-Secret-JWT-Key-2024-Production-Ready"',
        'export ACCESS_TOKEN_EXPIRE_MINUTES="30"',
        'export HOST="0.0.0.0"',
        'export PORT="8000"',
        'export RELOAD="false"',
        'export ADMIN_PASSWORD="AdminSecure123!"',
        'export CHAIR_PASSWORD="ChairSecure123!"',
        'export DEAN_PASSWORD="DeanSecure123!"',
        'export SECRETARY_PASSWORD="SecretarySecure123!"'
    ]
    
    for cmd in commands:
        print(cmd)
    
    print("\nCopy and paste these commands in your terminal before running the app")

if __name__ == "__main__":
    print("IntelliSched Environment Setup")
    print("Choose an option:")
    print("1. Set environment variables for current session")
    print("2. Show export commands for manual setup")
    print("3. Both")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        set_environment_variables()
    elif choice == "2":
        show_export_commands()
    elif choice == "3":
        set_environment_variables()
        show_export_commands()
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)
