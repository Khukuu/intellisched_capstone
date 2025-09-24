# IntelliSched - User Roles and Permissions

This document describes the user roles and their specific functionalities in the IntelliSched system.

## User Roles Overview

The system now supports four distinct user roles, each with specific permissions and access levels:

### 1. Administrator (admin)
- **Username:** `admin`
- **Password:** `admin123`
- **Access Level:** Full system access
- **Capabilities:**
  - System administration
  - User management (future feature)
  - Access to all system functions

### 2. Department Chair (chair)
- **Username:** `chair`
- **Password:** `chair123`
- **Access Level:** Schedule generation and management
- **Capabilities:**
  - Generate class schedules
  - Save schedules (automatically creates approval requests)
  - View and manage data (subjects, teachers, rooms, sections)
  - Upload CSV data
  - Access to full scheduling dashboard

### 3. Dean (dean)
- **Username:** `dean`
- **Password:** `dean123`
- **Access Level:** Schedule approval and oversight
- **Capabilities:**
  - View pending schedule approval requests
  - Approve or reject proposed schedules
  - Add comments to approval decisions
  - View approved schedules
  - Receive notifications when schedules are submitted for approval

### 4. Secretary (secretary)
- **Username:** `sec`
- **Password:** `sec123`
- **Access Level:** Schedule management and maintenance
- **Capabilities:**
  - View approved schedules only
  - Edit schedule details (name, comments)
  - Delete approved schedules
  - Cannot generate new schedules
  - Cannot approve/reject schedules

## Workflow Process

### 1. Schedule Creation (Chair)
1. Chair logs in and accesses the scheduling dashboard
2. Chair generates a new schedule using the system
3. Chair saves the schedule with a name
4. System automatically creates an approval request for the dean

### 2. Schedule Approval (Dean)
1. Dean logs in and accesses the dean dashboard
2. Dean views pending schedule approval requests
3. Dean can:
   - View schedule details
   - Approve the schedule (with optional comments)
   - Reject the schedule (with optional comments)
4. System sends notification to the chair about the decision

### 3. Schedule Management (Secretary)
1. Secretary logs in and accesses the secretary dashboard
2. Secretary can view all approved schedules
3. Secretary can:
   - Edit schedule names and comments
   - Delete approved schedules
   - View schedule details

## Database Schema

### New Tables Added

#### `schedule_approvals`
Tracks schedule approval requests and their status:
- `id` - Primary key
- `schedule_id` - Reference to saved schedule
- `schedule_name` - Human-readable schedule name
- `semester` - Academic semester
- `status` - pending/approved/rejected
- `created_by` - Username of the chair who created it
- `approved_by` - Username of the dean who approved/rejected it
- `created_at` - Timestamp when request was created
- `approved_at` - Timestamp when decision was made
- `comments` - Optional comments from dean

#### `notifications`
Tracks system notifications for users:
- `id` - Primary key
- `user_id` - Reference to users table
- `title` - Notification title
- `message` - Notification message
- `type` - info/success/warning/error
- `is_read` - Boolean flag for read status
- `created_at` - Timestamp when notification was created

## API Endpoints

### Schedule Approval Endpoints
- `POST /api/schedule_approval` - Create approval request (Chair only)
- `GET /api/pending_schedules` - Get pending schedules (Dean only)
- `GET /api/approved_schedules` - Get approved schedules (Dean/Secretary)
- `POST /api/approve_schedule/{schedule_id}` - Approve schedule (Dean only)
- `POST /api/reject_schedule/{schedule_id}` - Reject schedule (Dean only)
- `GET /api/schedule_approval_status/{schedule_id}` - Get approval status

### Notification Endpoints
- `GET /api/notifications` - Get all notifications for user
- `GET /api/notifications/unread` - Get unread notifications
- `POST /api/notifications/{notification_id}/read` - Mark notification as read

## Dashboard URLs

- **Admin Dashboard:** `/admin`
- **Chair Dashboard:** `/chair`
- **Dean Dashboard:** `/dean`
- **Secretary Dashboard:** `/secretary`
- **Login Page:** `/login`

## Security Features

### Role-Based Access Control
- Each endpoint is protected with role-specific permissions
- Users can only access their designated dashboards
- Automatic redirection based on user role after login

### Authentication
- JWT token-based authentication
- Secure password hashing with salt
- Session management with token expiration

## Testing

To test the new user roles, run the test script:

```bash
cd Algorithm
python test_new_users.py
```

This will verify that all users are created correctly and can authenticate properly.

## Future Enhancements

1. **Email Notifications:** Send email notifications for schedule approvals
2. **Advanced User Management:** Admin interface for managing users
3. **Audit Logging:** Track all user actions for compliance
4. **Schedule Versioning:** Track changes to approved schedules
5. **Bulk Operations:** Allow bulk approval/rejection of schedules
6. **Advanced Filtering:** More sophisticated filtering options for schedules

## Troubleshooting

### Common Issues

1. **User cannot log in:**
   - Verify username and password are correct
   - Check if user exists in database
   - Ensure database connection is working

2. **Access denied errors:**
   - Verify user has correct role
   - Check if JWT token is valid
   - Ensure user is accessing correct dashboard

3. **Schedules not appearing:**
   - Check if schedule was saved properly
   - Verify approval request was created
   - Check user permissions for viewing schedules

### Database Issues

If you encounter database issues, you can reset the users by running:

```python
from database import db
# This will recreate all default users
db.create_default_admin()
```

## Support

For technical support or questions about the user role system, please refer to the main project documentation or contact the development team.
