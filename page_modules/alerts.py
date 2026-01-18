"""Stock alerts page for low inventory warnings."""
import streamlit as st
from core.constants import LOW_STOCK_THRESHOLD_DEFAULT
from core.services import get_products, get_movements


def render(conn):
    """Render the stock alerts page."""
    st.header("🚨 Low Stock Alerts")
    threshold = st.slider("Threshold", 0, 20, LOW_STOCK_THRESHOLD_DEFAULT)
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
