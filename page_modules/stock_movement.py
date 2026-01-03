"""Stock movement recording page."""
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from constants import MOVEMENT_TYPES
from services import get_products, record_movement

# Lebanon timezone
LEBANON_TZ = ZoneInfo("Asia/Beirut")


def render(conn):
    """Render the stock movement page."""
    if not st.session_state.admin_mode:
        st.warning("🔒 Admin only")
        return
    
    # Check if movement was just recorded and show toast
    if st.session_state.get("movement_recorded_success"):
        movement_msg = st.session_state.get("movement_recorded_msg", "Movement recorded")
        st.toast(movement_msg, icon="📦")
        del st.session_state["movement_recorded_success"]
        del st.session_state["movement_recorded_msg"]
    
    st.header("📦 Record Stock Movement")
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
        valid_qty = qty_val > 0
    except ValueError:
        valid_qty = False

    # Client-side validation: if this is a SALE, ensure quantity does not
    # exceed available stock and surface a helpful message.
    insufficient_stock = False
    if valid_qty and mtype == "SALE":
        try:
            available = int(row.get("current_stock") or 0)
        except Exception:
            available = 0
        if qty_val > available:
            insufficient_stock = True

    # Other fields persisted per product

    price_key = f"move_price_{selected_product}"
    price_disabled = mtype in ("ADJUSTMENT", "REPLACEMENT")
    if price_key not in st.session_state or price_disabled:
        st.session_state[price_key] = 0.0 if not price_disabled else 0.0
    price = st.number_input(
        "Price", min_value=0.0, key=price_key, disabled=price_disabled
    )
    # For ADJUSTMENT/REPLACEMENT, treat price as 'NA' in movement log
    price_to_log = price if not price_disabled else "N/A"

    party_key = f"move_party_{selected_product}"
    # Auto-fill supplier if movement type is PURCHASE and not already set
    if mtype == "PURCHASE" and not st.session_state.get(party_key):
        st.session_state[party_key] = row.get("supplier", "")
    party = st.text_input("Supplier / Customer", key=party_key)

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

    btn_disabled = not valid_qty or insufficient_stock
    if st.button(
        "📝 Record Movement",
        disabled=btn_disabled,
    ):
        try:
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
            st.toast(f"❌ {e}", icon="⚠️")
        else:
            # Set flag to show toast after rerun
            msg = f"📦 {mtype} of {qty_val} units for {row['name']} recorded"
            st.session_state["movement_recorded_success"] = True
            st.session_state["movement_recorded_msg"] = msg
            # set flag to clear quantity and rerun
            st.session_state[f"clear_{qty_key}"] = True
            st.rerun()
    # Show client-side error messaging next to the form controls
    if insufficient_stock:
        st.error(f"Insufficient stock: only {row.get('current_stock', 0)} available.")
