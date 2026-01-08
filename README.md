# BIM POS Inventory System

A cloud-ready web-based inventory management system built with Streamlit and PostgreSQL.

## ✨ Features
- 📊 Dashboard with inventory overview and analytics
- 📋 View complete inventory with search and filters
- ⚠️ Stock alerts for low inventory items
- 🔄 Movement log tracking all inventory changes
- ➕ Add/Edit products with flexible categories (Admin/Owner only)
- 📦 Stock movement management (Admin/Owner only)
- 👥 **User Management** - Signup, approval system, and role-based access
- 🔐 **Secure Authentication** - Custom login with auto-login sessions
- 🗄️ **PostgreSQL database** for reliable, persistent data storage
- ☁️ **Cloud-ready** - Deploy to Streamlit Cloud in minutes

## 📁 Project Structure

```
Web-Inventory/
├── app.py                    # Main entry point
├── requirements.txt          # Dependencies
├── runtime.txt               # Python version for deployment
│
├── core/                     # Core application logic
│   ├── constants.py          # Configuration and constants
│   ├── services.py           # Database operations
│   ├── db_init.py            # Database initialization
│   ├── mobile_styles.py      # Mobile CSS tweaks
│   └── simple_auth.py        # Authentication system
│
├── page_modules/             # Streamlit page modules
│   ├── dashboard.py          # Dashboard with analytics
│   ├── inventory.py          # Inventory view
│   ├── add_product.py        # Add/Edit products
│   ├── stock_movement.py     # Record movements
│   ├── alerts.py             # Low stock alerts
│   ├── movements.py          # Movement history
│   └── user_management.py    # User approval & management
│
├── ui/                       # UI components
│   ├── sidebar.py            # Navigation & logout
│   └── components.py         # Reusable UI elements
│
├── utils/                    # Utility scripts
│   └── generate_password_hash.py  # Password hash generator
│
├── assets/                   # Static assets (images, etc.)
│   └── product_images/       # Product images for inventory
│
├── data/                     # Local database files
│
├── .streamlit/               # Streamlit configuration
│   ├── config.toml           # App settings
│   └── secrets.toml          # Owner account (not in git)
│
└── .devcontainer/            # (Optional) VS Code Dev Container config
```

## 🚀 Quick Deployment (3 Steps)

### 1. Set Up PostgreSQL Database (5 minutes)

1. Go to https://supabase.com and sign in with GitHub
2. Create new project: `bimpos-inventory`
3. Set a strong password and save it
4. Wait 2-3 minutes for initialization
5. Go to Project Settings → Database
6. Copy connection details:
   - Host: `db.xxxxx.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`

### 2. Deploy to Streamlit Cloud (3 minutes)

1. Go to https://streamlit.io/cloud
2. Sign in with GitHub
3. Click "New app"
4. Fill in:
   - Repository: `jadelasmar/Web-Inventory`
   - Branch: `main`
   - Main file: `app.py`
5. Click "Deploy"

### 3. Add Database Secrets (2 minutes)

1. In your Streamlit app dashboard, click "⚙️" → "Secrets"
2. Paste your database credentials:

```toml
[postgres]
host = "db.xxxxx.supabase.co"
port = 5432
database = "postgres"
user = "postgres"
password = "your-password-here"
```

3. Save → App restarts automatically ✅

**Your app is now live!** Get the URL like: `https://web-inventory-[random].streamlit.app`

## 💻 Local Development

### Quick Start (SQLite - No Setup)
```bash
pip install -r requirements.txt
streamlit run app.py
```
The app uses SQLite automatically for local development.

### Use PostgreSQL Locally (Optional)
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Add your Supabase/Neon credentials
3. Run: `streamlit run app.py`

## 🗄️ Database

- **Production**: PostgreSQL (Supabase) - Persistent, cloud storage
- **Local Dev**: SQLite (default) - Automatic fallback, no setup

## 🔐 Authentication & User Management

### Owner Account Setup

1. **Generate your password hash:**
```bash
python utils/generate_password_hash.py
```

2. **Create `.streamlit/secrets.toml`** (local development):
```toml
[users.YourUsername]
password_hash = "your-generated-hash-here"
name = "Your Name"
role = "owner"
```

3. **For Streamlit Cloud:** Add the same to Settings → Secrets

### User Roles
- **Owner** - Full access: approve users, delete users, change roles
- **Admin** - Can approve/reject users, manage inventory
- **Viewer** - Read-only access to inventory and reports

### User Signup & Approval
1. Users sign up through the app's signup form
2. Accounts are created with "pending" status
3. Owner/Admin approves users in "👥 User Management" page
4. Approved users can login and access based on their role

### Auto-Login
Users stay logged in for 30 days - no need to login repeatedly!

## 🔄 Auto-Deploy

Push changes to GitHub → Streamlit Cloud automatically redeploys in ~2 minutes!

```bash
git add .
git commit -m "Your changes"
git push
```
