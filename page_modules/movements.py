"""Movement log page to view transaction history."""
import streamlit as st
from core.constants import MOVEMENT_TYPES
from core.services import get_movements


def render(conn):
    """Render the movement log page."""
    st.header("🔄 Movement Log")
    days = st.selectbox("Last", [1, 7, 30, 90, "All"])
    types = st.multiselect("Type", MOVEMENT_TYPES, default=MOVEMENT_TYPES)
    days_val = None if days == "All" else days
    df = get_movements(conn, days_val, types)
    search = st.text_input("Search by name, category, or supplier")
    if not df.empty:
        # Case-insensitive partial search across product_name, product_category, supplier_customer
        if search:
            mask = (
                df["product_name"].str.contains(search, case=False, na=False)
                | df["product_category"].str.contains(search, case=False, na=False)
                | df["supplier_customer"].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        if "product_name" in df.columns:
            df = df.sort_values("product_name", key=lambda s: s.str.casefold())

    # Standardize column names for movement log even when there are no rows,
    # so the UI shows friendly headers instead of raw DB column names.
    rename_map = {
        "product_name": "Name",
        "product_category": "Category",
        "movement_type": "Type",
        "quantity": "Quantity",
        "price": "Price",
        "supplier_customer": "Party",
        "notes": "Notes",
        "movement_date": "Date",
    }
    df = df.rename(columns=rename_map)
    # Ensure all movement columns exist
    move_cols = [
        "Name",
        "Category",
        "Type",
        "Quantity",
        "Price",
        "Party",
        "Date",
        "Notes",
    ]
    for col in move_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[move_cols]
    if df.empty:
        st.info("No movements to show")
        return
    st.markdown(
        "<style>td {vertical-align: middle !important;}</style>", unsafe_allow_html=True
    )
    st.dataframe(df, width='stretch', hide_index=True)
