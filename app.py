"""BIM POS Inventory - Main Application Entry Point."""
import streamlit as st
from core.db_init import init_db
from core.simple_auth import login_form, require_auth, get_current_user
from core.mobile_styles import apply_mobile_styles
from ui.sidebar import render_sidebar_menu, render_backup

# Import page render functions
from page_modules import dashboard, inventory, add_product, stock_movement, alerts, movements, user_management

# Page configuration
st.set_page_config(
    page_title="BIM POS Inventory",
    page_icon="💳",
    layout="wide",
)

# Apply mobile-friendly styles
apply_mobile_styles()

# Initialize database connection (needed for auth)
@st.cache_resource
def get_db_connection():
    return init_db()

conn = get_db_connection()

# Check authentication
if not require_auth():
    login_form(conn)
    st.stop()

# User is authenticated - get user info
user = get_current_user()

# Initialize session state
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = user['is_admin']
if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = "📊 Dashboard"
if "input_values" not in st.session_state:
    st.session_state.input_values = {}

# Initialize database connection (cached to avoid reconnecting on every interaction)
@st.cache_resource
def get_db_connection():
    return init_db()

conn = get_db_connection()

# Render sidebar menu and backup button
menu = render_sidebar_menu()
render_backup()

# Page routing
pages = {
    "📊 Dashboard": lambda: dashboard.render(conn),
    "📋 View Inventory": lambda: inventory.render(conn),
    "⚠️ Stock Alerts": lambda: alerts.render(conn),
    "🔄 Movement Log": lambda: movements.render(conn),
}

# Add admin-only pages
if st.session_state.admin_mode:
    pages["➕ Add Product"] = lambda: add_product.render(conn)
    pages["📦 Stock Movement"] = lambda: stock_movement.render(conn)
    pages["👥 User Management"] = lambda: user_management.render(conn)

# Render selected page
if menu not in pages:
    menu = "📊 Dashboard"
pages[menu]()
