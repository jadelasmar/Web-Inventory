"""Stock alerts page for low inventory warnings."""
import streamlit as st
from core.constants import LOW_STOCK_THRESHOLD_DEFAULT
from core.services import get_products, get_latest_purchase_parties


def render(conn):
    """Render the stock alerts page."""
    st.header("\U0001F6A8 Low Stock Alerts")
    threshold = st.slider("Threshold", 0, 20, LOW_STOCK_THRESHOLD_DEFAULT)
    df = get_products(conn)
    if df.empty:
        st.info("No products available")
        return
    party_map = get_latest_purchase_parties(conn)
    df = df.copy()
    df["party"] = df["name"].map(party_map).fillna("")
    if "current_stock" not in df.columns:
        st.info("No stock data available")
        return
    low = df[df["current_stock"] <= threshold]
    if not low.empty:
        low = low.sort_values("name", key=lambda s: s.str.casefold())
    # Show only Name, Category, Brand, Stock, Party for stock alerts
    if not low.empty:
        table_cols = ["name", "category", "brand", "current_stock", "cost_price", "party"]
        display_df = low.copy()
        for c in table_cols:
            if c not in display_df.columns:
                display_df[c] = ""
        display_df = display_df[table_cols]
        display_df = display_df.rename(
            columns={
                "name": "Name",
                "category": "Category",
                "brand": "Brand",
                "current_stock": "Stock",
                "cost_price": "Cost",
                "party": "Party",
            }
        )
        st.markdown(
            "<style>td {vertical-align: middle !important;}</style>",
            unsafe_allow_html=True,
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No products at or below the threshold ({threshold})")
