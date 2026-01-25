"""Reusable UI components."""
import streamlit as st
from urllib.parse import unquote_plus
import base64
from pathlib import Path


def image_to_base64(image_path):
    """Convert local image file to base64 data URI."""
    try:
        # Check if it's a local file (not a URL)
        if image_path and not image_path.startswith(('http://', 'https://')):
            file_path = Path(image_path)
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                b64 = base64.b64encode(image_data).decode()
                # Determine mime type from extension
                ext = file_path.suffix.lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                }
                mime = mime_types.get(ext, 'image/png')
                return f"data:{mime};base64,{b64}"
        return image_path  # Return original if URL or file doesn't exist
    except Exception:
        return image_path


def render_products_table(df):
    """Render products as a table with image thumbnails."""
    if df.empty:
        st.info("No products to show")
        return

    # Standardized column names
    table_cols = [
        "name",
        "category",
        "brand",
        "current_stock",
        "cost_price",
        "sale_price",
        "party",
        "description",
        "image_url",
    ]
    display_df = df.copy()
    for c in table_cols:
        if c not in display_df.columns:
            display_df[c] = ""
    display_df = display_df[table_cols]

    # Convert local image paths to base64 data URIs
    if 'image_url' in display_df.columns:
        display_df['image_url'] = display_df['image_url'].apply(image_to_base64)

    display_df = display_df.rename(
        columns={
            "name": "Name",
            "category": "Category",
            "brand": "Brand",
            "current_stock": "Stock",
            "cost_price": "Cost",
            "sale_price": "Price",
            "party": "Supplier",
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
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


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
            st.image(view, width=600)
        st.query_params.clear()
