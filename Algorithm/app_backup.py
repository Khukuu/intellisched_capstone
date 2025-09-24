from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scheduler import generate_schedule
from database import db, load_subjects_from_db, load_teachers_from_db, load_rooms_from_db, load_sections_from_db
import os
import io
import json
import csv
from datetime import datetime, timedelta
import jwt  # PyJWT is installed as 'jwt'
from typing import Optional

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer(auto_error=False)

# JWT Token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(allowed_roles: list):
    """Decorator to require specific roles for access"""
    def role_checker(username: str = Depends(verify_token)):
        user = db.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user_role = user.get('role', 'user')
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return username
    return role_checker

def require_chair_role(username: str = Depends(require_role(['chair']))):
    """Require chair role for access"""
    return username

def require_admin_role(username: str = Depends(require_role(['admin']))):
    """Require admin role for access"""
    return username

def require_dean_role(username: str = Depends(require_role(['dean']))):
    """Require dean role for access"""
    return username

def require_secretary_role(username: str = Depends(require_role(['secretary']))):
    """Require secretary role for access"""
    return username

def require_dean_or_secretary_role(username: str = Depends(require_role(['dean', 'secretary']))):
    """Require dean or secretary role for access"""
    return username

# Authentication endpoints
@app.post('/auth/login')
async def login(payload: dict):
    try:
        username = payload.get('username')
        password = payload.get('password')
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        print(f"🔐 Login attempt for user: {username}")
        
        # Verify credentials
        user = db.verify_user_credentials(username, password)
        if not user:
            print(f"❌ Login failed for user {username}: Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        print(f"✅ Login successful for user {username}")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": username,
            "full_name": user.get('full_name'),
            "role": user.get('role')
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get('/auth/me')
async def get_current_user(username: str = Depends(verify_token)):
    """Get current user information"""
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post('/auth/logout')
async def logout():
    """Logout endpoint (client-side token removal)"""
    return {"message": "Successfully logged out"}

@app.post('/auth/register')
async def register(payload: dict):
    """Create a new user account"""
    try:
        username = (payload.get('username') or '').strip()
        password = payload.get('password') or ''
        full_name = (payload.get('full_name') or '').strip()
        email = (payload.get('email') or '').strip()

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")

        # Check if user already exists
        existing = db.get_user_by_username(username)
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")

        ok = db.create_user({
            'username': username,
            'password': password,
            'full_name': full_name,
            'email': email,
            'role': 'user'
        })
        if not ok:
            raise HTTPException(status_code=500, detail="Could not create user")

        # Auto-login: issue token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)
        return {
            "message": "Account created successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "username": username,
            "full_name": full_name or None,
            "role": 'user'
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/health')
async def health_check():
    """Health check endpoint to test database connectivity"""
    try:
        # Test database connection
        from database import db
        test_query = db.db.execute_query("SELECT 1 as test")
        if test_query and len(test_query) > 0:
            return {"status": "healthy", "database": "connected", "message": "All systems operational"}
        else:
            return {"status": "unhealthy", "database": "error", "message": "Database query failed"}
    except Exception as e:
        return {"status": "unhealthy", "database": "error", "message": f"Database error: {str(e)}"}

# Main route - redirect to appropriate dashboard based on role
@app.get('/')
async def index():
    """Main route - redirect users to appropriate dashboard"""
    return RedirectResponse(url='/login')

# Chair-specific route for scheduling functionality
@app.get('/chair')
async def chair_dashboard():
    """Chair dashboard with scheduling and data management - authentication handled by frontend"""
    index_path = os.path.join('static', 'index.html')
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail='Index file not found')
    return FileResponse(index_path, media_type='text/html')

# Admin route (placeholder for future admin functionality)
@app.get('/admin')
async def admin_dashboard():
    """Admin dashboard - placeholder for future admin functionality - authentication handled by frontend"""
    admin_path = os.path.join('static', 'admin.html')
    if not os.path.exists(admin_path):
        # Create a simple admin placeholder page
        admin_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IntelliSched - Admin Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="bi bi-shield-check me-2"></i>
                IntelliSched Admin
            </a>
            <div class="d-flex">
                <button id="logoutBtn" class="btn btn-outline-light btn-sm">
                    <i class="bi bi-box-arrow-right"></i> Logout
                </button>
            </div>
        </div>
    </nav>
    
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="bi bi-tools" style="font-size: 4rem; color: #6c757d;"></i>
                        <h2 class="mt-3">Admin Dashboard</h2>
                        <p class="text-muted">Admin functionality coming soon...</p>
                        <p class="small text-muted">This area will contain user management, system settings, and administrative tools.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Authentication check and role-based access control
        document.addEventListener('DOMContentLoaded', function() {
            const token = localStorage.getItem('authToken');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            // Check user role - only admin users should access this page
            const userRole = localStorage.getItem('role');
            if (userRole !== 'admin') {
                alert('Access denied. This area is only accessible to Admin users.');
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                localStorage.removeItem('role');
                window.location.href = '/login';
                return;
            }
            
            // Update navbar with user info
            const username = localStorage.getItem('username');
            if (username) {
                const logoutBtn = document.getElementById('logoutBtn');
                logoutBtn.innerHTML = `<i class="bi bi-person"></i> ${username} (Admin) <i class="bi bi-box-arrow-right ms-1"></i> Logout`;
            }
        });
        
        document.getElementById('logoutBtn').addEventListener('click', function() {
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
            window.location.href = '/login';
        });
    </script>
</body>
</html>
        """
        with open(admin_path, 'w', encoding='utf-8') as f:
            f.write(admin_content)
    
    return FileResponse(admin_path, media_type='text/html')

@app.get('/login')
async def login_page():
    """Serve login page for unauthenticated users"""
    login_path = os.path.join('static', 'login.html')
    if not os.path.exists(login_path):
        raise HTTPException(status_code=404, detail='Login file not found')
    return FileResponse(login_path, media_type='text/html')

@app.get('/register')
async def register_page():
    """Serve registration page for new account creation"""
    register_path = os.path.join('static', 'register.html')
    if not os.path.exists(register_path):
        raise HTTPException(status_code=404, detail='Register file not found')
    return FileResponse(register_path, media_type='text/html')

@app.get('/dean')
async def dean_dashboard():
    """Dean dashboard for viewing and approving proposed schedules"""
    dean_path = os.path.join('static', 'dean.html')
    if not os.path.exists(dean_path):
        # Create dean dashboard page
        dean_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntelliSched — Dean Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
  <style>
    .schedule-card {
      transition: transform 0.2s;
    }
    .schedule-card:hover {
      transform: translateY(-2px);
    }
    .status-pending {
      background-color: #fff3cd;
      border-color: #ffeaa7;
    }
    .status-approved {
      background-color: #d4edda;
      border-color: #c3e6cb;
    }
    .status-rejected {
      background-color: #f8d7da;
      border-color: #f5c6cb;
    }
    .dropdown-item:hover {
      background-color: #f8f9fa;
    }
    .dropdown-item.active {
      background-color: #0d6efd;
      color: white;
    }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark custom-navbar mb-4">
    <div class="container-fluid">
      <a class="navbar-brand d-flex align-items-center" href="#">
        <i class="bi bi-calendar3-fill me-2" aria-hidden="true"></i>
        <span class="fs-5">IntelliSched - Dean</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li class="nav-item">
            <a class="nav-link active" aria-current="page" href="#" id="pendingNavLink">Pending Approvals</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" id="approvedNavLink">Approved Schedules</a>
          </li>
        </ul>
        <div class="d-flex align-items-center">
          <button id="logoutBtn" class="btn btn-outline-light btn-sm rounded-pill"><i class="bi bi-box-arrow-right"></i> Logout</button>
        </div>
      </div>
    </div>
  </nav>

  <div class="container mt-4">
    <div id="pending-section" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative;">
      <div class="row">
        <!-- Profile Section (Left) -->
        <div class="col-12 col-md-6 d-flex align-items-stretch mb-4 mb-md-0">
          <div class="card w-100 h-100 rounded-4 card-mac-style border-0 shadow-none bg-light">
            <div class="card-body d-flex flex-column justify-content-center align-items-center h-100">
              <i class="bi bi-shield-check" style="font-size: 3rem; color: #0d6efd;"></i>
              <h5 class="mt-3 mb-1" id="profile-username">Dean</h5>
              <span class="badge bg-primary" id="profile-role">Dean</span>
              <p class="text-muted mt-3 mb-0 text-center">Schedule Approval Dashboard<br>Review and approve proposed schedules.</p>
            </div>
          </div>
        </div>
        <!-- Pending Schedules Controls (Right) -->
        <div class="col-12 col-md-6">
          <div class="d-flex align-items-start justify-content-between mb-3">
            <div>
              <h1 class="card-title mb-1">Pending Approvals</h1>
              <p class="text-muted small mb-0">Review and approve proposed schedules from department chairs.</p>
            </div>
          </div>
          <div class="mb-3">
            <button class="btn btn-outline-primary btn-sm" onclick="loadPendingSchedules()">
              <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pending Schedules Display -->
    <div id="pendingSchedules" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative;">
      <div class="text-center">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    </div>

    <!-- Approved Schedules Section -->
    <div id="approved-section" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative;display:none;">
      <div class="row">
        <!-- Profile Section (Left) -->
        <div class="col-12 col-md-6 d-flex align-items-stretch mb-4 mb-md-0">
          <div class="card w-100 h-100 rounded-4 card-mac-style border-0 shadow-none bg-light">
            <div class="card-body d-flex flex-column justify-content-center align-items-center h-100">
              <i class="bi bi-check-circle" style="font-size: 3rem; color: #198754;"></i>
              <h5 class="mt-3 mb-1" id="profile-username-approved">Dean</h5>
              <span class="badge bg-success" id="profile-role-approved">Dean</span>
              <p class="text-muted mt-3 mb-0 text-center">Approved Schedules<br>View previously approved schedules.</p>
            </div>
          </div>
        </div>
        <!-- Approved Schedules Controls (Right) -->
        <div class="col-12 col-md-6">
          <div class="d-flex align-items-start justify-content-between mb-3">
            <div>
              <h1 class="card-title mb-1">Approved Schedules</h1>
              <p class="text-muted small mb-0">View all schedules that have been approved.</p>
            </div>
          </div>
          <div class="mb-3">
            <button class="btn btn-outline-success btn-sm" onclick="loadApprovedSchedules()">
              <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Approved Schedules Display -->
    <div id="approvedSchedules" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative;display:none;">
      <div class="text-center">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    </div>
  </div>
    
    <!-- Approval Modal -->
    <div class="modal fade" id="approvalModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Schedule Approval</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="approvalComments" class="form-label">Comments (Optional)</label>
                        <textarea class="form-control" id="approvalComments" rows="3"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-success" id="approveBtn">Approve</button>
                    <button type="button" class="btn btn-danger" id="rejectBtn">Reject</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentScheduleId = null;
        
        // Navigation functionality
        function showSection(sectionId) {
            const pendingSection = document.getElementById('pending-section');
            const pendingSchedules = document.getElementById('pendingSchedules');
            const approvedSection = document.getElementById('approved-section');
            const approvedSchedules = document.getElementById('approvedSchedules');
            const pendingNavLink = document.getElementById('pendingNavLink');
            const approvedNavLink = document.getElementById('approvedNavLink');

            // Hide all sections
            pendingSection.style.display = 'none';
            pendingSchedules.style.display = 'none';
            approvedSection.style.display = 'none';
            approvedSchedules.style.display = 'none';

            // Remove active class from nav links
            pendingNavLink.classList.remove('active');
            approvedNavLink.classList.remove('active');

            if (sectionId === 'pending') {
                pendingSection.style.display = 'block';
                pendingSchedules.style.display = 'block';
                pendingNavLink.classList.add('active');
            } else if (sectionId === 'approved') {
                approvedSection.style.display = 'block';
                approvedSchedules.style.display = 'block';
                approvedNavLink.classList.add('active');
            }
        }

        // Authentication check
        document.addEventListener('DOMContentLoaded', function() {
            const token = localStorage.getItem('authToken');
            if (!token) {
                window.location.href = '/login';
                return;
            }
            
            const userRole = localStorage.getItem('role');
            if (userRole !== 'dean') {
                alert('Access denied. This area is only accessible to Dean users.');
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                localStorage.removeItem('role');
                window.location.href = '/login';
                return;
            }
            
            const username = localStorage.getItem('username');
            if (username) {
                const logoutBtn = document.getElementById('logoutBtn');
                logoutBtn.innerHTML = `<i class="bi bi-person"></i> ${username} (Dean) <i class="bi bi-box-arrow-right ms-1"></i> Logout`;
            }
            
            // Set up navigation
            document.getElementById('pendingNavLink').addEventListener('click', (e) => {
                e.preventDefault();
                showSection('pending');
            });
            
            document.getElementById('approvedNavLink').addEventListener('click', (e) => {
                e.preventDefault();
                showSection('approved');
            });
            
            // Load initial data
            loadPendingSchedules();
            loadApprovedSchedules();
            
            // Show pending section by default
            showSection('pending');
        });
        
        function getAuthHeaders() {
            const token = localStorage.getItem('authToken');
            return {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            };
        }
        
        async function loadPendingSchedules() {
            try {
                const response = await fetch('/api/pending_schedules', {
                    headers: getAuthHeaders()
                });
                const schedules = await response.json();
                renderSchedules(schedules, 'pendingSchedules', true);
            } catch (error) {
                console.error('Error loading pending schedules:', error);
                document.getElementById('pendingSchedules').innerHTML = '<p class="text-danger">Error loading pending schedules.</p>';
            }
        }
        
        async function loadApprovedSchedules() {
            try {
                const response = await fetch('/api/approved_schedules', {
                    headers: getAuthHeaders()
                });
                const schedules = await response.json();
                renderSchedules(schedules, 'approvedSchedules', false);
            } catch (error) {
                console.error('Error loading approved schedules:', error);
                document.getElementById('approvedSchedules').innerHTML = '<p class="text-danger">Error loading approved schedules.</p>';
            }
        }
        
        function renderSchedules(schedules, containerId, showActions) {
            const container = document.getElementById(containerId);
            
            if (schedules.length === 0) {
                container.innerHTML = '<p class="text-muted">No schedules found.</p>';
                return;
            }
            
            let html = '<div class="row">';
            schedules.forEach(schedule => {
                const statusClass = schedule.status === 'approved' ? 'status-approved' : 
                                  schedule.status === 'rejected' ? 'status-rejected' : 'status-pending';
                
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="card schedule-card ${statusClass}">
                            <div class="card-body">
                                <h6 class="card-title">${schedule.schedule_name || 'Unnamed Schedule'}</h6>
                                <p class="card-text">
                                    <small class="text-muted">
                                        <strong>ID:</strong> ${schedule.schedule_id}<br>
                                        <strong>Semester:</strong> ${schedule.semester || 'N/A'}<br>
                                        <strong>Created:</strong> ${new Date(schedule.created_at).toLocaleDateString()}<br>
                                        <strong>Status:</strong> <span class="badge bg-${schedule.status === 'approved' ? 'success' : schedule.status === 'rejected' ? 'danger' : 'warning'}">${schedule.status}</span>
                                    </small>
                                </p>
                                ${showActions ? `
                                    <div class="d-flex gap-2">
                                        <button class="btn btn-sm btn-outline-primary" onclick="viewSchedule('${schedule.schedule_id}')">
                                            <i class="bi bi-eye"></i> View
                                        </button>
                                        <button class="btn btn-sm btn-success" onclick="openApprovalModal('${schedule.schedule_id}', 'approve')">
                                            <i class="bi bi-check"></i> Approve
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="openApprovalModal('${schedule.schedule_id}', 'reject')">
                                            <i class="bi bi-x"></i> Reject
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
        
        function openApprovalModal(scheduleId, action) {
            currentScheduleId = scheduleId;
            document.getElementById('approvalComments').value = '';
            
            const modal = new bootstrap.Modal(document.getElementById('approvalModal'));
            modal.show();
            
            // Update button visibility based on action
            const approveBtn = document.getElementById('approveBtn');
            const rejectBtn = document.getElementById('rejectBtn');
            
            if (action === 'approve') {
                approveBtn.style.display = 'inline-block';
                rejectBtn.style.display = 'none';
            } else {
                approveBtn.style.display = 'none';
                rejectBtn.style.display = 'inline-block';
            }
        }
        
        document.getElementById('approveBtn').addEventListener('click', async function() {
            await handleApproval('approve');
        });
        
        document.getElementById('rejectBtn').addEventListener('click', async function() {
            await handleApproval('reject');
        });
        
        async function handleApproval(action) {
            if (!currentScheduleId) return;
            
            const comments = document.getElementById('approvalComments').value;
            
            try {
                const endpoint = action === 'approve' ? 'approve' : 'reject';
                const response = await fetch(`/api/${endpoint}_schedule/${currentScheduleId}`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ comments })
                });
                
                if (response.ok) {
                    alert(`Schedule ${action}d successfully!`);
                    bootstrap.Modal.getInstance(document.getElementById('approvalModal')).hide();
                    loadPendingSchedules();
                    loadApprovedSchedules();
                } else {
                    const error = await response.json();
                    alert(`Error: ${error.detail || 'Failed to ${action} schedule'}`);
                }
            } catch (error) {
                console.error(`Error ${action}ing schedule:`, error);
                alert(`Error ${action}ing schedule. Please try again.`);
            }
        }
        
        function viewSchedule(scheduleId) {
            // For now, just show an alert. In a real implementation, this would open a detailed view
            alert(`Viewing schedule: ${scheduleId}`);
        }
        
        document.getElementById('logoutBtn').addEventListener('click', function() {
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
            window.location.href = '/login';
        });
    </script>
</body>
</html>
        """
        with open(dean_path, 'w', encoding='utf-8') as f:
            f.write(dean_content)
    
    return FileResponse(dean_path, media_type='text/html')

@app.get('/secretary')
async def secretary_dashboard():
    """Secretary dashboard for viewing, editing, and deleting schedules"""
    secretary_path = os.path.join('static', 'secretary.html')
    if not os.path.exists(secretary_path):
        # Create secretary dashboard page
        secretary_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntelliSched — Secretary Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
  <style>
    .dropdown-item:hover {
      background-color: #f8f9fa;
    }
    .dropdown-item.active {
      background-color: #0d6efd;
      color: white;
    }
    #roomDropdown {
      border: 1px solid #ced4da;
      border-radius: 0.375rem;
      box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    }
    
    /* Drop shadows for all dropdowns */
    #yearFilter, #sectionFilter, #roomFilter, #viewMode {
      box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark custom-navbar mb-4">
    <div class="container-fluid">
      <a class="navbar-brand d-flex align-items-center" href="#">
        <i class="bi bi-calendar3-fill me-2" aria-hidden="true"></i>
        <span class="fs-5">IntelliSched - Secretary</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li class="nav-item">
            <a class="nav-link active" aria-current="page" href="#" id="scheduleNavLink">Schedule</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" id="dataNavLink">Data</a>
          </li>
        </ul>
        <div class="d-flex align-items-center">
          <button id="logoutBtn" class="btn btn-outline-light btn-sm rounded-pill"><i class="bi bi-box-arrow-right"></i> Logout</button>
        </div>
      </div>
    </div>
  </nav>

  <div class="container mt-4">
    <div id="schedule-section" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative;">
      <div class="row">
        <!-- Profile Section (Left) -->
        <div class="col-12 col-md-6 d-flex align-items-stretch mb-4 mb-md-0">
          <div class="card w-100 h-100 rounded-4 card-mac-style border-0 shadow-none bg-light">
            <div class="card-body d-flex flex-column justify-content-center align-items-center h-100">
              <i class="bi bi-clipboard-data" style="font-size: 3rem; color: #198754;"></i>
              <h5 class="mt-3 mb-1" id="profile-username">Secretary</h5>
              <span class="badge bg-success" id="profile-role">Secretary</span>
              <p class="text-muted mt-3 mb-0 text-center">Schedule Management Dashboard<br>View and manage approved schedules.</p>
            </div>
          </div>
        </div>
        <!-- Schedule Controls (Right) -->
        <div class="col-12 col-md-6">
          <div class="d-flex align-items-start justify-content-between mb-3">
            <div>
              <h1 class="card-title mb-1">View Schedules</h1>
              <p class="text-muted small mb-0">View and manage approved schedules. You cannot generate new schedules.</p>
            </div>
          </div>
          <div class="mb-3">
            <label for="semesterSelect" class="form-label">Select Semester:</label>
            <select class="form-select" id="semesterSelect">
              <option value="1" selected>1st Semester</option>
              <option value="2">2nd Semester</option>
              <option value="3">Summer Semester</option>
            </select>
          </div>
          <div class="row g-2 mb-3 align-items-center">
            <div class="col-12 mb-3">
              <div class="d-flex align-items-center gap-2">
                <input type="text" id="saveNameInput" class="form-control" style="max-width: 200px;" placeholder="Schedule name (optional)" />
                <button id="saveBtn" class="btn btn-light border-0 shadow-sm">Save</button>
                <select id="savedSchedulesSelect" class="form-select" style="min-width: 200px;">
                  <option value="">Select saved schedule…</option>
                </select>
                <button id="loadBtn" class="btn btn-light border-0 shadow-sm">Load</button>
              </div>
            </div>
            <div class="col-auto">
              <button id="downloadBtn" class="btn btn-light border-0 shadow-sm"><i class="bi bi-download me-1"></i> CSV</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div id="data-management-section" class="card p-4 shadow-sm mb-4 rounded-4 card-mac-style" style="display:none;">
      <h1 class="card-title mb-4">Data Management</h1>
      <!-- Tabs -->
      <ul class="nav nav-tabs mb-3" id="dataTabs" role="tablist">
        <li class="nav-item" role="presentation">
          <button class="nav-link active" id="tab-subjects" data-tab="subjects" data-bs-toggle="tab" data-bs-target="#pane-subjects" type="button" role="tab" aria-controls="pane-subjects" aria-selected="true">Subjects</button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="tab-teachers" data-tab="teachers" data-bs-toggle="tab" data-bs-target="#pane-teachers" type="button" role="tab" aria-controls="pane-teachers" aria-selected="false">Teachers</button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="tab-rooms" data-tab="rooms" data-bs-toggle="tab" data-bs-target="#pane-rooms" type="button" role="tab" aria-controls="pane-rooms" aria-selected="false">Rooms</button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="tab-sections" data-tab="sections" data-bs-toggle="tab" data-bs-target="#pane-sections" type="button" role="tab" aria-controls="pane-sections" aria-selected="false">Sections</button>
        </li>
      </ul>
      <div class="tab-content">
        <div class="tab-pane fade show active" id="pane-subjects" role="tabpanel" aria-labelledby="tab-subjects">
          <h2>Subjects</h2>
          <div class="mb-3 d-flex align-items-center gap-2 flex-wrap">
            <input id="subjectsSearch" class="form-control form-control-sm me-2" placeholder="Search subjects (code, name)…" />
            <button id="subjectsRefresh" class="btn btn-sm btn-outline-secondary">Refresh</button>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button id="subjectsAdd" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> Add</button>
              <button id="subjectsEdit" class="btn btn-sm btn-warning"><i class="bi bi-pencil-square"></i> Edit</button>
              <button id="subjectsDelete" class="btn btn-sm btn-danger"><i class="bi bi-trash"></i> Delete</button>
            </div>
          </div>
          <div id="subjectsData" class="table-responsive mb-4"></div>
        </div>
        <div class="tab-pane fade" id="pane-teachers" role="tabpanel" aria-labelledby="tab-teachers">
          <h2>Teachers</h2>
          <div class="mb-3 d-flex align-items-center gap-2 flex-wrap">
            <input id="teachersSearch" class="form-control form-control-sm me-2" placeholder="Search teachers (id, name, subjects)…" />
            <button id="teachersRefresh" class="btn btn-sm btn-outline-secondary">Refresh</button>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button id="teachersAdd" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> Add</button>
              <button id="teachersEdit" class="btn btn-sm btn-warning"><i class="bi bi-pencil-square"></i> Edit</button>
              <button id="teachersDelete" class="btn btn-sm btn-danger"><i class="bi bi-trash"></i> Delete</button>
            </div>
          </div>
          <div id="teachersData" class="table-responsive mb-4"></div>
        </div>
        <div class="tab-pane fade" id="pane-rooms" role="tabpanel" aria-labelledby="tab-rooms">
          <h2>Rooms</h2>
          <div class="mb-3 d-flex align-items-center gap-2 flex-wrap">
            <input id="roomsSearch" class="form-control form-control-sm me-2" placeholder="Search rooms (id, name)…" />
            <button id="roomsRefresh" class="btn btn-sm btn-outline-secondary">Refresh</button>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button id="roomsAdd" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> Add</button>
              <button id="roomsEdit" class="btn btn-sm btn-warning"><i class="bi bi-pencil-square"></i> Edit</button>
              <button id="roomsDelete" class="btn btn-sm btn-danger"><i class="bi bi-trash"></i> Delete</button>
            </div>
          </div>
          <div id="roomsData" class="table-responsive mb-4"></div>
        </div>
        <div class="tab-pane fade" id="pane-sections" role="tabpanel" aria-labelledby="tab-sections">
          <h2>Sections</h2>
          <div class="mb-3 d-flex align-items-center gap-2 flex-wrap">
            <input id="sectionsSearch" class="form-control form-control-sm me-2" placeholder="Search sections (id, subject)…" />
            <button id="sectionsRefresh" class="btn btn-sm btn-outline-secondary">Refresh</button>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button id="sectionsAdd" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> Add</button>
              <button id="sectionsEdit" class="btn btn-sm btn-warning"><i class="bi bi-pencil-square"></i> Edit</button>
              <button id="sectionsDelete" class="btn btn-sm btn-danger"><i class="bi bi-trash"></i> Delete</button>
            </div>
          </div>
          <div id="sectionsData" class="table-responsive mb-4"></div>
        </div>
      </div>
    </div>

    <!-- Results Card at the bottom (outside both sections) -->
    <div class="card p-4 shadow-sm mb-4 mx-auto rounded-4 card-mac-style" id="results-card" style="width:90vw;max-width:100vw;left:50%;transform:translateX(-50%);position:relative; min-height:40vh;">
      <!-- Filters now at the top of the results card -->
      <div class="row g-3 align-items-end mb-4 justify-content-center text-center">
        <div class="col-12 col-md-3">
          <label for="yearFilter" class="form-label">Filter by Year</label>
          <select id="yearFilter" class="form-select">
            <option value="all" selected>All Years</option>
            <option value="1">1st Year</option>
            <option value="2">2nd Year</option>
            <option value="3">3rd Year</option>
            <option value="4">4th Year</option>
          </select>
        </div>
        <div class="col-12 col-md-3">
          <label for="sectionFilter" class="form-label">Filter by Section</label>
          <select id="sectionFilter" class="form-select" disabled>
            <option value="all" selected>All Sections</option>
          </select>
        </div>
        <div class="col-12 col-md-3">
          <label for="roomFilter" class="form-label">Filter by Room</label>
          <div class="position-relative">
            <input type="text" id="roomFilter" class="form-select" placeholder="Search rooms..." disabled>
            <div id="roomDropdown" class="dropdown-menu w-100" style="max-height: 200px; overflow-y: auto; display: none;">
              <div class="dropdown-item" data-value="all">All Rooms</div>
            </div>
          </div>
        </div>
        <div class="col-12 col-md-3">
          <label for="viewMode" class="form-label">View</label>
          <select id="viewMode" class="form-select">
            <option value="both" selected>Both (side-by-side)</option>
            <option value="list">List only</option>
            <option value="timetable">Timetable only</option>
          </select>
        </div>
      </div>
      <div class="row g-3">
        <div class="col-12 col-md-6" id="result">
          <div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 200px;">No schedule loaded yet. Load a saved schedule to view it.</div>
        </div>
        <div class="col-12 col-md-6" id="timetable">
          <div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 200px;">Timetable will appear here after loading a schedule.</div>
        </div>
      </div>
    </div>
  </div>
    
    <!-- Edit Modal -->
    <div class="modal fade" id="editModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Schedule</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="editScheduleName" class="form-label">Schedule Name</label>
                        <input type="text" class="form-control" id="editScheduleName">
                    </div>
                    <div class="mb-3">
                        <label for="editComments" class="form-label">Comments</label>
                        <textarea class="form-control" id="editComments" rows="3"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="saveEditBtn">Save Changes</button>
                </div>
            </div>
        </div>
    </div>
    
  <!-- Logout Confirmation Modal -->
  <div class="modal fade" id="logoutModal" tabindex="-1" aria-labelledby="logoutModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content card-mac-style">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title" id="logoutModalLabel">
            <i class="bi bi-box-arrow-right text-danger me-2"></i>
            Confirm Logout
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <p class="mb-0">Are you sure you want to log out?</p>
          <p class="text-muted small mb-0">You will need to log in again to access the application.</p>
        </div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
            <i class="bi bi-x-circle me-1"></i>
            Cancel
          </button>
          <button type="button" class="btn btn-danger" id="confirmLogoutBtn">
            <i class="bi bi-box-arrow-right me-1"></i>
            Yes, Logout
          </button>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Bulk Edit Modal -->
  <div class="modal fade" id="bulkEditModal" tabindex="-1" aria-labelledby="bulkEditModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
      <div class="modal-content card-mac-style">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title" id="bulkEditModalLabel">
            <i class="bi bi-pencil-square text-warning me-2"></i>
            Bulk Edit
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body" id="bulkEditContent">
          <!-- Dynamic content will be inserted here -->
        </div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
            <i class="bi bi-x-circle me-1"></i>
            Cancel
          </button>
          <button type="button" class="btn btn-warning" id="bulkEditSaveBtn">
            <i class="bi bi-check-circle me-1"></i>
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  <script src="/static/script.js"></script>
  <script>
    // Override the generate button functionality for secretary
    document.addEventListener('DOMContentLoaded', function() {
      const token = localStorage.getItem('authToken');
      if (!token) {
        window.location.href = '/login';
        return;
      }
      
      const userRole = localStorage.getItem('role');
      if (userRole !== 'secretary') {
        alert('Access denied. This area is only accessible to Secretary users.');
        localStorage.removeItem('authToken');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
        window.location.href = '/login';
        return;
      }
      
      const username = localStorage.getItem('username');
      if (username) {
        const logoutBtn = document.getElementById('logoutBtn');
        logoutBtn.innerHTML = `<i class="bi bi-person"></i> ${username} (Secretary) <i class="bi bi-box-arrow-right ms-1"></i> Logout`;
      }
      
      // Update profile section
      const profileUsername = document.getElementById('profile-username');
      const profileRole = document.getElementById('profile-role');
      if (profileUsername) profileUsername.textContent = username || 'Secretary';
      if (profileRole) {
        profileRole.textContent = 'Secretary';
        profileRole.className = 'badge bg-success';
      }
      
      // Remove generate button functionality
      const generateBtn = document.getElementById('generateBtn');
      if (generateBtn) {
        generateBtn.style.display = 'none';
      }
      
      // Remove upload forms
      const uploadForms = document.querySelectorAll('form[id$="Form"]');
      uploadForms.forEach(form => {
        if (form.id.includes('upload')) {
          form.style.display = 'none';
        }
      });
      
      // Load rooms data to populate room mapping
      loadRoomsTable();
      // Hook up CRUD action buttons
      setupCrudButtons();
    });
  </script>
</body>
</html>
        """
        }
        
        async function loadApprovedSchedules() {
            try {
                const response = await fetch('/api/approved_schedules', {
                    headers: getAuthHeaders()
                });
                const schedules = await response.json();
                renderSchedules(schedules);
            } catch (error) {
                console.error('Error loading approved schedules:', error);
                document.getElementById('approvedSchedules').innerHTML = '<p class="text-danger">Error loading approved schedules.</p>';
            }
        }
        
        function renderSchedules(schedules) {
            const container = document.getElementById('approvedSchedules');
            
            if (schedules.length === 0) {
                container.innerHTML = '<p class="text-muted">No approved schedules found.</p>';
                return;
            }
            
            let html = '<div class="row">';
            schedules.forEach(schedule => {
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="card schedule-card status-approved">
                            <div class="card-body">
                                <h6 class="card-title">${schedule.schedule_name || 'Unnamed Schedule'}</h6>
                                <p class="card-text">
                                    <small class="text-muted">
                                        <strong>ID:</strong> ${schedule.schedule_id}<br>
                                        <strong>Semester:</strong> ${schedule.semester || 'N/A'}<br>
                                        <strong>Created:</strong> ${new Date(schedule.created_at).toLocaleDateString()}<br>
                                        <strong>Approved:</strong> ${schedule.approved_at ? new Date(schedule.approved_at).toLocaleDateString() : 'N/A'}<br>
                                        <strong>Approved by:</strong> ${schedule.approved_by || 'N/A'}<br>
                                        <strong>Status:</strong> <span class="badge bg-success">${schedule.status}</span>
                                    </small>
                                </p>
                                ${schedule.comments ? `<p class="card-text"><small><strong>Comments:</strong> ${schedule.comments}</small></p>` : ''}
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewSchedule('${schedule.schedule_id}')">
                                        <i class="bi bi-eye"></i> View
                                    </button>
                                    <button class="btn btn-sm btn-outline-warning" onclick="openEditModal('${schedule.schedule_id}', '${schedule.schedule_name || ''}', '${schedule.comments || ''}')">
                                        <i class="bi bi-pencil"></i> Edit
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteSchedule('${schedule.schedule_id}')">
                                        <i class="bi bi-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
        
        function openEditModal(scheduleId, scheduleName, comments) {
            currentScheduleId = scheduleId;
            document.getElementById('editScheduleName').value = scheduleName;
            document.getElementById('editComments').value = comments;
            
            const modal = new bootstrap.Modal(document.getElementById('editModal'));
            modal.show();
        }
        
        document.getElementById('saveEditBtn').addEventListener('click', async function() {
            if (!currentScheduleId) return;
            
            const scheduleName = document.getElementById('editScheduleName').value;
            const comments = document.getElementById('editComments').value;
            
            try {
                // For now, just show a success message. In a real implementation, this would call an API
                alert('Schedule updated successfully! (Note: This is a demo - actual update functionality would be implemented here)');
                bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
                loadApprovedSchedules();
            } catch (error) {
                console.error('Error updating schedule:', error);
                alert('Error updating schedule. Please try again.');
            }
        });
        
        function viewSchedule(scheduleId) {
            // For now, just show an alert. In a real implementation, this would open a detailed view
            alert(`Viewing schedule: ${scheduleId}`);
        }
        
        function deleteSchedule(scheduleId) {
            if (confirm(`Are you sure you want to delete schedule ${scheduleId}? This action cannot be undone.`)) {
                // For now, just show a success message. In a real implementation, this would call an API
                alert('Schedule deleted successfully! (Note: This is a demo - actual delete functionality would be implemented here)');
                loadApprovedSchedules();
            }
        }
        
        document.getElementById('logoutBtn').addEventListener('click', function() {
            localStorage.removeItem('authToken');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
            window.location.href = '/login';
        });
    </script>
</body>
</html>
        """
        with open(secretary_path, 'w', encoding='utf-8') as f:
            f.write(secretary_content)
    
    return FileResponse(secretary_path, media_type='text/html')

@app.post('/schedule')
async def schedule(payload: dict, username: str = Depends(require_chair_role)):
    print('Received request for /schedule')
    subjects = load_subjects_from_db()
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()

    semester_filter = payload.get('semester')

    num_sections_year_1 = payload.get('numSectionsYear1', 0)
    num_sections_year_2 = payload.get('numSectionsYear2', 0)
    num_sections_year_3 = payload.get('numSectionsYear3', 0)
    num_sections_year_4 = payload.get('numSectionsYear4', 0)

    desired_sections_per_year = {
        1: num_sections_year_1,
        2: num_sections_year_2,
        3: num_sections_year_3,
        4: num_sections_year_4,
    }

    print(f"Filtering for semester: {semester_filter}. Desired sections per year: {desired_sections_per_year}")

    try:
        if semester_filter:
            # Convert semester_filter to int for comparison
            semester_filter_int = int(semester_filter) if semester_filter else None
            available_years = set(
                int(s.get('year_level', 0)) for s in subjects
                if int(s.get('semester', 0)) == semester_filter_int and s.get('year_level')
            )
        else:
            available_years = set(
                int(s.get('year_level', 0)) for s in subjects if s.get('year_level')
            )
    except Exception as e:
        print(f"Error in year filtering: {e}")
        available_years = {1, 2, 3, 4}

    print(f"Available years: {available_years}")
    print(f"Desired sections per year: {desired_sections_per_year}")
    
    filtered_desired_sections_per_year = {
        year: count for year, count in desired_sections_per_year.items()
        if count and (year in available_years)
    }
    
    print(f"Filtered desired sections: {filtered_desired_sections_per_year}")

    if not filtered_desired_sections_per_year:
        print('Scheduler: No applicable year levels for the selected semester based on requested sections. Returning empty schedule.')
        return JSONResponse(content=[])

    result = generate_schedule(subjects, teachers, rooms, semester_filter, filtered_desired_sections_per_year)
    return JSONResponse(content=result)

def _ensure_saved_dir():
    saved_dir = os.path.join('.', 'saved_schedules')
    os.makedirs(saved_dir, exist_ok=True)
    return saved_dir

def _safe_filename_part(name: str) -> str:
    return ''.join(c for c in (name or '') if c.isalnum() or c in ('-', '_'))[:64] or 'schedule'

def _list_saved_summaries():
    saved_dir = _ensure_saved_dir()
    items = []
    for fname in os.listdir(saved_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(saved_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items.append({
                'id': data.get('id') or fname[:-5],
                'name': data.get('name') or fname[:-5],
                'semester': data.get('semester'),
                'created_at': data.get('created_at'),
                'count': len(data.get('schedule') or []),
            })
        except Exception:
            # Skip unreadable files
            continue
    # Sort newest first
    items.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return items

@app.get('/saved_schedules')
async def saved_schedules(username: str = Depends(require_chair_role)):
    return JSONResponse(content=_list_saved_summaries())

@app.post('/save_schedule')
async def save_schedule(payload: dict, username: str = Depends(require_chair_role)):
    schedule = payload.get('schedule')
    if not isinstance(schedule, list) or len(schedule) == 0:
        raise HTTPException(status_code=400, detail='No schedule provided to save')
    name = payload.get('name') or 'schedule'
    semester = payload.get('semester')
    created_at = datetime.utcnow().isoformat()
    uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    saved_dir = _ensure_saved_dir()
    safe_name = _safe_filename_part(name)
    filename = f"{uid}_{safe_name}.json"
    path = os.path.join(saved_dir, filename)
    data = {
        'id': uid,
        'name': name,
        'semester': semester,
        'created_at': created_at,
        'schedule': schedule,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Create approval request for the saved schedule
    try:
        from database import create_schedule_approval
        create_schedule_approval(uid, name, semester, username)
        print(f"✅ Schedule approval request created for {uid}")
    except Exception as e:
        print(f"⚠️ Could not create approval request: {e}")
    
    return JSONResponse(content={'id': uid, 'name': name, 'semester': semester, 'created_at': created_at})

@app.get('/load_schedule')
async def load_schedule(id: str, username: str = Depends(require_chair_role)):
    saved_dir = _ensure_saved_dir()
    # Find file by id prefix
    candidates = [fn for fn in os.listdir(saved_dir) if fn.startswith(id) and fn.endswith('.json')]
    if not candidates:
        raise HTTPException(status_code=404, detail='Saved schedule not found')
    fpath = os.path.join(saved_dir, candidates[0])
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return JSONResponse(content=data)

@app.get('/download_schedule')
async def download_schedule(id: str | None = None, semester: str | None = None, username: str = Depends(require_chair_role)):
    # Determine which schedule to download
    schedule_data = None
    if id:
        saved_dir = _ensure_saved_dir()
        candidates = [fn for fn in os.listdir(saved_dir) if fn.startswith(id) and fn.endswith('.json')]
        if not candidates:
            raise HTTPException(status_code=404, detail='Saved schedule not found')
        with open(os.path.join(saved_dir, candidates[0]), 'r', encoding='utf-8') as f:
            saved = json.load(f)
            schedule_data = saved.get('schedule') or []
    elif semester:
        # Pick most recent for semester
        summaries = [s for s in _list_saved_summaries() if str(s.get('semester')) == str(semester)]
        if summaries:
            chosen = summaries[0]
            return await download_schedule(id=chosen['id'])
        else:
            raise HTTPException(status_code=404, detail='No saved schedule found for that semester')
    else:
        raise HTTPException(status_code=400, detail='Specify id or semester')

    fieldnames = ['section_id', 'subject_code', 'subject_name', 'type', 'teacher_name', 'room_id', 'day', 'start_time_slot', 'duration_slots']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in schedule_data:
        writer.writerow({k: row.get(k, '') for k in fieldnames})
    csv_bytes = output.getvalue().encode('utf-8')
    headers = {"Content-Disposition": "attachment; filename=schedule.csv"}
    return Response(content=csv_bytes, media_type='text/csv', headers=headers)

@app.get('/data/{filename}')
async def get_data(filename: str, username: str = Depends(require_chair_role)):
    try:
        if filename in ['cs_curriculum', 'subjects']:
            data = load_subjects_from_db()
        elif filename == 'teachers':
            data = load_teachers_from_db()
        elif filename == 'rooms':
            data = load_rooms_from_db()
        elif filename == 'sections':
            data = load_sections_from_db()
        else:
            raise HTTPException(status_code=404, detail='Data type not found')
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/upload/{filename}')
async def upload_file(filename: str, file: UploadFile = File(...), username: str = Depends(require_chair_role)):
    """Accept CSV uploads and upsert into database for supported datasets."""
    try:
        content = await file.read()
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        # Normalize keys to lowercase for robust mapping
        rows = []
        for raw in reader:
            rows.append({ (k or '').strip().lower(): (v or '').strip() for k, v in raw.items() })
        if not rows:
            raise HTTPException(status_code=400, detail='Empty CSV file')

        def safe_int(val):
            try:
                v = (val or '').strip()
                if v == '':
                    return 0
                # handle floats like '2.0'
                if '.' in v:
                    return int(float(v))
                return int(v)
            except Exception:
                return 0

        if filename in ['cs_curriculum', 'subjects']:
            from database import add_subject
            for r in rows:
                subject = {
                    'subject_code': r.get('subject_code') or r.get('code') or '',
                    'subject_name': r.get('subject_name') or r.get('name') or '',
                    'lecture_hours_per_week': safe_int(r.get('lecture_hours_per_week') or r.get('lec_hours')),
                    'lab_hours_per_week': safe_int(r.get('lab_hours_per_week') or r.get('lab_hours')),
                    'units': safe_int(r.get('units')),
                    'semester': (lambda x: (safe_int(x) or None))(r.get('semester')),
                    'program_specialization': (r.get('program_specialization') or r.get('program') or None),
                    'year_level': (lambda x: (safe_int(x) or None))(r.get('year_level') or r.get('year')),
                }
                if not subject['subject_code']:
                    continue
                add_subject(subject)
            return JSONResponse(content={'message': 'Subjects CSV uploaded successfully'})
        elif filename == 'teachers':
            from database import add_teacher
            for r in rows:
                teacher = {
                    'teacher_id': r.get('teacher_id') or r.get('id') or '',
                    'teacher_name': r.get('teacher_name') or r.get('name') or '',
                    'can_teach': r.get('can_teach') or r.get('subjects') or '',
                }
                if not teacher['teacher_id']:
                    continue
                add_teacher(teacher)
            return JSONResponse(content={'message': 'Teachers CSV uploaded successfully'})
        elif filename == 'rooms':
            from database import add_room
            for r in rows:
                val = (str(r.get('is_laboratory') or r.get('lab') or '').strip().lower())
                is_lab = val in ['1', 'true', 'yes', 'y']
                room = {
                    'room_id': r.get('room_id') or r.get('id') or '',
                    'room_name': (r.get('room_name') or r.get('name') or '') or (r.get('room_id') or ''),
                    'is_laboratory': is_lab,
                }
                if not room['room_id']:
                    continue
                add_room(room)
            return JSONResponse(content={'message': 'Rooms CSV uploaded successfully'})
        elif filename == 'sections':
            from database import add_section
            for r in rows:
                section = {
                    'section_id': r.get('section_id') or r.get('id') or '',
                    'subject_code': (r.get('subject_code') or '') or None,
                    'year_level': (lambda x: (safe_int(x) or None))(r.get('year_level') or r.get('year')),
                    'num_meetings_non_lab': safe_int(r.get('num_meetings_non_lab') or r.get('meetings')),
                }
                if not section['section_id']:
                    continue
                add_section(section)
            return JSONResponse(content={'message': 'Sections CSV uploaded successfully'})
        else:
            raise HTTPException(status_code=404, detail='Unsupported upload type')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Database management endpoints (Chair role required)
@app.post('/api/subjects')
async def add_subject_endpoint(subject_data: dict, username: str = Depends(require_chair_role)):
    """Add a new subject to the database"""
    try:
        from database import add_subject
        add_subject(subject_data)
        return JSONResponse(content={'message': 'Subject added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/subjects/{subject_code}')
async def update_subject_endpoint(subject_code: str, subject_data: dict, username: str = Depends(require_chair_role)):
    """Update an existing subject in the database"""
    try:
        from database import update_subject
        subject_data['subject_code'] = subject_code
        update_subject(subject_code, subject_data)
        return JSONResponse(content={'message': 'Subject updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/subjects/{subject_code}')
async def delete_subject_endpoint(subject_code: str, username: str = Depends(require_chair_role)):
    """Delete a subject from the database"""
    try:
        from database import delete_subject
        delete_subject(subject_code)
        return JSONResponse(content={'message': 'Subject deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/teachers')
async def add_teacher_endpoint(teacher_data: dict, username: str = Depends(require_chair_role)):
    """Add a new teacher to the database"""
    try:
        from database import add_teacher
        add_teacher(teacher_data)
        return JSONResponse(content={'message': 'Teacher added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/teachers/{teacher_id}')
async def update_teacher_endpoint(teacher_id: str, teacher_data: dict, username: str = Depends(require_chair_role)):
    """Update an existing teacher in the database"""
    try:
        from database import update_teacher
        teacher_data['teacher_id'] = teacher_id
        update_teacher(teacher_id, teacher_data)
        return JSONResponse(content={'message': 'Teacher updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/teachers/{teacher_id}')
async def delete_teacher_endpoint(teacher_id: str, username: str = Depends(require_chair_role)):
    """Delete a teacher from the database"""
    try:
        from database import delete_teacher
        delete_teacher(teacher_id)
        return JSONResponse(content={'message': 'Teacher deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/rooms')
async def add_room_endpoint(room_data: dict, username: str = Depends(require_chair_role)):
    """Add a new room to the database"""
    try:
        from database import add_room
        add_room(room_data)
        return JSONResponse(content={'message': 'Room added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/rooms/{room_id}')
async def update_room_endpoint(room_id: str, room_data: dict, username: str = Depends(require_chair_role)):
    """Update an existing room in the database"""
    try:
        from database import update_room
        room_data['room_id'] = room_id
        update_room(room_id, room_data)
        return JSONResponse(content={'message': 'Room updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/rooms/{room_id}')
async def delete_room_endpoint(room_id: str, username: str = Depends(require_chair_role)):
    """Delete a room from the database"""
    try:
        from database import delete_room
        delete_room(room_id)
        return JSONResponse(content={'message': 'Room deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sections CRUD
@app.post('/api/sections')
async def add_section_endpoint(section_data: dict, username: str = Depends(require_chair_role)):
    try:
        from database import add_section
        add_section(section_data)
        return JSONResponse(content={'message': 'Section added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/sections/{section_id}')
async def update_section_endpoint(section_id: str, section_data: dict, username: str = Depends(require_chair_role)):
    try:
        from database import update_section
        section_data['section_id'] = section_id
        update_section(section_id, section_data)
        return JSONResponse(content={'message': 'Section updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/sections/{section_id}')
async def delete_section_endpoint(section_id: str, username: str = Depends(require_chair_role)):
    try:
        from database import delete_section
        delete_section(section_id)
        return JSONResponse(content={'message': 'Section deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/migrate')
async def migrate_data_endpoint(username: str = Depends(require_chair_role)):
    """Trigger data migration from CSV to database"""
    try:
        from database import db
        db.migrate_from_csv()
        return JSONResponse(content={'message': 'Migration completed successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Schedule approval endpoints
@app.post('/api/schedule_approval')
async def create_schedule_approval_endpoint(payload: dict, username: str = Depends(require_chair_role)):
    """Create a schedule approval request"""
    try:
        from database import create_schedule_approval
        schedule_id = payload.get('schedule_id')
        schedule_name = payload.get('schedule_name', '')
        semester = payload.get('semester')
        
        if not schedule_id:
            raise HTTPException(status_code=400, detail="Schedule ID is required")
        
        success = create_schedule_approval(schedule_id, schedule_name, semester, username)
        if success:
            return JSONResponse(content={'message': 'Schedule approval request created successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to create approval request")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/pending_schedules')
async def get_pending_schedules_endpoint(username: str = Depends(require_dean_role)):
    """Get all pending schedule approvals for dean"""
    try:
        from database import get_pending_schedules
        schedules = get_pending_schedules()
        return JSONResponse(content=schedules)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/approved_schedules')
async def get_approved_schedules_endpoint(username: str = Depends(require_dean_or_secretary_role)):
    """Get all approved schedules for dean and secretary"""
    try:
        from database import get_approved_schedules
        schedules = get_approved_schedules()
        return JSONResponse(content=schedules)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/approve_schedule/{schedule_id}')
async def approve_schedule_endpoint(schedule_id: str, payload: dict, username: str = Depends(require_dean_role)):
    """Approve a schedule"""
    try:
        from database import approve_schedule
        comments = payload.get('comments', '')
        success = approve_schedule(schedule_id, username, comments)
        if success:
            return JSONResponse(content={'message': 'Schedule approved successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to approve schedule")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/reject_schedule/{schedule_id}')
async def reject_schedule_endpoint(schedule_id: str, payload: dict, username: str = Depends(require_dean_role)):
    """Reject a schedule"""
    try:
        from database import reject_schedule
        comments = payload.get('comments', '')
        success = reject_schedule(schedule_id, username, comments)
        if success:
            return JSONResponse(content={'message': 'Schedule rejected successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to reject schedule")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/schedule_approval_status/{schedule_id}')
async def get_schedule_approval_status_endpoint(schedule_id: str, username: str = Depends(verify_token)):
    """Get approval status for a specific schedule"""
    try:
        from database import get_schedule_approval_status
        status = get_schedule_approval_status(schedule_id)
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Notification endpoints
@app.get('/api/notifications')
async def get_notifications_endpoint(username: str = Depends(verify_token)):
    """Get notifications for the current user"""
    try:
        from database import get_user_notifications, get_user_id_by_username
        user_id = get_user_id_by_username(username)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        
        notifications = get_user_notifications(user_id)
        return JSONResponse(content=notifications)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/notifications/unread')
async def get_unread_notifications_endpoint(username: str = Depends(verify_token)):
    """Get unread notifications for the current user"""
    try:
        from database import get_user_notifications, get_user_id_by_username
        user_id = get_user_id_by_username(username)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        
        notifications = get_user_notifications(user_id, unread_only=True)
        return JSONResponse(content=notifications)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/notifications/{notification_id}/read')
async def mark_notification_read_endpoint(notification_id: int, username: str = Depends(verify_token)):
    """Mark a notification as read"""
    try:
        from database import mark_notification_read
        success = mark_notification_read(notification_id)
        if success:
            return JSONResponse(content={'message': 'Notification marked as read'})
        else:
            raise HTTPException(status_code=500, detail="Failed to mark notification as read")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=5000, reload=True)
