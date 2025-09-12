#!/usr/bin/env python3
"""
Test script for role-based access control in IntelliSched
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login(username, password):
    """Test login and return token and role"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token'), data.get('role')
    else:
        print(f"❌ Login failed for {username}: {response.text}")
        return None, None

def test_protected_endpoint(token, endpoint, method="GET", data=None):
    """Test access to a protected endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    if method == "GET":
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=data)
    
    return response.status_code, response.text

def main():
    print("🧪 Testing IntelliSched Role-Based Access Control")
    print("=" * 50)
    
    # Test admin login
    print("\n1. Testing Admin Login...")
    admin_token, admin_role = test_login("admin", "admin123")
    if admin_token:
        print(f"✅ Admin login successful - Role: {admin_role}")
    else:
        print("❌ Admin login failed")
        return
    
    # Test chair login
    print("\n2. Testing Chair Login...")
    chair_token, chair_role = test_login("chair", "chair123")
    if chair_token:
        print(f"✅ Chair login successful - Role: {chair_role}")
    else:
        print("❌ Chair login failed")
        return
    
    # Test admin access to admin dashboard
    print("\n3. Testing Admin Access to Admin Dashboard...")
    status, response = test_protected_endpoint(admin_token, "/admin")
    if status == 200:
        print("✅ Admin can access admin dashboard")
    else:
        print(f"❌ Admin cannot access admin dashboard: {status}")
    
    # Test chair access to admin dashboard (should fail)
    print("\n4. Testing Chair Access to Admin Dashboard (should fail)...")
    status, response = test_protected_endpoint(chair_token, "/admin")
    if status == 403:
        print("✅ Chair correctly denied access to admin dashboard")
    else:
        print(f"❌ Chair should not access admin dashboard: {status}")
    
    # Test chair access to chair dashboard
    print("\n5. Testing Chair Access to Chair Dashboard...")
    status, response = test_protected_endpoint(chair_token, "/chair")
    if status == 200:
        print("✅ Chair can access chair dashboard")
    else:
        print(f"❌ Chair cannot access chair dashboard: {status}")
    
    # Test admin access to chair dashboard (should fail)
    print("\n6. Testing Admin Access to Chair Dashboard (should fail)...")
    status, response = test_protected_endpoint(admin_token, "/chair")
    if status == 403:
        print("✅ Admin correctly denied access to chair dashboard")
    else:
        print(f"❌ Admin should not access chair dashboard: {status}")
    
    # Test chair access to scheduling endpoints
    print("\n7. Testing Chair Access to Scheduling Endpoints...")
    status, response = test_protected_endpoint(chair_token, "/saved_schedules")
    if status == 200:
        print("✅ Chair can access saved schedules")
    else:
        print(f"❌ Chair cannot access saved schedules: {status}")
    
    # Test admin access to scheduling endpoints (should fail)
    print("\n8. Testing Admin Access to Scheduling Endpoints (should fail)...")
    status, response = test_protected_endpoint(admin_token, "/saved_schedules")
    if status == 403:
        print("✅ Admin correctly denied access to scheduling endpoints")
    else:
        print(f"❌ Admin should not access scheduling endpoints: {status}")
    
    print("\n" + "=" * 50)
    print("🎉 Role-based access control test completed!")

if __name__ == "__main__":
    main()

