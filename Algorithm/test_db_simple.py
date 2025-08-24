#!/usr/bin/env python3
"""
Simple database test script for IntelliSched
"""

def test_database_import():
    """Test if we can import the database module"""
    try:
        from database import db
        print("✅ Database module imported successfully")
        return db
    except ImportError as e:
        print(f"❌ Failed to import database module: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error importing database: {e}")
        return None

def test_database_connection(db_instance):
    """Test database connection"""
    if not db_instance:
        return False
    
    try:
        # Test basic connection
        result = db_instance.db.execute_query("SELECT 1 as test")
        if result and len(result) > 0:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database query returned no results")
            return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_users_table(db_instance):
    """Test users table structure"""
    if not db_instance:
        return False
    
    try:
        # Check if users table exists
        result = db_instance.db.execute_query("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        if result and len(result) > 0 and result[0].get('exists'):
            print("✅ Users table exists")
            
            # Check table structure
            columns = db_instance.db.execute_query("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            
            print(f"📋 Users table has {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"  - {col['column_name']}: {col['data_type']} ({nullable})")
            
            # Check for required columns
            required_columns = {'id', 'username', 'password_hash', 'salt', 'full_name', 'email', 'role', 'created_at', 'last_login'}
            existing_columns = {col['column_name'] for col in columns}
            missing_columns = required_columns - existing_columns
            
            if missing_columns:
                print(f"⚠️ Missing columns: {', '.join(missing_columns)}")
                return False
            else:
                print("✅ All required columns are present")
                return True
        else:
            print("❌ Users table does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Error checking users table: {e}")
        return False

def test_admin_user(db_instance):
    """Test if admin user exists"""
    if not db_instance:
        return False
    
    try:
        # Check if admin user exists
        result = db_instance.db.execute_query("SELECT username, role FROM users WHERE username = 'admin'")
        
        if result and len(result) > 0:
            admin_user = result[0]
            print(f"✅ Admin user exists: {admin_user['username']} (Role: {admin_user['role']})")
            return True
        else:
            print("⚠️ Admin user not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking admin user: {e}")
        return False

def test_credential_verification(db_instance):
    """Test credential verification"""
    if not db_instance:
        return False
    
    try:
        # Test with correct credentials
        user = db_instance.verify_user_credentials("admin", "admin123")
        if user:
            print("✅ Credential verification successful for admin/admin123")
            return True
        else:
            print("❌ Credential verification failed for admin/admin123")
            return False
            
    except Exception as e:
        print(f"❌ Error during credential verification: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 IntelliSched Database Test")
    print("=" * 40)
    
    # Test 1: Import database module
    db_instance = test_database_import()
    if not db_instance:
        print("\n❌ Cannot proceed without database module")
        return
    
    # Test 2: Database connection
    if not test_database_connection(db_instance):
        print("\n❌ Cannot proceed without database connection")
        return
    
    # Test 3: Users table structure
    if not test_users_table(db_instance):
        print("\n⚠️ Users table has issues - run fix_users_table.py")
        return
    
    # Test 4: Admin user
    if not test_admin_user(db_instance):
        print("\n⚠️ Admin user missing - run fix_users_table.py")
        return
    
    # Test 5: Credential verification
    if not test_credential_verification(db_instance):
        print("\n❌ Credential verification failed")
        return
    
    print("\n🎉 All database tests passed!")
    print("Your authentication system should work now.")

if __name__ == "__main__":
    main()
