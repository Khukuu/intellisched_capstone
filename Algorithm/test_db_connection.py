#!/usr/bin/env python3
"""
Simple script to test database connection and check table structure
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection - update these values to match your setup
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'intellisched',
    'user': 'postgres',
    'password': 'asdf1234'
}

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connection successful!")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if database exists and has tables
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()['current_database']
            print(f"📊 Connected to database: {db_name}")
            
            # List all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            print(f"\n📋 Tables in database:")
            if tables:
                for table in tables:
                    print(f"  - {table['table_name']}")
            else:
                print("  No tables found")
            
            # Check users table specifically
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """)
            users_table_exists = cursor.fetchone()['exists']
            
            if users_table_exists:
                print("\n🔍 Users table exists. Checking structure...")
                
                # Get users table columns
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                print("  Columns in users table:")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"    - {col['column_name']}: {col['data_type']} ({nullable})")
                
                # Check for required columns
                required_columns = {'id', 'username', 'password_hash', 'salt', 'full_name', 'email', 'role', 'created_at', 'last_login'}
                existing_columns = {col['column_name'] for col in columns}
                missing_columns = required_columns - existing_columns
                
                if missing_columns:
                    print(f"\n⚠️ Missing columns: {', '.join(missing_columns)}")
                    print("   Run fix_users_table.py to fix this issue.")
                else:
                    print("\n✅ Users table has all required columns!")
                    
                    # Check if admin user exists
                    cursor.execute("SELECT username, role FROM users WHERE username = 'admin'")
                    admin_user = cursor.fetchone()
                    
                    if admin_user:
                        print(f"✅ Admin user exists: {admin_user['username']} (Role: {admin_user['role']})")
                    else:
                        print("⚠️ Admin user not found")
            else:
                print("\n❌ Users table does not exist")
                print("   This will be created when you run the application.")
            
        conn.close()
        print("\n✅ Database test completed successfully!")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your database credentials in DB_CONFIG")
        print("3. Ensure the 'intellisched' database exists")
        print("4. Verify PostgreSQL is listening on localhost:5432")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🔍 Testing IntelliSched Database Connection")
    print("=" * 50)
    test_connection()
