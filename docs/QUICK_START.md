# 🎯 Quick Deployment Checklist

Use this as your deployment checklist!

## ☑️ Step 1: Set Up Database (5 min)

1. Go to **https://supabase.com**
2. Sign in with GitHub
3. Create new project: `bimpos-inventory`
4. Set a strong password (SAVE IT!)
5. Wait for database to initialize
6. Go to Project Settings → Database
7. Note down these details:
   - Host: `db.xxxxx.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: (your password)

## ☑️ Step 2: Deploy App (3 min)

1. Go to **https://streamlit.io/cloud**
2. Sign in with GitHub
3. Click "New app"
4. Fill in:
   - Repository: `jadelasmar/Web-Inventory`
   - Branch: `main`
   - Main file: `app.py`
5. Click "Deploy"
6. Wait 2-3 minutes

## ☑️ Step 3: Configure Secrets (2 min)

1. In Streamlit Cloud, click your app
2. Click ⚙️ Settings
3. Go to "Secrets" tab
4. Paste this (with YOUR details):

```toml
[postgres]
host = "db.xxxxx.supabase.co"
port = 5432
database = "postgres"
user = "postgres"
password = "your-password-here"
```

5. Click "Save"
6. App will restart automatically

## ☑️ Step 4: Test It! (1 min)

1. Open your app URL
2. Add a test product
3. Refresh the page
4. ✅ Product should still be there!

## 📱 Share Your App

Your app URL: `https://[your-app-name].streamlit.app`

Share this with your team! They can:
- ✅ View inventory
- ✅ Check stock alerts
- ✅ See movement history
- ❌ Cannot add/edit (admin only)

## 🔄 Making Changes

After deployment, to update your app:

```bash
# Make your changes locally
git add .
git commit -m "Description of changes"
git push
```

App redeploys automatically in ~2 minutes!

## 📖 Need More Help?

- Database Setup: [DATABASE_SETUP.md](DATABASE_SETUP.md)
- Full Deployment Guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Supabase Dashboard: https://app.supabase.com
- Streamlit Dashboard: https://share.streamlit.io
