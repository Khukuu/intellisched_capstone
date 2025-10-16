@echo off
echo Setting IntelliSched Environment Variables...

set DATABASE_URL=postgresql://postgres:asdf1234@localhost:5432/intellisched
set SECRET_KEY=IntelliSched-Super-Secret-JWT-Key-2024-Production-Ready
set ACCESS_TOKEN_EXPIRE_MINUTES=30
set HOST=0.0.0.0
set PORT=8000
set RELOAD=false
set ADMIN_PASSWORD=AdminSecure123!
set CHAIR_PASSWORD=ChairSecure123!
set DEAN_PASSWORD=DeanSecure123!
set SECRETARY_PASSWORD=SecretarySecure123!

echo Environment variables set successfully!
echo.
echo You can now run: python app.py
echo Or: uvicorn app:app --host 0.0.0.0 --port 8000
echo.
pause
