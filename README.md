# BIM POS Inventory System

A cloud-ready web-based inventory management system built with Streamlit and PostgreSQL.

## ✨ Features
- 📊 Dashboard with inventory overview and analytics
- 📋 View complete inventory with search and filters
- ⚠️ Stock alerts for low inventory items
- 🔄 Movement log tracking all inventory changes
- ➕ Add/Edit products with flexible categories (Admin only)
- 📦 Stock movement management (Admin only)
- 🗄️ **PostgreSQL database** for reliable, persistent data storage
- ☁️ **Cloud-ready** - Deploy to Streamlit Cloud in minutes

## 📁 Project Structure

```
Web-Inventory/
├── app.py                    # Main entry point
├── requirements.txt          # Dependencies
│
├── core/                     # Core application logic
│   ├── constants.py         # Configuration and constants
│   ├── services.py          # Database operations
│   └── db_init.py           # Database initialization
│
├── page_modules/            # Streamlit page modules
│   ├── dashboard.py         # Dashboard with analytics
│   ├── inventory.py         # Inventory view
│   ├── add_product.py       # Add/Edit products
│   ├── stock_movement.py    # Record movements
│   ├── alerts.py            # Low stock alerts
│   └── movements.py         # Movement history
│
├── ui/                      # UI components
│   ├── sidebar.py           # Navigation & auth
│   └── components.py        # Reusable UI elements
│
├── docs/                    # Documentation
│   ├── DATABASE_SETUP.md    # Database setup guide
│   ├── DEPLOYMENT.md        # Deployment guide
│   └── QUICK_START.md       # Quick start guide
│
├── .streamlit/              # Streamlit configuration
│   ├── config.toml          # App settings
│   └── secrets.toml.example # Secrets template
│
└── data/                    # Local database files
```

## 🚀 Deployment

This app is designed to run on **Streamlit Community Cloud** with **PostgreSQL**.

### Quick Deploy:
1. **Set up free PostgreSQL** (Supabase/Neon) - See [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md)
2. **Deploy to Streamlit Cloud** - See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
3. **Add database secrets** in Streamlit Cloud settings

**Full guides:**
- 📖 [Database Setup Guide](docs/DATABASE_SETUP.md) - Set up PostgreSQL
- 📖 [Deployment Guide](docs/DEPLOYMENT.md) - Deploy to Streamlit Cloud
- 📖 [Quick Start Guide](docs/QUICK_START.md) - Get started quickly

## 💻 Local Development

### Option 1: SQLite (No Setup Required)
```bash
pip install -r requirements.txt
streamlit run app.py
```
The app will automatically use SQLite for local development.

### Option 2: Connect to PostgreSQL
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Add your PostgreSQL credentials
3. Run: `streamlit run app.py`

## 🗄️ Database

- **Production**: PostgreSQL (Supabase/Neon) - Persistent, reliable storage
- **Local Dev**: SQLite (default) - No setup needed, automatic fallback

The app automatically detects which database to use based on environment.

## 🔐 Admin Access

Default admin password: `admin`

Change it by setting `ADMIN_PASSWORD` in Streamlit Cloud secrets:
```toml
ADMIN_PASSWORD = "your-secure-password"
```
