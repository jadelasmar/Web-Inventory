"""Sidebar menu and logout button."""
import streamlit as st
from core.simple_auth import logout, get_current_user
from core.services import backup_database


def render_sidebar_menu():
    """Render the sidebar navigation menu with user info and logout."""
    
    # Show current user info
    user = get_current_user()
    st.sidebar.markdown(f"👤 **{user['name']}**")
    st.sidebar.caption(f"Role: {user['role'].title()}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    
    st.sidebar.divider()
    
    # Navigation menu
    menu = ["📊 Dashboard", "📋 View Inventory", "⚠️ Stock Alerts", "🔄 Movement Log"]
    if st.session_state.admin_mode:
        # Only show admin pages if admin_mode is enabled
        menu.insert(1, "➕ Add Product")
        menu.insert(2, "📦 Stock Movement")
        menu.append("👥 User Management")
    if (
        "menu_selection" not in st.session_state
        or st.session_state.menu_selection not in menu
    ):
        st.session_state.menu_selection = menu[0]
    selected = st.sidebar.radio("Select Page", menu, key="menu_selection")
    
    return selected


def render_backup():
    """Render database backup button in sidebar for admin users."""
    if not st.session_state.admin_mode:
        return
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Backup Database"):
        msg = backup_database()
        st.sidebar.success(msg)
        st.toast("💾 Backup completed", icon="💽")
