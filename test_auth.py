#!/usr/bin/env python3
"""
Test script for the IntelliSched authentication system
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
PROTECTED_URL = f"{BASE_URL}/"

def test_authentication():
    print("🧪 Testing IntelliSched Authentication System")
    print("=" * 50)
    
    # Test 0: Health check
    print("\n0️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check successful: {health_data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 1: Access protected route without authentication
    print("\n1️⃣ Testing access to protected route without authentication...")
    try:
        response = requests.get(PROTECTED_URL)
        if response.status_code == 401:
            print("✅ Correctly blocked unauthenticated access (401)")
        elif response.status_code == 403:
            print("⚠️ Got 403 Forbidden (this might be expected)")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Login with valid credentials
    print("\n2️⃣ Testing login with valid credentials...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            username = data.get('username')
            print(f"✅ Login successful for user: {username}")
            print(f"✅ Token received: {token[:20]}...")
            
            # Test 3: Access protected route with valid token
            print("\n3️⃣ Testing access to protected route with valid token...")
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(PROTECTED_URL, headers=headers)
            
            if response.status_code == 200:
                print("✅ Successfully accessed protected route with token")
            else:
                print(f"❌ Failed to access protected route: {response.status_code}")
                print(f"Response: {response.text}")
                
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during login: {e}")
    
    # Test 4: Login with invalid credentials
    print("\n4️⃣ Testing login with invalid credentials...")
    invalid_login = {
        "username": "admin",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=invalid_login)
        if response.status_code == 401:
            print("✅ Correctly rejected invalid credentials")
        else:
            print(f"❌ Unexpected response for invalid credentials: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Authentication tests completed!")

if __name__ == "__main__":
    test_authentication()
