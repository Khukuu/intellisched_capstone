# User Approval Feature Implementation

## Overview
This document describes the implementation of the user approval workflow for IntelliSched. The feature requires new user accounts to be approved by an administrator before they can access the system.

## Features Implemented

### 1. Enhanced Registration Process
- **Required Fields**: Username, Full Name, Email, Role, Password
- **Role Selection**: Dropdown menu with options: Dean, Chair, Secretary
- **Email Validation**: Must be unique and properly formatted
- **Password Strength**: Minimum 8 characters with uppercase, lowercase, and numbers
- **Status**: All new accounts are created with `status = "pending"`

### 2. Database Schema Updates
- Added `status` column to users table (default: "pending")
- Made `email` column unique
- Updated default users to have `status = "active"`

### 3. Backend API Changes

#### Registration Endpoint (`/auth/register`)
- Enhanced validation for all required fields
- Email uniqueness check
- Password strength validation
- Role validation (only dean, chair, secretary allowed)
- Returns success message instead of auto-login

#### New Admin Endpoints
- `GET /api/pending_users` - Get all pending users (Admin only)
- `POST /api/approve_user/{user_id}` - Approve a pending user (Admin only)
- `POST /api/reject_user/{user_id}` - Reject a pending user (Admin only)

#### Login Security
- Updated `verify_user_credentials()` to check user status
- Only users with `status = "active"` can log in
- Pending users receive "Invalid credentials" error (security best practice)

### 4. Frontend Updates

#### Registration Form (`/static/register.html`)
- Added role dropdown with Dean, Chair, Secretary options
- Made Full Name and Email required fields
- Enhanced password validation with strength requirements
- Updated success message to inform about pending approval
- Redirects to login page after successful registration

#### Admin Dashboard (`/static/admin.html`)
- Added "Manage Users" functionality
- Displays pending users in card format
- Approve/Reject buttons for each pending user
- Real-time updates after actions
- Confirmation dialogs for actions

### 5. User Management Functions

#### Database Functions (in `database.py`)
- `get_pending_users()` - Retrieve all pending users
- `approve_user(user_id, approved_by)` - Approve user and send notification
- `reject_user(user_id, rejected_by, reason)` - Reject and delete user
- `check_email_exists(email)` - Check email uniqueness
- `get_user_by_email(email)` - Get user by email

## Workflow

### For New Users:
1. User visits registration page
2. Fills out form with all required information
3. Selects appropriate role (Dean, Chair, Secretary)
4. Account is created with `status = "pending"`
5. User receives message about pending approval
6. User cannot log in until approved

### For Administrators:
1. Admin logs in and accesses admin dashboard
2. Clicks "Manage Users" to view pending users
3. Reviews user information (name, email, role, application date)
4. Approves or rejects each user
5. Approved users receive notification and can log in
6. Rejected users are removed from the system

## Security Features

1. **Email Uniqueness**: Prevents duplicate accounts
2. **Password Strength**: Enforces strong passwords
3. **Role Validation**: Only allows valid roles
4. **Admin-Only Access**: Only admins can approve/reject users
5. **Status Checking**: Login blocked for pending users
6. **Input Validation**: Comprehensive validation on both frontend and backend

## Testing

A test script (`test_user_approval.py`) is provided to verify the complete workflow:
- Admin login
- User registration
- Pending user login attempt (should fail)
- Admin approval process
- Approved user login (should succeed)

## Default Users

The system creates default users with `status = "active"`:
- **admin** / admin123 (Admin)
- **chair** / chair123 (Chair)
- **dean** / dean123 (Dean)
- **sec** / sec123 (Secretary)

## API Endpoints Summary

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| POST | `/auth/register` | Register new user | Public |
| POST | `/auth/login` | Login user | Public |
| GET | `/api/pending_users` | Get pending users | Admin only |
| POST | `/api/approve_user/{id}` | Approve user | Admin only |
| POST | `/api/reject_user/{id}` | Reject user | Admin only |

## Files Modified

1. `database.py` - Database schema and user management functions
2. `app.py` - Backend API endpoints and validation
3. `static/register.html` - Registration form with role selection
4. `static/admin.html` - Admin dashboard with user management
5. `test_user_approval.py` - Test script for the workflow

## Future Enhancements

1. Email notifications for approval/rejection
2. Bulk approval/rejection functionality
3. User role modification by admin
4. Account suspension/reactivation
5. Audit trail for user management actions
