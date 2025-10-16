# 🚀 IntelliSched Deployment Guide

## Quick Deployment Commands

### **Option 1: Direct Uvicorn Command (Recommended)**
```bash
# Install dependencies
pip install -r requirements.txt

# Run in production mode
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### **Option 2: Using Environment Variables**
```bash
# Set environment variables
export HOST=0.0.0.0
export PORT=8000
export RELOAD=false

# Run the application
python app.py
```

## 🔧 **CRITICAL: Fix Security Issues Before Deployment**

### **1. Change Database Credentials**
Update `database.py` line 14:
```python
# OLD (INSECURE):
"postgresql://postgres:asdf1234@localhost:5432/intellisched"

# NEW (SECURE):
os.getenv('DATABASE_URL', 'postgresql://postgres:your-secure-password@your-db-host:5432/intellisched')
```

### **2. Change JWT Secret Key**
Update `app.py` line 166:
```python
# OLD (INSECURE):
SECRET_KEY = "your-secret-key-change-in-production"

# NEW (SECURE):
SECRET_KEY = os.getenv('SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')
```

### **3. Change Default Passwords**
The application creates default users with weak passwords:
- admin/admin123
- chair/chair123  
- dean/dean123
- secretary/sec123

**Change these immediately after deployment!**

## 🌐 **Production Deployment Steps**

### **1. Prepare Your Server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y
```

### **2. Setup Database**
```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE intellisched;
CREATE USER intellisched_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE intellisched TO intellisched_user;
\q
```

### **3. Deploy Application**
```bash
# Clone your repository
git clone <your-repo-url>
cd intellisched_capstone

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python migrate_to_db.py

# Start the application
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### **4. Setup Reverse Proxy (Optional but Recommended)**
```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/intellisched
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔒 **Security Checklist**

- [ ] Change database password from `asdf1234`
- [ ] Change JWT secret key from default
- [ ] Change all default user passwords
- [ ] Use HTTPS in production
- [ ] Setup firewall rules
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

## 🚨 **Current Security Issues**

Your application has these **CRITICAL** security vulnerabilities:

1. **Hardcoded database password**: `asdf1234`
2. **Weak JWT secret**: `your-secret-key-change-in-production`
3. **Default admin passwords**: `admin123`, `chair123`, etc.
4. **No HTTPS configuration**
5. **No environment variable usage**

**DO NOT deploy to production without fixing these issues!**

## 📝 **Next Steps**

1. **Fix security issues** (database password, JWT secret, default passwords)
2. **Test locally** with production settings
3. **Deploy to staging** environment first
4. **Setup monitoring** and logging
5. **Deploy to production** with proper security measures

## 🆘 **Need Help?**

If you need help fixing the security issues or setting up proper deployment, I can help you:
1. Update the code to use environment variables
2. Create secure configuration files
3. Setup proper database credentials
4. Configure production-ready settings
