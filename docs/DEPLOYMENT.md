# 🚀 Deployment Guide - Streamlit Community Cloud

## Quick Start (3 Steps!)

### 1. **Set Up PostgreSQL Database** (5 minutes)
   - Follow the detailed guide: [DATABASE_SETUP.md](DATABASE_SETUP.md)
   - Use Supabase (free, 500MB) or Neon (free, 3GB)
   - Save your database credentials

### 2. **Deploy to Streamlit Cloud** (3 minutes)
   - Go to: https://streamlit.io/cloud
   - Sign in with GitHub
   - Click "New app"
   - Repository: `jadelasmar/Web-Inventory`
   - Branch: `main`
   - Main file: `app.py`
   - Click "Deploy!"

### 3. **Add Database Secrets** (2 minutes)
   - In Streamlit Cloud app settings
   - Go to "Secrets" section
   - Add your PostgreSQL credentials:
   ```toml
   [postgres]
   host = "your-database-host.supabase.co"
   port = 5432
   database = "postgres"
   user = "postgres"
   password = "your-password"
   ```
   - Save and your app will restart

### ✅ Done! Your app is live with persistent data storage!

---

## Features of This Setup

✅ **Persistent Data** - Your inventory data is permanently saved  
✅ **Multi-User Access** - Team can view inventory simultaneously  
✅ **Auto-Deploy** - Push to GitHub, app updates automatically  
✅ **Free Hosting** - Both Streamlit Cloud and database are free  
✅ **Secure** - Database credentials encrypted in Streamlit secrets  
✅ **Backup** - Supabase/Neon provide automatic backups

---

## 🔄 Updating Your App

Any changes you push to GitHub automatically redeploy:

```bash
git add .
git commit -m "Description of changes"
git push
```

Streamlit Cloud detects the push and redeploys in ~2 minutes!

---

## 📊 Your App URL

After deployment, you'll get a URL like:
- `https://web-inventory-[random].streamlit.app`

Share this with your team!

---

## 🔐 Admin Authentication

The app already has admin mode built-in. You can enhance security by:

1. Going to Streamlit Cloud app settings
2. Adding to Secrets:
```toml
[passwords]
admin_password = "your-secure-password"
```

3. Update your code to check `st.secrets["passwords"]["admin_password"]`

---

## 🆘 Troubleshooting

### App crashes on startup
- Check Streamlit Cloud logs (in app settings)
- Verify database credentials in secrets
- Ensure database is running on Supabase/Neon

### Data not persisting
- Verify PostgreSQL secrets are configured correctly
- Check database connection in Supabase/Neon dashboard
- Look for errors in Streamlit Cloud logs

### Can't access the app
- Check if the app URL is correct
- See if the app is "sleeping" - just visit the URL to wake it
- Free Streamlit apps sleep after inactivity

For detailed database setup, see: [DATABASE_SETUP.md](DATABASE_SETUP.md)

---

## 💡 Local Development

Run locally with SQLite (no setup needed):
```bash
streamlit run app.py
```

Or connect to your cloud PostgreSQL:
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Add your database credentials
3. Run `streamlit run app.py`
