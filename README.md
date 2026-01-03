# BIM POS Inventory System

A cloud-ready web-based inventory management system built with Streamlit and PostgreSQL.

## ✨ Features
- 📊 Dashboard with inventory overview and analytics
- 📋 View complete inventory with search and filters
- ⚠️ Stock alerts for low inventory items
- 🔄 Movement log tracking all inventory changes
- ➕ Add products (Admin only)
- 📦 Stock movement management (Admin only)
- 🗄️ **PostgreSQL database** for reliable, persistent data storage
- ☁️ **Cloud-ready** - Deploy to Streamlit Cloud in minutes

## 🚀 Deployment

This app is designed to run on **Streamlit Community Cloud** with **PostgreSQL**.

### Quick Deploy:
1. **Set up free PostgreSQL** (Supabase/Neon) - See [DATABASE_SETUP.md](DATABASE_SETUP.md)
2. **Deploy to Streamlit Cloud** - See [DEPLOYMENT.md](DEPLOYMENT.md)
3. **Add database secrets** in Streamlit Cloud settings

**Full guides:**
- 📖 [Database Setup Guide](DATABASE_SETUP.md) - Set up PostgreSQL
- 📖 [Deployment Guide](DEPLOYMENT.md) - Deploy to Streamlit Cloud

## 💻 Local Development

### Option 1: SQLite (No Setup Required)
```bash
pip install -r Requirements.txt
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
