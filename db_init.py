# ---------- db_init.py ----------
"""Create and return a database connection (PostgreSQL or SQLite).
Schema creation is delegated to `services.init_db(conn)` to avoid 
duplicated table definitions.
"""
import os
import sqlite3

import streamlit as st

from services import init_db as init_schema


def init_db():
    """Initialize database connection. 
    Uses PostgreSQL in production (Streamlit Cloud) or SQLite locally.
    """
    # Check if running on Streamlit Cloud with PostgreSQL credentials
    if hasattr(st, 'secrets') and 'postgres' in st.secrets:
        import psycopg2
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            port=st.secrets["postgres"]["port"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"]
        )
        conn.autocommit = False
    else:
        # Fallback to SQLite for local development
        conn = sqlite3.connect("bimpos_inventory.db", check_same_thread=False)
    
    # Delegate schema creation to services.init_db
    init_schema(conn)
    return conn

