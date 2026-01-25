"""Inventory view page."""
import streamlit as st
from core.services import get_products, get_latest_purchase_parties
from ui.components import maybe_open_image_modal, render_products_table


def render(conn):
    """Render the inventory page."""
    st.header("\U0001F5C2\ufe0f Inventory")
    df = get_products(conn)
    party_map = get_latest_purchase_parties(conn)
    if not df.empty:
        df = df.copy()
        df["party"] = df["name"].map(party_map).fillna("")

    search = st.text_input("Search by name, category, brand, description, or party")
    if not df.empty:
        # Case-insensitive partial search across name, category, brand, description, party
        if search:
            mask = df["name"].str.contains(search, case=False, na=False, regex=False)
            if "category" in df.columns:
                mask = mask | df["category"].str.contains(search, case=False, na=False, regex=False)
            if "brand" in df.columns:
                mask = mask | df["brand"].str.contains(search, case=False, na=False, regex=False)
            if "description" in df.columns:
                mask = mask | df["description"].str.contains(search, case=False, na=False, regex=False)
            if "party" in df.columns:
                mask = mask | df["party"].str.contains(search, case=False, na=False, regex=False)
            df = df[mask]
        df = (
            df.sort_values("name", key=lambda s: s.str.casefold())
            if "name" in df.columns
            else df
        )
    maybe_open_image_modal()
    render_products_table(df)
