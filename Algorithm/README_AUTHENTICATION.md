# 🔐 IntelliSched Authentication System

This document explains the new authentication system added to IntelliSched.

## 🚀 Features

- **Secure Login**: Username/password authentication
- **JWT Tokens**: Secure, time-limited access tokens
- **Protected Routes**: All main functionality requires authentication
- **User Management**: Database-backed user accounts
- **Session Management**: Automatic token expiration and renewal

## 🏗️ Architecture

### Frontend
- **Login Page**: `/login` - Beautiful, responsive login interface
- **Main App**: `/` - Protected main application
- **Authentication Check**: Automatic redirect to login if not authenticated

### Backend
- **Authentication Endpoints**: `/auth/login`, `/auth/me`, `/auth/logout`
- **Protected Routes**: All main endpoints require valid JWT token
- **Database**: User accounts stored in PostgreSQL with salted password hashes

## 🔧 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Setup
The system automatically creates the `users` table and a default admin account:
- **Username**: `admin`
- **Password**: `admin123`

### 3. Start the Application
```bash
uvicorn app:app --reload
```

## 📱 Usage

### Login Flow
1. Navigate to `/login`
2. Enter credentials (admin/admin123 by default)
3. Upon successful login, you'll be redirected to the main app
4. All API calls automatically include the authentication token

### Logout
- Click the logout button in the top-right corner
- This clears the local token and redirects to login

## 🛡️ Security Features

- **Password Hashing**: SHA-256 with random salt
- **JWT Tokens**: 30-minute expiration
- **Protected Endpoints**: All sensitive operations require authentication
- **Automatic Redirects**: Unauthenticated users are sent to login

## 🔍 API Endpoints

### Public Endpoints
- `GET /login` - Login page
- `POST /auth/login` - Authenticate user
- `POST /auth/logout` - Logout (client-side token removal)

### Protected Endpoints
- `GET /` - Main application
- `POST /schedule` - Generate schedule
- `GET /data/*` - Data management
- `POST /save_schedule` - Save schedules
- `GET /load_schedule` - Load saved schedules
- And more...

## 🧪 Testing

Run the authentication test script:
```bash
python test_auth.py
```

This will test:
- Unauthenticated access blocking
- Valid login
- Protected route access with token
- Invalid credential rejection

## 🔧 Configuration

### JWT Settings (in `app.py`)
```python
SECRET_KEY = "your-secret-key-change-in-production"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### Database Connection (in `database.py`)
```python
connection_string = "postgresql://postgres:asdf1234@localhost:5432/intellisched"
```

## 🚨 Security Notes

1. **Change the SECRET_KEY** in production
2. **Use HTTPS** in production environments
3. **Regular password updates** for admin accounts
4. **Monitor failed login attempts**
5. **Consider rate limiting** for login endpoints

## 🔄 Adding New Users

### Via Database
```sql
INSERT INTO users (username, password_hash, salt, full_name, email, role)
VALUES ('newuser', 'hashed_password', 'random_salt', 'Full Name', 'email@example.com', 'user');
```

### Via Python
```python
from database import db
db.create_user({
    'username': 'newuser',
    'password': 'password123',
    'full_name': 'Full Name',
    'email': 'email@example.com',
    'role': 'user'
})
```

## 🐛 Troubleshooting

### Common Issues

1. **"Could not validate credentials"**
   - Check if JWT token is expired
   - Verify token is being sent in Authorization header

2. **"Token has expired"**
   - User needs to log in again
   - Consider implementing token refresh

3. **Database connection errors**
   - Verify PostgreSQL is running
   - Check connection string in database.py

4. **Login page not loading**
   - Ensure `/login` route is accessible
   - Check static file serving

## 🔮 Future Enhancements

- [ ] Password reset functionality
- [ ] User registration
- [ ] Role-based access control
- [ ] Two-factor authentication
- [ ] Session management dashboard
- [ ] Audit logging

## 📞 Support

For issues or questions about the authentication system, check:
1. Application logs for error messages
2. Database connectivity
3. JWT token validity
4. Browser console for frontend errors
