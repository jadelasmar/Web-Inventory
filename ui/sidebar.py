"""Sidebar menu and logout button."""
import streamlit as st
import base64
from core.simple_auth import logout, get_current_user
from core.services import backup_database


def render_sidebar_menu():
    """Render the sidebar navigation menu with user info and logout."""
    
    # Add custom CSS for centering logo
    st.sidebar.markdown("""
    <style>
    /* Center sidebar image at all screen sizes */
    [data-testid="stSidebar"] .sidebar-logo {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    }
    
    /* Control image size - fixed at 150px */
    [data-testid="stSidebar"] .sidebar-logo img {
        width: 150px !important;
        min-width: 150px !important;
        max-width: none !important;
        height: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Show logo at top (centered)
    try:
        with open("assets/logo.png", "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
        st.sidebar.markdown(
            f'<div class="sidebar-logo"><img src="data:image/png;base64,{img_base64}"></div>',
            unsafe_allow_html=True
        )
    except:
        pass  # If logo not found, just skip it
    
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

    st.sidebar.divider()
    
    # Show current user info
    user = get_current_user()
    st.sidebar.markdown(f"👤 **{user['name']}**")
    st.sidebar.caption(f"Role: {user['role'].title()}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    

    
    return selected


def render_backup():
    """Render database backup button in sidebar for admin users."""
    if not st.session_state.admin_mode:
        return
    st.sidebar.markdown("---")
    if st.sidebar.button("📥 Backup Database", use_container_width=True):
        msg = backup_database()
        st.sidebar.success(msg)
        st.toast("💾 Backup completed", icon="💽")
