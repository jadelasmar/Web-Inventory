# Copilot Instructions for BIM POS Inventory System

## Project Overview
- **Purpose:** Cloud-ready inventory management system for small businesses, built with Streamlit and PostgreSQL (cloud) or SQLite (local).
- **Entry Point:** `app.py` orchestrates authentication, page routing, and database connection.
- **Major Components:**
  - `core/`: Database logic, authentication, constants, mobile styles.
  - `page_modules/`: Each file is a Streamlit page (dashboard, inventory, add product, etc.).
  - `ui/`: Sidebar and reusable UI components.
  - `utils/`: Utility scripts (e.g., password hash generator).
  - `assets/`: Static files (images, etc.).

## Key Patterns & Conventions
- **Page Routing:**
  - Pages are mapped in a `pages` dict in `app.py` using emoji-labeled keys (e.g., "📈 Dashboard").
  - Admin-only pages are conditionally added based on `st.session_state.admin_mode`.
- **Authentication:**
  - Custom login via `core/simple_auth.py`.
  - User roles: owner, admin, viewer. Role logic in `user_management.py` and `simple_auth.py`.
  - Session state is used for login persistence and role management.
- **Database:**
  - Uses PostgreSQL in production (via Streamlit secrets) and SQLite for local dev (auto fallback).
  - DB connection is cached with `@st.cache_resource` in `app.py`.
- **UI:**
  - Sidebar navigation in `ui/sidebar.py`.
  - Mobile-friendly tweaks in `core/mobile_styles.py`.
- **Assets:**
  - Product images in `assets/product_images/`.

## Developer Workflows
- **Run Locally:**
  - `pip install -r requirements.txt`
  - `streamlit run app.py` (uses SQLite by default)
- **Production Deploy:**
  - Push to GitHub → auto-deploys on Streamlit Cloud.
  - Configure DB credentials in `.streamlit/secrets.toml` or Streamlit Cloud Secrets.
- **Password Hashing:**
  - Use `python utils/generate_password_hash.py` to generate password hashes for owner/admin setup.
- **User Approval:**
  - New users require approval in the "👥 User Management" page.

## Integration & Extensibility
- **Add a Page:**
  - Create a new module in `page_modules/` and add to the `pages` dict in `app.py`.
- **Add Sidebar Items:**
  - Update `ui/sidebar.py`.
- **Database Schema:**
  - Managed in `core/db_init.py` and `core/services.py`.

## Project-Specific Notes
- **Emoji labels** are used for all navigation and page keys.
- **Session state** is the primary mechanism for user state, role, and navigation.
- **No test suite** is present; manual testing via UI is standard.
- **No migrations**; DB schema is initialized/updated at runtime.

## References
- See `README.md` for deployment, DB setup, and secrets management.
- See `core/` and `page_modules/` for main logic and page patterns.

---

**If unsure about a pattern, check `app.py` for the canonical approach.**
