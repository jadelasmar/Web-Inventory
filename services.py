# ---------- services.py ----------
"""Database access and utility functions used by the Streamlit app."""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables for a new database (safe to run on existing DB)."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                image_url TEXT,
                current_stock INTEGER DEFAULT 0,
                cost_price REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                supplier TEXT,
                isactive INTEGER DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                product_category TEXT,
                movement_type TEXT,
                quantity INTEGER,
                price REAL,
                supplier_customer TEXT,
                notes TEXT,
                movement_date TEXT,
                FOREIGN KEY(product_name) REFERENCES products(name)
            )
            """
        )
        # Schema migrations for older databases: ensure `isactive` exists
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(products)")
            cols = [r[1] for r in cur.fetchall()]
            if "isactive" not in cols:
                # Add isactive column with default 1 (active)
                cur.execute(
                    "ALTER TABLE products ADD COLUMN isactive INTEGER DEFAULT 1"
                )
        except Exception:
            # Non-fatal: log via logger when available; keep compatibility
            pass


def add_product(conn: sqlite3.Connection, data: tuple) -> None:
    """Insert a new product into the products table."""
    import sqlite3

    import sqlite3

    name = data[0]
    cur = conn.cursor()
    cur.execute("SELECT name FROM products WHERE LOWER(name) = ?", (name.lower(),))
    if cur.fetchone():
        raise sqlite3.IntegrityError("Duplicate product name (case-insensitive)")
    with conn:
        conn.execute(
            (
                "INSERT INTO products (name, category, description, "
                "image_url, current_stock, "
                "cost_price, sale_price, supplier) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            data,
        )


def update_product(conn: sqlite3.Connection, data: tuple) -> None:
    """Update product information (by name)."""
    with conn:
        conn.execute(
            (
                "UPDATE products SET category=?, description=?, image_url=?, "
                "cost_price=?, sale_price=?, supplier=? WHERE name=?"
            ),
            data,
        )


def delete_product(conn: sqlite3.Connection, name: str) -> None:
    """Soft-delete a product by marking it inactive (isactive=0)."""
    with conn:
        conn.execute("UPDATE products SET isactive=0 WHERE name=?", (name,))


def restore_product(conn: sqlite3.Connection, name: str) -> None:
    """Restore a previously soft-deleted product (isactive=1)."""
    with conn:
        conn.execute("UPDATE products SET isactive=1 WHERE name=?", (name,))


def record_movement(conn: sqlite3.Connection, data: tuple) -> None:
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

    cur = conn.cursor()
    # read current stock and active flag
    cur.execute(
        "SELECT current_stock, COALESCE(isactive,1) FROM products WHERE name= ?",
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
    with conn:
        conn.execute(
            "UPDATE products SET current_stock=? WHERE name=?",
            (new_stock, product_name),
        )
        conn.execute(
            (
                "INSERT INTO movements (product_name, product_category, "
                "movement_type, quantity, price, supplier_customer, "
                "notes, movement_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            ),
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


def get_products(
    conn: sqlite3.Connection, include_inactive: bool = False
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
    conn: sqlite3.Connection,
    days: Optional[int] = None,
    types: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Return movements filtered by days and types."""
    query = "SELECT * FROM movements WHERE 1=1"
    if days:
        query += " AND movement_date >= " f"date('now','-{int(days)} days')"
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            backups_dir,
            f"bimpos_backup_{timestamp}.db",
        )
        shutil.copy2(src, backup_file)
        return "Backup created: " + backup_file
    except Exception as e:
        logger.exception("Backup failed: %s", e)
        return "Backup failed: " + str(e)
