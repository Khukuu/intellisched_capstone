# 🚀 Railway Deployment Guide for IntelliSched

## Prerequisites
- GitHub account
- Railway account (free at railway.app)
- Your IntelliSched code ready

## Step 1: Push to GitHub

1. **Initialize Git** (if not already done):
```bash
git init
git add .
git commit -m "Initial commit - IntelliSched ready for deployment"
```

2. **Create GitHub repository**:
   - Go to github.com
   - Click "New repository"
   - Name it "intellisched" (or any name you prefer)
   - Make it public or private
   - Don't initialize with README (since you have files)

3. **Push your code**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/intellisched.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Railway

1. **Go to Railway**:
   - Visit railway.app
   - Sign up with GitHub
   - Click "New Project"

2. **Connect GitHub**:
   - Select "Deploy from GitHub repo"
   - Choose your intellisched repository
   - Click "Deploy Now"

3. **Add PostgreSQL Database**:
   - In your project dashboard
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will create a PostgreSQL database automatically

## Step 3: Configure Environment Variables

In Railway dashboard, go to your app service and add these environment variables:

### Required Variables:
```
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
DATABASE_URL=postgresql://postgres:password@host:port/database
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

### User Passwords:
```
ADMIN_PASSWORD=YourSecureAdminPass123!
CHAIR_PASSWORD=YourSecureChairPass123!
DEAN_PASSWORD=YourSecureDeanPass123!
SECRETARY_PASSWORD=YourSecureSecretaryPass123!
```

**Note**: Railway will automatically set `DATABASE_URL` when you add the PostgreSQL service.

## Step 4: Deploy

1. **Railway will automatically**:
   - Install dependencies from requirements.txt
   - Run your app
   - Provide a public URL

2. **Your app will be available at**:
   - `https://your-app-name.railway.app`

## Step 5: Test Your Deployment

1. **Visit your app URL**
2. **Test login with**:
   - Admin: `admin` / `YourSecureAdminPass123!`
   - Chair: `chair` / `YourSecureChairPass123!`
   - Dean: `dean` / `YourSecureDeanPass123!`
   - Secretary: `sec` / `YourSecureSecretaryPass123!`

## Troubleshooting

### If deployment fails:
1. **Check logs** in Railway dashboard
2. **Verify environment variables** are set correctly
3. **Ensure DATABASE_URL** is properly configured

### If database connection fails:
1. **Check PostgreSQL service** is running
2. **Verify DATABASE_URL** format
3. **Run database migrations** if needed

## Cost
- **Free tier**: 500 hours/month
- **PostgreSQL**: Free tier available
- **Perfect for development and small projects**

## Next Steps
- Set up custom domain (optional)
- Configure SSL (automatic with Railway)
- Set up monitoring and logging
