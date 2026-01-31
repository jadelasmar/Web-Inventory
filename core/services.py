# ---------- services.py ----------
"""Database access and utility functions used by the Streamlit app."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Iterable, Optional, Union

import pandas as pd
import streamlit as st

try:
    import psycopg2
    import psycopg2.extensions
except ImportError:
    psycopg2 = None
try:
    import sqlalchemy
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
except ImportError:
    sqlalchemy = None
    create_engine = None
    URL = None

logger = logging.getLogger(__name__)

# Type alias for database connections
DBConnection = Union[sqlite3.Connection, 'psycopg2.extensions.connection']


def is_postgres(conn: DBConnection) -> bool:
    """Check if connection is PostgreSQL."""
    return psycopg2 is not None and isinstance(conn, psycopg2.extensions.connection)


def _placeholder(conn: DBConnection) -> str:
    return "%s" if is_postgres(conn) else "?"


def _placeholders(conn: DBConnection, count: int) -> str:
    return ", ".join([_placeholder(conn)] * count)


def _get_sqlalchemy_engine():
    if sqlalchemy is None or create_engine is None or URL is None:
        return None
    if not hasattr(st, "secrets") or "postgres" not in st.secrets:
        return None
    cache_key = "_sqlalchemy_engine"
    engine = st.session_state.get(cache_key)
    if engine is not None:
        return engine
    pg = st.secrets["postgres"]
    try:
        url = URL.create(
            "postgresql+psycopg2",
            username=pg.get("user"),
            password=pg.get("password"),
            host=pg.get("host"),
            port=int(pg.get("port", 5432)),
            database=pg.get("database"),
            query={"sslmode": "require"},
        )
    except Exception:
        return None
    engine = create_engine(url, pool_pre_ping=True)
    st.session_state[cache_key] = engine
    return engine


def _read_sql(conn: DBConnection, query: str, params: Optional[Iterable] = None) -> pd.DataFrame:
    if is_postgres(conn):
        engine = _get_sqlalchemy_engine()
        if engine is not None:
            return pd.read_sql(query, engine, params=params or None)
    return pd.read_sql(query, conn, params=params or None)


def get_product_movement_summary(conn: DBConnection, product_name: str) -> dict:
    """Return movement counts and initial stock info for a product."""
    placeholder = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM movements WHERE product_name={placeholder}",
            (product_name,),
        )
        total_count = int(cur.fetchone()[0] or 0)
        cur.execute(
            f"""
            SELECT id, quantity, price, supplier_customer, notes, movement_date
            FROM movements
            WHERE product_name={placeholder} AND movement_type='INITIAL STOCK'
            ORDER BY id DESC
            LIMIT 1
            """,
            (product_name,),
        )
        row = cur.fetchone()
        if row:
            return {
                "total_count": total_count,
                "initial_stock_id": row[0],
                "initial_stock_qty": row[1],
                "initial_stock_price": row[2],
                "initial_stock_party": row[3],
                "initial_stock_notes": row[4],
                "initial_stock_date": row[5],
            }
        return {"total_count": total_count, "initial_stock_id": None}
    except Exception:
        return {"total_count": 0, "initial_stock_id": None}


def upsert_initial_stock(
    conn: DBConnection,
    product_name: str,
    quantity: int,
    price: Optional[Union[int, float, str]],
    supplier_customer: str,
    notes: str,
    movement_date,
    movement_id: Optional[int] = None,
) -> None:
    """Insert or update INITIAL STOCK and set product stock to quantity."""
    placeholder = _placeholder(conn)
    cur = conn.cursor()
    if hasattr(movement_date, "isoformat"):
        movement_date = movement_date.isoformat()
    price_db = None if price in (None, "", "N/A") else float(price)
    try:
        cur.execute(
            f"SELECT category, COALESCE(isactive,1) FROM products WHERE name={placeholder}",
            (product_name,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Product not found: {product_name}")
        category, isactive = row[0], int(row[1] or 1)
        if isactive == 0:
            raise ValueError(f"Product is inactive: {product_name}")

        if movement_id:
            cur.execute(
                f"""
                UPDATE movements
                SET quantity={placeholder}, price={placeholder},
                    supplier_customer={placeholder}, notes={placeholder},
                    movement_date={placeholder}
                WHERE id={placeholder}
                """,
                (
                    int(quantity),
                    price_db,
                    supplier_customer,
                    notes,
                    movement_date,
                    int(movement_id),
                ),
            )
        else:
            placeholders_list = _placeholders(conn, 8)
            cur.execute(
                f"""
                INSERT INTO movements (product_name, product_category,
                                     movement_type, quantity, price, supplier_customer,
                                     notes, movement_date)
                VALUES ({placeholders_list})
                """,
                (
                    product_name,
                    category or "",
                    "INITIAL STOCK",
                    int(quantity),
                    price_db,
                    supplier_customer,
                    notes,
                    movement_date,
                ),
            )

        cur.execute(
            f"UPDATE products SET current_stock={placeholder} WHERE name={placeholder}",
            (int(quantity), product_name),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        st.session_state["products_cache_version"] = st.session_state.get(
            "products_cache_version", 0
        ) + 1
        st.session_state["movements_cache_version"] = st.session_state.get(
            "movements_cache_version", 0
        ) + 1
        st.cache_data.clear()


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
    # Normalize usernames to lowercase for consistency
    try:
        cur.execute("UPDATE users SET username = LOWER(username) WHERE username IS NOT NULL")
    except Exception:
        pass

    # Parties table for suppliers/customers
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS parties (
            id {id_type},
            name TEXT UNIQUE NOT NULL,
            party_type TEXT DEFAULT 'Other',
            isactive INTEGER DEFAULT 1,
            created_at TEXT
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

    # Schema migrations: ensure parties columns exist
    try:
        if is_pg:
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='parties' AND column_name='party_type'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN party_type TEXT DEFAULT 'Other'"
                )
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='parties' AND column_name='isactive'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN isactive INTEGER DEFAULT 1"
                )
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='parties' AND column_name='created_at'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN created_at TEXT"
                )
        else:
            cur.execute("PRAGMA table_info(parties)")
            cols = [r[1] for r in cur.fetchall()]
            if "party_type" not in cols:
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN party_type TEXT DEFAULT 'Other'"
                )
            if "isactive" not in cols:
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN isactive INTEGER DEFAULT 1"
                )
            if "created_at" not in cols:
                cur.execute(
                    "ALTER TABLE parties ADD COLUMN created_at TEXT"
                )
    except Exception:
        pass

    # Normalize party types to title case and drop legacy "both"
    try:
        if is_pg:
            cur.execute("UPDATE parties SET party_type='Supplier' WHERE LOWER(party_type)='supplier'")
            cur.execute("UPDATE parties SET party_type='Customer' WHERE LOWER(party_type)='customer'")
            cur.execute("UPDATE parties SET party_type='Other' WHERE LOWER(party_type) IN ('other','both') OR party_type IS NULL")
        else:
            cur.execute("UPDATE parties SET party_type='Supplier' WHERE LOWER(party_type)='supplier'")
            cur.execute("UPDATE parties SET party_type='Customer' WHERE LOWER(party_type)='customer'")
            cur.execute("UPDATE parties SET party_type='Other' WHERE LOWER(party_type) IN ('other','both') OR party_type IS NULL")
    except Exception:
        pass
    
    conn.commit()


def add_product(conn: DBConnection, data: tuple) -> None:
    """Insert a new product into the products table."""
    name = data[0]
    cur = conn.cursor()
    
    # Use parameterized query appropriate for the database
    placeholder = _placeholder(conn)
    cur.execute(
        f"SELECT name FROM products WHERE LOWER(name) = {placeholder}",
        (name.lower(),)
    )
    if cur.fetchone():
        error_class = psycopg2.IntegrityError if is_postgres(conn) else sqlite3.IntegrityError
        raise error_class("Duplicate product name (case-insensitive)")
    
    placeholders = _placeholders(conn, len(data))
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
    placeholder = _placeholder(conn)
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
    placeholder = _placeholder(conn)
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
    placeholder = _placeholder(conn)
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
    placeholder = _placeholder(conn)
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
    placeholder = _placeholder(conn)
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

    placeholder = _placeholder(conn)
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
        if movement_type == "PURCHASE" and supplier_customer:
            cur.execute(
                f"UPDATE products SET supplier={placeholder} WHERE name={placeholder}",
                (supplier_customer, product_name),
            )

        placeholders_list = _placeholders(conn, 8)
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
                return _read_sql(conn, query)

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
                # Older DB without isactive -- return all rows (can't filter)
                query = "SELECT * FROM products"

            return _read_sql(conn, query)
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
                # movement_date is stored as TEXT; cast to date for reliable comparison
                query += f" AND movement_date::date >= CURRENT_DATE - INTERVAL '{int(days)} days'"
            else:
                query += f" AND movement_date >= date('now','-{int(days)} days')"
        if types_tuple:
            placeholder = _placeholder(conn)
            placeholders = ",".join([placeholder] * len(types_tuple))
            query += f" AND movement_type IN ({placeholders})"
            params.extend(types_tuple)
        try:
            return _read_sql(conn, query, params=params)
        except Exception as e:
            logger.exception("Failed to read movements: %s", e)
            return pd.DataFrame()
    
    # Convert types to tuple for hashability in cache
    types_tuple = tuple(types) if types else None
    cache_version = st.session_state.get("movements_cache_version", 0)
    cache_key = f"movements_{days}_{types_tuple}_{cache_version}"
    return _fetch_movements(cache_key, days, types_tuple)


def get_latest_purchase_parties(conn: DBConnection) -> dict:
    """Return a map of product_name -> latest purchase party."""
    movements_df = get_movements(conn, days=None, types=["PURCHASE"])
    if movements_df.empty or "product_name" not in movements_df.columns:
        return {}
    sort_cols = ["movement_date"]
    if "id" in movements_df.columns:
        sort_cols.append("id")
    latest = movements_df.sort_values(sort_cols).drop_duplicates(
        "product_name", keep="last"
    )
    if "supplier_customer" not in latest.columns:
        return {}
    return latest.set_index("product_name")["supplier_customer"].dropna().to_dict()


def get_parties(conn: DBConnection, include_inactive: bool = False) -> pd.DataFrame:
    """Return parties list as DataFrame."""
    try:
        _ensure_parties_table(conn)
        if include_inactive:
            return _read_sql(conn, "SELECT * FROM parties")
        return _read_sql(conn, "SELECT * FROM parties WHERE isactive=1")
    except Exception:
        return pd.DataFrame()


def _merge_party_type(existing: str, incoming: str) -> str:
    if not existing:
        return incoming or "Other"
    if existing == incoming:
        return existing
    if existing in ("Supplier", "Customer") and incoming == "Other":
        return existing
    if incoming in ("Supplier", "Customer") and existing == "Other":
        return incoming
    # If conflicting (Supplier vs Customer), keep existing and let admin decide.
    return existing


def _normalize_party_type(value: str) -> str:
    if not value:
        return "Other"
    value = str(value).strip().lower()
    if value == "supplier":
        return "Supplier"
    if value == "customer":
        return "Customer"
    return "Other"


def upsert_party(conn: DBConnection, name: str, party_type: str = "Other") -> None:
    """Insert party if missing; merge type if exists."""
    if not name or not str(name).strip():
        return
    _ensure_parties_table(conn)
    party_name = str(name).strip()
    placeholder = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, party_type FROM parties WHERE LOWER(name) = {placeholder}",
            (party_name.lower(),),
        )
        row = cur.fetchone()
        if row:
            party_id, existing_type = row[0], row[1]
            merged_type = _merge_party_type(
                _normalize_party_type(existing_type), _normalize_party_type(party_type)
            )
            cur.execute(
                f"UPDATE parties SET party_type={placeholder}, isactive=1 WHERE id={placeholder}",
                (merged_type, party_id),
            )
        else:
            placeholders_list = _placeholders(conn, 4)
            cur.execute(
                f"""
                INSERT INTO parties (name, party_type, isactive, created_at)
                VALUES ({placeholders_list})
                """,
                (
                    party_name,
                    _normalize_party_type(party_type),
                    1,
                    datetime.now().isoformat(),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def update_party_name(conn: DBConnection, old_name: str, new_name: str) -> None:
    """Rename a party and update linked text fields in products/movements."""
    if not old_name or not new_name:
        return
    _ensure_parties_table(conn)
    old_name = str(old_name).strip()
    new_name = str(new_name).strip()
    placeholder = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id FROM parties WHERE LOWER(name)={placeholder}",
            (old_name.lower(),),
        )
        row = cur.fetchone()
        if not row:
            return
        party_id = row[0]
        # ensure new name doesn't collide
        cur.execute(
            f"SELECT id FROM parties WHERE LOWER(name)={placeholder}",
            (new_name.lower(),),
        )
        existing = cur.fetchone()
        if existing and existing[0] != party_id:
            raise ValueError("Party name already exists")

        cur.execute(
            f"UPDATE parties SET name={placeholder} WHERE id={placeholder}",
            (new_name, party_id),
        )
        cur.execute(
            f"UPDATE products SET supplier={placeholder} WHERE supplier={placeholder}",
            (new_name, old_name),
        )
        cur.execute(
            f"UPDATE movements SET supplier_customer={placeholder} WHERE supplier_customer={placeholder}",
            (new_name, old_name),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def deactivate_party(conn: DBConnection, name: str) -> None:
    """Soft-delete a party (keeps movements intact)."""
    _ensure_parties_table(conn)
    placeholder = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE parties SET isactive=0 WHERE LOWER(name)={placeholder}",
            (str(name).strip().lower(),),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _ensure_parties_table(conn: DBConnection) -> None:
    """Create parties table if missing (safe no-op for existing table)."""
    cur = conn.cursor()
    is_pg = is_postgres(conn)
    id_type = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    try:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS parties (
                id {id_type},
                name TEXT UNIQUE NOT NULL,
                party_type TEXT DEFAULT 'Other',
                isactive INTEGER DEFAULT 1,
                created_at TEXT
            )
            """
        )
        conn.commit()
    except Exception:
        conn.rollback()




def delete_movement(conn: DBConnection, movement_id: int) -> None:
    """Delete a movement record and adjust stock accordingly. Owner only."""
    placeholder = _placeholder(conn)
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
            try:
                quantity = int(quantity)
            except Exception:
                quantity = 0
            movement_type = movement_type or ""

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
        return _read_sql(conn, query)
    except Exception as e:
        logger.exception("Failed to read users: %s", e)
        return pd.DataFrame()


def get_pending_users(conn: DBConnection) -> pd.DataFrame:
    """Get all pending users."""
    try:
        query = "SELECT id, username, name, role, created_at FROM users WHERE status = 'pending' ORDER BY created_at ASC"
        return _read_sql(conn, query)
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
