#!/usr/bin/env python3
"""
Simple Environment Variables Checker
"""

import os

# Load environment variables (same as your app does)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] .env file loaded successfully!")
except ImportError:
    print("[WARN] python-dotenv not installed")
except Exception as e:
    print(f"[ERROR] Error loading .env file: {e}")

print("\nEnvironment Variables Status:")
print("=" * 40)

# Check key variables
variables = {
    'SECRET_KEY': 'JWT Secret Key',
    'DATABASE_URL': 'Database Connection',
    'HOST': 'Server Host',
    'PORT': 'Server Port',
    'RELOAD': 'Development Mode',
    'ADMIN_PASSWORD': 'Admin Password',
    'CHAIR_PASSWORD': 'Chair Password',
    'DEAN_PASSWORD': 'Dean Password',
    'SECRETARY_PASSWORD': 'Secretary Password'
}

for var, description in variables.items():
    value = os.getenv(var)
    if value:
        # Hide sensitive values
        if 'PASSWORD' in var or 'SECRET' in var or 'URL' in var:
            display_value = f"{value[:10]}..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"[OK] {var}: {display_value}")
    else:
        print(f"[MISSING] {var}: NOT SET")

print("\nSummary:")
loaded_count = sum(1 for var in variables if os.getenv(var))
total_count = len(variables)
print(f"Loaded: {loaded_count}/{total_count} variables")

if loaded_count == total_count:
    print("[SUCCESS] All environment variables are loaded! Your app is ready.")
else:
    print("[WARN] Some environment variables are missing. Check your .env file.")
