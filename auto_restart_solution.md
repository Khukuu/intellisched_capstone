# 🔄 IntelliSched Auto-Restart Solutions

## Current Status: ✅ ALREADY IMPLEMENTED!

Your Railway deployment **already has auto-restart** configured! Here's what's working:

### Current Auto-Restart Features:
- ✅ **Automatic restart on failure** (up to 10 retries)
- ✅ **Health check monitoring** (`/health` endpoint)
- ✅ **Request limit restart** (after 1000 requests)
- ✅ **Graceful shutdown** with timeouts

## 🚀 Enhanced Auto-Restart Solutions

### 1. **Railway Configuration (Already Updated)**

Your `railway.json` now includes:
```json
{
  "deploy": {
    "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 --limit-max-requests 1000 --timeout-keep-alive 30 --timeout-graceful-shutdown 30",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "restartPolicyDelay": 5
  }
}
```

**What this does:**
- 🔄 **Auto-restart on failure** (10 retries with 5-second delay)
- ⏱️ **Graceful shutdown** (30-second timeout)
- 🔍 **Health monitoring** (checks `/health` endpoint)
- 📊 **Request limit restart** (after 1000 requests)

### 2. **Application-Level Auto-Restart (Process Manager)**

Create a process manager script:

```bash
# Create restart_wrapper.sh
#!/bin/bash
while true; do
    echo "Starting IntelliSched..."
    uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 --limit-max-requests 1000
    echo "IntelliSched stopped. Restarting in 5 seconds..."
    sleep 5
done
```

### 3. **Docker-Based Auto-Restart (Alternative)**

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Use restart policy
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-max-requests", "1000"]
```

### 4. **Systemd Service (VPS/Server)**

Create `/etc/systemd/system/intellisched.service`:
```ini
[Unit]
Description=IntelliSched Auto-Restart Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/intellisched
Environment=PATH=/path/to/intellisched/venv/bin
ExecStart=/path/to/intellisched/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1 --limit-max-requests 1000
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=intellisched

[Install]
WantedBy=multi-user.target
```

## 🔧 **Manual vs Automatic Restart**

### **Automatic (Current Setup):**
- ✅ **Railway handles it automatically**
- ✅ **No manual intervention needed**
- ✅ **Health checks ensure service is running**
- ✅ **Graceful shutdown and restart**

### **Manual (If needed):**
```bash
# Railway CLI commands
railway up                    # Deploy latest version
railway restart              # Restart service
railway logs                 # Check logs
railway status               # Check service status
```

## 📊 **Monitoring Your Auto-Restart**

### **Check Railway Dashboard:**
1. Go to your Railway project dashboard
2. Click on your service
3. Check "Deployments" tab for restart history
4. Monitor "Logs" for restart events

### **Health Check Endpoints:**
- `GET /health` - Basic health check
- `GET /health/database` - Database connectivity check

### **Log Monitoring:**
```bash
# Check Railway logs
railway logs --follow

# Check specific service
railway logs --service your-service-name
```

## 🚨 **Troubleshooting Auto-Restart Issues**

### **If Auto-Restart Isn't Working:**

1. **Check Railway Configuration:**
   ```bash
   railway status
   railway logs
   ```

2. **Verify Health Check:**
   ```bash
   curl https://your-app.railway.app/health
   ```

3. **Check Resource Limits:**
   - Memory usage
   - CPU usage
   - Database connections

4. **Manual Restart:**
   ```bash
   railway restart
   ```

### **Common Issues:**

1. **Memory Leaks:** App restarts after 1000 requests (this is normal!)
2. **Database Connection Issues:** Check DATABASE_URL
3. **Port Conflicts:** Ensure PORT environment variable is set
4. **Health Check Failures:** Verify `/health` endpoint works

## 🎯 **Recommended Solution**

**For Railway (Current Setup):**
Your current configuration is **already optimal**! Railway will:
- ✅ Auto-restart on failure
- ✅ Handle graceful shutdowns
- ✅ Monitor health checks
- ✅ Restart after request limits

**No additional setup needed** - your app will automatically restart when:
- It crashes
- It reaches 1000 requests
- Health checks fail
- Resource limits are exceeded

## 🔍 **How to Verify Auto-Restart is Working**

1. **Check Railway Dashboard:**
   - Look for restart events in deployment history
   - Monitor resource usage graphs

2. **Test Health Endpoint:**
   ```bash
   curl https://your-app.railway.app/health
   ```

3. **Monitor Logs:**
   ```bash
   railway logs --follow
   ```

4. **Check Request Count:**
   - Your app will restart after 1000 requests (this is intentional!)

## 📈 **Performance Optimization**

To reduce restart frequency:

1. **Increase Request Limit:**
   ```json
   "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 --limit-max-requests 5000"
   ```

2. **Add Memory Management:**
   ```python
   import gc
   gc.collect()  # Add to your scheduler.py
   ```

3. **Optimize Database Connections:**
   - Use connection pooling
   - Close connections properly

## ✅ **Summary**

**Your IntelliSched is already configured for auto-restart!** 

Railway will automatically:
- 🔄 Restart on failure (up to 10 times)
- ⏱️ Restart after 1000 requests
- 🔍 Monitor health checks
- 📊 Handle graceful shutdowns

**No manual intervention required** - your app will stay running automatically!
