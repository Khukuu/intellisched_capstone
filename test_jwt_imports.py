#!/usr/bin/env python3
"""
Test script to identify JWT library conflicts
"""

def test_jwt_imports():
    """Test different JWT import methods"""
    print("Testing JWT Library Imports")
    print("=" * 40)
    
    # Test 1: Standard import
    try:
        import jwt
        print(f"✅ Standard import: {type(jwt)}")
        print(f"   Attributes: {[attr for attr in dir(jwt) if not attr.startswith('_')][:10]}")
        if hasattr(jwt, 'encode'):
            print("   ✅ Has 'encode' method")
        else:
            print("   ❌ Missing 'encode' method")
    except ImportError as e:
        print(f"❌ Standard import failed: {e}")
    
    # Test 2: PyJWT import
    try:
        import PyJWT
        print(f"✅ PyJWT import: {type(PyJWT)}")
        print(f"   Attributes: {[attr for attr in dir(PyJWT) if not attr.startswith('_')][:10]}")
        if hasattr(PyJWT, 'encode'):
            print("   ✅ Has 'encode' method")
        else:
            print("   ❌ Missing 'encode' method")
    except ImportError as e:
        print(f"❌ PyJWT import failed: {e}")
    
    # Test 3: Try to find any JWT-related modules
    import sys
    jwt_modules = [name for name in sys.modules.keys() if 'jwt' in name.lower()]
    if jwt_modules:
        print(f"\n📋 Found JWT-related modules: {jwt_modules}")
    
    # Test 4: Check if we can create a token
    print("\n🔐 Testing JWT Token Creation")
    print("-" * 30)
    
    try:
        import PyJWT as jwt
        test_data = {"sub": "testuser", "exp": 1234567890}
        token = jwt.encode(test_data, "test_secret", algorithm="HS256")
        print(f"✅ Token creation successful: {token[:20]}...")
        
        # Test decode
        decoded = jwt.decode(token, "test_secret", algorithms=["HS256"])
        print(f"✅ Token decode successful: {decoded}")
        
    except Exception as e:
        print(f"❌ Token creation failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jwt_imports()


