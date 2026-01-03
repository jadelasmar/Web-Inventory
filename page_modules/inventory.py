"""Inventory view page."""
import streamlit as st
from services import get_products
from ui.components import maybe_open_image_modal, render_products_table


def render(conn):
    """Render the inventory page."""
    st.header("📋 Inventory")
    df = get_products(conn)
    search = st.text_input("Search by name, category, or supplier")
    if not df.empty:
        # Case-insensitive partial search across name, category, supplier
        if search:
            mask = (
                df["name"].str.contains(search, case=False, na=False)
                | df["category"].str.contains(search, case=False, na=False)
                | df["supplier"].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        df = (
            df.sort_values("name", key=lambda s: s.str.casefold())
            if "name" in df.columns
            else df
        )
    maybe_open_image_modal()
    render_products_table(df, conn)
