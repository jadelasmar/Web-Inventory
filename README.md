# BIM POS Inventory System

Local-first inventory management built with Streamlit and SQLite.

## Features
- Dashboard with inventory overview and analytics
- Inventory list with search and filters
- Low stock alerts
- Movement log for all stock changes
- Add/Edit products (Admin/Owner only)
- Stock movements (Admin/Owner only)
- User management with approvals and roles
- Secure login with 30-day auto-login
- SQLite database stored in `data/bimpos_inventory.db`

## Project Structure
```
Web-Inventory/
├── app.py                    # Main entry point
├── requirements.txt          # Dependencies
├── core/                     # Core application logic
├── page_modules/             # Streamlit page modules
├── ui/                       # UI components
├── utils/                    # Utility scripts
├── assets/                   # Static assets
├── data/                     # Local database files
└── .streamlit/               # Streamlit configuration (local only)
```

## Local Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

## Owner Account Setup (Local)
Option A: Create owner via secrets (bootstrap)
1. Generate a password hash:
```bash
python utils/generate_password_hash.py
```
2. Create `.streamlit/secrets.toml`:
```toml
[users.YourUsername]
password_hash = "your-generated-hash-here"
name = "Your Name"
role = "owner"
```

Option B: Insert owner directly into SQLite
See the instructions in the app support notes or use a small script to insert
into the `users` table with `role='owner'` and `status='approved'`.

## Local Hosting
See `docs/local_hosting_steps.txt` for Windows LAN hosting instructions.
