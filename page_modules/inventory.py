"""Inventory view page."""
import streamlit as st
from core.services import get_products, get_movements
from ui.components import maybe_open_image_modal, render_products_table


def render(conn):
    """Render the inventory page."""
    st.header("🗂️ Inventory")
    df = get_products(conn)
    movements_df = get_movements(conn, days=None, types=["PURCHASE"])
    party_map = {}
    if not movements_df.empty and "product_name" in movements_df.columns:
        sort_cols = ["movement_date"]
        if "id" in movements_df.columns:
            sort_cols.append("id")
        latest = movements_df.sort_values(sort_cols).drop_duplicates(
            "product_name", keep="last"
        )
        party_map = (
            latest.set_index("product_name")["supplier_customer"].dropna().to_dict()
        )
    if not df.empty:
        df = df.copy()
        df["party"] = df["name"].map(party_map).fillna("")

    search = st.text_input("Search by name, category, brand, description, or party")
    if not df.empty:
        # Case-insensitive partial search across name, category, brand, description, party
        if search:
            mask = df["name"].str.contains(search, case=False, na=False)
            if "category" in df.columns:
                mask = mask | df["category"].str.contains(search, case=False, na=False)
            if "brand" in df.columns:
                mask = mask | df["brand"].str.contains(search, case=False, na=False)
            if "description" in df.columns:
                mask = mask | df["description"].str.contains(search, case=False, na=False)
            if "party" in df.columns:
                mask = mask | df["party"].str.contains(search, case=False, na=False)
            df = df[mask]
        df = (
            df.sort_values("name", key=lambda s: s.str.casefold())
            if "name" in df.columns
            else df
        )
    maybe_open_image_modal()
    render_products_table(df, conn)
