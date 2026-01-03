"""Sidebar menu and admin authentication."""
import streamlit as st
from constants import ADMIN_PASSWORD
from services import backup_database


def render_sidebar_menu():
    """Render the sidebar navigation menu with admin login/logout."""
    
    menu = ["📊 Dashboard", "📋 View Inventory", "⚠️ Stock Alerts", "🔄 Movement Log"]
    if st.session_state.admin_mode:
        # Only show admin pages if admin_mode is enabled
        menu.insert(1, "➕ Add Product")
        menu.insert(2, "📦 Stock Movement")
    if (
        "menu_selection" not in st.session_state
        or st.session_state.menu_selection not in menu
    ):
        st.session_state.menu_selection = menu[0]
    selected = st.sidebar.radio("Select Page", menu, key="menu_selection")
    
    # Admin login/logout UI in sidebar only
    if "show_admin_login" not in st.session_state:
        st.session_state.show_admin_login = False
    if st.session_state.admin_mode:
        st.sidebar.success("Admin mode enabled.")
        if st.sidebar.button("🚪 Logout Admin", key="sidebar_admin_logout"):
            st.session_state.admin_mode = False
            st.session_state.show_admin_login = False
            st.toast("Logged out of admin mode.", icon="🔒")
            st.rerun()
    else:
        if not st.session_state.show_admin_login:
            if st.sidebar.button("🔑 Admin Mode", key="show_admin_btn"):
                st.session_state.show_admin_login = True
                st.rerun()
        else:
            with st.sidebar.form("admin_login_form"):
                pw = st.text_input(
                    "Enter admin password", type="password", key="sidebar_admin_pw"
                )
                login_clicked = st.form_submit_button("Login as Admin")
                if login_clicked:
                    if pw == ADMIN_PASSWORD:
                        st.session_state.admin_mode = True
                        st.sidebar.success("Admin mode enabled.")
                        st.toast("Admin mode enabled.", icon="🔑")
                        st.session_state.show_admin_login = False
                        st.rerun()
                    else:
                        st.sidebar.error("Incorrect password.")
                        st.sidebar.caption(f"Debug: Password length = {len(ADMIN_PASSWORD)}")
    
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
