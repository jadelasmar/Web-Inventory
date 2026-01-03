# ---------- db_init.py ----------
"""Create and return a sqlite3 connection. Schema creation is delegated
to `services.init_db(conn)` to avoid duplicated table definitions.
"""
import sqlite3

from services import init_db as init_schema


def init_db():
    conn = sqlite3.connect("bimpos_inventory.db", check_same_thread=False)
    # Delegate schema creation to services.init_db to keep a single source
    # of truth for table definitions. `services.init_db` is safe to run
    # on an existing database.
    init_schema(conn)
    return conn
