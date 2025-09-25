#!/usr/bin/env python3
"""
Simple test for web application
"""

import urllib.request
import json

def test_endpoint():
    try:
        print("🧪 Testing web endpoint...")
        url = "http://localhost:5000/data/cs_curriculum"
        
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(f"✅ Success! Found {len(data)} subjects")
            if data:
                print(f"Sample: {data[0]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the app is running with: python app.py")

if __name__ == "__main__":
    test_endpoint()
