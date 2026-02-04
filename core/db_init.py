# ---------- db_init.py ----------
"""Create and return a database connection (PostgreSQL or SQLite).
Schema creation is delegated to `services.init_db(conn)` to avoid
duplicated table definitions.
"""
import logging
import sqlite3

import streamlit as st

from core.services import init_db as init_schema

logger = logging.getLogger(__name__)


def init_db():
    """Initialize database connection. 
    Uses PostgreSQL in production (Streamlit Cloud) or SQLite locally.
    Connection pooling is handled by caching in app.py.
    """
    # Check if running on Streamlit Cloud with PostgreSQL credentials
    try:
        if hasattr(st, 'secrets') and 'postgres' in st.secrets:
            import psycopg2
            
            try:
                # Connect to PostgreSQL (Supabase requires SSL)
                # Use parameter format to handle special characters in password
                conn = psycopg2.connect(
                    host=st.secrets["postgres"]["host"],
                    port=int(st.secrets["postgres"]["port"]),
                    database=st.secrets["postgres"]["database"],
                    user=st.secrets["postgres"]["user"],
                    password=st.secrets["postgres"]["password"],
                    sslmode='require',
                    connect_timeout=10,
                    # Performance optimizations for cloud deployment
                    options='-c statement_timeout=30000'  # 30 second query timeout
                )
                conn.autocommit = False
            except Exception as e:
                logger.exception('PostgreSQL connection failed')
                st.error(f"\u26A0\ufe0f PostgreSQL connection failed: {str(e)}")
                st.warning("\U0001F4DD Check: 1) Supabase project is ACTIVE (not paused), 2) Secrets are correct, 3) Database allows connections")
                # Do not fall back to SQLite when PostgreSQL secrets are provided.
                st.stop()
        else:
            # Fallback to SQLite for local development
            conn = _connect_sqlite()
    except Exception:
        logger.exception('Database initialization fallback to SQLite')
        # If secrets file doesn't exist or any other error, use SQLite
        conn = _connect_sqlite()
    
    # Delegate schema creation to services.init_db
    init_schema(conn)
    return conn


def _connect_sqlite() -> sqlite3.Connection:
    """Create local SQLite connection (ensures data dir exists)."""
    try:
        import os
        os.makedirs("data", exist_ok=True)
    except Exception:
        pass
    return sqlite3.connect("data/bimpos_inventory.db", check_same_thread=False)

