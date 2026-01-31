"""Simple authentication module without external dependencies."""
import logging
import streamlit as st
import hashlib
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LEBANON_TZ = ZoneInfo("Asia/Beirut")
SESSION_FILE = ".streamlit/user_session.json"
SESSION_DURATION_DAYS = 30  # Stay logged in for 30 days (when Remember Me is off)

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def save_session(username: str, name: str, role: str, remember: bool = False):
    """Save user session to file."""
    try:
        os.makedirs(".streamlit", exist_ok=True)
        session_data = {
            'username': username,
            'name': name,
            'role': role,
            'remember': bool(remember),
            'expires': None if remember else (
                datetime.now(LEBANON_TZ) + timedelta(days=SESSION_DURATION_DAYS)
            ).isoformat(),
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)
    except Exception:
        pass


def load_session():
    """Load user session from file if valid.
    Returns: (username, name, role) or (None, None, None)
    """
    try:
        if not os.path.exists(SESSION_FILE):
            return None, None, None
        
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
        
        # Check if session has expired (skip if remember is enabled)
        if session_data.get('remember'):
            return session_data['username'], session_data['name'], session_data['role']
        expires_raw = session_data.get('expires')
        if expires_raw:
            expires = datetime.fromisoformat(expires_raw)
            if datetime.now(LEBANON_TZ) > expires:
                clear_session()
                return None, None, None
        
        return session_data['username'], session_data['name'], session_data['role']
    except Exception:
        return None, None, None


def clear_session():
    """Delete session file."""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass


def get_bootstrap_users():
    """Get bootstrap owner from secrets.toml (used for initial access)."""
    try:
        if 'users' in st.secrets:
            return dict(st.secrets['users'])
    except Exception:
        pass
    return {}


def get_db_user(conn, username: str):
    """Get user from database."""
    cur = conn.cursor()
    username = (username or "").strip()
    try:
        # Check if we're using PostgreSQL or SQLite
        from core.services import is_postgres
        if is_postgres(conn):
            cur.execute("SELECT username, password_hash, name, role, status FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
        else:
            cur.execute("SELECT username, password_hash, name, role, status FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        
        row = cur.fetchone()
        if row:
            return {
                'username': row[0],
                'password_hash': row[1],
                'name': row[2],
                'role': row[3],
                'status': row[4]
            }
    except Exception:
        logger.exception("Failed to read user from database")
    return None


def verify_login(conn, username: str, password: str) -> tuple:
    """Verify login credentials from database or bootstrap users.
    Returns: (success: bool, name: str, role: str)
    """
    username = (username or "").strip()
    password_hash = hash_password(password)
    
    # First check bootstrap users from secrets.toml (for owner access)
    bootstrap_users = get_bootstrap_users()
    if username:
        for key, user in bootstrap_users.items():
            if key.lower() == username.lower():
                if password_hash == user['password_hash']:
                    return True, user['name'], user['role']
                break
    
    # Then check database users
    user = get_db_user(conn, username)
    if user:
        # Only allow approved users to login
        if user['status'] != 'approved':
            return False, None, None
        
        if password_hash == user['password_hash']:
            return True, user['name'], user['role']
    
    return False, None, None


def signup_user(conn, username: str, password: str, name: str) -> tuple:
    """Create new pending user account.
    Returns: (success: bool, message: str)
    """
    username = (username or "").strip()
    if not username or not password or not name:
        return False, "All fields are required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    # Check if username exists in bootstrap users
    bootstrap_users = get_bootstrap_users()
    for key in bootstrap_users.keys():
        if key.lower() == username.lower():
            return False, "Username already exists"
    
    # Check if username exists in database
    if get_db_user(conn, username):
        return False, "Username already exists"
    
    # Create new pending user
    password_hash = hash_password(password)
    created_at = datetime.now(LEBANON_TZ).isoformat()
    
    cur = conn.cursor()
    try:
        from core.services import is_postgres
        if is_postgres(conn):
            cur.execute(
                "INSERT INTO users (username, password_hash, name, role, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (username.lower(), password_hash, name, 'viewer', 'pending', created_at)
            )
        else:
            cur.execute(
                "INSERT INTO users (username, password_hash, name, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username.lower(), password_hash, name, 'viewer', 'pending', created_at)
            )
        conn.commit()
        return True, "Account created! Waiting for admin approval."
    except Exception as e:
        conn.rollback()
        return False, f"Error creating account: {str(e)}"


def login_form(conn):
    """Display login and signup forms."""
    # Initialize show_signup state
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False
    
    if not st.session_state.show_signup:
        # Show Login Form
        st.markdown("### \U0001F510 Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember me on this device", value=True)
            submit = st.form_submit_button("Login", width="stretch")
            
            if submit:
                if username and password:
                    success, name, role = verify_login(conn, username, password)
                    
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.name = name
                        st.session_state.role = role
                        st.session_state.admin_mode = (role in ['admin', 'owner'])
                        
                        # Save session for auto-login
                        save_session(username, name, role, remember=remember_me)
                        
                        st.rerun()
                    else:
                        st.error("\u274C Invalid username or password")
                else:
                    st.warning("\u26A0\ufe0f Please enter both username and password")
        
        # Link to signup
        if st.button("\U0001F4DD Don't have an account? Sign up here"):
            st.session_state.show_signup = True
            st.rerun()
    
    else:
        # Show Signup Form
        st.markdown("### \U0001F4DD Sign Up")
        with st.form("signup_form", clear_on_submit=False):
            new_username = st.text_input("Choose Username", key="signup_username")
            new_name = st.text_input("Full Name", key="signup_name")
            new_password = st.text_input("Choose Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            signup_submit = st.form_submit_button("Sign Up", width="stretch")
            
            if signup_submit:
                if new_password != confirm_password:
                    st.error("\u274C Passwords don't match")
                else:
                    success, message = signup_user(conn, new_username, new_password, new_name)
                    if success:
                        st.success(f"\u2705 {message}")
                    else:
                        st.error(f"\u274C {message}")
        
        # Link back to login
        if st.button("\U0001F510 Already have an account? Login here"):
            st.session_state.show_signup = False
            st.rerun()


def logout():
    """Clear authentication session."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.role = None
    st.session_state.admin_mode = False
    
    # Clear saved session
    clear_session()


def require_auth():
    """Check if user is authenticated. Returns True if authenticated, False otherwise."""
    # Check if already authenticated in session state
    if st.session_state.get('authenticated', False):
        return True
    
    # Try to auto-login from saved session
    username, name, role = load_session()
    if username:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.name = name
        st.session_state.role = role
        st.session_state.admin_mode = (role in ['admin', 'owner'])
        return True
    
    return False


def get_current_user():
    """Get current user info."""
    role = st.session_state.get('role')
    return {
        'username': st.session_state.get('username'),
        'name': st.session_state.get('name'),
        'role': role,
        'is_admin': role in ['admin', 'owner'],
        'is_owner': role == 'owner'
    }
