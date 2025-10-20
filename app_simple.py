from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import json
from datetime import datetime, timedelta
import jwt
from typing import Optional

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

# Mount static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
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

# Basic endpoints
@app.get('/')
async def index():
    """Main route - redirect users to login"""
    return RedirectResponse(url='/login')

@app.get('/health')
async def health_check():
    """Health check endpoint"""
    try:
        return {"status": "healthy", "message": "Application is running"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Application error: {str(e)}"}

@app.get('/status')
async def status():
    """Simple status endpoint for Railway healthcheck"""
    return {"status": "ok", "message": "IntelliSched is running"}

@app.get('/login')
async def login_page():
    """Serve login page for unauthenticated users"""
    login_path = os.path.join('static', 'login.html')
    if not os.path.exists(login_path):
        raise HTTPException(status_code=404, detail='Login file not found')
    return FileResponse(login_path, media_type='text/html')

# Authentication endpoints
@app.post('/auth/login')
async def login(payload: dict):
    try:
        username = payload.get('username')
        password = payload.get('password')
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        logger.info(f"Login attempt for user: {username}")
        
        # For now, just return a simple response
        # TODO: Add proper database authentication
        if username == "admin" and password == "admin123":
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": username}, expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "username": username,
                "full_name": "Administrator",
                "role": "admin",
                "status": "active"
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == '__main__':
    import uvicorn
    import os
    
    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    reload = os.getenv('RELOAD', 'false').lower() == 'true'
    
    uvicorn.run('app_simple:app', host=host, port=port, reload=reload)
