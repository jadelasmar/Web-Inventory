"""User Management Page - Admin/Owner only."""
import streamlit as st
from core.services import (
    get_all_users, 
    get_pending_users, 
    approve_user, 
    reject_user, 
    delete_user, 
    update_user_role
)
from core.simple_auth import get_current_user


def render(conn):
    """Render user management page."""
    user = get_current_user()
    
    # Check permissions
    if user['role'] not in ['admin', 'owner']:
        st.error("⛔ Access denied. This page is for admins and owners only.")
        return
    
    st.title("🧑‍💻 User Management")
    
    # Pending approvals section
    st.header("🕒 Pending Approvals")
    pending_df = get_pending_users(conn)
    
    if pending_df.empty:
        st.info("No pending user requests.")
    else:
        st.write(f"**{len(pending_df)}** user(s) waiting for approval")
        
        for _, row in pending_df.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{row['name']}**")
                    st.caption(f"Username: {row['username']}")
                
                with col2:
                    st.caption(f"Requested: {row['created_at'][:10]}")
                
                with col3:
                    if st.button("✅ Approve", key=f"approve_{row['id']}"):
                        if approve_user(conn, row['id'], user['username']):
                            st.success(f"Approved {row['username']}")
                            st.rerun()
                        else:
                            st.error("Failed to approve user")
                
                with col4:
                    if st.button("❌ Reject", key=f"reject_{row['id']}"):
                        if reject_user(conn, row['id']):
                            st.success(f"Rejected {row['username']}")
                            st.rerun()
                        else:
                            st.error("Failed to reject user")
                
                st.divider()
    
    # Active users section
    st.header("👥 Active Users")
    all_users_df = get_all_users(conn)
    active_users = all_users_df[all_users_df['status'] == 'approved']
    
    if active_users.empty:
        st.info("No active users.")
    else:
        for _, row in active_users.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    role_emoji = "👑" if row['role'] == "owner" else "🔑" if row['role'] == "admin" else "👁️"
                    st.write(f"{role_emoji} **{row['name']}**")
                    st.caption(f"@{row['username']}")
                
                with col2:
                    st.caption(f"Role: {row['role'].title()}")
                    if row.get('approved_by'):
                        st.caption(f"Approved by: {row['approved_by']}")
                
                with col3:
                    # Owner can change roles, admins cannot
                    if user['is_owner'] and row['username'] != user['username']:
                        new_role = st.selectbox(
                            "Change role",
                            ['viewer', 'admin'],
                            index=0 if row['role'] == 'viewer' else 1,
                            key=f"role_{row['id']}"
                        )
                        if new_role != row['role']:
                            if st.button("💾 Save", key=f"save_role_{row['id']}"):
                                if update_user_role(conn, row['id'], new_role):
                                    st.success(f"Updated {row['username']} to {new_role}")
                                    st.rerun()
                                else:
                                    st.error("Failed to update role")
                
                with col4:
                    # Only owner can delete users
                    if user['is_owner'] and row['username'] != user['username']:
                        if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                            if delete_user(conn, row['id']):
                                st.success(f"Deleted {row['username']}")
                                st.rerun()
                            else:
                                st.error("Failed to delete user")
                    elif row['username'] == user['username']:
                        st.caption("(You)")
                
                st.divider()
    
    # Statistics
    st.header("📊 Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", len(all_users_df))
    with col2:
        st.metric("Active Users", len(active_users))
    with col3:
        st.metric("Pending", len(pending_df))
