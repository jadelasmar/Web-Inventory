"""Stock movement recording page."""
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from core.constants import MOVEMENT_TYPES
from core.services import (
    get_products,
    get_movements,
    record_movement,
    get_product_movement_summary,
    upsert_initial_stock,
)

# Lebanon timezone
LEBANON_TZ = ZoneInfo("Asia/Beirut")


def _coerce_date(value):
    if not value:
        return None
    if hasattr(value, "date"):
        return value.date()
    if hasattr(value, "isoformat"):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def render(conn):
    """Render the stock movement page."""
    if not st.session_state.admin_mode:
        st.warning("\U0001F512 Admin only")
        return

    if st.session_state.pop("reset_movement_form", False):
        last_product = st.session_state.pop("reset_movement_product", None)
        if last_product:
            st.session_state[f"move_notes_{last_product}"] = ""
            st.session_state[f"move_date_{last_product}"] = datetime.now(LEBANON_TZ).date()
            st.session_state[f"move_price_{last_product}"] = 0.0
            st.session_state[f"move_party_{last_product}"] = ""
            st.session_state.pop(f"move_party_{last_product}_choice", None)
            st.session_state[f"move_type_{last_product}"] = "PURCHASE"
            st.session_state.pop(f"_prev_move_type_{last_product}", None)
            st.session_state[f"qty_{last_product}"] = ""
            st.session_state.pop(f"clear_qty_{last_product}", None)
        st.session_state.pop("move_selected", None)
    
    # Check if movement was just recorded and show toast
    if st.session_state.get("movement_recorded_success"):
        movement_msg = st.session_state.get("movement_recorded_msg", "Movement recorded")
        st.toast(movement_msg, icon="\U0001F4E6")
        del st.session_state["movement_recorded_success"]
        del st.session_state["movement_recorded_msg"]
        st.session_state.pop("movement_busy", None)
    
    st.header("\U0001F4E6 Record Stock Movement")
    df = get_products(conn)
    if df.empty:
        st.info("No products available")
        return

    # Sort products alphabetically for predictable selection (case-insensitive)
    df = df.sort_values("name", key=lambda s: s.str.casefold())

    # Persist selected product across navigation
    selected_product = st.selectbox(
        "Product",
        df["name"],
        key="move_selected",
    )
    row = df[df["name"] == selected_product].iloc[0]

    movement_summary = get_product_movement_summary(conn, selected_product)
    total_movements = movement_summary.get("total_count", 0)
    initial_id = movement_summary.get("initial_stock_id")
    has_only_initial = total_movements == 1 and initial_id is not None
    allow_initial = total_movements == 0 or has_only_initial

    initial_key = f"initial_stock_{selected_product}"
    if initial_key not in st.session_state:
        st.session_state[initial_key] = False
    if not allow_initial:
        st.session_state[initial_key] = False

    initial_checked = st.checkbox(
        "Record as initial stock",
        key=initial_key,
        disabled=not allow_initial,
        help="Only allowed before other movements exist. If initial stock is the only movement, you can edit it.",
    )
    if not allow_initial:
        st.caption("Initial stock is locked once other movements exist.")

    if initial_checked:
        st.text_input("Movement Type", value="INITIAL STOCK", disabled=True)
        mtype = "INITIAL STOCK"
        if has_only_initial:
            initial_qty = movement_summary.get("initial_stock_qty")
            initial_price = movement_summary.get("initial_stock_price")
            initial_party = movement_summary.get("initial_stock_party") or ""
            initial_notes = movement_summary.get("initial_stock_notes") or ""
            initial_date = _coerce_date(movement_summary.get("initial_stock_date"))
            qty_key = f"qty_{selected_product}"
            price_key = f"move_price_{selected_product}"
            party_key = f"move_party_{selected_product}"
            notes_key = f"move_notes_{selected_product}"
            date_key = f"move_date_{selected_product}"
            if qty_key in st.session_state and not st.session_state[qty_key] and initial_qty is not None:
                st.session_state[qty_key] = str(int(initial_qty))
            if price_key in st.session_state and initial_price is not None:
                st.session_state[price_key] = float(initial_price)
            if party_key in st.session_state and not st.session_state[party_key]:
                st.session_state[party_key] = initial_party
            if notes_key in st.session_state and not st.session_state[notes_key]:
                st.session_state[notes_key] = initial_notes
            if date_key in st.session_state and initial_date is not None:
                st.session_state[date_key] = initial_date
    else:
        # Movement type is persisted per product (sorted for consistency)
        move_types_sorted = sorted(MOVEMENT_TYPES, key=str.casefold)
        default_mtype = (
            "PURCHASE" if "PURCHASE" in move_types_sorted else move_types_sorted[0]
        )
        mtype_key = f"move_type_{selected_product}"
        if mtype_key not in st.session_state:
            st.session_state[mtype_key] = default_mtype
        prev_mtype = st.session_state.get(f"_prev_{mtype_key}")
        mtype = st.selectbox(
            "Movement Type",
            move_types_sorted,
            key=mtype_key,
        )
        # Detect movement type change
        if prev_mtype != mtype:
            st.session_state[f"_prev_{mtype_key}"] = mtype
            # If changed from PURCHASE to other, clear supplier
            party_key = f"move_party_{selected_product}"
            if prev_mtype == "PURCHASE" and mtype != "PURCHASE":
                st.session_state[party_key] = ""
            # If changed to PURCHASE, auto-fill supplier from product
            elif mtype == "PURCHASE":
                st.session_state[party_key] = row.get("supplier", "")

    # Quantity (persistent per product)
    qty_key = f"qty_{selected_product}"
    clear_flag = f"clear_{qty_key}"
    if st.session_state.get(clear_flag):
        st.session_state[qty_key] = ""
        del st.session_state[clear_flag]
    if qty_key not in st.session_state:
        st.session_state[qty_key] = ""
    qty_input = st.text_input("Quantity", key=qty_key)
    try:
        qty_val = int(qty_input)
        if initial_checked:
            valid_qty = qty_val > 0
        elif mtype == "ADJUSTMENT":
            valid_qty = qty_val != 0
        else:
            valid_qty = qty_val > 0
    except ValueError:
        valid_qty = False

    # Client-side validation: if this is a SALE/ISSUED, ensure quantity does not
    # exceed available stock and surface a helpful message.
    insufficient_stock = False
    if valid_qty and mtype in ("SALE", "ISSUED"):
        try:
            available = int(row.get("current_stock") or 0)
        except Exception:
            available = 0
        if qty_val > available:
            insufficient_stock = True

    # Other fields persisted per product

    price_key = f"move_price_{selected_product}"
    price_disabled = mtype == "ADJUSTMENT"
    if price_key not in st.session_state or price_disabled:
        st.session_state[price_key] = 0.0 if not price_disabled else 0.0
    price = st.number_input(
        "Price", min_value=0.0, key=price_key, disabled=price_disabled
    )
    # For ADJUSTMENT, treat price as 'NA' in movement log
    price_to_log = price if not price_disabled else "N/A"

    # Party with dropdown of known parties (from products + movements)
    parties_from_products = (
        set(df["supplier"].dropna().unique())
        if not df.empty and "supplier" in df.columns
        else set()
    )
    movements_df = get_movements(conn, days=None, types=None)
    parties_from_movements = (
        set(movements_df["supplier_customer"].dropna().unique())
        if not movements_df.empty and "supplier_customer" in movements_df.columns
        else set()
    )
    existing_parties = sorted(
        {p for p in (parties_from_products | parties_from_movements) if str(p).strip()},
        key=str.casefold,
    )
    party_key = f"move_party_{selected_product}"
    last_purchase_party = ""
    if not movements_df.empty and "product_name" in movements_df.columns:
        purchase_rows = movements_df[
            (movements_df["product_name"] == selected_product)
            & (movements_df["movement_type"] == "PURCHASE")
        ]
        if not purchase_rows.empty:
            sort_cols = ["movement_date"]
            if "id" in purchase_rows.columns:
                sort_cols.append("id")
            last_purchase_party = (
                purchase_rows.sort_values(sort_cols)
                .iloc[-1]
                .get("supplier_customer", "")
            )
    
    if existing_parties:
        party_options = existing_parties + ["Add new..."]
        # Auto-fill party if movement type is PURCHASE
        if mtype == "PURCHASE" and not st.session_state.get(f"{party_key}_choice"):
            if last_purchase_party in party_options:
                st.session_state[f"{party_key}_choice"] = last_purchase_party
        
        party_choice = st.selectbox(
            "Party",
            party_options,
            key=f"{party_key}_choice",
        )
        if party_choice == "Add new...":
            party = st.text_input("Enter new party", key=party_key)
        else:
            party = party_choice
    else:
        party = st.text_input("Party", key=party_key)

    notes_key = f"move_notes_{selected_product}"
    notes = st.text_area("Notes", key=notes_key)

    date_key = f"move_date_{selected_product}"
    if date_key in st.session_state:
        date = st.date_input(
            "Date",
            key=date_key,
        )
    else:
        date = st.date_input(
            "Date",
            value=datetime.now(LEBANON_TZ).date(),
            key=date_key,
        )

    move_busy = st.session_state.get("movement_busy", False)
    btn_disabled = not valid_qty or insufficient_stock or move_busy
    if st.button(
        "\U0001F4DD Record Movement",
        disabled=btn_disabled,
    ):
        st.session_state["movement_busy"] = True
        try:
            if initial_checked:
                upsert_initial_stock(
                    conn,
                    product_name=row["name"],
                    quantity=qty_val,
                    price=price_to_log,
                    supplier_customer=party,
                    notes=notes,
                    movement_date=date,
                    movement_id=initial_id if has_only_initial else None,
                )
            else:
                record_movement(
                    conn,
                    (
                        row["name"],
                        row["category"],
                        mtype,
                        qty_val,
                        price_to_log,
                        party,
                        notes,
                        date,
                    ),
                )
        except Exception as e:
            # Surface errors to the user (e.g., insufficient stock)
            st.toast(f"\u274C {e}", icon="\u26A0\ufe0f")
        else:
            # Set flag to show toast after rerun
            if initial_checked:
                msg = (
                    f"\U0001F4E6 Initial stock for {row['name']} "
                    f"{'updated' if has_only_initial else 'recorded'}"
                )
            else:
                msg = f"\U0001F4E6 {mtype} of {qty_val} units for {row['name']} recorded"
            st.session_state["movement_recorded_success"] = True
            st.session_state["movement_recorded_msg"] = msg
            st.session_state["reset_movement_form"] = True
            st.session_state["reset_movement_product"] = selected_product
            st.session_state["movement_busy"] = False
            st.rerun()
        st.session_state["movement_busy"] = False
    # Show client-side error messaging next to the form controls
    if insufficient_stock:
        st.error(f"Insufficient stock: only {row.get('current_stock', 0)} available.")
