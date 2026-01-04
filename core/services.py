# ---------- services.py ----------
"""Database access and utility functions used by the Streamlit app."""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Iterable, Optional, Union
from zoneinfo import ZoneInfo

import pandas as pd

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
        else:
            cur.execute("PRAGMA table_info(products)")
            cols = [r[1] for r in cur.fetchall()]
            if "isactive" not in cols:
                cur.execute(
                    "ALTER TABLE products ADD COLUMN isactive INTEGER DEFAULT 1"
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
        INSERT INTO products (name, category, description, 
                            image_url, current_stock, 
                            cost_price, sale_price, supplier) 
        VALUES ({placeholders})
        """,
        data,
    )
    conn.commit()


def update_product(conn: DBConnection, data: tuple) -> None:
    """Update product information (by name)."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE products SET category={placeholder}, description={placeholder}, 
                          image_url={placeholder}, cost_price={placeholder}, 
                          sale_price={placeholder}, supplier={placeholder} 
        WHERE name={placeholder}
        """,
        data,
    )
    conn.commit()


def delete_product(conn: DBConnection, name: str) -> None:
    """Soft-delete a product by marking it inactive (isactive=0)."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(f"UPDATE products SET isactive=0 WHERE name={placeholder}", (name,))
    conn.commit()


def restore_product(conn: DBConnection, name: str) -> None:
    """Restore a previously soft-deleted product (isactive=1)."""
    placeholder = "%s" if is_postgres(conn) else "?"
    cur = conn.cursor()
    cur.execute(f"UPDATE products SET isactive=1 WHERE name={placeholder}", (name,))
    conn.commit()


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

    # Decrement on SALE, increment otherwise. Do not allow negative stock;
    # raise an error if a sale exceeds current stock.
    if movement_type == "SALE":
        if int(quantity) > current:
            raise ValueError(
                f"Insufficient stock for sale of {product_name}: requested {int(quantity)}, available {current}"
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


def get_products(
    conn: DBConnection, include_inactive: bool = False
) -> pd.DataFrame:
    """Return products as a pandas DataFrame. By default excludes inactive products.

    This function is tolerant of older databases that may not have the
    `isactive` column: if the column is missing it falls back to returning
    all rows.
    """
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
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Failed to read products: %s", e)
        return pd.DataFrame()


def get_movements(
    conn: DBConnection,
    days: Optional[int] = None,
    types: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Return movements filtered by days and types."""
    query = "SELECT * FROM movements WHERE 1=1"
    if days:
        if is_postgres(conn):
            query += f" AND movement_date >= CURRENT_DATE - INTERVAL '{int(days)} days'"
        else:
            query += f" AND movement_date >= date('now','-{int(days)} days')"
    if types:
        type_str = ",".join(f"'{t}'" for t in types)
        query += " AND movement_type IN (" + type_str + ")"
    try:
        return pd.read_sql(query, conn)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Failed to read movements: %s", e)
        return pd.DataFrame()


def backup_database(
    src: str = "bimpos_inventory.db",
    backups_dir: str = "backups",
) -> str:
    """Create a dated copy of the DB in the backups directory."""
    try:
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = datetime.now(LEBANON_TZ).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            backups_dir,
            f"bimpos_backup_{timestamp}.db",
        )
        shutil.copy2(src, backup_file)
        return "Backup created: " + backup_file
    except Exception as e:
        logger.exception("Backup failed: %s", e)
        return "Backup failed: " + str(e)
