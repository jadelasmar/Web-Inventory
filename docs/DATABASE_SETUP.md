# 🗄️ PostgreSQL Database Setup Guide

## Why PostgreSQL?

Your inventory app now uses **PostgreSQL** for persistent data storage. This means:
- ✅ Your data is permanently saved
- ✅ No data loss when the app restarts
- ✅ Multiple users can access simultaneously
- ✅ Better performance for larger inventories
- ✅ Free with Supabase (500MB) or Neon (3GB)

---

## Step 1: Create a Free PostgreSQL Database

### Option A: Supabase (Recommended)

1. **Sign up at Supabase**
   - Go to https://supabase.com
   - Click "Start your project"
   - Sign in with GitHub

2. **Create a new project**
   - Click "New Project"
   - Name: `bimpos-inventory`
   - Database Password: Create a strong password (save it!)
   - Region: Choose closest to you
   - Click "Create new project"
   - Wait 2-3 minutes for setup

3. **Get connection details**
   - Click "Project Settings" (gear icon)
   - Go to "Database" section
   - Under "Connection string", select "URI" mode
   - Copy the connection details:
     - Host: `db.xxxxxxxxxxxxx.supabase.co`
     - Port: `5432`
     - Database: `postgres`
     - User: `postgres`
     - Password: (the one you created)

### Option B: Neon (Alternative)

1. Go to https://neon.tech
2. Sign up with GitHub
3. Create a new project: `bimpos-inventory`
4. Copy the connection string
5. Extract: host, port, database, user, password

---

## Step 2: Configure Streamlit Cloud

After you deploy your app to Streamlit Cloud:

1. **Go to your app dashboard**
   - Visit https://share.streamlit.io
   - Find your deployed app

2. **Add database secrets**
   - Click the "⚙️" (settings) button
   - Go to "Secrets" section
   - Paste the following (replace with YOUR credentials):

```toml
[postgres]
host = "db.xxxxxxxxxxxxx.supabase.co"
port = 5432
database = "postgres"
user = "postgres"
password = "your-password-here"
```

3. **Save and restart**
   - Click "Save"
   - Your app will automatically restart
   - The database tables will be created automatically!

---

## Step 3: Verify It Works

1. Open your deployed app
2. Go to "Add Product" (admin mode)
3. Add a test product
4. Close the app and reopen it
5. ✅ Your product should still be there!

---

## Local Development

### Keep using SQLite locally (easiest)
- Just run `streamlit run app.py`
- It will use the local SQLite database
- No configuration needed!

### Use PostgreSQL locally (optional)
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Add your Supabase credentials
3. Run `streamlit run app.py`

**Note:** Never commit `.streamlit/secrets.toml` to GitHub!

---

## Migrating Existing Data

If you already have data in your SQLite database:

### Option 1: Manual Migration (Small Dataset)
1. Export from SQLite: Open your local app, view products
2. Manually add them to the deployed app

### Option 2: SQL Export (Larger Dataset)
1. Use a SQLite browser tool to export as CSV
2. Use SQL INSERT statements to import into PostgreSQL
3. Or use pgAdmin to import CSV files

### Option 3: Python Script
I can create a migration script if you have substantial data to migrate.

---

## Troubleshooting

### "Connection refused" error
- Check your database credentials in Streamlit secrets
- Verify the database is running on Supabase/Neon dashboard
- Make sure port is 5432

### "No module named 'psycopg2'" error
- The requirements.txt already includes `psycopg2-binary`
- Streamlit Cloud will install it automatically

### Tables not created
- The app creates tables automatically on first run
- Check Streamlit Cloud logs for errors
- Verify database user has CREATE TABLE permissions

### Local development fails with PostgreSQL
- Make sure `.streamlit/secrets.toml` exists and has correct format
- Or just remove the file to use SQLite locally

---

## Database Management

### View your data
- **Supabase**: Use the Table Editor in your project dashboard
- **Neon**: Use the SQL Editor or connect with pgAdmin

### Backup your database
- **Supabase**: Project Settings → Database → Download backup
- **Neon**: Database → Backups (automatic daily backups)

### Reset/Clear database
Run this SQL in Supabase SQL Editor:
```sql
DROP TABLE IF EXISTS movements;
DROP TABLE IF EXISTS products;
```
Then restart your Streamlit app to recreate tables.

---

## Security Notes

- ✅ Database credentials are stored in Streamlit secrets (encrypted)
- ✅ Never commit secrets.toml to GitHub
- ✅ Use strong passwords for your database
- ✅ Supabase/Neon databases are SSL-encrypted by default

---

## Cost & Limits

### Supabase Free Tier
- 500 MB database
- 2 GB bandwidth
- 50,000 monthly active users
- Sufficient for most small-medium inventories

### Neon Free Tier
- 3 GB storage
- 1 shared compute
- 1 project
- More storage for larger inventories

Both are more than enough for an inventory management system!

---

## Need Help?

If you encounter issues:
1. Check Streamlit Cloud logs (in app settings)
2. Check Supabase/Neon dashboard for database status
3. Verify all credentials are correct in secrets
4. Ensure your database is in an active state (not paused)
