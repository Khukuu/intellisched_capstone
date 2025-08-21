#!/usr/bin/env python3
"""
Test script to simulate schedule generation request
"""

import urllib.request
import json

def test_schedule_generation():
    try:
        print("🧪 Testing Schedule Generation...")
        url = "http://localhost:5000/schedule"
        
        # Simulate the request payload
        payload = {
            "semester": 1,
            "numSectionsYear1": 1,
            "numSectionsYear2": 1,
            "numSectionsYear3": 1,
            "numSectionsYear4": 0
        }
        
        print(f"Payload: {payload}")
        
        # Convert payload to JSON
        data = json.dumps(payload).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json',
            'Content-Length': len(data)
        })
        
        print("Sending request...")
        
        # Send request
        with urllib.request.urlopen(req) as response:
            print(f"Response status: {response.status}")
            result = json.loads(response.read().decode())
            print(f"✅ Schedule generation successful!")
            print(f"Generated {len(result)} schedule items")
            
            if result:
                print("Sample schedule items:")
                if isinstance(result, list):
                    for item in result[:3]:
                        print(f"  - {item.get('section_id')}: {item.get('subject_code')} ({item.get('type')})")
                else:
                    print(f"  - {result}")
            else:
                print("⚠️ No schedule items generated")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schedule_generation()
