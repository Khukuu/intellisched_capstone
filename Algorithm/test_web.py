#!/usr/bin/env python3
"""
Test script to check web endpoints
"""

import requests
import json

def test_web_endpoints():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Web Endpoints")
    print("=" * 50)
    
    try:
        # Test subjects endpoint
        print("📚 Testing /data/cs_curriculum endpoint...")
        response = requests.get(f"{base_url}/data/cs_curriculum")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} subjects")
            if data:
                print(f"   Sample: {data[0]}")
        else:
            print(f"   ❌ Error: {response.text}")
            
        # Test teachers endpoint
        print("\n👨‍🏫 Testing /data/teachers endpoint...")
        response = requests.get(f"{base_url}/data/teachers")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} teachers")
            if data:
                print(f"   Sample: {data[0]}")
        else:
            print(f"   ❌ Error: {response.text}")
            
        # Test rooms endpoint
        print("\n🏫 Testing /data/rooms endpoint...")
        response = requests.get(f"{base_url}/data/rooms")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Found {len(data)} rooms")
            if data:
                print(f"   Sample: {data[0]}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure the app is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_web_endpoints()
