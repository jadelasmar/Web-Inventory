"""Reusable UI components."""
import streamlit as st
from urllib.parse import unquote_plus
import pandas as pd


def maybe_open_image_modal():
    """Open an in-page modal if URL query contains view_image param, then clear params."""
    try:
        qp = st.query_params
    except Exception:
        return
    view = qp.get("view_image", None)
    vname = qp.get("view_name", None)
    if isinstance(view, list):
        view = view[0]
    if isinstance(vname, list):
        vname = vname[0]
    if view:
        try:
            view = unquote_plus(view)
            vname = unquote_plus(vname) if vname else vname
        except Exception:
            pass
        with st.modal(vname or "Image"):
            st.image(view, use_column_width=True)
        st.query_params.clear()


def render_products_table(df, conn):
    """Render products as a table with image thumbnails."""
    if df.empty:
        st.info("No products to show")
        return

    # Standardized column names
    table_cols = [
        "name",
        "category",
        "current_stock",
        "cost_price",
        "sale_price",
        "supplier",
        "description",
        "image_url",
    ]
    display_df = df.copy()
    for c in table_cols:
        if c not in display_df.columns:
            display_df[c] = ""
    display_df = display_df[table_cols]

    # Rename columns first
    display_df = display_df.rename(
        columns={
            "name": "Name",
            "category": "Category",
            "current_stock": "Stock",
            "cost_price": "Cost",
            "sale_price": "Price",
            "supplier": "Supplier",
            "description": "Description",
            "image_url": "Image",
        }
    )

    # Fix long lines in st.markdown and st.dataframe
    st.markdown(
        "<style>td {vertical-align: middle !important;}</style>", unsafe_allow_html=True
    )

    # Configure Image column to show thumbnails
    column_config = {
        "Image": st.column_config.ImageColumn(
            "Image", help="Product image thumbnail", width="small"
        )
    }

    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config=column_config,
    )
