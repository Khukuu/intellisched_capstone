from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scheduler import generate_schedule
from database import (
    db,
    load_subjects_from_db,
    load_teachers_from_db,
    load_rooms_from_db,
    load_sections_from_db,
    get_pending_users,
    approve_user,
    reject_user,
    check_email_exists,
    get_all_users,
    delete_user,
    create_schedule_approval,
    get_pending_schedules,
    get_approved_schedules,
    approve_schedule,
    reject_schedule,
    get_schedule_approval_status,
)
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
            "role": user.get('role'),
            "status": user.get('status', 'active')
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

    # If request explicitly asks to persist as pending schedule (Chair flow)
    if payload.get('persist', False):
        try:
            name = (payload.get('name') or 'Generated Schedule')
            semester_int = int(semester_filter) if semester_filter else None
            # Create synthetic id based on timestamp like saved schedules
            uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            created = create_schedule_approval(uid, name, semester_int or 0, username)
            if not created:
                print('Warning: failed to create schedule approval record')
            return JSONResponse(content={
                'id': uid,
                'name': name,
                'status': 'pending',
                'semester': semester_int,
                'schedule': result,
            })
        except Exception as e:
            # Fall back to returning just the result
            print(f"Warning: persist schedule failed: {e}")
            return JSONResponse(content=result)

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
                # include approval status if exists
                'status': (lambda sid: (get_schedule_approval_status(sid) or {}).get('status'))(data.get('id') or ''),
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
    # Reuse existing generation logic by calling /schedule path here
    subjects = load_subjects_from_db()
    teachers = load_teachers_from_db()
    rooms = load_rooms_from_db()
    semester_filter = payload.get('semester')

    desired_sections_per_year = {
        1: payload.get('numSectionsYear1', 0),
        2: payload.get('numSectionsYear2', 0),
        3: payload.get('numSectionsYear3', 0),
        4: payload.get('numSectionsYear4', 0),
    }

    result = generate_schedule(subjects, teachers, rooms, semester_filter, desired_sections_per_year)
    name = (payload.get('name') or 'Generated Schedule')
    semester_int = int(semester_filter) if semester_filter else None
    uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    create_schedule_approval(uid, name, semester_int or 0, username)
    return JSONResponse(content={'id': uid, 'name': name, 'status': 'pending', 'semester': semester_int, 'schedule': result})

@app.get('/schedules/pending')
async def list_pending_schedules(username: str = Depends(require_role(['dean']))):
    """Dean views all pending schedules (grouping is done client-side)."""
    items = get_pending_schedules()
    return JSONResponse(content=items)

@app.get('/api/pending_schedules')
async def list_pending_schedules_alias(username: str = Depends(require_role(['dean']))):
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

@app.get('/api/approved_schedules')
async def list_approved_schedules_alias(username: str = Depends(require_role(['dean']))):
    items = get_approved_schedules()
    return JSONResponse(content=items)

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
        # Prevent admin from deleting themselves
        admin_user = db.get_user_by_username(username)
        if admin_user and admin_user.get('id') == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        success = delete_user(user_id, username)
        if success:
            return JSONResponse(content={'message': 'User deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete user")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=5000, reload=True)
