"""Stock alerts page for low inventory warnings."""
import streamlit as st
from constants import LOW_STOCK_THRESHOLD_DEFAULT
from services import get_products


def render(conn):
    """Render the stock alerts page."""
    st.header("⚠️ Low Stock Alerts")
    threshold = st.slider("Threshold", 0, 20, LOW_STOCK_THRESHOLD_DEFAULT)
    df = get_products(conn)
    low = df[df["current_stock"] <= threshold]
    if not low.empty:
        low = low.sort_values("name", key=lambda s: s.str.casefold())
    # Show only Name, Category, Stock, Supplier for stock alerts
    if not low.empty:
        table_cols = ["name", "category", "current_stock", "cost_price", "supplier"]
        display_df = low.copy()
        for c in table_cols:
            if c not in display_df.columns:
                display_df[c] = ""
        display_df = display_df[table_cols]
        display_df = display_df.rename(
            columns={
                "name": "Name",
                "category": "Category",
                "current_stock": "Stock",
                "cost_price": "Cost",
                "supplier": "Supplier",
            }
        )
        st.markdown(
            "<style>td {vertical-align: middle !important;}</style>",
            unsafe_allow_html=True,
        )
        st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.info(f"No products at or below the threshold ({threshold})")
