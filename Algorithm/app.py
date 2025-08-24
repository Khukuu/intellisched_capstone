from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scheduler import generate_schedule
from database import db, load_subjects_from_db, load_teachers_from_db, load_rooms_from_db
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

# Main route - serve main app (authentication handled by frontend)
@app.get('/')
async def index():
    """Main route - serve main app, authentication handled by frontend"""
    index_path = os.path.join('static', 'index.html')
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail='Index file not found')
    return FileResponse(index_path, media_type='text/html')

@app.get('/login')
async def login_page():
    """Serve login page for unauthenticated users"""
    login_path = os.path.join('static', 'login.html')
    if not os.path.exists(login_path):
        raise HTTPException(status_code=404, detail='Login file not found')
    return FileResponse(login_path, media_type='text/html')

@app.post('/schedule')
async def schedule(payload: dict, username: str = Depends(verify_token)):
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
async def saved_schedules(username: str = Depends(verify_token)):
    return JSONResponse(content=_list_saved_summaries())

@app.post('/save_schedule')
async def save_schedule(payload: dict, username: str = Depends(verify_token)):
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
    return JSONResponse(content={'id': uid, 'name': name, 'semester': semester, 'created_at': created_at})

@app.get('/load_schedule')
async def load_schedule(id: str, username: str = Depends(verify_token)):
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
async def download_schedule(id: str | None = None, semester: str | None = None, username: str = Depends(verify_token)):
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
async def get_data(filename: str, username: str = Depends(verify_token)):
    try:
        if filename in ['cs_curriculum', 'subjects']:
            data = load_subjects_from_db()
        elif filename == 'teachers':
            data = load_teachers_from_db()
        elif filename == 'rooms':
            data = load_rooms_from_db()
        else:
            raise HTTPException(status_code=404, detail='Data type not found')
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/upload/{filename}')
async def upload_file(filename: str, file: UploadFile = File(...), username: str = Depends(verify_token)):
    """Legacy endpoint - CSV uploads are no longer supported"""
    raise HTTPException(status_code=400, detail='CSV uploads are no longer supported. Data is now managed through PostgreSQL database.')

# Database management endpoints
@app.post('/api/subjects')
async def add_subject_endpoint(subject_data: dict):
    """Add a new subject to the database"""
    try:
        from database import add_subject
        add_subject(subject_data)
        return JSONResponse(content={'message': 'Subject added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/subjects/{subject_code}')
async def update_subject_endpoint(subject_code: str, subject_data: dict):
    """Update an existing subject in the database"""
    try:
        from database import update_subject
        subject_data['subject_code'] = subject_code
        update_subject(subject_code, subject_data)
        return JSONResponse(content={'message': 'Subject updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/subjects/{subject_code}')
async def delete_subject_endpoint(subject_code: str):
    """Delete a subject from the database"""
    try:
        from database import delete_subject
        delete_subject(subject_code)
        return JSONResponse(content={'message': 'Subject deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/teachers')
async def add_teacher_endpoint(teacher_data: dict):
    """Add a new teacher to the database"""
    try:
        from database import add_teacher
        add_teacher(teacher_data)
        return JSONResponse(content={'message': 'Teacher added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/teachers/{teacher_id}')
async def update_teacher_endpoint(teacher_id: str, teacher_data: dict):
    """Update an existing teacher in the database"""
    try:
        from database import update_teacher
        teacher_data['teacher_id'] = teacher_id
        update_teacher(teacher_id, teacher_data)
        return JSONResponse(content={'message': 'Teacher updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/teachers/{teacher_id}')
async def delete_teacher_endpoint(teacher_id: str):
    """Delete a teacher from the database"""
    try:
        from database import delete_teacher
        delete_teacher(teacher_id)
        return JSONResponse(content={'message': 'Teacher deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/rooms')
async def add_room_endpoint(room_data: dict):
    """Add a new room to the database"""
    try:
        from database import add_room
        add_room(room_data)
        return JSONResponse(content={'message': 'Room added successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/rooms/{room_id}')
async def update_room_endpoint(room_id: str, room_data: dict):
    """Update an existing room in the database"""
    try:
        from database import update_room
        room_data['room_id'] = room_id
        update_room(room_id, room_data)
        return JSONResponse(content={'message': 'Room updated successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/api/rooms/{room_id}')
async def delete_room_endpoint(room_id: str):
    """Delete a room from the database"""
    try:
        from database import delete_room
        delete_room(room_id)
        return JSONResponse(content={'message': 'Room deleted successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/migrate')
async def migrate_data_endpoint():
    """Trigger data migration from CSV to database"""
    try:
        from database import db
        db.migrate_from_csv()
        return JSONResponse(content={'message': 'Migration completed successfully'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=5000, reload=True)
