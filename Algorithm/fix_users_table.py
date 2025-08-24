#!/usr/bin/env python3
"""
Script to fix the users table structure in the IntelliSched database.
This script will ensure the users table has all required columns for authentication.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import secrets

# Database connection - update these values to match your setup
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'intellisched',
    'user': 'postgres',
    'password': 'asdf1234'
}

def get_connection():
    """Get a database connection"""
    return psycopg2.connect(**DB_CONFIG)

def check_table_structure():
    """Check the current structure of the users table"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check if users table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    );
                """)
                table_exists = cursor.fetchone()['exists']
                
                if not table_exists:
                    print("❌ Users table does not exist")
                    return False
                
                # Get table columns
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                print("📋 Current users table structure:")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"  - {col['column_name']}: {col['data_type']} ({nullable})")
                
                # Check for required columns
                required_columns = {
                    'id': 'SERIAL PRIMARY KEY',
                    'username': 'VARCHAR(50) UNIQUE NOT NULL',
                    'password_hash': 'VARCHAR(255) NOT NULL',
                    'salt': 'VARCHAR(255) NOT NULL',
                    'full_name': 'VARCHAR(255)',
                    'email': 'VARCHAR(255)',
                    'role': 'VARCHAR(20) DEFAULT user',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'last_login': 'TIMESTAMP'
                }
                
                existing_columns = {col['column_name'] for col in columns}
                missing_columns = set(required_columns.keys()) - existing_columns
                
                if missing_columns:
                    print(f"\n⚠️ Missing columns: {', '.join(missing_columns)}")
                    return False
                else:
                    print("\n✅ All required columns are present")
                    return True
                    
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False

def fix_users_table():
    """Fix the users table structure"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                print("\n🔧 Fixing users table structure...")
                
                # Drop existing users table if it exists
                cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
                print("✅ Dropped existing users table")
                
                # Create new users table with correct structure
                create_table_sql = """
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    email VARCHAR(255),
                    role VARCHAR(20) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                """
                
                cursor.execute(create_table_sql)
                print("✅ Created new users table with correct structure")
                
                # Create default admin user
                password = "admin123"
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                
                insert_admin_sql = """
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_admin_sql, (
                    'admin', 
                    password_hash, 
                    salt, 
                    'Administrator', 
                    'admin@intellisched.com', 
                    'admin'
                ))
                
                print("✅ Created default admin user (username: admin, password: admin123)")
                
                # Commit the changes
                conn.commit()
                print("✅ All changes committed successfully")
                
                return True
                
    except Exception as e:
        print(f"❌ Error fixing table structure: {e}")
        return False

def verify_fix():
    """Verify that the fix worked"""
    print("\n🔍 Verifying the fix...")
    
    if check_table_structure():
        print("✅ Table structure is now correct!")
        
        # Test admin user creation
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT username, full_name, role FROM users WHERE username = 'admin'")
                    admin_user = cursor.fetchone()
                    
                    if admin_user:
                        print(f"✅ Admin user verified: {admin_user['username']} ({admin_user['full_name']}) - Role: {admin_user['role']}")
                        return True
                    else:
                        print("❌ Admin user not found")
                        return False
        except Exception as e:
            print(f"❌ Error verifying admin user: {e}")
            return False
    else:
        print("❌ Table structure is still incorrect")
        return False

def main():
    """Main function to fix the users table"""
    print("🔐 IntelliSched Users Table Fix Script")
    print("=" * 50)
    
    # Check current structure
    if check_table_structure():
        print("\n✅ Users table structure is already correct!")
        return
    
    # Fix the table
    if fix_users_table():
        # Verify the fix
        if verify_fix():
            print("\n🎉 Users table has been successfully fixed!")
            print("You can now run your IntelliSched application.")
        else:
            print("\n❌ Fix verification failed")
    else:
        print("\n❌ Failed to fix users table")

if __name__ == "__main__":
    main()
