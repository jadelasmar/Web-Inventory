# ---------- services.py ----------
"""Database access and utility functions used by the Streamlit app."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Iterable, Optional, Union
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

# Lebanon timezone
LEBANON_TZ = ZoneInfo("Asia/Beirut")

try:
    import psycopg2
    import psycopg2.extensions
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)

# Type alias for database connections
DBConnection = Union[sqlite3.Connection, 'psycopg2.extensions.connection']


def is_postgres(conn: DBConnection) -> bool:
    """Check if connection is PostgreSQL."""
    return psycopg2 is not None and isinstance(conn, psycopg2.extensions.connection)


def init_db(conn: DBConnection) -> None:
    """Create tables for a new database (safe to run on existing DB)."""
    is_pg = is_postgres(conn)
    
    # Use SERIAL for PostgreSQL, INTEGER PRIMARY KEY AUTOINCREMENT for SQLite
    id_type = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    # Use NUMERIC for PostgreSQL, REAL for SQLite
    real_type = "NUMERIC(10,2)" if is_pg else "REAL"
    
    cur = conn.cursor()
    
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS products (
            id {id_type},
            name TEXT UNIQUE NOT NULL,
            category TEXT,
            brand TEXT,
            description TEXT,
            image_url TEXT,
            current_stock INTEGER DEFAULT 0,
            cost_price {real_type} DEFAULT 0,
            sale_price {real_type} DEFAULT 0,
            supplier TEXT,
            isactive INTEGER DEFAULT 1
        )
        """
    )
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS movements (
            id {id_type},
            product_name TEXT NOT NULL,
            product_category TEXT,
            movement_type TEXT,
            quantity INTEGER,
            price {real_type},
            supplier_customer TEXT,
            notes TEXT,
            movement_date TEXT
        )
        """
    )
    
    # Users table for authentication
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            approved_by TEXT
        )
        """
    )
    
    # Add foreign key for PostgreSQL (SQLite doesn't enforce it by default)
    if is_pg:
        try:
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'fk_movements_product_name'
                    ) THEN
                        ALTER TABLE movements 
                        ADD CONSTRAINT fk_movements_product_name 
                        FOREIGN KEY(product_name) REFERENCES products(name);
                    END IF;
                END $$;
            """)
        except Exception:
            pass
    
    # Schema migrations: ensure `isactive` exists
    try:
        if is_pg:
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='products' AND column_name='isactive'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE products ADD COLUMN isactive INTEGER DEFAULT 1"
                )
            # Normalize nulls for older rows
            cur.execute("UPDATE products SET isactive=1 WHERE isactive IS NULL")
        else:
            cur.execute("PRAGMA table_info(products)")
            cols = [r[1] for r in cur.fetchall()]
            if "isactive" not in cols:
                cur.execute(
                    "ALTER TABLE products ADD COLUMN isactive INTEGER DEFAULT 1"
                )
            # Normalize nulls for older rows
            cur.execute("UPDATE products SET isactive=1 WHERE isactive IS NULL")
    except Exception:
        pass

    # Schema migrations: ensure `brand` exists
    try:
        if is_pg:
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='products' AND column_name='brand'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE products ADD COLUMN brand TEXT"
                )
        else:
            cur.execute("PRAGMA table_info(products)")
            cols = [r[1] for r in cur.fetchall()]
            if "brand" not in cols:
                cur.execute(
                    "ALTER TABLE products ADD COLUMN brand TEXT"
                )
    except Exception:
        pass
    
    conn.commit()


def add_product(conn: DBConnection, data: tuple) -> None:
    """Insert a new product into the products table."""
    name = data[0]
    cur = conn.cursor()
    
    # Use parameterized query appropriate for the database
    placeholder = "%s" if is_postgres(conn) else "?"
    cur.execute(
        f"SELECT name FROM products WHERE LOWER(name) = {placeholder}",
        (name.lower(),)
    )
    if cur.fetchone():
        error_class = psycopg2.IntegrityError if is_postgres(conn) else sqlite3.IntegrityError
        raise error_class("Duplicate product name (case-insensitive)")
    
    placeholders = ", ".join([placeholder] * len(data))
    cur.execute(
        f"""
        INSERT INTO products (name, category, brand, description, 
                            image_url, current_stock, 
                            cost_price, sale_price, supplier) 
        VALUES ({placeholders})
        """,
        data,
    )
    conn.commit()
    # Invalidate products cache so new items appear immediately
    st.session_state["products_cache_version"] = st.session_state.get(
        "products_cache_version", 0
    ) + 1


def set_product_stock(conn: DBConnection, name: str, stock: int) -> None:
    """Set the current stock for a product by name."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(
        f"UPDATE products SET current_stock={placeholder} WHERE name={placeholder}",
        (int(stock), name),
    )
    conn.commit()
    st.session_state["products_cache_version"] = st.session_state.get(
        "products_cache_version", 0
    ) + 1


def find_product_by_name(conn: DBConnection, name: str) -> Optional[dict]:
    """Find a product by name (case-insensitive). Returns dict with isactive."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT name, COALESCE(isactive, 1) FROM products WHERE LOWER(name) = {placeholder}",
            (name.lower(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {"name": row[0], "isactive": int(row[1] or 1)}
    except Exception:
        # Fallback for older schemas without isactive
        cur.execute(
            f"SELECT name FROM products WHERE LOWER(name) = {placeholder}",
            (name.lower(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {"name": row[0], "isactive": 1}


def update_product(conn: DBConnection, data: tuple) -> None:
    """Update product information (allows renaming by name)."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    try:
        (
            new_name,
            category,
            brand,
            description,
            image_url,
            cost_price,
            sale_price,
            supplier,
            old_name,
        ) = data
        if new_name and new_name.lower() != old_name.lower():
            cur.execute(
                f"SELECT name FROM products WHERE LOWER(name) = {placeholder}",
                (new_name.lower(),),
            )
            if cur.fetchone():
                error_class = psycopg2.IntegrityError if is_postgres(conn) else sqlite3.IntegrityError
                raise error_class("Duplicate product name (case-insensitive)")

        cur.execute(
            f"""
            UPDATE products SET name={placeholder}, category={placeholder},
                              brand={placeholder}, description={placeholder}, image_url={placeholder},
                              cost_price={placeholder}, sale_price={placeholder},
                              supplier={placeholder}
            WHERE name={placeholder}
            """,
            (
                new_name,
                category,
                brand,
                description,
                image_url,
                cost_price,
                sale_price,
                supplier,
                old_name,
            ),
        )
        if new_name and new_name != old_name:
            cur.execute(
                f"UPDATE movements SET product_name={placeholder} WHERE product_name={placeholder}",
                (new_name, old_name),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # Invalidate products cache
        st.session_state["products_cache_version"] = st.session_state.get(
            "products_cache_version", 0
        ) + 1


def delete_product(conn: DBConnection, name: str) -> None:
    """Soft-delete a product by marking it inactive (isactive=0). Owner only."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(f"DELETE FROM movements WHERE product_name={placeholder}", (name,))
    cur.execute(f"UPDATE products SET isactive=0 WHERE name={placeholder}", (name,))
    conn.commit()
    # Invalidate products cache
    st.session_state["products_cache_version"] = st.session_state.get(
        "products_cache_version", 0
    ) + 1
    st.session_state["movements_cache_version"] = st.session_state.get(
        "movements_cache_version", 0
    ) + 1


def restore_product(conn: DBConnection, name: str) -> None:
    """Restore a previously soft-deleted product (isactive=1). Owner only."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(f"UPDATE products SET isactive=1 WHERE name={placeholder}", (name,))
    conn.commit()
    # Invalidate products cache
    st.session_state["products_cache_version"] = st.session_state.get(
        "products_cache_version", 0
    ) + 1


def record_movement(conn: DBConnection, data: tuple) -> None:
    """Record a stock movement and update the product's current stock.

    data = (
        product_name,
        product_category,
        movement_type,
        quantity,
        price,
        supplier_customer,
        notes,
        movement_date,
    )
    """
    (
        product_name,
        _,
        movement_type,
        quantity,
        price,
        supplier_customer,
        notes,
        movement_date,
    ) = data

    # Ensure movement_date is stored as ISO string (YYYY-MM-DD) for reliable
    # date filtering in SQL (get_movements uses date comparisons).
    if hasattr(movement_date, "isoformat"):
        movement_date = movement_date.isoformat()

    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    try:
        # read current stock and active flag
        cur.execute(
            f"SELECT current_stock, COALESCE(isactive,1) FROM products WHERE name={placeholder}",
            (product_name,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Product not found: {product_name}")

        current = int(row[0] or 0)
        isactive = int(row[1] or 1)
        if isactive == 0:
            raise ValueError(f"Product is inactive: {product_name}")

        # Decrement on SALE/ISSUED, increment otherwise. Do not allow negative stock;
        # raise an error if a sale/issue exceeds current stock.
        if movement_type in ("SALE", "ISSUED"):
            if int(quantity) > current:
                raise ValueError(
                    f"Insufficient stock for {movement_type.lower()} of {product_name}: requested {int(quantity)}, available {current}"
                )
            new_stock = current - int(quantity)
        else:
            new_stock = current + int(quantity)

        # If price is 'N/A', store as None (NULL in DB)
        price_db = None if price in (None, "", "N/A") else float(price)

        cur.execute(
            f"UPDATE products SET current_stock={placeholder} WHERE name={placeholder}",
            (new_stock, product_name),
        )

        placeholders_list = ", ".join([placeholder] * 8)
        cur.execute(
            f"""
            INSERT INTO movements (product_name, product_category, 
                                 movement_type, quantity, price, supplier_customer, 
                                 notes, movement_date) 
            VALUES ({placeholders_list})
            """,
            (
                product_name,
                data[1],
                movement_type,
                int(quantity),
                price_db,
                supplier_customer,
                notes,
                movement_date,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # Invalidate products + movements cache
        st.session_state["products_cache_version"] = st.session_state.get(
            "products_cache_version", 0
        ) + 1
        st.session_state["movements_cache_version"] = st.session_state.get(
            "movements_cache_version", 0
        ) + 1
        st.cache_data.clear()


def get_products(
    conn: DBConnection, include_inactive: bool = False
) -> pd.DataFrame:
    """Return products as a pandas DataFrame. By default excludes inactive products.

    This function is tolerant of older databases that may not have the
    `isactive` column: if the column is missing it falls back to returning
    all rows.
    
    Cached for 30 seconds to improve performance on Streamlit Cloud.
    """
    @st.cache_data(ttl=30)
    def _fetch_products(cache_key: str, include_inactive: bool = False):
        try:
            if include_inactive:
                query = "SELECT * FROM products"
                return pd.read_sql(query, conn)

            # Prefer to filter by `isactive` when present; detect column existence
            cur = conn.cursor()
            try:
                if is_postgres(conn):
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='products' AND column_name='isactive'
                    """)
                    cols = [r[0] for r in cur.fetchall()]
                else:
                    cur.execute("PRAGMA table_info(products)")
                    cols = [r[1] for r in cur.fetchall()]
            except Exception:
                cols = []

            if "isactive" in cols:
                query = "SELECT * FROM products WHERE isactive=1"
            else:
                # Older DB without isactive — return all rows (can't filter)
                query = "SELECT * FROM products"

            return pd.read_sql(query, conn)
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return pd.DataFrame()
    
    # Use a cache key tied to the explicit cache version so results are reused
    # until data-changing operations increment the version.
    cache_version = st.session_state.get("products_cache_version", 0)
    cache_key = f"products_{include_inactive}_{cache_version}"
    return _fetch_products(cache_key, include_inactive)


def get_movements(
    conn: DBConnection,
    days: Optional[int] = None,
    types: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Return movements filtered by days and types.
    
    Cached for 10 seconds to improve performance.
    """
    @st.cache_data(ttl=10)
    def _fetch_movements(cache_key: str, days: Optional[int] = None, types_tuple: Optional[tuple] = None):
        query = "SELECT * FROM movements WHERE 1=1"
        params = []
        if days:
            if is_postgres(conn):
                query += f" AND movement_date >= CURRENT_DATE - INTERVAL '{int(days)} days'"
            else:
                query += f" AND movement_date >= date('now','-{int(days)} days')"
        if types_tuple:
            placeholder = "%s" if is_postgres(conn) else "?"
            placeholders = ",".join([placeholder] * len(types_tuple))
            query += f" AND movement_type IN ({placeholders})"
            params.extend(types_tuple)
        try:
            return pd.read_sql(query, conn, params=params or None)
        except Exception as e:
            logger.exception("Failed to read movements: %s", e)
            return pd.DataFrame()
    
    # Convert types to tuple for hashability in cache
    types_tuple = tuple(types) if types else None
    cache_version = st.session_state.get("movements_cache_version", 0)
    cache_key = f"movements_{days}_{types_tuple}_{cache_version}"
    return _fetch_movements(cache_key, days, types_tuple)


def delete_movement(conn: DBConnection, movement_id: int) -> None:
    """Delete a movement record and adjust stock accordingly. Owner only."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cursor = conn.cursor()

    try:
        # First, get the movement details to reverse the stock change
        cursor.execute(
            f"SELECT product_name, movement_type, quantity FROM movements WHERE id={placeholder}",
            (movement_id,),
        )
        row = cursor.fetchone()
        if row:
            product_name, movement_type, quantity = row

            # Reverse the stock adjustment:
            # PURCHASE/RECEIVED added stock, so subtract it back
            # SALE/ISSUED subtracted stock, so add it back
            # ADJUSTMENT could be +/-, reverse the sign
            if movement_type in ["PURCHASE", "RECEIVED", "INITIAL STOCK"]:
                stock_adjustment = -quantity  # Subtract what was added
            elif movement_type in ["SALE", "ISSUED"]:
                stock_adjustment = quantity  # Add back what was subtracted
            else:  # ADJUSTMENT
                stock_adjustment = -quantity  # Reverse the adjustment

            # Update product stock
            cursor.execute(
                f"UPDATE products SET current_stock = current_stock + {placeholder} WHERE name = {placeholder}",
                (stock_adjustment, product_name),
            )

        # Delete the movement
        cursor.execute(
            f"DELETE FROM movements WHERE id={placeholder}",
            (movement_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # Invalidate products + movements cache
        st.session_state["products_cache_version"] = st.session_state.get(
            "products_cache_version", 0
        ) + 1
        st.session_state["movements_cache_version"] = st.session_state.get(
            "movements_cache_version", 0
        ) + 1
        st.cache_data.clear()


# ============================================================================
# User Management Functions
# ============================================================================

def get_all_users(conn: DBConnection) -> pd.DataFrame:
    """Get all users from database."""
    try:
        query = "SELECT id, username, name, role, status, created_at, approved_by FROM users ORDER BY created_at DESC"
        return pd.read_sql(query, conn)
    except Exception as e:
        logger.exception("Failed to read users: %s", e)
        return pd.DataFrame()


def get_pending_users(conn: DBConnection) -> pd.DataFrame:
    """Get all pending users."""
    try:
        query = "SELECT id, username, name, role, created_at FROM users WHERE status = 'pending' ORDER BY created_at ASC"
        return pd.read_sql(query, conn)
    except Exception as e:
        logger.exception("Failed to read pending users: %s", e)
        return pd.DataFrame()


def approve_user(conn: DBConnection, user_id: int, approved_by: str) -> bool:
    """Approve a pending user."""
    cur = conn.cursor()
    try:
        if is_postgres(conn):
            cur.execute("UPDATE users SET status = %s, approved_by = %s WHERE id = %s", ('approved', approved_by, user_id))
        else:
            cur.execute("UPDATE users SET status = ?, approved_by = ? WHERE id = ?", ('approved', approved_by, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to approve user: %s", e)
        return False


def reject_user(conn: DBConnection, user_id: int) -> bool:
    """Reject a pending user (delete them)."""
    cur = conn.cursor()
    try:
        if is_postgres(conn):
            cur.execute("DELETE FROM users WHERE id = %s AND status = %s", (user_id, 'pending'))
        else:
            cur.execute("DELETE FROM users WHERE id = ? AND status = ?", (user_id, 'pending'))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to reject user: %s", e)
        return False


def delete_user(conn: DBConnection, user_id: int) -> bool:
    """Delete a user (owner only)."""
    cur = conn.cursor()
    try:
        if is_postgres(conn):
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        else:
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to delete user: %s", e)
        return False


def update_user_role(conn: DBConnection, user_id: int, new_role: str) -> bool:
    """Update user role (owner only)."""
    cur = conn.cursor()
    try:
        if is_postgres(conn):
            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        else:
            cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to update user role: %s", e)
        return False
