#!/usr/bin/env python3
"""
Test script for the new user approval workflow
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:5000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def test_user_approval_workflow():
    """Test the complete user approval workflow"""
    
    print("🧪 Testing User Approval Workflow")
    print("=" * 50)
    
    # Step 1: Login as admin
    print("\n1. Logging in as admin...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    })
    
    if login_response.status_code != 200:
        print(f"❌ Admin login failed: {login_response.text}")
        return False
    
    admin_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    print("✅ Admin login successful")
    
    # Step 2: Register a new user (this should create a pending user)
    print("\n2. Registering a new user...")
    new_user_data = {
        "username": "testuser123",
        "full_name": "Test User",
        "email": "testuser@example.com",
        "role": "chair",
        "password": "TestPass123"
    }
    
    register_response = requests.post(f"{BASE_URL}/auth/register", json=new_user_data)
    
    if register_response.status_code != 200:
        print(f"❌ User registration failed: {register_response.text}")
        return False
    
    print("✅ User registration successful (pending approval)")
    
    # Step 3: Try to login as the new user (should fail)
    print("\n3. Attempting to login as pending user...")
    pending_login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": new_user_data["username"],
        "password": new_user_data["password"]
    })
    
    if pending_login_response.status_code == 200:
        print("❌ Pending user login should have failed!")
        return False
    
    print("✅ Pending user login correctly blocked")
    
    # Step 4: Get pending users as admin
    print("\n4. Getting pending users...")
    pending_users_response = requests.get(f"{BASE_URL}/api/pending_users", headers=headers)
    
    if pending_users_response.status_code != 200:
        print(f"❌ Failed to get pending users: {pending_users_response.text}")
        return False
    
    pending_users = pending_users_response.json()
    print(f"✅ Found {len(pending_users)} pending users")
    
    # Find our test user
    test_user = None
    for user in pending_users:
        if user["username"] == new_user_data["username"]:
            test_user = user
            break
    
    if not test_user:
        print("❌ Test user not found in pending users")
        return False
    
    print(f"✅ Test user found: {test_user['full_name']} ({test_user['role']})")
    
    # Step 5: Approve the user
    print("\n5. Approving the user...")
    approve_response = requests.post(
        f"{BASE_URL}/api/approve_user/{test_user['id']}", 
        headers=headers
    )
    
    if approve_response.status_code != 200:
        print(f"❌ User approval failed: {approve_response.text}")
        return False
    
    print("✅ User approved successfully")
    
    # Step 6: Try to login as the approved user (should succeed)
    print("\n6. Attempting to login as approved user...")
    approved_login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": new_user_data["username"],
        "password": new_user_data["password"]
    })
    
    if approved_login_response.status_code != 200:
        print(f"❌ Approved user login failed: {approved_login_response.text}")
        return False
    
    user_data = approved_login_response.json()
    print(f"✅ Approved user login successful: {user_data['username']} ({user_data['role']})")
    
    # Step 7: Verify no pending users remain
    print("\n7. Verifying no pending users remain...")
    final_pending_response = requests.get(f"{BASE_URL}/api/pending_users", headers=headers)
    
    if final_pending_response.status_code != 200:
        print(f"❌ Failed to get final pending users: {final_pending_response.text}")
        return False
    
    final_pending_users = final_pending_response.json()
    remaining_test_users = [u for u in final_pending_users if u["username"] == new_user_data["username"]]
    
    if remaining_test_users:
        print("❌ Test user still appears in pending users")
        return False
    
    print("✅ No pending users remain")
    
    print("\n🎉 All tests passed! User approval workflow is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_user_approval_workflow()
        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
