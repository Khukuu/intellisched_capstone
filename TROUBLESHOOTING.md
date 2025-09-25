# 🔧 IntelliSched Troubleshooting Guide

This guide helps you resolve common issues with the IntelliSched authentication system.

## 🚨 Common Issues & Solutions

### 1. Database Connection Issues

#### Error: `column "salt" of relation "users" does not exist`

**Problem**: The users table was created without the required `salt` column for password hashing.

**Solution**: Run the fix script:
```bash
python fix_users_table.py
```

**Alternative**: The application will now automatically detect and fix this issue on startup.

#### Error: `connection to server at "localhost" (127.0.0.1), port 5432 failed`

**Problem**: PostgreSQL is not running or not accessible.

**Solutions**:
1. **Start PostgreSQL service**:
   - Windows: Open Services app → PostgreSQL → Start
   - macOS: `brew services start postgresql`
   - Linux: `sudo systemctl start postgresql`

2. **Check if PostgreSQL is running**:
   ```bash
   # Windows
   netstat -an | findstr 5432
   
   # macOS/Linux
   netstat -an | grep 5432
   ```

3. **Verify database exists**:
   ```sql
   -- Connect to PostgreSQL as postgres user
   psql -U postgres
   
   -- List databases
   \l
   
   -- Create database if it doesn't exist
   CREATE DATABASE intellisched;
   ```

### 2. Authentication Issues

#### Error: `Could not validate credentials`

**Problem**: JWT token is invalid, expired, or missing.

**Solutions**:
1. **Clear browser storage** and log in again
2. **Check token expiration** (default: 30 minutes)
3. **Verify token format** in browser console:
   ```javascript
   console.log(localStorage.getItem('authToken'));
   ```

#### Error: `Token has expired`

**Problem**: JWT token has passed its expiration time.

**Solution**: Log in again to get a new token.

#### Login page not loading

**Problem**: Route not accessible or static files not served.

**Solutions**:
1. **Check if app is running**: `http://localhost:8000/login`
2. **Verify static file serving** in `app.py`
3. **Check file permissions** for `static/login.html`

### 3. Database Table Issues

#### Users table missing or corrupted

**Problem**: Table structure is incorrect or missing.

**Solutions**:
1. **Run the fix script**:
   ```bash
   python fix_users_table.py
   ```

2. **Check table structure manually**:
   ```bash
   python test_db_connection.py
   ```

3. **Recreate table manually**:
   ```sql
   DROP TABLE IF EXISTS users CASCADE;
   
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
   ```

### 4. Application Startup Issues

#### Error: `ModuleNotFoundError: No module named 'jwt'`

**Problem**: PyJWT dependency not installed.

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

#### Error: `ImportError: No module named 'psycopg2'`

**Problem**: PostgreSQL adapter not installed.

**Solution**: Install psycopg2:
```bash
pip install psycopg2-binary
```

## 🔍 Diagnostic Steps

### Step 1: Test Database Connection
```bash
python test_db_connection.py
```

**Expected Output**:
```
✅ Database connection successful!
📊 Connected to database: intellisched
📋 Tables in database:
  - rooms
  - teachers
  - users
🔍 Users table exists. Checking structure...
  Columns in users table:
    - id: integer (NOT NULL)
    - username: character varying (NOT NULL)
    - password_hash: character varying (NOT NULL)
    - salt: character varying (NOT NULL)
    - full_name: character varying (NULL)
    - email: character varying (NULL)
    - role: character varying (NULL)
    - created_at: timestamp without time zone (NULL)
    - last_login: timestamp without time zone (NULL)
✅ Users table has all required columns!
✅ Admin user exists: admin (Role: admin)
```

### Step 2: Test Authentication System
```bash
python test_auth.py
```

**Expected Output**:
```
🧪 Testing IntelliSched Authentication System
==================================================

1️⃣ Testing access to protected route without authentication...
✅ Correctly blocked unauthenticated access

2️⃣ Testing login with valid credentials...
✅ Login successful for user: admin
✅ Token received: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

3️⃣ Testing access to protected route with valid token...
✅ Successfully accessed protected route with token

4️⃣ Testing login with invalid credentials...
✅ Correctly rejected invalid credentials

==================================================
🏁 Authentication tests completed!
```

### Step 3: Check Application Logs
Start the application and check for errors:
```bash
uvicorn app:app --reload
```

**Look for**:
- Database connection messages
- Table creation messages
- Admin user creation messages
- Any error messages

## 🛠️ Manual Database Fixes

### Fix Users Table Structure
If automatic fixes fail, manually fix the database:

```sql
-- Connect to PostgreSQL
psql -U postgres -d intellisched

-- Drop existing users table
DROP TABLE IF EXISTS users CASCADE;

-- Create new users table
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

-- Create admin user (password: admin123)
INSERT INTO users (username, password_hash, salt, full_name, email, role)
VALUES (
    'admin',
    'hashed_password_here',  -- You'll need to generate this
    'random_salt_here',      -- You'll need to generate this
    'Administrator',
    'admin@intellisched.com',
    'admin'
);
```

### Generate Password Hash Manually
```python
import hashlib
import secrets

password = "admin123"
salt = secrets.token_hex(16)
password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

print(f"Salt: {salt}")
print(f"Hash: {password_hash}")
```

## 📞 Getting Help

If you're still experiencing issues:

1. **Check the logs** for specific error messages
2. **Run diagnostic scripts** to identify the problem
3. **Verify database credentials** and connection settings
4. **Check file permissions** and paths
5. **Ensure all dependencies** are installed correctly

## 🔧 Configuration Checklist

- [ ] PostgreSQL is running and accessible
- [ ] Database 'intellisched' exists
- [ ] User 'postgres' has access to the database
- [ ] All Python dependencies are installed
- [ ] Static files are in the correct location
- [ ] Database connection string is correct in `database.py`
- [ ] JWT secret key is set in `app.py`

## 🚀 Quick Recovery

If everything is broken, here's the quickest way to recover:

1. **Stop the application**
2. **Run the fix script**: `python fix_users_table.py`
3. **Test the database**: `python test_db_connection.py`
4. **Start the application**: `uvicorn app:app --reload`
5. **Test authentication**: `python test_auth.py`
6. **Access the webapp**: `http://localhost:8000/login`

This should get you back to a working state with the default admin account (admin/admin123).
