#!/usr/bin/env python3
"""
Local authentication test for IntelliSched
Tests the authentication components without HTTP requests
"""

def test_jwt_token_creation():
    """Test JWT token creation and verification"""
    print("🔐 Testing JWT Token Creation")
    print("-" * 30)
    
    try:
        import jwt
        from datetime import datetime, timedelta
        
        # Test data
        test_data = {"sub": "testuser", "exp": datetime.utcnow() + timedelta(minutes=30)}
        secret_key = "your-secret-key-change-in-production"
        
        # Create token
        token = jwt.encode(test_data, secret_key, algorithm="HS256")
        print(f"✅ Token created: {token[:30]}...")
        
        # Verify token
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        print(f"✅ Token decoded: {decoded}")
        
        return True
        
    except Exception as e:
        print(f"❌ JWT test failed: {e}")
        return False

def test_database_authentication():
    """Test database authentication functions"""
    print("\n🗄️ Testing Database Authentication")
    print("-" * 30)
    
    try:
        from database import db
        
        # Test credential verification
        user = db.verify_user_credentials("admin", "admin123")
        if user:
            print(f"✅ Admin login successful: {user.get('username')}")
            print(f"   Role: {user.get('role')}")
            print(f"   Full name: {user.get('full_name')}")
            return True
        else:
            print("❌ Admin login failed")
            return False
            
    except Exception as e:
        print(f"❌ Database auth test failed: {e}")
        return False

def test_app_import():
    """Test if the FastAPI app can be imported"""
    print("\n🚀 Testing FastAPI App Import")
    print("-" * 30)
    
    try:
        # This will test all imports and dependencies
        from app import app, create_access_token, verify_token
        
        print("✅ FastAPI app imported successfully")
        print("✅ Authentication functions imported successfully")
        
        # Test token creation function
        test_token = create_access_token({"sub": "testuser"})
        print(f"✅ App token creation works: {test_token[:30]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ App import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🧪 IntelliSched Local Authentication Test")
    print("=" * 50)
    
    tests = [
        ("JWT Token Creation", test_jwt_token_creation),
        ("Database Authentication", test_database_authentication),
        ("FastAPI App Import", test_app_import),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your authentication system is ready!")
        print("\n🚀 Next steps:")
        print("   1. Start the web app: python app.py")
        print("   2. Open: http://localhost:5000/login")
        print("   3. Login with: admin / admin123")
    else:
        print(f"\n⚠️ {len(results) - passed} test(s) failed. Check the errors above.")

if __name__ == "__main__":
    main()
