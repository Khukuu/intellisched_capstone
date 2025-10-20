from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import logging
# Import modules only when needed to avoid startup errors
# from scheduler import generate_schedule
# from database import db, load_subjects_from_db, etc.
import os
import io
import json
import csv
from datetime import datetime, timedelta
import jwt  # PyJWT is installed as 'jwt'
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, continue without it
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intellisched.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Maintenance Mode Middleware
class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if maintenance mode is enabled
        try:
            maintenance_mode = get_system_setting('maintenance_mode', 'false')
            if maintenance_mode.lower() == 'true':
                # Allow access to maintenance page, login, auth endpoints, admin pages, and static files
                # CRITICAL: Always allow login and auth endpoints so admin can login to disable maintenance
                # BLOCK: All other user dashboards (chair, dean, secretary) should be blocked
                if (request.url.path in ['/maintenance', '/login', '/register', '/admin', '/static/maintenance.html'] or
                    request.url.path.startswith('/api/maintenance/') or
                    request.url.path.startswith('/api/auth/') or
                    request.url.path.startswith('/auth/') or  # Allow /auth/login endpoint
                    request.url.path.startswith('/api/system/') or
                    request.url.path.startswith('/api/admin/') or
                    request.url.path.startswith('/static/')):
                    response = await call_next(request)
                    return response
                
                # Block access to user-specific dashboards and APIs during maintenance
                blocked_paths = ['/chair', '/dean', '/secretary', '/saved-schedules']
                blocked_api_prefixes = ['/api/schedules', '/api/data', '/api/notifications', '/api/pending_schedules', 
                                      '/api/saved_schedules']
                
                # Check if accessing blocked dashboard
                if request.url.path in blocked_paths:
                    return RedirectResponse(url="/maintenance", status_code=302)
                
                # Check if accessing blocked API endpoints
                for prefix in blocked_api_prefixes:
                    if request.url.path.startswith(prefix):
                        return JSONResponse(
                            status_code=503,
                            content={"detail": "System is under maintenance", "maintenance_mode": True}
                        )
                
                # Check if user is admin (bypass maintenance mode)
                # Check both Authorization header and cookies for admin token
                admin_bypass = False
                
                # Check Authorization header
                try:
                    auth_header = request.headers.get('authorization')
                    if auth_header and auth_header.startswith('Bearer '):
                        token = auth_header.split(' ')[1]
                        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
                        username = payload.get("sub")
                        if username:
                            user = db.get_user_by_username(username)
                            if user and user.get('role') == 'admin':
                                admin_bypass = True
                except:
                    pass
                
                # Check cookies for admin token (for frontend requests)
                try:
                    auth_cookie = request.cookies.get('authToken')
                    if auth_cookie:
                        payload = jwt.decode(auth_cookie, "your-secret-key", algorithms=["HS256"])
                        username = payload.get("sub")
                        if username:
                            user = db.get_user_by_username(username)
                            if user and user.get('role') == 'admin':
                                admin_bypass = True
                except:
                    pass
                
                # If admin user detected, allow access
                if admin_bypass:
                    response = await call_next(request)
                    return response
                
                # Redirect to maintenance page
                if request.url.path.startswith('/api/'):
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "System is under maintenance", "maintenance_mode": True}
                    )
                else:
                    return RedirectResponse(url="/maintenance", status_code=302)
        except Exception as e:
            logger.error(f"Error in maintenance middleware: {e}")
        
        response = await call_next(request)
        return response

# Add maintenance middleware
app.add_middleware(MaintenanceMiddleware)

# Mount static files with no-cache headers
from fastapi.staticfiles import StaticFiles

class NoCacheStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount('/static', NoCacheStaticFiles(directory='static'), name='static')

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')  # Use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

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
        
        logger.info(f"Login attempt for user: {username}")
        
        # Verify credentials
        user = db.verify_user_credentials(username, password)
        if not user:
            logger.warning(f"Login failed for user {username}: Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        logger.info(f"Login successful for user {username}")
        
        # Record user activity
        try:
            from database import get_user_id_by_username, record_user_activity
            user_id = get_user_id_by_username(username)
            if user_id:
                record_user_activity(user_id, "login", f"User {username} logged in successfully")
        except Exception as e:
            logger.warning(f"Could not record login activity: {e}")
        
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
            "role": user.get('role'),
            "status": user.get('status', 'active')
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

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
        role = (payload.get('role') or '').strip()

        # Validation
        if not username or not password or not full_name or not email or not role:
            raise HTTPException(status_code=400, detail="All fields are required")

        # Validate role
        valid_roles = ['dean', 'chair', 'secretary']
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role selected")

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        # Validate password strength
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        
        # Check for at least one uppercase, one lowercase, and one digit
        if not re.search(r'[A-Z]', password):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            raise HTTPException(status_code=400, detail="Password must contain at least one digit")

        # Check if username already exists
        existing_username = db.get_user_by_username(username)
        if existing_username:
            raise HTTPException(status_code=409, detail="Username already exists")

        # Check if email already exists
        if check_email_exists(email):
            raise HTTPException(status_code=409, detail="Email already exists")

        # Create user with pending status
        ok = db.create_user({
            'username': username,
            'password': password,
            'full_name': full_name,
            'email': email,
            'role': role,
            'status': 'pending'
        })
        if not ok:
            raise HTTPException(status_code=500, detail="Could not create user")

        return {
            "message": "Account created successfully. Your account is pending approval from an administrator. You will receive an email notification once approved.",
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/health')
async def health_check():
    """Health check endpoint to test database connectivity"""
    try:
        # Simple health check first
        return {"status": "healthy", "message": "Application is running"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Application error: {str(e)}"}

@app.get('/health/database')
async def health_check_database():
    """Detailed health check endpoint to test database connectivity"""
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

@app.get('/status')
async def status():
    """Simple status endpoint for Railway healthcheck"""
    return {"status": "ok", "message": "IntelliSched is running"}

@app.get('/maintenance')
async def maintenance_page():
    """Serve maintenance page when system is under maintenance"""
    maintenance_path = os.path.join('static', 'maintenance.html')
    if os.path.exists(maintenance_path):
        return FileResponse(maintenance_path)
    else:
        raise HTTPException(status_code=404, detail="Maintenance page not found")

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
        
        with open(dean_path, 'w', encoding='utf-8') as f:
            f.write(dean_content)
    
    return FileResponse(dean_path, media_type='text/html')

@app.get('/secretary')
async def secretary_dashboard():
    """Secretary dashboard for viewing, editing, and deleting schedules"""
    secretary_path = os.path.join('static', 'secretary.html')
    if not os.path.exists(secretary_path):
        # Create secretary dashboard page
        
        
        with open(secretary_path, 'w', encoding='utf-8') as f:
            f.write(secretary_content)
    
    return FileResponse(secretary_path, media_type='text/html')

@app.get('/saved-schedules')
async def saved_schedules_page():
    """Saved schedules management page for chair users"""
    saved_schedules_path = os.path.join('static', 'saved-schedules.html')
    if not os.path.exists(saved_schedules_path):
        raise HTTPException(status_code=404, detail='Saved schedules page not found')
    return FileResponse(saved_schedules_path, media_type='text/html')


@app.post('/schedule')
async def schedule(payload: dict, username: str = Depends(require_chair_role)):
    logger.info('Received request for /schedule')
    
    # Get program selection (default to CS for backward compatibility)
    programs = payload.get('programs', ['CS'])
    if isinstance(programs, str):
        programs = [programs]  # Handle single program as string
    logger.info(f'Scheduling for programs: {programs}')
    
    subjects = load_subjects_from_db(programs)
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()

    semester_filter = payload.get('semester')

    # Handle program-specific section counts
    program_sections = payload.get('programSections', {})
    
    # If old format is used, convert to new format
    if not program_sections and any(key.startswith('numSectionsYear') for key in payload.keys()):
        # Legacy format - use same sections for all programs
        num_sections_year_1 = payload.get('numSectionsYear1', 0)
        num_sections_year_2 = payload.get('numSectionsYear2', 0)
        num_sections_year_3 = payload.get('numSectionsYear3', 0)
        num_sections_year_4 = payload.get('numSectionsYear4', 0)
        
        for program in programs:
            program_sections[program] = {
                1: num_sections_year_1,
                2: num_sections_year_2,
                3: num_sections_year_3,
                4: num_sections_year_4
            }
    
    # Ensure all selected programs have section counts
    for program in programs:
        if program not in program_sections:
            program_sections[program] = {1: 1, 2: 1, 3: 1, 4: 1}  # Default to 1 section per year

    logger.info(f"Filtering for semester: {semester_filter}. Program sections: {program_sections}")

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
        logger.warning(f"Error in year filtering: {e}")
        available_years = {1, 2, 3, 4}

    logger.info(f"Available years: {available_years}")
    logger.info(f"Program sections: {program_sections}")
    
    # Filter program sections to only include years with available curriculum
    # But don't reject if some years don't have curriculum - just warn and adjust
    filtered_program_sections = {}
    has_valid_sections = False
    adjusted_years = []
    
    for program, sections in program_sections.items():
        filtered_sections = {}
        for year, count in sections.items():
            year_int = int(year)
            if count and (year_int in available_years):
                filtered_sections[year_int] = count
                has_valid_sections = True
            elif count and (year_int not in available_years):
                # Year requested but no curriculum available
                adjusted_years.append(f"{program} Year {year}")
                logger.warning(f"No curriculum available for {program} Year {year} in semester {semester_filter}")
        
        if filtered_sections:
            filtered_program_sections[program] = filtered_sections
    
    logger.info(f"Filtered program sections: {filtered_program_sections}")
    
    # Log adjustments made
    if adjusted_years:
        logger.info(f"Adjusted sections for years without curriculum: {adjusted_years}")

    if not has_valid_sections:
        logger.warning('Scheduler: No applicable year levels for the selected semester based on requested sections. Returning empty schedule.')
        return JSONResponse(content=[])

    result = generate_schedule(subjects, teachers, rooms, semester_filter, filtered_program_sections, programs)

    # Record user activity
    try:
        from database import get_user_id_by_username, record_user_activity
        user_id = get_user_id_by_username(username)
        if user_id:
            record_user_activity(user_id, "schedule_generation", f"Generated schedule for programs: {programs}")
    except Exception as e:
        logger.warning(f"Could not record schedule generation activity: {e}")

    # If request explicitly asks to persist as pending schedule (Chair flow)
    if payload.get('persist', False):
        try:
            name = (payload.get('name') or 'Generated Schedule')
            semester_int = int(semester_filter) if semester_filter else None
            # Create synthetic id based on timestamp like saved schedules
            uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            created = create_schedule_approval(uid, name, semester_int or 0, username)
            if not created:
                logger.warning('Failed to create schedule approval record')
            return JSONResponse(content={
                'id': uid,
                'name': name,
                'status': 'pending',
                'semester': semester_int,
                'schedule': result,
            })
        except Exception as e:
            # Fall back to returning just the result
            logger.warning(f"Persist schedule failed: {e}")
            return JSONResponse(content=result)

    return JSONResponse(content=result)

def _ensure_saved_dir():
    """Ensure the saved_schedules directory exists and is accessible"""
    try:
        saved_dir = os.path.join('.', 'saved_schedules')
        os.makedirs(saved_dir, exist_ok=True)
        
        # Verify the directory was created and is accessible
        if not os.path.exists(saved_dir):
            logger.error(f"Failed to create saved_schedules directory: {saved_dir}")
            raise Exception(f"Cannot create saved_schedules directory")
        
        # Test if we can write to the directory
        test_file = os.path.join(saved_dir, '.test_write')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            logger.error(f"Cannot write to saved_schedules directory: {e}")
            raise Exception(f"Cannot write to saved_schedules directory: {e}")
        
        logger.info(f"Saved schedules directory ready: {saved_dir}")
        return saved_dir
        
    except Exception as e:
        logger.error(f"Error ensuring saved_schedules directory: {e}")
        raise

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
            # Get approval details
            approval_data = get_schedule_approval_status(data.get('id') or '')
            
            items.append({
                'id': data.get('id') or fname[:-5],
                'name': data.get('name') or fname[:-5],
                'semester': data.get('semester'),
                'created_at': data.get('created_at'),
                'count': len(data.get('schedule') or []),
                # include full approval details if exists
                'status': approval_data.get('status') if approval_data else None,
                'approved_at': approval_data.get('approved_at') if approval_data else None,
                'approved_by': approval_data.get('approved_by') if approval_data else None,
                'comments': approval_data.get('comments') if approval_data else None,
            })
        except Exception:
            # Skip unreadable files
            continue
    # Sort newest first
    items.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return items
@app.post('/schedules/generate')
async def generate_and_submit_schedule(payload: dict, username: str = Depends(require_chair_role)):
    """Chair generates and submits schedule for approval (status=pending)."""
    # Prefer client-provided schedule when available; fall back to server generation
    client_schedule = payload.get('schedule')
    programs = payload.get('programs', ['CS'])
    if isinstance(programs, str):
        programs = [programs]  # Handle single program as string
    subjects = load_subjects_from_db(programs)
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()
    semester_filter = payload.get('semester')

    # Handle program-specific section counts (same logic as main endpoint)
    program_sections = payload.get('programSections', {})
    
    # If old format is used, convert to new format
    if not program_sections and any(key.startswith('numSectionsYear') for key in payload.keys()):
        # Legacy format - use same sections for all programs
        num_sections_year_1 = payload.get('numSectionsYear1', 0)
        num_sections_year_2 = payload.get('numSectionsYear2', 0)
        num_sections_year_3 = payload.get('numSectionsYear3', 0)
        num_sections_year_4 = payload.get('numSectionsYear4', 0)
        
        for program in programs:
            program_sections[program] = {
                1: num_sections_year_1,
                2: num_sections_year_2,
                3: num_sections_year_3,
                4: num_sections_year_4
            }
    
    # Ensure all selected programs have section counts
    for program in programs:
        if program not in program_sections:
            program_sections[program] = {1: 1, 2: 1, 3: 1, 4: 1}  # Default to 1 section per year

    result = client_schedule if isinstance(client_schedule, list) and len(client_schedule) > 0 else generate_schedule(subjects, teachers, rooms, semester_filter, program_sections, programs)
    name = (payload.get('name') or 'Generated Schedule')
    semester_int = int(semester_filter) if semester_filter else None
    uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    # Persist generated schedule to database so Dean can view by ID
    try:
        from database import save_schedule_to_db
        success = save_schedule_to_db(uid, name, semester_int or 0, username, result)
        if not success:
            logger.warning(f"Could not save schedule to database for {uid}")
    except Exception as e:
        # Non-fatal: still proceed with approval record
        logger.warning(f"Could not persist schedule to database for {uid}: {e}")

    # Create approval record
    create_schedule_approval(uid, name, semester_int or 0, username)
    return JSONResponse(content={'id': uid, 'name': name, 'status': 'pending', 'semester': semester_int, 'schedule': result})

@app.get('/schedules/pending')
async def list_pending_schedules(username: str = Depends(require_role(['dean']))):
    """Dean views all pending schedules (grouping is done client-side)."""
    items = get_pending_schedules()
    return JSONResponse(content=items)


@app.post('/schedules/{schedule_id}/approve')
async def approve_schedule_endpoint(schedule_id: str, payload: dict = None, username: str = Depends(require_role(['dean']))):
    comments = (payload or {}).get('comments') if isinstance(payload, dict) else None
    ok = approve_schedule(schedule_id, username, comments)
    if not ok:
        raise HTTPException(status_code=500, detail='Failed to approve schedule')
    return JSONResponse(content={'message': 'Schedule approved', 'id': schedule_id})

@app.post('/schedules/{schedule_id}/deny')
async def deny_schedule_endpoint(schedule_id: str, payload: dict = None, username: str = Depends(require_role(['dean']))):
    comments = (payload or {}).get('comments') if isinstance(payload, dict) else None
    ok = reject_schedule(schedule_id, username, comments)
    if not ok:
        raise HTTPException(status_code=500, detail='Failed to deny schedule')
    return JSONResponse(content={'message': 'Schedule denied', 'id': schedule_id})

# Aliases for dean.html
@app.post('/api/approve_schedule/{schedule_id}')
async def approve_schedule_endpoint_alias(schedule_id: str, payload: dict, username: str = Depends(require_role(['dean']))):
    return await approve_schedule_endpoint(schedule_id, payload, username)  # type: ignore

@app.post('/api/reject_schedule/{schedule_id}')
async def reject_schedule_endpoint_alias(schedule_id: str, payload: dict, username: str = Depends(require_role(['dean']))):
    return await deny_schedule_endpoint(schedule_id, payload, username)  # type: ignore


@app.get('/saved_schedules')
async def saved_schedules(username: str = Depends(require_chair_role)):
    """Get all saved schedules from database"""
    try:
        from database import list_saved_schedules_from_db
        schedules = list_saved_schedules_from_db(username)
        logger.info(f"Retrieved {len(schedules)} saved schedules for user {username}")
        return JSONResponse(content=schedules)
    except Exception as e:
        logger.error(f"Error retrieving saved schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.delete('/saved_schedules/{schedule_id}')
async def delete_saved_schedule(schedule_id: str, username: str = Depends(require_chair_role)):
    """Delete a saved schedule from database and remove approval record if exists."""
    try:
        logger.info(f"Deleting saved schedule {schedule_id} for user {username}")
        
        # Delete from database
        from database import delete_schedule_from_db
        success = delete_schedule_from_db(schedule_id)
        
        if not success:
            raise HTTPException(status_code=500, detail='Failed to delete schedule from database')

        # Delete the schedule approval record so it's no longer visible to dean
        logger.info(f"Attempting to delete schedule approval record for {schedule_id}")
        approval_deleted = delete_schedule_approval(schedule_id)
        if approval_deleted:
            logger.info(f"Successfully deleted schedule approval record for {schedule_id}")
        else:
            logger.warning(f"Could not delete schedule approval record for {schedule_id}")
            # Don't fail the entire operation if approval record deletion fails
        
        # Verify deletion by checking if record still exists
        remaining_status = get_schedule_approval_status(schedule_id)
        if remaining_status:
            logger.error(f"Schedule approval record still exists after deletion attempt: {remaining_status}")
            logger.error(f"Schedule {schedule_id} will still be visible to dean")
        else:
            logger.info(f"Confirmed: Schedule approval record successfully deleted for {schedule_id}")
            logger.info(f"Schedule {schedule_id} should no longer be visible to dean")

        return JSONResponse(content={'message': 'Saved schedule deleted', 'id': schedule_id})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved schedule {schedule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.delete('/api/schedule/{schedule_id}')
async def delete_schedule_endpoint(schedule_id: str, username: str = Depends(require_role(['dean', 'chair']))):
    """Delete a schedule (both file and approval record) - accessible by dean and chair"""
    # Check if schedule exists
    approval_status = get_schedule_approval_status(schedule_id)
    if not approval_status:
        raise HTTPException(status_code=404, detail='Schedule not found')
    
    # Check if user has permission to delete this schedule
    user_role = db.get_user_by_username(username).get('role')
    schedule_status = approval_status.get('status')
    
    # Chair can delete any schedule they created or any pending schedule
    # Dean can delete any approved schedule
    if user_role == 'chair':
        if approval_status.get('created_by') != username and schedule_status != 'pending':
            raise HTTPException(status_code=403, detail='You can only delete schedules you created or pending schedules')
    elif user_role == 'dean':
        if schedule_status != 'approved':
            raise HTTPException(status_code=403, detail='Dean can only delete approved schedules')
    
    # Delete the schedule file
    saved_dir = _ensure_saved_dir()
    candidates = [fn for fn in os.listdir(saved_dir) if fn.startswith(schedule_id) and fn.endswith('.json')]
    if candidates:
        fpath = os.path.join(saved_dir, candidates[0])
        try:
            os.remove(fpath)
            logger.info(f"Deleted schedule file: {fpath}")
        except Exception as e:
            logger.warning(f"Could not delete schedule file: {e}")
    
    # Delete the schedule approval record
    logger.info(f"Attempting to delete schedule approval record for {schedule_id}")
    approval_deleted = delete_schedule_approval(schedule_id)
    if approval_deleted:
        logger.info(f"Successfully deleted schedule approval record for {schedule_id}")
    else:
        logger.warning(f"Could not delete schedule approval record for {schedule_id}")
    
    return JSONResponse(content={'message': 'Schedule deleted successfully', 'id': schedule_id})

@app.post('/save_schedule')
async def save_schedule(payload: dict, username: str = Depends(require_chair_role)):
    """Save a schedule to the database"""
    try:
        schedule = payload.get('schedule')
        if not isinstance(schedule, list) or len(schedule) == 0:
            raise HTTPException(status_code=400, detail='No schedule provided to save')
        
        name = payload.get('name') or 'schedule'
        semester = payload.get('semester')
        created_at = datetime.utcnow().isoformat()
        uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        logger.info(f"Saving schedule {uid} for user {username}")
        
        # Save to database
        from database import save_schedule_to_db
        success = save_schedule_to_db(uid, name, semester, username, schedule)
        
        if not success:
            raise HTTPException(status_code=500, detail='Failed to save schedule to database')
        
        # Create approval request for the saved schedule
        try:
            from database import create_schedule_approval
            create_schedule_approval(uid, name, semester, username)
            logger.info(f"Schedule approval request created for {uid}")
        except Exception as e:
            logger.warning(f"Could not create approval request: {e}")
        
        return JSONResponse(content={'id': uid, 'name': name, 'semester': semester, 'created_at': created_at})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.get('/load_schedule')
async def load_schedule(id: str, username: str = Depends(require_chair_role)):
    """Load a saved schedule by ID from database"""
    try:
        logger.info(f"Loading schedule with ID: {id} for user: {username}")
        
        from database import load_schedule_from_db
        schedule_data = load_schedule_from_db(id)
        
        if not schedule_data:
            logger.warning(f"No saved schedule found with ID: {id}")
            raise HTTPException(status_code=404, detail=f'Saved schedule with ID {id} not found')
        
        logger.info(f"Successfully loaded schedule {id} with {len(schedule_data.get('schedule', []))} entries")
        return JSONResponse(content=schedule_data)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading schedule {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

# Dean view: fetch schedule details by id
@app.get('/api/schedule/{schedule_id}')
async def get_schedule_for_dean(schedule_id: str, username: str = Depends(require_dean_or_secretary_role)):
    """Allow Dean and Secretary to view a saved schedule by id. Only if the schedule approval record still exists."""
    try:
        # First check if the schedule approval record still exists
        approval_status = get_schedule_approval_status(schedule_id)
        if not approval_status:
            raise HTTPException(status_code=404, detail='Schedule not found or has been deleted')
        
        # Load schedule from database
        from database import load_schedule_from_db
        schedule_data = load_schedule_from_db(schedule_id)
        
        if not schedule_data:
            raise HTTPException(status_code=404, detail='Schedule data not found')
        
        return JSONResponse(content=schedule_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading schedule {schedule_id} for dean/secretary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')

@app.get('/download_schedule')
async def download_schedule(id: str | None = None, semester: str | None = None, username: str = Depends(require_role(['chair', 'dean']))):
    """Download a schedule as CSV"""
    try:
        # Determine which schedule to download
        schedule_data = None
        if id:
            from database import load_schedule_from_db
            schedule = load_schedule_from_db(id)
            if not schedule:
                raise HTTPException(status_code=404, detail='Saved schedule not found')
            schedule_data = schedule.get('schedule') or []
        elif semester:
            # Pick most recent for semester
            from database import list_saved_schedules_from_db
            summaries = list_saved_schedules_from_db()
            semester_schedules = [s for s in summaries if str(s.get('semester')) == str(semester)]
            if semester_schedules:
                chosen = semester_schedules[0]
                return await download_schedule(id=chosen['id'])
            else:
                raise HTTPException(status_code=404, detail='No saved schedule found for that semester')
        else:
            raise HTTPException(status_code=400, detail='Specify id or semester')

    # Helper function to calculate end time from start time slot and duration
    def calculate_time_range(start_time_slot, duration_slots):
        if not start_time_slot or not duration_slots:
            return start_time_slot or ''
        
        # Ensure duration_slots is an integer
        duration_slots = int(duration_slots) if duration_slots else 0
        
        # Parse start time (e.g., "07:00-07:30")
        start_time = start_time_slot.split('-')[0]  # Get "07:00"
        start_hour, start_minute = map(int, start_time.split(':'))
        
        # Calculate total minutes from start
        start_total_minutes = start_hour * 60 + start_minute
        
        # Duration is in 30-minute slots, so multiply by 30
        duration_minutes = duration_slots * 30
        
        # Calculate end time
        end_total_minutes = start_total_minutes + duration_minutes
        end_hour = end_total_minutes // 60
        end_minute = end_total_minutes % 60
        
        # Format end time with proper zero padding
        end_time = f"{end_hour:02d}:{end_minute:02d}"
        
        # Ensure both start and end times have proper formatting
        return f"{start_time}-{end_time}"
    
    fieldnames = ['section_id', 'subject_code', 'subject_name', 'type', 'teacher_name', 'room_id', 'day', 'time_range', 'duration_hours']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in schedule_data:
        # Calculate proper time range and duration in hours
        duration_slots = int(row.get('duration_slots', 0)) if row.get('duration_slots') else 0
        time_range = calculate_time_range(row.get('start_time_slot'), duration_slots)
        duration_hours = (duration_slots * 30) / 60
        
        # Create the CSV row with proper formatting
        csv_row = {
            'section_id': row.get('section_id', ''),
            'subject_code': row.get('subject_code', ''),
            'subject_name': row.get('subject_name', ''),
            'type': row.get('type', ''),
            'teacher_name': row.get('teacher_name', ''),
            'room_id': row.get('room_id', ''),
            'day': row.get('day', ''),
            'time_range': time_range,
            'duration_hours': f"{duration_hours:.1f}" if duration_hours > 0 else ''
        }
        writer.writerow(csv_row)
    csv_bytes = output.getvalue().encode('utf-8')
    headers = {"Content-Disposition": "attachment; filename=schedule.csv"}
    return Response(content=csv_bytes, media_type='text/csv', headers=headers)

@app.get('/data/{filename}')
async def get_data(filename: str, username: str = Depends(require_chair_role)):
    try:
        if filename in ['cs_curriculum', 'subjects']:
            data = load_subjects_from_db(['CS'])
        elif filename == 'it_curriculum':
            data = load_subjects_from_db(['IT'])
        elif filename == 'all_curriculum':
            data = load_subjects_from_db(['CS', 'IT'])
        elif filename == 'teachers':
            data = load_teachers_from_db()
        elif filename == 'rooms':
            data = load_rooms_from_db()
        elif filename == 'sections':
            data = load_sections_from_db()
        else:
            raise HTTPException(status_code=404, detail='Data type not found')
        return JSONResponse(content=data)
    except HTTPException:
        # Preserve original status codes (e.g., 401/403/404)
        raise
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
            return JSONResponse(content={'message': 'CS Curriculum CSV uploaded successfully'})
        elif filename == 'it_curriculum':
            from database import add_it_subject
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
                add_it_subject(subject)
            return JSONResponse(content={'message': 'IT Curriculum CSV uploaded successfully'})
        elif filename == 'teachers':
            from database import add_teacher
            added_count = 0
            for r in rows:
                teacher = {
                    'teacher_name': r.get('teacher_name') or r.get('name') or '',
                    'can_teach': r.get('can_teach') or r.get('subjects') or '',
                }
                if not teacher['teacher_name']:
                    continue
                teacher_id = add_teacher(teacher)
                added_count += 1
                logger.info(f"Added teacher '{teacher['teacher_name']}' with ID: {teacher_id}")
            return JSONResponse(content={'message': f'Teachers CSV uploaded successfully. Added {added_count} teachers.'})
        elif filename == 'rooms':
            from database import add_room
            added_count = 0
            for r in rows:
                val = (str(r.get('is_laboratory') or r.get('lab') or '').strip().lower())
                is_lab = val in ['1', 'true', 'yes', 'y']
                room = {
                    'room_name': (r.get('room_name') or r.get('name') or ''),
                    'is_laboratory': is_lab,
                }
                if not room['room_name']:
                    continue
                room_id = add_room(room)
                added_count += 1
                logger.info(f"Added room '{room['room_name']}' with ID: {room_id}")
            return JSONResponse(content={'message': f'Rooms CSV uploaded successfully. Added {added_count} rooms.'})
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

# IT Subjects API endpoints
@app.post('/api/it-subjects')
async def add_it_subject_endpoint(subject_data: dict, username: str = Depends(require_chair_role)):
    """Add a new IT subject to the database"""
    try:
        from database import add_it_subject
        add_it_subject(subject_data)
        return JSONResponse(content={'message': 'IT Subject added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/it-subjects/{subject_code}')
async def update_it_subject_endpoint(subject_code: str, subject_data: dict, username: str = Depends(require_chair_role)):
    """Update an existing IT subject in the database"""
    try:
        from database import update_it_subject
        subject_data['subject_code'] = subject_code
        update_it_subject(subject_code, subject_data)
        return JSONResponse(content={'message': 'IT Subject updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/it-subjects/{subject_code}')
async def delete_it_subject_endpoint(subject_code: str, username: str = Depends(require_chair_role)):
    """Delete an IT subject from the database"""
    try:
        from database import delete_it_subject
        delete_it_subject(subject_code)
        return JSONResponse(content={'message': 'IT Subject deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/teachers')
async def add_teacher_endpoint(teacher_data: dict, username: str = Depends(require_chair_role)):
    """Add a new teacher to the database"""
    try:
        from database import add_teacher
        teacher_id = add_teacher(teacher_data)
        logger.info(f"Teacher added successfully with ID: {teacher_id}")
        return JSONResponse(content={'message': 'Teacher added successfully', 'teacher_id': teacher_id})
    except Exception as e:
        logger.error(f"Error adding teacher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/teachers/{teacher_id}')
async def update_teacher_endpoint(teacher_id: str, teacher_data: dict, username: str = Depends(require_chair_role)):
    """Update an existing teacher in the database"""
    try:
        from database import update_teacher
        logger.info(f"Updating teacher {teacher_id} with data: {teacher_data}")
        update_teacher(teacher_id, teacher_data)
        return JSONResponse(content={'message': 'Teacher updated successfully'})
    except Exception as e:
        logger.error(f"Error updating teacher {teacher_id}: {e}", exc_info=True)
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
        room_id = add_room(room_data)
        logger.info(f"Room added successfully with ID: {room_id}")
        return JSONResponse(content={'message': 'Room added successfully', 'room_id': room_id})
    except Exception as e:
        logger.error(f"Error adding room: {e}", exc_info=True)
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
        logger.info(f"Dean requesting pending schedules. Found {len(schedules)} schedules")
        for schedule in schedules:
            logger.debug(f"  - Schedule ID: {schedule.get('schedule_id')}, Status: {schedule.get('status')}")
        return JSONResponse(content=schedules)
    except Exception as e:
        logger.error(f"Error getting pending schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/approved_schedules')
async def get_approved_schedules_endpoint(username: str = Depends(require_role(['dean', 'secretary', 'chair']))):
    """Get all approved schedules for dean, secretary, and chair"""
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

@app.get('/api/debug/all_schedules')
async def debug_all_schedules(username: str = Depends(require_dean_role)):
    """Debug endpoint to see all schedules in database"""
    try:
        from database import db
        query = "SELECT * FROM schedule_approvals ORDER BY created_at DESC"
        all_schedules = db.db.execute_query(query)
        logger.info(f"DEBUG: All schedules in database: {len(all_schedules)}")
        for schedule in all_schedules:
            logger.debug(f"  - ID: {schedule.get('schedule_id')}, Status: {schedule.get('status')}, Name: {schedule.get('schedule_name')}")
        return JSONResponse(content=all_schedules)
    except Exception as e:
        logger.error(f"DEBUG ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Notification endpoints
@app.get('/api/notifications')
async def get_notifications_endpoint(username: str = Depends(verify_token)):
    """Get notifications for the current user"""
    try:
        from database import get_user_notifications, get_user_id_by_username
        logger.info(f"Getting notifications for username: {username}")
        
        user_id = get_user_id_by_username(username)
        if not user_id:
            logger.error(f"User not found: {username}")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        logger.info(f"Retrieving notifications for user_id: {user_id}")
        notifications = get_user_notifications(user_id)
        logger.info(f"Found {len(notifications)} notifications for user_id: {user_id}")
        
        return JSONResponse(content=notifications)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting notifications for username {username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get('/api/notifications/unread')
async def get_unread_notifications_endpoint(username: str = Depends(verify_token)):
    """Get unread notifications for the current user"""
    try:
        from database import get_user_notifications, get_user_id_by_username
        logger.info(f"Getting unread notifications for username: {username}")
        
        user_id = get_user_id_by_username(username)
        if not user_id:
            logger.error(f"User not found: {username}")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        logger.info(f"Retrieving unread notifications for user_id: {user_id}")
        notifications = get_user_notifications(user_id, unread_only=True)
        logger.info(f"Found {len(notifications)} unread notifications for user_id: {user_id}")
        
        return JSONResponse(content=notifications)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting unread notifications for username {username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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

@app.delete('/api/notifications/{notification_id}')
async def delete_notification_endpoint(notification_id: int, username: str = Depends(verify_token)):
    """Delete a notification"""
    try:
        from database import delete_notification
        success = delete_notification(notification_id)
        if success:
            return JSONResponse(content={'message': 'Notification deleted successfully'})
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/debug-user')
async def debug_user_endpoint(username: str = Depends(verify_token)):
    """Debug endpoint to check user info"""
    try:
        from database import get_user_id_by_username
        logger.info(f"Debug: Checking user info for username: {username}")
        
        user_id = get_user_id_by_username(username)
        if not user_id:
            logger.error(f"Debug: User not found: {username}")
            return JSONResponse(content={'error': f'User "{username}" not found', 'user_id': None})
        
        logger.info(f"Debug: Found user_id: {user_id} for username: {username}")
        return JSONResponse(content={'username': username, 'user_id': user_id, 'status': 'found'})
    except Exception as e:
        logger.error(f"Debug: Error checking user info: {e}", exc_info=True)
        return JSONResponse(content={'error': str(e), 'username': username, 'user_id': None})

@app.get('/api/debug-database')
async def debug_database_endpoint(username: str = Depends(require_admin_role)):
    """Debug endpoint to check database tables and foreign key constraints"""
    try:
        # Check if all required tables exist
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('users', 'notifications', 'schedule_approvals', 'user_activity_log')
        ORDER BY table_name
        """
        
        tables = db.db.execute_query(tables_query)
        logger.info(f"Found {len(tables)} required tables: {[t['table_name'] for t in tables]}")
        
        # Check foreign key constraints
        fk_query = """
        SELECT 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY' 
        AND tc.table_name IN ('notifications', 'user_activity_log')
        """
        
        foreign_keys = db.db.execute_query(fk_query)
        logger.info(f"Found {len(foreign_keys)} foreign key constraints")
        
        return JSONResponse(content={
            'tables_found': [t['table_name'] for t in tables],
            'foreign_keys': foreign_keys,
            'status': 'database_check_complete'
        })
        
    except Exception as e:
        logger.error(f"Debug database error: {e}", exc_info=True)
        return JSONResponse(content={'error': str(e), 'status': 'database_check_failed'})

@app.get('/api/debug-saved-schedules')
async def debug_saved_schedules_endpoint(username: str = Depends(require_chair_role)):
    """Debug endpoint to check saved schedules directory and files"""
    try:
        logger.info(f"Debug: Checking saved schedules for user: {username}")
        
        # Check if saved_schedules directory exists
        saved_dir = os.path.join('.', 'saved_schedules')
        directory_exists = os.path.exists(saved_dir)
        
        if not directory_exists:
            logger.warning(f"Saved schedules directory does not exist: {saved_dir}")
            return JSONResponse(content={
                'directory_exists': False,
                'directory_path': saved_dir,
                'files': [],
                'error': 'Directory does not exist'
            })
        
        # List all files in the directory
        try:
            all_files = os.listdir(saved_dir)
            logger.info(f"Found {len(all_files)} files in saved_schedules directory")
        except Exception as e:
            logger.error(f"Cannot list files in saved_schedules directory: {e}")
            return JSONResponse(content={
                'directory_exists': True,
                'directory_path': saved_dir,
                'files': [],
                'error': f'Cannot list files: {str(e)}'
            })
        
        # Get file details
        file_details = []
        for filename in all_files:
            if filename.endswith('.json'):
                filepath = os.path.join(saved_dir, filename)
                try:
                    stat = os.stat(filepath)
                    file_details.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'readable': os.access(filepath, os.R_OK)
                    })
                except Exception as e:
                    file_details.append({
                        'filename': filename,
                        'error': str(e)
                    })
        
        return JSONResponse(content={
            'directory_exists': True,
            'directory_path': saved_dir,
            'files': file_details,
            'total_files': len(all_files),
            'json_files': len([f for f in all_files if f.endswith('.json')])
        })
        
    except Exception as e:
        logger.error(f"Debug saved schedules error: {e}", exc_info=True)
        return JSONResponse(content={'error': str(e), 'status': 'debug_failed'})

@app.post('/api/test-notification')
async def test_notification_endpoint(username: str = Depends(verify_token)):
    """Test endpoint to create a notification"""
    try:
        from database import create_notification, get_user_id_by_username
        logger.info(f"Creating test notification for username: {username}")
        
        user_id = get_user_id_by_username(username)
        if not user_id:
            logger.error(f"User not found: {username}")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        logger.info(f"Creating test notification for user_id: {user_id}")
        success = create_notification(
            user_id,
            "Test Notification",
            f"This is a test notification for user {username}",
            "info"
        )
        
        if success:
            logger.info(f"Test notification created successfully for user {username}")
            return JSONResponse(content={'message': 'Test notification created successfully', 'user_id': user_id})
        else:
            raise HTTPException(status_code=500, detail="Failed to create test notification")
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error creating test notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# User management endpoints (Admin only)
@app.get('/api/pending_users')
async def get_pending_users_endpoint(username: str = Depends(require_admin_role)):
    """Get all pending users for admin approval"""
    try:
        users = get_pending_users()
        return JSONResponse(content=users)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/approve_user/{user_id}')
async def approve_user_endpoint(user_id: int, username: str = Depends(require_admin_role)):
    """Approve a pending user"""
    try:
        success = approve_user(user_id, username)
        if success:
            # Record admin activity
            try:
                from database import get_user_id_by_username, record_user_activity
                admin_user_id = get_user_id_by_username(username)
                if admin_user_id:
                    record_user_activity(admin_user_id, "user_approval", f"Approved user ID: {user_id}")
            except Exception as e:
                logger.warning(f"Could not record approval activity: {e}")
            
            return JSONResponse(content={'message': 'User approved successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to approve user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/reject_user/{user_id}')
async def reject_user_endpoint(user_id: int, payload: dict, username: str = Depends(require_admin_role)):
    """Reject a pending user"""
    try:
        reason = payload.get('reason', 'No reason provided')
        success = reject_user(user_id, username, reason)
        if success:
            return JSONResponse(content={'message': 'User rejected successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to reject user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/all_users')
async def get_all_users_endpoint(username: str = Depends(require_admin_role)):
    """Get all users for admin management"""
    try:
        users = get_all_users()
        return JSONResponse(content=users)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/delete_user/{user_id}')
async def delete_user_endpoint(user_id: int, username: str = Depends(require_admin_role)):
    """Delete a user (admin only)"""
    try:
        logger.info(f"Admin {username} attempting to delete user {user_id}")
        
        # Prevent admin from deleting themselves
        admin_user = db.get_user_by_username(username)
        if admin_user and admin_user.get('id') == user_id:
            logger.warning(f"Admin {username} attempted to delete their own account")
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Check if user exists before attempting deletion
        target_user = db.db.execute_query("SELECT username, full_name, role FROM users WHERE id = %s", (user_id,))
        if not target_user:
            logger.warning(f"User with ID {user_id} not found for deletion")
            raise HTTPException(status_code=404, detail="User not found")
        
        target_user_info = target_user[0]
        logger.info(f"Attempting to delete user: {target_user_info['username']} (ID: {user_id})")
        
        success = delete_user(user_id, username)
        if success:
            logger.info(f"User {user_id} successfully deleted by admin {username}")
            return JSONResponse(content={'message': 'User deleted successfully'})
        else:
            logger.error(f"Failed to delete user {user_id} - delete_user function returned False")
            raise HTTPException(status_code=500, detail="Failed to delete user - check logs for details")
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Analytics endpoints (Admin only)
@app.get('/api/analytics/overview')
async def get_analytics_overview(username: str = Depends(require_admin_role)):
    """Get comprehensive system analytics overview"""
    try:
        analytics_data = get_system_analytics()
        return JSONResponse(content=analytics_data)
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/analytics/user-activity')
async def get_user_activity_analytics(days: int = 30, username: str = Depends(require_admin_role)):
    """Get user activity analytics"""
    try:
        activity_data = get_user_activity_stats(days)
        return JSONResponse(content=activity_data)
    except Exception as e:
        logger.error(f"Error getting user activity analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/analytics/metrics/{metric_name}')
async def get_metric_history(metric_name: str, days: int = 30, username: str = Depends(require_admin_role)):
    """Get historical data for a specific metric"""
    try:
        metric_data = get_metrics_history(metric_name, days)
        return JSONResponse(content=metric_data)
    except Exception as e:
        logger.error(f"Error getting metric history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/analytics/record-activity')
async def record_user_activity_endpoint(
    activity_type: str, 
    description: str, 
    request: Request,
    username: str = Depends(verify_token)
):
    """Record user activity (for all authenticated users)"""
    try:
        user_id = get_user_id_by_username(username)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get client IP and user agent
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        
        success = record_user_activity(user_id, activity_type, description, client_ip, user_agent)
        if success:
            return JSONResponse(content={'message': 'Activity recorded successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to record activity")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording user activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Settings endpoints (Admin only)
@app.get('/api/system/settings')
async def get_all_settings(username: str = Depends(require_admin_role)):
    """Get all system settings"""
    try:
        settings = get_all_system_settings()
        return JSONResponse(content=settings)
    except Exception as e:
        logger.error(f"Error getting system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/system/settings/{setting_key}')
async def get_setting(setting_key: str, username: str = Depends(require_admin_role)):
    """Get a specific system setting"""
    try:
        value = get_system_setting(setting_key)
        return JSONResponse(content={'key': setting_key, 'value': value})
    except Exception as e:
        logger.error(f"Error getting system setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/system/public-settings/{setting_key}')
async def get_public_setting(setting_key: str):
    """Get a specific system setting (public access for non-sensitive settings)"""
    try:
        # Only allow access to specific public settings
        public_settings = ['default_semester', 'default_sections', 'enable_notifications']
        if setting_key not in public_settings:
            raise HTTPException(status_code=403, detail="Setting not accessible publicly")
        
        value = get_system_setting(setting_key)
        return JSONResponse(content={'key': setting_key, 'value': value})
    except Exception as e:
        logger.error(f"Error getting public system setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/maintenance/status')
async def get_maintenance_status():
    """Get current maintenance mode status (public endpoint)"""
    try:
        maintenance_mode = get_system_setting('maintenance_mode', 'false')
        return JSONResponse(content={
            'maintenance_mode': maintenance_mode.lower() == 'true',
            'message': 'System is under maintenance' if maintenance_mode.lower() == 'true' else 'System is operational'
        })
    except Exception as e:
        logger.error(f"Error getting maintenance status: {e}")
        return JSONResponse(content={'maintenance_mode': False, 'message': 'System is operational'})

@app.get('/api/maintenance/admin-bypass')
async def check_admin_bypass(username: str = Depends(verify_token)):
    """Check if current user is admin and can bypass maintenance mode"""
    try:
        user = db.get_user_by_username(username)
        if user and user.get('role') == 'admin':
            return JSONResponse(content={
                'is_admin': True,
                'can_bypass': True,
                'message': 'Admin access granted'
            })
        else:
            return JSONResponse(content={
                'is_admin': False,
                'can_bypass': False,
                'message': 'Admin access required'
            })
    except Exception as e:
        logger.error(f"Error checking admin bypass: {e}")
        return JSONResponse(content={
            'is_admin': False,
            'can_bypass': False,
            'message': 'Error checking admin status'
        })

@app.put('/api/system/settings/{setting_key}')
async def update_setting(
    setting_key: str, 
    payload: dict, 
    username: str = Depends(require_admin_role)
):
    """Update a system setting"""
    try:
        value = payload.get('value')
        setting_type = payload.get('type', 'string')
        description = payload.get('description')
        
        if value is None:
            raise HTTPException(status_code=400, detail="Value is required")
        
        success = set_system_setting(setting_key, value, setting_type, description, username)
        if success:
            return JSONResponse(content={'message': 'Setting updated successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to update setting")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/system/settings')
async def create_setting(payload: dict, username: str = Depends(require_admin_role)):
    """Create a new system setting"""
    try:
        setting_key = payload.get('key')
        value = payload.get('value')
        setting_type = payload.get('type', 'string')
        description = payload.get('description')
        
        if not setting_key or value is None:
            raise HTTPException(status_code=400, detail="Key and value are required")
        
        success = set_system_setting(setting_key, value, setting_type, description, username)
        if success:
            return JSONResponse(content={'message': 'Setting created successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to create setting")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating system setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/system/settings/{setting_key}')
async def delete_setting(setting_key: str, username: str = Depends(require_admin_role)):
    """Delete a system setting"""
    try:
        success = delete_system_setting(setting_key)
        if success:
            return JSONResponse(content={'message': 'Setting deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete setting")
    except Exception as e:
        logger.error(f"Error deleting system setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/system/record-metric')
async def record_system_metric(
    metric_name: str, 
    metric_value: float, 
    metric_data: dict = None,
    username: str = Depends(require_admin_role)
):
    """Record a system metric"""
    try:
        success = record_metric(metric_name, metric_value, metric_data)
        if success:
            return JSONResponse(content={'message': 'Metric recorded successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to record metric")
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    import os
    
    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')  # Railway needs 0.0.0.0
    port = int(os.getenv('PORT', 8000))  # Railway sets PORT automatically
    reload = os.getenv('RELOAD', 'false').lower() == 'true'  # Disable reload in production
    
    uvicorn.run('app:app', host=host, port=port, reload=reload)
