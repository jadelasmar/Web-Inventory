# ---------- db_init.py ----------
"""Create and return a local SQLite connection.
Schema creation is delegated to `services.init_db(conn)` to avoid
duplicated table definitions.
"""
import logging
import sqlite3

import streamlit as st

from core.services import init_db as init_schema

logger = logging.getLogger(__name__)


def init_db():
    """Initialize local SQLite connection.
    Connection pooling is handled by caching in app.py.
    """
    try:
        conn = _connect_sqlite()
        st.session_state["db_backend"] = "sqlite"
    except Exception:
        logger.exception("Database initialization failed")
        conn = _connect_sqlite()
        st.session_state["db_backend"] = "sqlite"
    
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

